import pandas as pd
from datetime import datetime
from config import *
from Logs.logger import setup_logger
import joblib
from datetime import timedelta

logger=setup_logger("Statistics",os.path.join(LOGS_DIR,"Procces.log"))

def get_season(month,latitude):
    
    if latitude >= 0:  # Northern Hemisphere
        if month in ["December", "January", "February"]:
            return "Winter"
        elif month in ["March", "April", "May"]:
            return "Spring"
        elif month in ["June", "July", "August"]:
            return "Summer"
        else:
            return "Autumn"
    else:  # Southern Hemisphere
        if month in ["December", "January", "February"]:
            return "Summer"
        elif month in ["March", "April", "May"]:
            return "Autumn"
        elif month in ["June", "July", "August"]:
            return "Winter"
        else:
            return "Spring"

def make_statistics(df):
    yesterday=now-timedelta(days=1)
    previous_day=yesterday.day
    previous_month=yesterday.strftime("%B")
    real_year=yesterday.year
    logger.info(f"Creating statistics of {previous_day}/{previous_month}/{real_year}")
    df_data_day=make_statistics_day(df,previous_day,previous_month,real_year)
    if now.day==1: 
        df_data_month=make_statistics_month(df_data_day,previous_month,real_year)
    model_result = make_model_prediction() #make model prediction based on the last day statistics

def make_statistics_day(df,day,month,year):
    logger.info(f"Creating statistics day")
    keys=["temp_max","temp_min","temp_mean","precipitaciones_totales",
          "precipitacion_max_1h","wind_speed_max","season","humidity","pressure",
          "clouds"]
    temp_max=df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['temp (C)'].max()
    temp_min=df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['temp (C)'].min()
    temp_mean=df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['temp (C)'].mean()
    humidity = df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['hum(%)'].mean()
    pressure = df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['pres(hPa)'].mean()
    clouds = df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['clouds(%)'].mean()
    precipitaciones_totales = df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['precipitation (mm/h)'].sum()
    df['Precipitacion_1h'] = df['precipitation (mm/h)'].rolling(window=2).sum()
    precipitacion_max_1h = df['Precipitacion_1h'].max()
    wind_speed_max=df[(df['Mes'] == month) & (df['Dia'] == day) & (df['Year'] == year)]['wind_speed(m/s)'].max()
    try:
        season=get_season(month,get_station_latitude())
    except Exception as e:
        logger.error(f"Failed to calculate season: {e}")
        season="Unknown"
    values=[temp_max,temp_min,temp_mean,precipitaciones_totales,precipitacion_max_1h,
            wind_speed_max,season,humidity,pressure,clouds]
    data_day=dict(zip(keys,values))
    new_data={"Year":year,"Mes":month,"Dia":day}
    data_day={**new_data,**data_day}
    df_data_day=pd.DataFrame([data_day])
    from Data_storage.storage_builder import save_csv
    return save_csv(df_data_day,STATISTICS_DAY_DIR)

def make_statistics_month(df,month,year):
    logger.info(f"Creating statistics month")
    current_df=pd.read_csv(resolve_data_path(STATISTICS_MONTH_DIR))
    current_filter_df=current_df[current_df["Mes"]!=month]
    keys=["temp_max","temp_min","temp_mean","precipitaciones_totales","wind_speed_max"]
    temp_max=df[(df['Mes']==month) & (df['Year']==year)]['temp_max'].max()
    temp_min=df[(df['Mes']==month) & (df['Year']==year)]['temp_min'].min()
    temp_mean=df[(df['Mes']==month) & (df['Year']==year)]['temp_mean'].mean()
    precipitaciones_totales=df[(df['Mes']==month) & (df['Year']==year)]['precipitaciones_totales'].sum()
    wind_speed_max=df[(df['Mes']==month) & (df['Year']==year)]['wind_speed_max'].max()
    values=[temp_max,temp_min,temp_mean,precipitaciones_totales,wind_speed_max]
    data_month=dict(zip(keys,values))
    new_data={"Year":year,"Mes":month}
    data_month={**new_data,**data_month}
    df_data_month=pd.DataFrame([data_month])
    from Data_storage.storage_builder import save_csv
    return save_csv(df_data_month,STATISTICS_MONTH_DIR)

def make_statistics_electricity_day(dfs):
    logger.info(f"Creating statistics electricity day")
    tags=["consumption","production"]
    keys=["nuclear","geothermal","biomass","coal","wind","solar","hydro","gas","oil","unknown","hydro discharge","battery discharge"]
    for i,df in enumerate(dfs):
        yesterday=now-timedelta(days=1)
        previous_day = yesterday.day
        previous_month = yesterday.strftime("%B")
        previous_year = yesterday.year
        nuclear = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['nuclear'].mean()
        geothermal = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['geothermal'].mean()
        biomass = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['biomass'].mean()
        coal = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['coal'].mean()
        wind = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['wind'].mean()
        solar = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day)& (df['Year'] == previous_year)]['solar'].mean()
        hydro = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['hydro'].mean()
        gas = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['gas'].mean()
        oil = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['oil'].mean()
        unknown = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['unknown'].mean()
        hydro_discharge = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['hydro discharge'].mean()
        battery_discharge = df[(df['Mes'] == previous_month) & (df['Dia'] == previous_day) & (df['Year'] == previous_year)]['battery discharge'].mean()
        values = [nuclear, geothermal, biomass, coal, wind, solar, hydro, gas, oil, unknown, hydro_discharge, battery_discharge]
        data_electricity_day = dict(zip(keys, values))
        new_data={"Year":previous_year,"Mes":previous_month,"Dia":previous_day}
        data_electricity_day={**new_data,**data_electricity_day}
        df_data_electricity_day=pd.DataFrame([data_electricity_day])
        from Data_storage.storage_builder import save_csv
        if tags[i]=="consumption":
            save_csv(df_data_electricity_day,STATISTICS_ELECTRICITY_DAY_CONSUMPTION_DIR)
        elif tags[i]=="production":
            save_csv(df_data_electricity_day,STATISTICS_ELECTRICITY_DAY_PRODUCTION_DIR)

def make_model_prediction():
    logger.info("Making model prediction")
    try:
        model = joblib.load(SEASON_PREDICTION_MODEL_DIR)
        df = pd.read_csv(resolve_data_path(STATISTICS_DAY_DIR))

        feature_columns = [
            "temp_max",
            "temp_min",
            "temp_mean",
            "precipitaciones_totales",
            "wind_speed_max",
            "humidity",
            "pressure",
            "clouds",
        ]

        X = df[feature_columns].tail(1)# Last row => most recent day data

        prediction = model.predict(X)[0]
        probabilities = model.predict_proba(X)[0]
        classes = model.classes_

        season_probabilities = {
            str(class_name): round(float(probability), 4)
            for class_name, probability in zip(classes, probabilities)
        }

        logger.info(f"Model prediction: {prediction}")
        logger.info(f"Season probabilities: {season_probabilities}")

        month = df['Mes'].iloc[-1]  # Get the month of the last row
        season=get_season(month,get_station_latitude())  # Ensure the function is called to determine the season based on the month and latitude
        from Data_storage.storage_builder import save_csv
        save_csv(pd.DataFrame([{**df[["Year", "Mes", "Dia"]].iloc[-1].to_dict(), "real_season": season, "prediction": prediction, **{f"prob_{k}": v for k, v in
            season_probabilities.items()}}]), SEASON_PREDICTION_DIR)

        return {
              "prediction": str(prediction),
              "probabilities": season_probabilities,
          } #example: {"prediction": "Winter", "probabilities": {"Winter": 0.85, "Spring": 0.05, "Summer": 0.05, "Autumn": 0.05}}



    except Exception as e:
        logger.error(f"Failed to make model prediction: {e}")
        return None
