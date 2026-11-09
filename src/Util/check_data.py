import pandas as pd
import sys
import os
from collections import Counter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Logs.logger import setup_logger
from config import * 

logger=setup_logger("UTIL",os.path.join(LOGS_DIR,"Procces.log"))

def get_today_data():
    """Audit the current day; never synthesize readings for missing slots."""
    df = pd.read_csv(HISTORICAL_WEATHER_DIR)
    today_data = df[(df['Year'] == year) & (df['Mes'] == meses[current_month-1]) & (df['Dia'] == current_day)]
    check_data_day(today_data)


def check_data_day(df_day):
    return find_error(df_day)


def find_error(df_day):
    expected = {f"{hour:02d}:{minute:02d}" for hour in range(24) for minute in (0, 30)}
    present = set(df_day['Hora'])
    missing = sorted(expected - present)
    duplicates = df_day['Hora'][df_day['Hora'].duplicated()].tolist()
    if missing:
        logger.warning(f"Missing data hours: {', '.join(missing)}")
    if duplicates:
        logger.warning(f"Duplicate data hours: {', '.join(duplicates)}")
    return None


if __name__ == "__main__":
    get_today_data()
