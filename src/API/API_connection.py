import requests
import json
import time
from config import *
from datetime import timezone,timedelta
from Logs.logger import setup_logger
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
from abc import ABC, abstractmethod
from API.water_reserve_api import obtener_datos

logger=setup_logger("API_connection",os.path.join(LOGS_DIR,"Procces.log"))

RETRY_DELAY_SECONDS=10
FAILED_RESPONSE=None

class APIConnection(ABC):
    @abstractmethod
    def get_current_data(self, params):
        pass
    def request_data_from_api(self, url, params=None, file_json=None, headers=None):
        attempt = 0
        max_retries = 2
        while attempt < max_retries:
            try:
                response = requests.get(url, params=params, headers=headers)
                logger.debug(f"Url:{self.sanitize_url(response.url)}")
                response.raise_for_status()  # Lanza una excepción si hay un error HTTP
                # Parsear la respuesta JSON
                data = response.json()
                with open(file_json, "w") as file:
                    json.dump(data, file, indent=4)  # Formato legible para humanos
                return data
            except requests.exceptions.HTTPError as http_err:
                attempt += 1
                if attempt < max_retries:
                    logger.error(f"HTTPError--->{http_err},attempt={attempt}")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"HTTP error occurred: {http_err}")
                    return FAILED_RESPONSE
            except requests.exceptions.RequestException as req_err:
                attempt += 1
                if attempt < max_retries:
                    logger.error(f"RequestException--->{req_err},attempt={attempt}")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"Request error occurred: {req_err}")
                    return FAILED_RESPONSE
            except TypeError as type_err:
                attempt += 1
                if attempt < max_retries:
                    logger.error(f"TypeError--->{type_err},attempt={attempt}")
                    time.sleep(RETRY_DELAY_SECONDS)
                else:
                    logger.error(f"Type error occurred: {type_err}")
                    return FAILED_RESPONSE

    def sanitize_url(self, url):
        parts=urlsplit(url)
        sensitive_keys={"apikey","api_key","appid","auth-token","token"}
        query_params=parse_qsl(parts.query,keep_blank_values=True)
        safe_query=urlencode(
            [(key,"***" if key.lower() in sensitive_keys else value) for key,value in query_params]
        )
        return urlunsplit((parts.scheme,parts.netloc,parts.path,safe_query,parts.fragment))


class TomorrowAPIConnection(APIConnection):
    def __init__(self, logger):
        self.logger = logger
        self.name = "tomorrow_api"

    def get_current_data(self, params):
        self.logger.info(f"Getting data from {self.name}")
        url = f"https://api.tomorrow.io/v4/timelines?location={params['latitude']},{params['longitude']}&fields=precipitationIntensity,temperature,humidity,windSpeed,visibility,cloudCover,pressureSurfaceLevel,windDirection,&timesteps=30m&units=metric&apikey={params['api_key']}"
        data=self.request_data_from_api(url,file_json=TOMORROW_API_DIR)
        intervals = data["data"]["timelines"][0]["intervals"]
        # Extraer el primer intervalo (ejemplo de datos actuales)
        first_interval = intervals[0]
        precipitation = first_interval["values"].get("precipitationIntensity", "N/A")
        temperature = first_interval["values"].get("temperature", "N/A")
        wind_direction = first_interval["values"].get("windDirection", "N/A")
        wind_speed = first_interval["values"].get("windSpeed", "N/A")
        humidity = first_interval["values"].get("humidity", "N/A")
        pressure = first_interval["values"].get("pressureSurfaceLevel", "N/A")
        percent_clouds = first_interval["values"].get("cloudCover", "N/A")
        visibliity=first_interval["values"].get("visibility", "N/A")
        # Devolver solo los valores de precipitationIntensity
        return {"temp (C)": temperature,"precipitation (mm/h)": precipitation,"wind_direction(º)":wind_direction,
                "wind_speed(m/s)":wind_speed,"hum(%)":humidity,"pres(hPa)":pressure,"clouds(%)":percent_clouds,
                "visibility(m)":visibliity}

class TomorrowForecastAPIConnection(APIConnection):
    def __init__(self, logger):
        self.logger = logger
        self.name = "tomorrow_forecast_api"

    def get_current_data(self, params):
        if now.hour == 0 and  now.minute == 0:
            self.logger.info(f"Getting data from {self.name}")
            return self.get_forecast_data(params)
        else:
            return FAILED_RESPONSE
    
    def get_forecast_data(self, params):
        url=f"https://api.tomorrow.io/v4/weather/forecast?location={params['latitude']},{params['longitude']}&apikey={params['api_key']}"
        data=self.request_data_from_api(url,file_json=TOMORROW_API_FORECAST_DIR)
        dates = {
            "mañana": (now + timedelta(days=1)).date(),
            "3_dias": (now + timedelta(days=3)).date(),
            "5_dias": (now + timedelta(days=5)).date(),
        }
        dates_keys=list(dates.keys())
        daily_data = data["timelines"]["daily"]
        now_date=now.date()
        dict_forecast={"Fecha Actual":str(now_date)}
        for date in dates.items():
            if date[0]=="mañana":
                dict_forecast[f"Tmax {dates_keys[0]}"]=daily_data[1]["values"]["temperatureMax"]
                dict_forecast[f"Tmin {dates_keys[0]}"]=daily_data[1]["values"]["temperatureMin"]
                dict_forecast[f"Rain acum. {dates_keys[0]}"]=daily_data[1]["values"]["rainAccumulationSum"]
            if date[0]=="3_dias":
                dict_forecast[f"Tmax {dates_keys[1]}"]=daily_data[3]["values"]["temperatureMax"]
                dict_forecast[f"Tmin {dates_keys[1]}"]=daily_data[3]["values"]["temperatureMin"]
                dict_forecast[f"Rain acum. {dates_keys[1]}"]=daily_data[3]["values"]["rainAccumulationSum"]
            if date[0]=="5_dias":
                dict_forecast[f"Tmax {dates_keys[2]}"]=daily_data[5]["values"]["temperatureMax"]
                dict_forecast[f"Tmin {dates_keys[2]}"]=daily_data[5]["values"]["temperatureMin"]
                dict_forecast[f"Rain acum. {dates_keys[2]}"]=daily_data[5]["values"]["rainAccumulationSum"]
        return dict_forecast

class ElectricityAPIConnection(APIConnection):
    def __init__(self, logger):
        self.logger = logger
        self.name = "electricity_api"

    def get_current_data(self, params):
        self.logger.info(f"Getting data from {self.name}")
        zone = get_zone_config()
        query_params = {"zone": zone} if zone else {}
        headers={"auth-token":params["auth-token"]}
        data=self.request_data_from_api(electricity_api_url,file_json=ELECTRICITY_API_DIR,params=query_params,headers=headers)
        if not all(key in data for key in ("powerConsumptionBreakdown","powerProductionBreakdown")):
            self.logger.error("Invalid electricity API response")
            return FAILED_RESPONSE
        data_filtered={"consumption":data["powerConsumptionBreakdown"],"production":data["powerProductionBreakdown"]}
        return data_filtered

class WaterReserveAPIConnection(APIConnection):
    def __init__(self, logger):
        self.logger = logger
        self.name = "water_reserve_api"

    def get_current_data(self, params):
        if day_name=="Tuesday" and hour==16 and minute==0:
            try:
                self.logger.info(f"Getting data from {self.name}")
                data=obtener_datos(params.get("url", water_reserve_url))
                if not isinstance(data, dict) or data.get("error"):
                    self.logger.error(f"Invalid water reserve response: {data}")
                    return FAILED_RESPONSE

                embalses=data.get("embalses") or {}
                valores=embalses.get("valores") or {}
                agua_embalsada_hm3=valores.get("agua_embalsada_hm3")
                porcentaje_embalsado=valores.get("porcentaje_embalsado")

                if agua_embalsada_hm3 is None or porcentaje_embalsado is None:
                    self.logger.error("Invalid water reserve response: missing reservoir values")
                    return FAILED_RESPONSE

                data_filtered={
                    "agua_embalsada_hm3":agua_embalsada_hm3,
                    "porcentaje_embalsado":porcentaje_embalsado,
                }
                if embalses.get("provincia"):
                    data_filtered["provincia"]=embalses["provincia"]
                if embalses.get("fecha_dato"):
                    data_filtered["fecha_dato"]=embalses["fecha_dato"]
                return data_filtered
            except Exception as e:
                self.logger.error(f"Error in water_reserve_api:{e}")
                return FAILED_RESPONSE
        
        else:
            return FAILED_RESPONSE



def get_data_from_api(params):
    logger.info("Starting data retrieval from APIs")
    api_connections = [
      (TomorrowAPIConnection(logger), "current_status"),
      (TomorrowForecastAPIConnection(logger), "forecast_status"),
      (ElectricityAPIConnection(logger), "electricity_status"),
      (WaterReserveAPIConnection(logger), "water_reserve_status"),
  ]

    data = {}
    for api_connection, status_key in api_connections:
        api_params = params.get(api_connection.name, {})
        if not api_params.get("enabled", True):
            logger.info(f"{api_connection.name} is disabled. Skipping data retrieval.")
            data[status_key] = api_failure()
            continue
        try:
            api_data = api_connection.get_current_data(params[api_connection.name])
            data[status_key] = api_failure() if api_data is None else api_success(api_data)
        except Exception as e:
            logger.error(f"Error retrieving data from {api_connection.name}: {e}")
            data[status_key] = api_failure()
    logger.info("Data retrieval completed")
    return data

def is_failed_response(data):
    return data == FAILED_RESPONSE

def api_success(data):
    return {"ok":True,"data":data}

def api_failure(data=None):
    return {"ok":False,"data":FAILED_RESPONSE}
