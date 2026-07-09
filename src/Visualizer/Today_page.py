import sys
import threading
import time
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import HISTORICAL_WEATHER_DIR, get_station_name
from config import (
    ELECTRICITY_DIR_CONSUMPTION,
    ELECTRICITY_DIR_PRODUCTION,
    HISTORICAL_WEATHER_FORECAST_DIR,
    SATELLITE_STATUS,
    SEASON_PREDICTION_DIR,
    STATISTICS_DAY_DIR,
    STATISTICS_MONTH_DIR,
    WATER_RESERVE,
)
from Visualizer.dashboard_charts import (
    historical_cloud_chart,
    historical_humidity_chart,
    historical_precipitation_chart,
    historical_pressure_chart,
    historical_temperature_chart,
    historical_wind_chart,
    temperature_humidity_scatter_chart,
)
from Visualizer.dashboard_data import (
    available_values,
    cloud_cover_icon_key,
    current_weather_summary,
    dashboard_page_availability,
    filter_historical_weather,
    format_metric,
    load_csv_file,
    prepare_historical_weather,
    weather_summary,
)


WEATHER_ASSETS_DIR = Path(__file__).resolve().parent / "assets" / "weather"
WEATHER_ICON_FILES = {
    "sun": "sun.png",
    "sun_few_clouds": "sun_few_clouds.png",
    "sun_mostly_cloudy": "sun_mostly_cloudy.png",
    "clouds": "clouds.png",
    "rain": "rain_clouds.png",
}
WEATHER_ICON_LABELS = {
    "sun": "Despejado",
    "sun_few_clouds": "Pocas nubes",
    "sun_mostly_cloudy": "Muy nuboso",
    "clouds": "Cubierto",
    "rain": "Lluvia",
}


def dashboard_title():
    try:
        station_name = get_station_name()
    except RuntimeError:
        station_name = ""

    if station_name:
        return f"Dashboard Meteorologico - {station_name}"
    return "Dashboard Meteorologico"


@st.cache_data
def load_data():
    return load_csv_file(HISTORICAL_WEATHER_DIR, "Historical_weather.csv")


def select_default(values):
    return [values[-1]] if values else []


def render_current_weather(historical_data):
    current_summary = current_weather_summary(historical_data)
    latest_row = current_summary["latest_row"]
    icon_key = cloud_cover_icon_key(latest_row)

    current_cols = st.columns([1, 1, 1, 1, 1, 1])
    current_cols[0].metric("Temperatura actual", format_metric(current_summary["temperature"], " °C"))
    current_cols[1].metric("Humedad", format_metric(current_summary["humidity"], " %"))
    current_cols[2].metric("Lluvia hoy", format_metric(current_summary["rain_today"], " mm"))
    current_cols[3].metric("Viento actual", format_metric(current_summary["wind_speed"], " m/s"))
    current_cols[4].metric("Presion actual", format_metric(current_summary["pressure"], " hPa"))

    with current_cols[5]:
        if icon_key is None:
            st.warning("Sin dato de nubosidad.")
            return

        icon_path = WEATHER_ASSETS_DIR / WEATHER_ICON_FILES[icon_key]
        if icon_path.exists():
            st.image(str(icon_path), width=72)
            st.caption(WEATHER_ICON_LABELS[icon_key])
        else:
            st.warning("Icono no disponible.")


def render_dashboard_home():
    st.title(dashboard_title())

    try:
        df = prepare_historical_weather(load_data())
    except ValueError as exc:
        st.error(str(exc))
        return

    unique_years = available_values(df, "Year")

    if not unique_years:
        st.warning("No hay datos disponibles.")
        return

    render_current_weather(df)

    selected_years = st.sidebar.multiselect(
        "Seleccionar Años",
        unique_years,
        default=select_default(unique_years),
    )
    df_year = df[df["Year"].isin(selected_years)]

    months = available_values(df_year, "Mes")
    selected_months = st.sidebar.multiselect(
        "Seleccionar Meses",
        months,
        default=select_default(months),
    )
    df_year_month = df_year[df_year["Mes"].isin(selected_months)]

    days = available_values(df_year_month, "Dia")
    selected_days = st.sidebar.multiselect(
        "Seleccionar Días",
        days,
        default=select_default(days),
    )

    filtered_df = filter_historical_weather(df, selected_years, selected_months, selected_days)

    if filtered_df.empty:
        st.warning("No hay datos para la selección actual.")
        return

    summary = weather_summary(filtered_df)
    st.caption(f"Periodo seleccionado: {summary['period']} · {summary['records']} registros")

    st.subheader("Comparativa horaria")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(historical_temperature_chart(filtered_df), use_container_width=True)
    with col2:
        st.plotly_chart(historical_precipitation_chart(filtered_df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(historical_wind_chart(filtered_df), use_container_width=True)
    with col2:
        st.plotly_chart(historical_humidity_chart(filtered_df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(historical_pressure_chart(filtered_df), use_container_width=True)
    with col2:
        if {"temp (C)", "hum(%)"}.issubset(filtered_df.columns):
            st.plotly_chart(temperature_humidity_scatter_chart(filtered_df), use_container_width=True)

    col1, col2 = st.columns(2)
    with col1:
        if "clouds(%)" in filtered_df.columns and filtered_df["clouds(%)"].notna().any():
            st.plotly_chart(historical_cloud_chart(filtered_df), use_container_width=True)
        else:
            st.info("No hay columna de nubosidad en el historico.")

    if st.checkbox("Mostrar muestra de datos filtrados"):
        st.subheader("Muestra de datos filtrados")
        st.dataframe(filtered_df.tail(20), use_container_width=True, hide_index=True)


def auto_reload(interval_seconds=1800):
    while True:
        st.cache_data.clear()
        time.sleep(interval_seconds)
        st.rerun()


def dashboard_csv_paths():
    return {
        "forecast": HISTORICAL_WEATHER_FORECAST_DIR,
        "daily_stats": STATISTICS_DAY_DIR,
        "monthly_stats": STATISTICS_MONTH_DIR,
        "electricity_consumption": ELECTRICITY_DIR_CONSUMPTION,
        "electricity_production": ELECTRICITY_DIR_PRODUCTION,
        "water_reservoir": WATER_RESERVE,
        "satellites": SATELLITE_STATUS,
        "season_predictions": SEASON_PREDICTION_DIR,
    }


def build_navigation_pages():
    pages_dir = Path(__file__).resolve().parent / "pages"
    page_factories = {
        "home": lambda: st.Page(render_dashboard_home, title="Dashboard", icon=":material/home:"),
        "forecast": lambda: st.Page(pages_dir / "Forecast.py", title="Forecast", icon=":material/cloud:"),
        "daily_stats": lambda: st.Page(pages_dir / "day_stats.py", title="Daily stats", icon=":material/bar_chart:"),
        "monthly_stats": lambda: st.Page(
            pages_dir / "month_stats.py",
            title="Monthly stats",
            icon=":material/calendar_month:",
        ),
        "electricity": lambda: st.Page(
            pages_dir / "Electricity_info.py",
            title="Electricity",
            icon=":material/bolt:",
        ),
        "water_reservoir": lambda: st.Page(
            pages_dir / "Water_reservoir.py",
            title="Water reservoir",
            icon=":material/water_drop:",
        ),
        "satellites": lambda: st.Page(
            pages_dir / "Satellite_info.py",
            title="Satellites",
            icon=":material/satellite_alt:",
        ),
        "season_predictions": lambda: st.Page(
            pages_dir / "Season_predictions.py",
            title="Season predictions",
            icon=":material/event_available:",
        ),
        "logs": lambda: st.Page(pages_dir / "meteo_logviewer.py", title="Logs", icon=":material/article:"),
        "todo": lambda: st.Page(pages_dir / "TODO.py", title="TODO", icon=":material/checklist:"),
    }
    return [page_factories[key]() for key in dashboard_page_availability(dashboard_csv_paths())]


def main():
    st.set_page_config(page_title=dashboard_title(), layout="wide")
    if "reload_thread" not in st.session_state:
        reload_thread = threading.Thread(target=auto_reload, daemon=True)
        reload_thread.start()
        st.session_state["reload_thread"] = reload_thread

    navigation = st.navigation(build_navigation_pages())
    navigation.run()


if __name__ == "__main__":
    main()
