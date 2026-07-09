from html import escape
from pathlib import Path

import pandas as pd

from config import legacy_data_path, resolve_data_path


MONTH_MAPPING = {
    "January": 1,
    "February": 2,
    "March": 3,
    "April": 4,
    "May": 5,
    "June": 6,
    "July": 7,
    "August": 8,
    "September": 9,
    "October": 10,
    "November": 11,
    "December": 12,
}

MONTH_NAMES = {value: key for key, value in MONTH_MAPPING.items()}

WEATHER_COMPARE_COLUMN = "Año_Mes_Dia_Hora"
WEATHER_PERIOD_COLUMN = "Periodo"

ELECTRICITY_COLUMNS = [
    "nuclear",
    "geothermal",
    "biomass",
    "coal",
    "wind",
    "solar",
    "hydro",
    "gas",
    "oil",
    "unknown",
]

ALWAYS_VISIBLE_DASHBOARD_PAGES = ("home", "logs", "todo")


def dashboard_page_availability(csv_paths, exists_func=None):
    exists = exists_func or (lambda path: Path(path).exists())
    path_available = lambda path: exists(path) or exists(legacy_data_path(path))
    electricity_available = exists(csv_paths["electricity_consumption"]) or exists(
        csv_paths["electricity_production"]
    )

    rules = [
        ("home", True),
        ("forecast", path_available(csv_paths["forecast"])),
        ("daily_stats", path_available(csv_paths["daily_stats"])),
        ("monthly_stats", path_available(csv_paths["monthly_stats"])),
        ("electricity", electricity_available),
        ("water_reservoir", path_available(csv_paths["water_reservoir"])),
        ("satellites", path_available(csv_paths["satellites"])),
        ("season_predictions", path_available(csv_paths["season_predictions"])),
        ("logs", True),
        ("todo", True),
    ]
    return [page_key for page_key, available in rules if available]


def load_csv_file(path, dataset_name=None):
    file_path = Path(resolve_data_path(path))
    name = dataset_name or file_path.name
    try:
        return pd.read_csv(file_path)
    except FileNotFoundError as exc:
        raise ValueError(
            f"No existe {name}. Ejecuta primero el recolector de datos o añade el CSV correspondiente."
        ) from exc
    except pd.errors.EmptyDataError as exc:
        raise ValueError(f"{name} existe, pero esta vacio.") from exc


def ensure_columns(data, required_columns, dataset_name="data"):
    missing_columns = set(required_columns).difference(data.columns)
    if missing_columns:
        missing = ", ".join(sorted(missing_columns))
        raise ValueError(f"Faltan columnas requeridas en {dataset_name}: {missing}")


def normalize_month(value):
    if pd.isna(value):
        return pd.NA

    if isinstance(value, str):
        cleaned_value = value.strip()
        if cleaned_value in MONTH_MAPPING:
            return MONTH_MAPPING[cleaned_value]
        if cleaned_value.isdigit():
            return int(cleaned_value)
        return pd.NA

    try:
        return int(value)
    except (TypeError, ValueError):
        return pd.NA


def available_values(data, column):
    if data.empty or column not in data.columns:
        return []
    return data[column].dropna().unique().tolist()


def filter_historical_weather(data, years, months, days):
    ensure_columns(data, {"Year", "Mes", "Dia", "Hora"}, "Historical_weather.csv")
    filtered_data = data[
        data["Year"].isin(years)
        & data["Mes"].isin(months)
        & data["Dia"].isin(days)
    ].copy()
    filtered_data[WEATHER_COMPARE_COLUMN] = (
        filtered_data["Mes"].astype(str)
        + "/"
        + filtered_data["Dia"].astype(str)
        + " - "
        + filtered_data["Hora"].astype(str)
        + " ("
        + filtered_data["Year"].astype(str)
        + ")"
    )
    return filtered_data


def prepare_historical_weather(data):
    ensure_columns(data, {"Year", "Mes", "Dia", "Hora"}, "Historical_weather.csv")
    prepared_data = data.copy()
    prepared_data["Mes_Num"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")
    prepared_data["Year"] = pd.to_numeric(prepared_data["Year"], errors="coerce").astype("Int64")
    prepared_data["Dia"] = pd.to_numeric(prepared_data["Dia"], errors="coerce").astype("Int64")
    prepared_data = prepared_data.dropna(subset=["Year", "Mes_Num", "Dia"]).copy()
    prepared_data["Fecha"] = pd.to_datetime(
        {
            "year": prepared_data["Year"].astype(int),
            "month": prepared_data["Mes_Num"].astype(int),
            "day": prepared_data["Dia"].astype(int),
        },
        errors="coerce",
    )
    prepared_data = prepared_data.dropna(subset=["Fecha"]).copy()
    prepared_data[WEATHER_PERIOD_COLUMN] = (
        prepared_data["Year"].astype(str)
        + "-"
        + prepared_data["Mes_Num"].astype(str).str.zfill(2)
        + "-"
        + prepared_data["Dia"].astype(str).str.zfill(2)
    )
    return prepared_data.sort_values(["Fecha", "Hora"]).reset_index(drop=True)


def _historical_weather_with_sort_columns(data):
    ensure_columns(data, {"Year", "Mes", "Dia", "Hora"}, "Historical_weather.csv")
    prepared_data = data.copy()
    prepared_data["_Mes_Num"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")
    prepared_data["_Year_Num"] = pd.to_numeric(prepared_data["Year"], errors="coerce").astype("Int64")
    prepared_data["_Dia_Num"] = pd.to_numeric(prepared_data["Dia"], errors="coerce").astype("Int64")
    prepared_data = prepared_data.dropna(subset=["_Year_Num", "_Mes_Num", "_Dia_Num"]).copy()
    prepared_data["_Fecha"] = pd.to_datetime(
        {
            "year": prepared_data["_Year_Num"].astype(int),
            "month": prepared_data["_Mes_Num"].astype(int),
            "day": prepared_data["_Dia_Num"].astype(int),
        },
        errors="coerce",
    )
    hour_text = prepared_data["Hora"].astype(str)
    prepared_data["_Hora"] = pd.to_datetime(hour_text, format="%H:%M", errors="coerce")
    prepared_data["_Hora"] = prepared_data["_Hora"].fillna(
        pd.to_datetime(hour_text, format="%H:%M:%S", errors="coerce")
    )
    prepared_data = prepared_data.dropna(subset=["_Fecha", "_Hora"]).copy()
    return prepared_data


def latest_weather_reading(data):
    prepared_data = _historical_weather_with_sort_columns(data)
    if prepared_data.empty:
        return pd.Series(dtype=object)
    sorted_data = prepared_data.sort_values(["_Fecha", "_Hora"]).reset_index(drop=True)
    return sorted_data.drop(columns=["_Mes_Num", "_Year_Num", "_Dia_Num", "_Fecha", "_Hora"]).iloc[-1]


def daily_rain_total_from_historical(data, latest_row):
    if latest_row.empty or "precipitation (mm/h)" not in data.columns:
        return pd.NA

    ensure_columns(data, {"Year", "Mes", "Dia"}, "Historical_weather.csv")
    day_data = data[
        (data["Year"] == latest_row.get("Year"))
        & (data["Mes"] == latest_row.get("Mes"))
        & (data["Dia"] == latest_row.get("Dia"))
    ]
    rain_values = pd.to_numeric(day_data["precipitation (mm/h)"], errors="coerce").dropna()
    return rain_values.sum() if not rain_values.empty else pd.NA


def _row_numeric_value(row, column):
    if row.empty or column not in row:
        return pd.NA
    value = pd.to_numeric(pd.Series([row.get(column)]), errors="coerce").iloc[0]
    return value if not pd.isna(value) else pd.NA


def current_weather_summary(historical_data):
    latest_row = latest_weather_reading(historical_data)
    return {
        "latest_row": latest_row,
        "temperature": _row_numeric_value(latest_row, "temp (C)"),
        "humidity": _row_numeric_value(latest_row, "hum(%)"),
        "rain_today": daily_rain_total_from_historical(historical_data, latest_row),
        "wind_speed": _row_numeric_value(latest_row, "wind_speed(m/s)"),
        "pressure": _row_numeric_value(latest_row, "pres(hPa)"),
    }


def cloud_cover_icon_key(latest_row):
    precipitation = _row_numeric_value(latest_row, "precipitation (mm/h)")
    if not pd.isna(precipitation) and precipitation != 0:
        return "rain"

    clouds = _row_numeric_value(latest_row, "clouds(%)")
    if pd.isna(clouds):
        return None
    if 0 <= clouds <= 25:
        return "sun"
    if 25 < clouds <= 50:
        return "sun_few_clouds"
    if 50 < clouds <= 75:
        return "sun_mostly_cloudy"
    if 75 < clouds <= 100:
        return "clouds"
    return None


def weather_summary(data):
    if data.empty:
        return {
            "records": 0,
            "period": "Sin datos",
            "temp_mean": pd.NA,
            "temp_min": pd.NA,
            "temp_max": pd.NA,
            "rain_total": pd.NA,
            "wind_max": pd.NA,
            "humidity_mean": pd.NA,
            "pressure_mean": pd.NA,
        }

    summary = {
        "records": len(data),
        "period": f"{data['Fecha'].min().date()} - {data['Fecha'].max().date()}" if "Fecha" in data else "Seleccion",
        "temp_mean": metric_value(data, "temp (C)", "mean"),
        "temp_min": metric_value(data, "temp (C)", "min"),
        "temp_max": metric_value(data, "temp (C)", "max"),
        "rain_total": metric_value(data, "precipitation (mm/h)", "sum"),
        "wind_max": metric_value(data, "wind_speed(m/s)", "max"),
        "humidity_mean": metric_value(data, "hum(%)", "mean"),
        "pressure_mean": metric_value(data, "pres(hPa)", "mean"),
    }
    return summary


def metric_value(data, column, aggregation):
    if column not in data.columns or data[column].dropna().empty:
        return pd.NA

    values = pd.to_numeric(data[column], errors="coerce").dropna()
    if values.empty:
        return pd.NA

    if aggregation == "mean":
        return values.mean()
    if aggregation == "min":
        return values.min()
    if aggregation == "max":
        return values.max()
    if aggregation == "sum":
        return values.sum()
    raise ValueError(f"Agregacion no soportada: {aggregation}")


def daily_weather_breakdown(data):
    if data.empty:
        return pd.DataFrame()

    aggregations = {
        "temp (C)": ["min", "mean", "max"],
        "precipitation (mm/h)": "sum",
        "wind_speed(m/s)": "max",
        "hum(%)": "mean",
        "pres(hPa)": "mean",
        "clouds(%)": "mean",
    }
    available_aggregations = {
        column: aggregation
        for column, aggregation in aggregations.items()
        if column in data.columns
    }
    if not available_aggregations:
        return pd.DataFrame()

    grouped = data.groupby(WEATHER_PERIOD_COLUMN, dropna=False).agg(available_aggregations)
    grouped.columns = [
        "_".join(column).strip("_") if isinstance(column, tuple) else column
        for column in grouped.columns
    ]
    grouped = grouped.reset_index().rename(
        columns={
            "temp (C)_min": "temp_min",
            "temp (C)_mean": "temp_mean",
            "temp (C)_max": "temp_max",
            "precipitation (mm/h)_sum": "precipitation_total",
            "wind_speed(m/s)_max": "wind_speed_max",
            "hum(%)_mean": "humidity_mean",
            "pres(hPa)_mean": "pressure_mean",
            "clouds(%)_mean": "clouds_mean",
        }
    )
    return grouped


def advanced_weather_insights(data):
    if data.empty:
        return {
            "thermal_amplitude": pd.NA,
            "rain_hours": 0,
            "max_rain_rate": pd.NA,
            "pressure_trend": pd.NA,
            "humidity_temp_corr": pd.NA,
            "cloud_cover_mean": pd.NA,
        }

    temp_min = metric_value(data, "temp (C)", "min")
    temp_max = metric_value(data, "temp (C)", "max")
    rain_values = pd.to_numeric(data.get("precipitation (mm/h)", pd.Series(dtype=float)), errors="coerce")
    pressure_values = pd.to_numeric(data.get("pres(hPa)", pd.Series(dtype=float)), errors="coerce").dropna()
    temp_values = pd.to_numeric(data.get("temp (C)", pd.Series(dtype=float)), errors="coerce")
    humidity_values = pd.to_numeric(data.get("hum(%)", pd.Series(dtype=float)), errors="coerce")
    cloud_values = pd.to_numeric(data.get("clouds(%)", pd.Series(dtype=float)), errors="coerce")

    aligned_temp_humidity = pd.concat([temp_values, humidity_values], axis=1).dropna()
    humidity_temp_corr = (
        aligned_temp_humidity.iloc[:, 0].corr(aligned_temp_humidity.iloc[:, 1])
        if len(aligned_temp_humidity) > 1
        else pd.NA
    )

    return {
        "thermal_amplitude": temp_max - temp_min if not pd.isna(temp_max) and not pd.isna(temp_min) else pd.NA,
        "rain_hours": int((rain_values.fillna(0) > 0).sum()),
        "max_rain_rate": rain_values.max() if not rain_values.dropna().empty else pd.NA,
        "pressure_trend": (
            pressure_values.iloc[-1] - pressure_values.iloc[0]
            if len(pressure_values) > 1
            else pd.NA
        ),
        "humidity_temp_corr": humidity_temp_corr,
        "cloud_cover_mean": cloud_values.mean() if not cloud_values.dropna().empty else pd.NA,
    }


def format_metric(value, suffix="", decimals=1, empty="--"):
    if pd.isna(value):
        return empty
    return f"{float(value):.{decimals}f}{suffix}"


def prepare_daily_statistics(data):
    ensure_columns(data, {"Year", "Mes", "Dia"}, "Statistics_day.csv")
    prepared_data = data.copy()
    prepared_data["Mes"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")
    prepared_data["Year"] = pd.to_numeric(prepared_data["Year"], errors="coerce").astype("Int64")
    prepared_data["Dia"] = pd.to_numeric(prepared_data["Dia"], errors="coerce").astype("Int64")
    prepared_data = prepared_data.dropna(subset=["Year", "Mes", "Dia"]).copy()
    prepared_data["Fecha"] = pd.to_datetime(
        {
            "year": prepared_data["Year"].astype(int),
            "month": prepared_data["Mes"].astype(int),
            "day": prepared_data["Dia"].astype(int),
        },
        errors="coerce",
    )
    return prepared_data.dropna(subset=["Fecha"]).sort_values("Fecha").reset_index(drop=True)


def filter_recent_days(data, num_days, end_date):
    start_date = pd.Timestamp(end_date) - pd.Timedelta(days=num_days)
    return data[
        (data["Fecha"] >= start_date)
        & (data["Fecha"] <= pd.Timestamp(end_date))
    ].copy()


def filter_latest_days(data, num_days):
    if data.empty:
        return data.copy()
    return data.sort_values("Fecha").tail(int(num_days)).copy()


def filter_daily_month(data, year, month):
    return data[
        (data["Year"].astype(int) == int(year))
        & (data["Mes"].astype(int) == int(month))
    ].copy()


def add_accumulated_precipitation(data):
    prepared_data = data.copy()
    prepared_data["precipitacion_acumulada"] = pd.to_numeric(
        prepared_data["precipitaciones_totales"], errors="coerce"
    ).fillna(0).cumsum()
    return prepared_data


def statistics_summary(data):
    if data.empty:
        return {
            "days": 0,
            "temp_max": pd.NA,
            "temp_min": pd.NA,
            "temp_mean": pd.NA,
            "rain_total": pd.NA,
            "wind_max": pd.NA,
            "humidity_mean": pd.NA,
            "pressure_mean": pd.NA,
            "clouds_mean": pd.NA,
        }

    return {
        "days": len(data),
        "temp_max": metric_value(data, "temp_max", "max"),
        "temp_min": metric_value(data, "temp_min", "min"),
        "temp_mean": metric_value(data, "temp_mean", "mean"),
        "rain_total": metric_value(data, "precipitaciones_totales", "sum"),
        "wind_max": metric_value(data, "wind_speed_max", "max"),
        "humidity_mean": metric_value(data, "humidity", "mean"),
        "pressure_mean": metric_value(data, "pressure", "mean"),
        "clouds_mean": metric_value(data, "clouds", "mean"),
    }


def prepare_monthly_statistics(data):
    ensure_columns(data, {"Year", "Mes"}, "Statistics_month.csv")
    prepared_data = data.copy()
    prepared_data["Mes_Num"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")
    prepared_data["Year"] = pd.to_numeric(prepared_data["Year"], errors="coerce").astype("Int64")
    prepared_data = prepared_data.dropna(subset=["Year", "Mes_Num"]).copy()
    return prepared_data.sort_values(["Year", "Mes_Num"]).reset_index(drop=True)


def filter_monthly_year(data, year):
    filtered_data = data[data["Year"].astype(int) == int(year)].sort_values(by="Mes_Num").copy()
    filtered_data["Mes"] = filtered_data["Mes_Num"].map(MONTH_NAMES)
    return add_accumulated_precipitation(filtered_data)


FORECAST_HORIZONS = [
    ("Mañana", 1, "Tmax mañana", "Tmin mañana", ("Rain acum. mañana", "Rain acum. Mañana")),
    ("3 días", 3, "Tmax 3_dias", "Tmin 3_dias", ("Rain acum. 3_dias",)),
    ("5 días", 5, "Tmax 5_dias", "Tmin 5_dias", ("Rain acum. 5_dias",)),
]


def _first_existing_column(data_or_index, candidates):
    columns = data_or_index.columns if hasattr(data_or_index, "columns") else data_or_index.index
    for column in candidates:
        if column in columns:
            return column
    raise ValueError(f"Faltan columnas requeridas en Historical_weather_forecast.csv: {' o '.join(candidates)}")


def prepare_forecast_row(forecast_data):
    if forecast_data.empty:
        raise ValueError("No hay datos de forecast disponibles.")

    forecast_tomorrow = forecast_data.iloc[-1]
    current_date = pd.to_datetime(forecast_tomorrow["Fecha Actual"])
    fecha_manana = (current_date + pd.Timedelta(days=1)).strftime("%Y-%m-%d")
    fecha_3dias = (current_date + pd.Timedelta(days=3)).strftime("%Y-%m-%d")
    fecha_5dias = (current_date + pd.Timedelta(days=5)).strftime("%Y-%m-%d")

    renamed_row = forecast_tomorrow.rename(
        {
            "Tmax mañana": f"Tmax {fecha_manana}",
            "Tmin mañana": f"Tmin {fecha_manana}",
            "Rain acum. mañana": f"Rain acum. {fecha_manana}",
            "Rain acum. Mañana": f"Rain acum. {fecha_manana}",
            "Tmax 3_dias": f"Tmax {fecha_3dias}",
            "Tmin 3_dias": f"Tmin {fecha_3dias}",
            "Rain acum. 3_dias": f"Rain acum. {fecha_3dias}",
            "Tmax 5_dias": f"Tmax {fecha_5dias}",
            "Tmin 5_dias": f"Tmin {fecha_5dias}",
            "Rain acum. 5_dias": f"Rain acum. {fecha_5dias}",
        }
    ).to_frame().T
    return forecast_tomorrow, renamed_row


def prepare_forecast_horizons(forecast_data):
    forecast_tomorrow, _ = prepare_forecast_row(forecast_data)
    current_date = pd.to_datetime(forecast_tomorrow["Fecha Actual"])
    rows = []
    for label, offset, max_column, min_column, rain_columns in FORECAST_HORIZONS:
        rain_column = _first_existing_column(forecast_tomorrow, rain_columns)
        rows.append(
            {
                "horizonte": label,
                "fecha": current_date + pd.Timedelta(days=offset),
                "temp_max": forecast_tomorrow[max_column],
                "temp_min": forecast_tomorrow[min_column],
                "rain_total": forecast_tomorrow[rain_column],
            }
        )
    return pd.DataFrame(rows)


def prepare_forecast_accuracy(forecast_data, daily_statistics):
    if forecast_data.empty or daily_statistics.empty:
        return pd.DataFrame()

    ensure_columns(
        forecast_data,
        {
            "Fecha Actual",
            "Tmax mañana",
            "Tmin mañana",
            "Tmax 3_dias",
            "Tmin 3_dias",
            "Rain acum. 3_dias",
            "Tmax 5_dias",
            "Tmin 5_dias",
            "Rain acum. 5_dias",
        },
        "Historical_weather_forecast.csv",
    )
    for _, _, _, _, rain_columns in FORECAST_HORIZONS:
        _first_existing_column(forecast_data, rain_columns)
    ensure_columns(
        daily_statistics,
        {"Fecha", "temp_max", "temp_min", "precipitaciones_totales"},
        "Statistics_day.csv",
    )

    forecast_rows = []
    for _, row in forecast_data.iterrows():
        forecast_date = pd.to_datetime(row["Fecha Actual"], errors="coerce")
        if pd.isna(forecast_date):
            continue
        for horizon, days_ahead, max_column, min_column, rain_columns in FORECAST_HORIZONS:
            rain_column = _first_existing_column(row, rain_columns)
            forecast_rows.append(
                {
                    "forecast_date": forecast_date.normalize(),
                    "target_date": (forecast_date + pd.Timedelta(days=days_ahead)).normalize(),
                    "horizonte": horizon,
                    "days_ahead": days_ahead,
                    "pred_temp_max": row[max_column],
                    "pred_temp_min": row[min_column],
                    "pred_rain_total": row[rain_column],
                }
            )

    prepared_forecast = pd.DataFrame(forecast_rows)
    if prepared_forecast.empty:
        return prepared_forecast

    for column in ("pred_temp_max", "pred_temp_min", "pred_rain_total"):
        prepared_forecast[column] = pd.to_numeric(prepared_forecast[column], errors="coerce")

    real_data = daily_statistics[
        ["Fecha", "temp_max", "temp_min", "precipitaciones_totales"]
    ].copy()
    real_data["target_date"] = pd.to_datetime(real_data["Fecha"], errors="coerce").dt.normalize()
    real_data = real_data.rename(
        columns={
            "temp_max": "real_temp_max",
            "temp_min": "real_temp_min",
            "precipitaciones_totales": "real_rain_total",
        }
    ).drop(columns=["Fecha"])
    for column in ("real_temp_max", "real_temp_min", "real_rain_total"):
        real_data[column] = pd.to_numeric(real_data[column], errors="coerce")

    verified = prepared_forecast.merge(real_data, on="target_date", how="inner")
    if verified.empty:
        return verified

    verified["error_temp_max"] = verified["pred_temp_max"] - verified["real_temp_max"]
    verified["error_temp_min"] = verified["pred_temp_min"] - verified["real_temp_min"]
    verified["error_rain_total"] = verified["pred_rain_total"] - verified["real_rain_total"]
    verified["abs_error_temp_max"] = verified["error_temp_max"].abs()
    verified["abs_error_temp_min"] = verified["error_temp_min"].abs()
    verified["abs_error_rain_total"] = verified["error_rain_total"].abs()
    return verified.sort_values(["target_date", "days_ahead"]).reset_index(drop=True)


def forecast_accuracy_summary(accuracy_data):
    if accuracy_data.empty:
        return pd.DataFrame()

    summary = (
        accuracy_data.groupby(["horizonte", "days_ahead"], as_index=False)
        .agg(
            samples=("target_date", "count"),
            mae_temp_max=("abs_error_temp_max", "mean"),
            mae_temp_min=("abs_error_temp_min", "mean"),
            mae_rain_total=("abs_error_rain_total", "mean"),
            bias_temp_max=("error_temp_max", "mean"),
            bias_temp_min=("error_temp_min", "mean"),
            bias_rain_total=("error_rain_total", "mean"),
        )
        .sort_values("days_ahead")
    )
    return summary


def filter_current_electricity_day(data, current_month, current_day):
    ensure_columns(data, {"Mes", "Dia"}, "Electricity CSV")
    month_name = MONTH_NAMES[int(current_month)]
    return data[
        (data["Mes"] == month_name)
        & (data["Dia"] == int(current_day))
    ].copy()


def electricity_breakdown_values(data):
    return data.filter(items=ELECTRICITY_COLUMNS).sum().sort_values(ascending=False)


def electricity_summary(data):
    values = electricity_breakdown_values(data)
    total = values.sum()
    main_source = values.index[0] if not values.empty and total else "--"
    main_value = values.iloc[0] if not values.empty else pd.NA
    return {
        "total": total,
        "main_source": main_source,
        "main_value": main_value,
        "sources": int((values > 0).sum()),
    }


def autopct_format(pct):
    return ("%1.1f%%" % pct) if pct > 3 else ""


def prepare_water_reserve(data):
    ensure_columns(data, {"Mes", "Dia"}, "Water_reserve.csv")
    prepared_data = data.copy()
    for column in ("agua_embalsada_hm3", "porcentaje_embalsado"):
        if column in prepared_data.columns:
            prepared_data[column] = pd.to_numeric(prepared_data[column], errors="coerce")
    if "Year" in prepared_data.columns:
        prepared_data["Mes_Num"] = prepared_data["Mes"].apply(normalize_month).astype("Int64")
        prepared_data["Fecha"] = pd.to_datetime(
            {
                "year": pd.to_numeric(prepared_data["Year"], errors="coerce"),
                "month": prepared_data["Mes_Num"],
                "day": pd.to_numeric(prepared_data["Dia"], errors="coerce"),
            },
            errors="coerce",
        )
        prepared_data = prepared_data.sort_values("Fecha")
    prepared_data["Mes_Dia"] = prepared_data["Mes"].astype(str) + "-" + prepared_data["Dia"].astype(str)
    return prepared_data


def water_reserve_summary(data):
    if data.empty:
        return {
            "last_hm3": pd.NA,
            "last_percent": pd.NA,
            "hm3_change": pd.NA,
            "percent_change": pd.NA,
            "last_label": "Sin datos",
        }

    latest = data.iloc[-1]
    previous = data.iloc[-2] if len(data) > 1 else None
    latest_hm3 = pd.to_numeric(pd.Series([latest.get("agua_embalsada_hm3", pd.NA)]), errors="coerce").iloc[0]
    latest_percent = pd.to_numeric(pd.Series([latest.get("porcentaje_embalsado", pd.NA)]), errors="coerce").iloc[0]
    previous_hm3 = (
        pd.to_numeric(pd.Series([previous.get("agua_embalsada_hm3", pd.NA)]), errors="coerce").iloc[0]
        if previous is not None
        else pd.NA
    )
    previous_percent = (
        pd.to_numeric(pd.Series([previous.get("porcentaje_embalsado", pd.NA)]), errors="coerce").iloc[0]
        if previous is not None
        else pd.NA
    )
    return {
        "last_hm3": latest_hm3,
        "last_percent": latest_percent,
        "hm3_change": (
            latest_hm3 - previous_hm3
            if previous is not None and not pd.isna(latest_hm3) and not pd.isna(previous_hm3)
            else pd.NA
        ),
        "percent_change": (
            latest_percent - previous_percent
            if previous is not None and not pd.isna(latest_percent) and not pd.isna(previous_percent)
            else pd.NA
        ),
        "last_label": str(latest.get("Fecha", latest.get("Mes_Dia", "Ultimo dato")))[:10],
    }


def satellite_state_counts(data):
    if data.empty or "state" not in data.columns:
        return {}
    return data["state"].value_counts().to_dict()


def satellite_state_style(val):
    if val == "active":
        return "background-color: green"
    if val == "inactive":
        return "background-color: grey"
    if val == "waiting":
        return "background-color: yellow"
    if val == "blocked":
        return "background-color: red"
    return ""


def log_level(line):
    for level in ("INFO", "ERROR", "WARNING", "DEBUG"):
        if level in line:
            return level
    return "OTHER"


def count_log_levels(lines):
    recent_lines = list(lines)
    return {
        "INFO": sum(1 for line in recent_lines if log_level(line) == "INFO"),
        "ERROR": sum(1 for line in recent_lines if log_level(line) == "ERROR"),
        "WARNING": sum(1 for line in recent_lines if log_level(line) == "WARNING"),
        "DEBUG": sum(1 for line in recent_lines if log_level(line) == "DEBUG"),
    }


def filter_log_lines(lines, show_info=True, show_error=True, show_warning=True, show_debug=True):
    enabled_levels = set()
    if show_info:
        enabled_levels.add("INFO")
    if show_error:
        enabled_levels.add("ERROR")
    if show_warning:
        enabled_levels.add("WARNING")
    if show_debug:
        enabled_levels.add("DEBUG")
    return [line for line in lines if log_level(line) in enabled_levels]


def format_log_message(message):
    safe_message = escape(message)
    if "INFO" in message:
        return f'<p style="color:green;">{safe_message}</p>'
    if "ERROR" in message:
        return f'<p style="color:red;">{safe_message}</p>'
    if "WARNING" in message:
        return f'<p style="color:yellow;">{safe_message}</p>'
    if "DEBUG" in message:
        return f'<p style="color:grey;">{safe_message}</p>'
    return f"<p>{safe_message}</p>"


def read_text_file(path, default=""):
    try:
        with open(path, "r") as file:
            return file.read()
    except FileNotFoundError:
        return default


def write_text_file(path, content):
    with open(path, "w") as file:
        file.write(content)
