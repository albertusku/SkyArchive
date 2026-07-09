from datetime import datetime
import json
import os
from functools import cache

#PATHS
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'Data_storage','Storage')
API_DIR = os.path.join(BASE_DIR, 'API')
VIS_DIR = os.path.join(BASE_DIR, 'Visualizer')
LOGS_DIR = os.path.join(BASE_DIR, 'Logs')
SDR_DIR = os.path.join(BASE_DIR,"SDR")
MODEL_DIR=os.path.join(BASE_DIR,"Models")

DEFAULT_METEO_VENV_DIR=os.path.join(BASE_DIR,"..","meteo_python")
METEO_VENV_DIR=os.environ.get("METEO_VENV_DIR", DEFAULT_METEO_VENV_DIR)
PYTHON_BIN=os.path.join(METEO_VENV_DIR,"bin","python")

DASH_DIR = os.path.join(BASE_DIR, 'Visualizer','main_pages.py')

HISTORICAL_WEATHER_DIR=os.path.join(DATA_DIR, 'Historical_weather.csv')
HISTORICAL_WEATHER_FORECAST_DIR=os.path.join(DATA_DIR, 'Historical_weather_forecast.csv')
STATISTICS_DAY_DIR=os.path.join(DATA_DIR, 'Statistics_day.csv')
STATISTICS_MONTH_DIR=os.path.join(DATA_DIR, 'Statistics_month.csv')
STATISTICS_ELECTRICITY_DAY_CONSUMPTION_DIR=os.path.join(DATA_DIR, 'Statistics_consumption.csv')
STATISTICS_ELECTRICITY_DAY_PRODUCTION_DIR=os.path.join(DATA_DIR, 'Statistics_production.csv')
ELECTRICITY_DIR_CONSUMPTION=os.path.join(DATA_DIR, 'Electricity_consumption.csv')
ELECTRICITY_DIR_PRODUCTION=os.path.join(DATA_DIR, 'Electricity_production.csv')
SATELLITE_STATUS=os.path.join(DATA_DIR,"Satellite_status.csv")
WATER_RESERVE=os.path.join(DATA_DIR,"Water_reserve.csv")
TODO_FILE_DIR=os.path.join(VIS_DIR,"TODO.txt")
METEO_LOG_DIR=os.path.join(LOGS_DIR,'Procces.log')
SEASON_PREDICTION_MODEL_DIR=os.path.join(MODEL_DIR,"season_pred.joblib")
SEASON_PREDICTION_DIR=os.path.join(DATA_DIR,"Season_prediction.csv")


TOMORROW_API_DIR=os.path.join(API_DIR,'api_tomorrow_response.json')
TOMORROW_API_FORECAST_DIR=os.path.join(API_DIR,'api_tomorrow_forecast_response.json')
ELECTRICITY_API_DIR=os.path.join(API_DIR,'api_electricity_response.json')
WATER_RESERVE_API_DIR=os.path.join(API_DIR,'api_water_reserve_response.json')
CONFIG_DATA=os.path.join(API_DIR,'data.json')

SATELLITE_OUTPUT = os.path.join(SDR_DIR,"output_satellite.txt")
NOAA_APT=os.path.join(SDR_DIR,"noaa-apt")


#DATETIME
now=datetime.now()
year=now.year
current_month = now.month
current_day = now.day
hour=now.hour
minute=now.minute
day_name=now.strftime("%A")
now_hour_min=now.strftime("%H:%M")
meses = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December"]

#URLS
tomorrow_api_url= url = "https://api.tomorrow.io/v4/weather/forecast"
electricity_api_url = "https://api.electricitymap.org/v3/power-breakdown/latest"
water_reserve_url= "https://www.embalses.net/provincia-3-palencia.html"
water_reserve_url_api= "http://127.0.0.1:5000/datos"


@cache
def load_config_data():
    try:
        with open(CONFIG_DATA, "r") as file:
            return json.load(file)
    except FileNotFoundError as exc:
        raise RuntimeError(f"No existe el archivo de configuracion: {CONFIG_DATA}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"El archivo de configuracion no es JSON valido: {CONFIG_DATA}") from exc


def read_data_json(key):
    config = load_config_data()

    try:
        return config[key]
    except KeyError as exc:
        raise RuntimeError(f"El archivo de configuracion no contiene la seccion '{key}'.") from exc


def get_station_latitude():
    return float(read_data_json("station")["latitude"])

def get_station_longitude():
    return float(read_data_json("station")["longitude"])

def get_station_altitude():
    return float(read_data_json("station")["altitude"])

def get_station_name():
    return read_data_json("station")["name"]

def get_extra_config():
    try:
        return read_data_json("extra_config")
    except RuntimeError as exc:
        if "seccion 'extra_config'" in str(exc):
            return {}
        raise

def get_zone_config():
    try:
        return read_data_json("station")["zone"]
    except RuntimeError as exc:
        if "seccion 'station'" in str(exc):
            return None
        raise
