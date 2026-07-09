from datetime import datetime, timezone
from pathlib import Path
import shutil
import pandas as pd
from Data_storage.statistics import make_statistics,make_statistics_electricity_day
import json
import os
from config import *
from Logs.logger import setup_logger
from Util.check_data import get_today_data
from API.API_connection import is_failed_response

logger=setup_logger("Storage_builder",os.path.join(LOGS_DIR,"Procces.log"))

timezone_offset=3600


def unix_to_time(unix_time):
    return datetime.fromtimestamp(unix_time + timezone_offset, tz=timezone.utc)

def create_storage(data):
    logger.info("Creating storage")
    try:
        create_storage_dataframe(data["current_status"])
    except Exception as e:
        logger.error(f"Failed to create storage dataframe: {e}")

    try:
        create_storage_forecast(data["forecast_status"])
    except Exception as e:
        logger.error(f"Failed to create storage forecast: {e}")

    try:
        create_storage_electricity(data["electricity_status"])
    except Exception as e:
        logger.error(f"Failed to create storage electricity: {e}")
        
    try:
        create_storage_water(data["water_reserve_status"])
    except Exception as e:
        logger.error(f"Failed to create storage water: {e}")

    
    if hour==23 and minute==30:
        get_today_data() # check if the data of the day is correct and fix it if not
    create_BK()


def create_storage_dataframe(data):
    # data["sunrise"]=unix_to_time(data["sunrise"])
    # data["sunset"]=unix_to_time(data["sunset"])
    data=response_data(data)
    if is_failed_response(data):
        return
    logger.info("Creating storage dataframe")
    mes=now.strftime("%B")
    dia=now.day
    hora=now.strftime("%H:%M")
    new_data={"Year":year,"Mes":mes,"Dia":dia,"Hora":hora}
    data={**new_data,**data}
    data.pop("data_time",None)
    df=pd.DataFrame([data])
    df_data=save_csv(df,HISTORICAL_WEATHER_DIR)
    #make_statistics(df_data) # for test purposes
    if now.hour == 0 and now.minute == 0: # Implica que un nuevo dia ha empezado
        logger.info("Creating statistics")
        make_statistics(df_data)


def save_csv(df,path):#CSV only one sheet allowed---->A collumn with the year is needed
    logger.info(f"Saving data in {path}")
    try:
        df.to_csv(path, mode="a", index=False, header=not os.path.exists(path))
    except FileNotFoundError:
        logger.error(f"File not found: {path}. Creating a new file.")
        df.to_csv(path, mode="a", index=False, header=True)
    print(f"Datos guardados exitosamente en '{path}'.")
    return pd.read_csv(path)


def ensure_csv_columns(path, columns):
    if not os.path.exists(path) or os.path.getsize(path) == 0:
        return

    existing_data = pd.read_csv(path)
    missing_columns = [column for column in columns if column not in existing_data.columns]
    if not missing_columns:
        return

    for column in missing_columns:
        existing_data[column] = pd.NA
    existing_data.to_csv(path, index=False)

def read_json():
    logger.info("Reading JSON")
    try:
        # Cargar datos desde el archivo JSON
        with open(CONFIG_DATA, "r") as file:
            config = json.load(file)

        check_config(config)  # Verificar la validez de la configuración
        # Construir los parámetros correctos para la API
        station_latitude = config["station"]["latitude"]
        station_longitude = config["station"]["longitude"]
        station_altitude = config["station"]["altitude"]
        station_name = config["station"]["name"]

        tomorrow_config = config["apis"]["tomorrow_api"]
        tomorrow_enabled = tomorrow_config.get("enabled", True)
        tomorrow_params = {
            "enabled": tomorrow_enabled,
            "latitude": station_latitude,
            "longitude": station_longitude,
        }
        if tomorrow_enabled:
            tomorrow_params["api_key"] = tomorrow_config["api_key"]

        electricity_config = config["apis"]["electricity_api"]
        electricity_enabled = electricity_config.get("enabled", True)
        electricity_params = {
            "enabled": electricity_enabled,
        }
        if electricity_enabled:
            electricity_params["auth-token"] = electricity_config["auth-token"]

        tomorrow_forecast_config = config["apis"]["tomorrow_forecast_api"]
        tomorrow_forecast_enabled = tomorrow_forecast_config.get("enabled", True)
        tomorrow_forecast_params = {
            "enabled": tomorrow_forecast_enabled,
            "latitude": station_latitude,
            "longitude": station_longitude,
        }
        if tomorrow_forecast_enabled:
            tomorrow_forecast_params["api_key"] = tomorrow_forecast_config["api_key"]

        water_reserve_config = config["apis"]["water_reserve_api"]
        water_reserve_enabled = water_reserve_config.get("enabled", True)
        water_reserve_params = {
            "enabled": water_reserve_enabled,
        }
        if water_reserve_enabled:
            water_reserve_params["url"] = water_reserve_config.get("url", water_reserve_url)
            if "auth-token" in water_reserve_config:
                water_reserve_params["auth-token"] = water_reserve_config["auth-token"]

        params = {
            "tomorrow_api": tomorrow_params,
            "electricity_api": electricity_params,
            "tomorrow_forecast_api": tomorrow_forecast_params,
            "water_reserve_api": water_reserve_params,
        }

        return params

    except FileNotFoundError as e:
        raise RuntimeError("Archivo de configuración no encontrado") from e
    except json.JSONDecodeError as e:
        raise RuntimeError("Archivo de configuración JSON inválido") from e

def check_config(config):
    logger.info("Checking config")
    required_keys = ["station", "apis"]
    for key in required_keys:
        if key not in config:
            raise ValueError(f"Missing required key: {key}")

    station_keys = ["latitude", "longitude", "altitude", "name"]
    for key in station_keys:
        if key not in config["station"]:
            raise ValueError(f"Missing required station key: {key}")



def get_backup_path():
    extra_config=get_extra_config()
    backup_config=extra_config.get("backup", {})
    if not backup_config.get("enabled", False):
        logger.info("Backup is disabled.")
        return None

    backup_path=backup_config.get("path")
    if not backup_path:
        logger.warning("Backup is enabled but no backup path is configured.")
        return None

    backup_path=Path(backup_path)
    if not backup_path.exists():
        logger.warning(f"Backup path does not exist: {backup_path}")
        return None

    if not backup_path.is_dir():
        logger.warning(f"Backup path is not a directory: {backup_path}")
        return None

    return backup_path


def create_BK():
    logger.info("Creating BK")
    files=os.listdir(DATA_DIR)
    files = [os.path.join(DATA_DIR, f) for f in files if os.path.isfile(os.path.join(DATA_DIR, f))]
    backup_path=get_backup_path()
    if backup_path is None:
        return
    for file in files:
        try:
            shutil.copy2(file, backup_path)
        except OSError as exc:
            logger.warning(f"Failed to copy {file} to {backup_path}: {exc}")

def save_SDR_files(wav_file,png_file,satelite):
    logger.info("Saving SDR files")
    backup_path=get_backup_path()
    if backup_path is None:
        return
    path=backup_path / satelite / str(year) / str(current_month) / str(current_day)
    logger.info(f"Saving SDR files inside of {path}")
    try:
        path.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        logger.warning(f"Failed creating SDR backup directory {path}: {exc}")
        return
    for file in (wav_file, png_file):
        try:
            shutil.move(file, path)
        except OSError as exc:
            logger.warning(f"Failed saving {file}: {exc}")

def response_data(response):
    if not response.get("ok"):
          return None
    return response["data"]


def create_storage_forecast(data):
    data=response_data(data)
    if is_failed_response(data):
        return
    logger.info("Creating storage forecast")
    df=pd.DataFrame([data])
    now=datetime.now()
    df_data=save_csv(df,HISTORICAL_WEATHER_FORECAST_DIR)

def create_storage_electricity(data):
    data=response_data(data)
    if is_failed_response(data):
        return
    logger.info("Creating storage electricity")
    data_consumption=data["consumption"]
    data_production=data["production"]
    mes=now.strftime("%B")
    dia=now.day
    hora=now.strftime("%H:%M")
    new_data={"Year":year,"Mes":mes,"Dia":dia,"Hora":hora}
    data_consumption={**new_data,**data_consumption}
    data_production={**new_data,**data_production}
    df_consumption=pd.DataFrame([data_consumption])
    df_production=pd.DataFrame([data_production])
    df_data_consumption=save_csv(df_consumption,ELECTRICITY_DIR_CONSUMPTION)
    df_data_production=save_csv(df_production,ELECTRICITY_DIR_PRODUCTION)
    if now.hour == 0 and now.minute == 0: # Implica que un nuevo dia ha empezado
        logger.info("Creating statistics electricity")
        make_statistics_electricity_day([df_data_consumption,df_data_production])

def create_storage_water(data):
    data=response_data(data)
    if is_failed_response(data):
        return
    logger.info("Creating storage water")
    mes=now.strftime("%B")
    dia=now.day
    new_data={"Year":year,"Mes":mes,"Dia":dia}
    data={**new_data,**data}
    data.pop("data_time",None)
    df=pd.DataFrame([data])
    ensure_csv_columns(WATER_RESERVE, df.columns)
    df_data=save_csv(df,WATER_RESERVE)
