from skyfield.api import Topos, load
from datetime import datetime, timedelta,timezone
import csv
import os
import sys
import subprocess
import time
import pandas as pd
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import *
from Data_storage.storage_builder import save_SDR_files

from Logs.logger import setup_logger

logger=setup_logger("SDR_APP",os.path.join(LOGS_DIR,"Procces.log"))

class Pass:
    def __init__(self,aos,max,los):
        self.aos=aos
        self.max=max
        self.los=los
    def __str__(self):
        return f"AOS:{self.aos},MAX:{self.max},LOS:{self.los}"

class Satellite:
    def __init__(self,name,frequency):
        self.name=name.replace(" ","_")
        self.frequency=frequency
        self.passes=[]
        self.service_name=f"rtl_sdr@{self.name}.service"
        self.state="inactive"
        self.transition={"inactive": {"Service_started":"waiting"},"waiting":{"Listening_started":"active","Other_service_started":"blocked"}
                         ,"active":{"Stop_service":"inactive"},"blocked":{"Service_started":"blocked","listening_started":"active"}}
    def update_passes(self,passes):
        self.passes=passes
    def __str__(self):
        return f"Name:{self.name},Frequency:{self.frequency},Passes:{self.passes}"
    def transicion(self,event):
        if event in self.transition[self.state]:
            nuevo_estado=self.transition[self.state][event]
            logger.debug(f"Transición de {self.name}: {self.state} -> {nuevo_estado}")
            self.state=nuevo_estado
            self.save_to_file(SATELLITE_OUTPUT)
            self.save_to_csv(SATELLITE_STATUS)
    def save_to_file(self, filename):
        with open(filename, 'w') as file:
            # Guardar atributos básicos
            file.write(f"name:{self.name}\n")
            file.write(f"frequency:{self.frequency}\n")
            file.write(f"state:{self.state}\n")
            file.write(f"service_name:{self.service_name}\n")

            # Guardar la lista de passes
            file.write("passes:\n")
            for pass_obj in self.passes:
                file.write(f"{pass_obj.aos},{pass_obj.max},{pass_obj.los}\n")
    def save_to_csv(self, filename):

        # Leer el archivo CSV actual
        try:
            df = pd.read_csv(filename)
        except FileNotFoundError:
            df = pd.DataFrame(columns=["name", "status", "next_pass"])

        # Actualizar la información del satélite
        next_pass = self.passes[0].aos if self.passes else "No passes available"
        satellite_data = {
            "name": self.name,
            "status": self.state,
            "next_pass": next_pass
        }

        # Buscar si el satélite ya existe en el DataFrame
        if self.name in df["name"].values:
            df.loc[df["name"] == self.name, ["status", "next_pass"]] = [self.state, next_pass]
        else:
            # Crear un DataFrame temporal con los nuevos datos
            nuevo_df = pd.DataFrame([satellite_data])
            # Concatenar el DataFrame original con el nuevo
            df = pd.concat([df, nuevo_df], ignore_index=True)

        # Guardar los cambios en el archivo CSV
        df.to_csv(filename, index=False)

    @classmethod
    def load_from_file(cls, filename):
        with open(filename, 'r') as file:
            lines = file.readlines()

            # Leer atributos básicos
            name = lines[0].split(":")[1].strip()
            frequency = lines[1].split(":")[1].strip()
            state = lines[2].split(":")[1].strip()
            service_name = lines[3].split(":")[1].strip()

            # Leer passes
            passes = []
            pass_index = 5  # Comienza después de la línea "passes:"
            while pass_index < len(lines) and lines[pass_index].strip() != "transition:":
                aos, max, los = lines[pass_index].strip().split(",")
                passes.append(Pass(aos, max, los))
                pass_index += 1
            satellite=cls(name,frequency)
            satellite.state=state
            satellite.passes=passes
            satellite.service_name=service_name
            return satellite
            


meteo_station=Topos(
    get_station_latitude(),
    get_station_longitude(),
    elevation_m=get_station_altitude(),
)



def find_passes(satellite, observer, start_time, end_time):
    t, events = satellite.find_events(observer, start_time, end_time, altitude_degrees=10.0)
    passes = []
    aos, max_elevation, los = None, None, None
    for ti, event in zip(t, events):
        if event == 0:  # AOS
            aos = ti.utc_datetime()
        elif event == 1:  # MAX
            max_elevation = ti.utc_datetime()
        elif event == 2:  # LOS
            los = ti.utc_datetime()
            if aos and max_elevation and los:
                passes.append(Pass(aos, max_elevation, los))
                aos, max_elevation, los = None, None, None
    return passes


def get_satellite_info():
    url = 'http://celestrak.com/NORAD/elements/weather.txt'
    satellites = load.tle_file(url)
    logger.info("Starting recolection of satellite info")
    ts = load.timescale()
    satellites = load.tle_file(url)
    satellites_data = {
        "NOAA 15": 137.62,
        "NOAA 18": 137.9125,
        "NOAA 19": 137.1,
    }
    start_time = ts.utc(year, current_month, current_day, hour)
    end_time = ts.utc(year, current_month, current_day, hour + 6)

    # Crear una lista de objetos Satellite
    satellite_objects = []
    for satellite_name, frequency in satellites_data.items():
        # Encontrar el satélite en los datos TLE
        satellite_data = next(sat for sat in satellites if sat.name == satellite_name)
        # Calcular los pases
        satellite_passes = find_passes(satellite_data, meteo_station, start_time, end_time)
        # Crear el objeto Satellite y actualizar sus pases
        satellite_obj = Satellite(satellite_name, frequency)
        satellite_obj.update_passes(satellite_passes)
        satellite_objects.append(satellite_obj)
    satellites_not_filtered=satellite_objects
    interval=180
    satellite_objects=passes_info(satellite_objects,interval)
    local_time=datetime.now(timezone.utc)+timedelta(hours=1)
    if satellite_objects!=[]:
        for satellite in satellite_objects:
            print(f"{satellite[0].name} with {satellite[1]}")
        next_pass_time = local_time + satellite_objects[0][1]
        comando = f'echo "systemctl start rtl_sdr@{satellite_objects[0][0].name}.service" | sudo at {next_pass_time.strftime("%H:%M %Y-%m-%d")}'
        logger.info(comando)
        # try:
        #     subprocess.run(comando,shell=True)
        #     logger.info(f"SUCCESS starting rtl_sdr@{satellite_objects[0][0].name}.service")
        #     satellite_objects[0][0].transicion("Service_started")
        #     satellite_objects[0][0].save_to_file(SATELLITE_OUTPUT)
        # except subprocess.CalledProcessError as e:
        #     # Maneja errores si el comando falla
        #     print("Error al ejecutar el comando:", e.stderr)
        #     logger.error(f"ERROR at inicialization of rtl_sdr@{satellite_objects[0][0].name}.service")
    else:
        logger.info(f"NO satellites availables in the next {interval} min")
        for satellite in satellites_not_filtered:
            for passes in satellite.passes:
                logger.debug(f"{satellite.name} with {passes}")

def passes_info(satellites,interval):
    list_satellites=[]
    local_time=datetime.now(timezone.utc)+timedelta(hours=1)
    for satellite in satellites:
        if satellite.passes != []:
            for pass_ in satellite.passes:
                if datetime.now(timezone.utc) + timedelta(hours=1,minutes=interval) > pass_.aos and local_time < pass_.aos:
                    time_next_pass=pass_.aos-local_time
                    logger.info(f"Next listen procces would be in {time_next_pass}")
                    list_satellites.append((satellite,time_next_pass))

    return list_satellites

def check_conditions(service):
    conditions=True
    logger.info("Checking conditions")
    servicios=["rtl_sdr@NOAA_15.service","rtl_sdr@NOAA_18.service","rtl_sdr@NOAA_19.service"]
    for servicio in servicios:
        if servicio == service:
            servicios.remove(servicio)
            break
    for servicio in servicios:
        resultado = subprocess.run(
        ["systemctl", "status", servicio],
        capture_output=True,
        text=True)
        if "active" in resultado.stdout.split():
            logger.info(f"{servicio} is active")
            conditions=False
            return conditions
    logger.info("All services are inactive")
    return conditions
    
    

def service_running():
    logger.info("Starting service")
    satellite=Satellite.load_from_file(SATELLITE_OUTPUT)
    logger.info(f"Listen to {satellite.name} with {satellite.frequency}")
    wav_file=os.path.join(SDR_DIR,f"{satellite.name}_{hour}_{current_day}_{current_month}_{year}_audio.wav")
    png_file=os.path.join(SDR_DIR,f"{satellite.name}_{hour}_{current_day}_{current_month}_{year}_image.png")
    if check_conditions(satellite.service_name):
        try:
            comando=f"rtl_fm -f {satellite.frequency}M -s 48000 -g 50 - | sox -t raw -r 48000 -e signed -b 16 -c 1 - {wav_file}"
            logger.info(comando)
            satellite.transicion("Listening_started")
            proceso=subprocess.Popen(comando,shell=True)
            time.sleep(600)
            proceso.terminate()
            proceso.wait()
            comando2=f"systemctl stop rtl_sdr@{satellite.name}.service"
            logger.info(comando2)
            subprocess.run(comando2,shell=True)
            satellite.transicion("Stop_service")
            comando3=f"./noaa-apt {wav_file} -o {png_file}"
            subprocess.run(comando3,cwd=SDR_DIR,shell=True)
            logger.info(comando3)
            save_SDR_files(wav_file,png_file,satellite.name)
        except subprocess.CalledProcessError as e:
            print(f"Error al ejecutar el comando: {e}")
        except Exception as e:
            print(f"Error inesperado: {e}")
    else:
        logger.info("Waiting for other service to finish")
        satellite.transicion("Other_service_started")
        time.sleep(360)
        service_running()

    
if __name__ == "__main__":
    service_running()
                    

