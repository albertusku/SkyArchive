import pandas as pd
import sys
import os
from collections import Counter
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from Logs.logger import setup_logger
from config import * 

logger=setup_logger("UTIL",os.path.join(LOGS_DIR,"Procces.log"))

def get_today_data():
    df=pd.read_csv(HISTORICAL_WEATHER_DIR)
    today_data = df[(df['Year'] == year) & (df['Mes'] == meses[current_month-1]) & (df['Dia'] == current_day)]
    result=check_data_day(today_data)
    if result is not None:
        mask = (df['Year'] == year) & (df['Mes'] == meses[current_month - 1]) & (df['Dia'] == current_day)
        df = df.loc[~mask]
        df = pd.concat([df, result], ignore_index=True)
        df.to_csv(HISTORICAL_WEATHER_DIR, index=False)
        logger.warning("Data day fixed")
    else:
        logger.info("Data day is correct")

def check_data_day(df_day):
    if len(df_day) == 48:
        return None
    else:
        logger.error("Data day is incorrect")
        df_fixed=find_error(df_day)
        return df_fixed

def find_error(df_day):
    time_list = [f"{str(hour).zfill(2)}:{minute:02d}" for hour in range(24) for minute in (0, 30)]
    list_hours=df_day['Hora'].tolist()
    missing_hours = sorted(list(set(time_list) - set(list_hours)))
    if missing_hours:
        logger.warning(f"Fixed missing data hours: {', '.join(missing_hours)}")
    for hour in missing_hours:
        previous_record = df_day[df_day["Hora"] < hour].iloc[-1].copy()
        previous_record["Hora"] = hour
        df_day = df_day._append(previous_record, ignore_index=True)
        df_day.sort_values(by=["Hora"], inplace=True, ignore_index=True)
    return df_day
    
       
if __name__ == "__main__":
    get_today_data()