import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import STATISTICS_DAY_DIR
from Visualizer.dashboard_charts import (
    precipitation_statistics_chart,
    statistics_metric_chart,
    temperature_statistics_chart,
)
from Visualizer.dashboard_data import (
    add_accumulated_precipitation,
    filter_daily_month,
    filter_latest_days,
    format_metric,
    load_csv_file,
    prepare_daily_statistics,
    statistics_summary,
)


st.set_page_config(page_title="Daily Statistics", layout="wide")
st.title("Estadisticas diarias")


@st.cache_data
def load_stats_data():
    return load_csv_file(STATISTICS_DAY_DIR, "Statistics_day.csv")


try:
    data = prepare_daily_statistics(load_stats_data())
except ValueError as exc:
    st.error(str(exc))
    st.stop()

st.sidebar.header("Parámetros de Visualización")
num_days = st.sidebar.slider("Selecciona el número de días a mostrar:", min_value=1, max_value=30, value=7)

filtered_data = filter_latest_days(data, num_days)

if filtered_data.empty:
    st.warning("No hay datos disponibles para el rango seleccionado.")
else:
    month_box = st.sidebar.checkbox("Mostrar por Mes")

    if not month_box:
        filtered_data = add_accumulated_precipitation(filtered_data)
        chart_x = "Fecha"
        title_suffix = f"Ultimos {num_days} dias"
    else:
        year_selected = st.sidebar.selectbox("Selecciona el Año", data["Year"].unique())
        month_selected = st.sidebar.selectbox("Selecciona el Mes", data["Mes"].unique())
        filtered_data = add_accumulated_precipitation(filter_daily_month(data, year_selected, month_selected))
        chart_x = "Dia"
        title_suffix = f"{month_selected}/{year_selected}"

    summary = statistics_summary(filtered_data)
    metric_cols = st.columns(6)
    metric_cols[0].metric("Dias", summary["days"])
    metric_cols[1].metric("Temp max", format_metric(summary["temp_max"], " °C"))
    metric_cols[2].metric("Temp min", format_metric(summary["temp_min"], " °C"))
    metric_cols[3].metric("Temp media", format_metric(summary["temp_mean"], " °C"))
    metric_cols[4].metric("Lluvia total", format_metric(summary["rain_total"], " mm"))
    metric_cols[5].metric("Viento max", format_metric(summary["wind_max"], " m/s"))

    st.subheader(f"Temperatura y precipitacion · {title_suffix}")
    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(temperature_statistics_chart(filtered_data, chart_x), use_container_width=True)
    with col2:
        st.plotly_chart(precipitation_statistics_chart(filtered_data, chart_x), use_container_width=True)

    optional_charts = [
        ("wind_speed_max", "Viento maximo", "m/s"),
        ("humidity", "Humedad media", "%"),
        ("pressure", "Presion media", "hPa"),
        ("clouds", "Nubosidad media", "%"),
    ]
    available_charts = [chart for chart in optional_charts if chart[0] in filtered_data.columns]
    if available_charts:
        st.subheader("Variables adicionales")
        for index in range(0, len(available_charts), 2):
            cols = st.columns(2)
            for col, (column, title, unit) in zip(cols, available_charts[index:index + 2]):
                with col:
                    st.plotly_chart(
                        statistics_metric_chart(filtered_data, chart_x, column, title, unit),
                        use_container_width=True,
                    )

    if st.checkbox("Mostrar datos crudos"):
        st.dataframe(filtered_data, use_container_width=True)
