import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import STATISTICS_MONTH_DIR
from Visualizer.dashboard_charts import (
    align_monthly_statistics_chart,
    precipitation_statistics_chart,
    statistics_metric_chart,
    temperature_statistics_chart,
)
from Visualizer.dashboard_data import (
    filter_monthly_year,
    format_metric,
    load_csv_file,
    prepare_monthly_statistics,
    statistics_summary,
)


st.set_page_config(page_title="Monthly Statistics", layout="wide")
st.title("Estadisticas mensuales")


@st.cache_data
def load_stats_data():
    return load_csv_file(STATISTICS_MONTH_DIR, "Statistics_month.csv")


try:
    data = prepare_monthly_statistics(load_stats_data())
except ValueError as exc:
    st.error(str(exc))
    st.stop()

years_available = sorted(data["Year"].dropna().astype(int).unique())

if not years_available:
    st.warning("No hay datos mensuales disponibles.")
    st.stop()

selected_year = st.sidebar.selectbox(
    "Seleccionar Año",
    years_available,
    index=len(years_available) - 1,
)

filtered_data = filter_monthly_year(data, selected_year)

summary = statistics_summary(filtered_data)
metric_cols = st.columns(5)
metric_cols[0].metric("Meses", summary["days"])
metric_cols[1].metric("Temp max", format_metric(summary["temp_max"], " °C"))
metric_cols[2].metric("Temp min", format_metric(summary["temp_min"], " °C"))
metric_cols[3].metric("Temp media", format_metric(summary["temp_mean"], " °C"))
metric_cols[4].metric("Lluvia anual", format_metric(summary["rain_total"], " mm"))

st.subheader(f"Temperatura y precipitacion · {selected_year}")
col1, col2 = st.columns(2)
month_order = filtered_data["Mes"].tolist()
with col1:
    temperature_fig = temperature_statistics_chart(filtered_data, "Mes", title="Temperaturas mensuales")
    st.plotly_chart(
        align_monthly_statistics_chart(temperature_fig, month_order),
        use_container_width=True,
    )
with col2:
    precipitation_fig = precipitation_statistics_chart(
        filtered_data,
        "Mes",
        daily_name="Precipitacion mensual",
    )
    st.plotly_chart(
        align_monthly_statistics_chart(precipitation_fig, month_order),
        use_container_width=True,
    )

optional_charts = [
    ("wind_speed_max", "Viento maximo mensual", "m/s"),
    ("humidity", "Humedad media mensual", "%"),
    ("pressure", "Presion media mensual", "hPa"),
    ("clouds", "Nubosidad media mensual", "%"),
]
available_charts = [chart for chart in optional_charts if chart[0] in filtered_data.columns]
if available_charts:
    st.subheader("Variables adicionales")
    for index in range(0, len(available_charts), 2):
        cols = st.columns(2)
        for col, (column, title, unit) in zip(cols, available_charts[index:index + 2]):
            with col:
                st.plotly_chart(
                    statistics_metric_chart(filtered_data, "Mes", column, title, unit),
                    use_container_width=True,
                )

if st.checkbox("Mostrar datos crudos"):
    st.dataframe(filtered_data, use_container_width=True, hide_index=True)
