import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import HISTORICAL_WEATHER_FORECAST_DIR, STATISTICS_DAY_DIR
from Visualizer.dashboard_charts import (
    forecast_rain_accuracy_chart,
    forecast_rain_chart,
    forecast_temperature_accuracy_chart,
    forecast_temperature_chart,
)
from Visualizer.dashboard_data import (
    forecast_accuracy_summary,
    format_metric,
    load_csv_file,
    prepare_daily_statistics,
    prepare_forecast_accuracy,
    prepare_forecast_horizons,
    prepare_forecast_row,
)


st.set_page_config(page_title="Forecast", layout="wide")


@st.cache_data
def load_forecast_data():
    return load_csv_file(HISTORICAL_WEATHER_FORECAST_DIR, "Historical_weather_forecast.csv")


@st.cache_data
def load_daily_stats_data():
    return load_csv_file(STATISTICS_DAY_DIR, "Statistics_day.csv")


try:
    forecast_data = load_forecast_data()
    forecast_tomorrow, forecast_tomorrow_renamed = prepare_forecast_row(forecast_data)
    forecast_horizons = prepare_forecast_horizons(forecast_data)
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

st.title("Prevision meteorologica")
st.caption(f"Actualizado con datos de {forecast_tomorrow['Fecha Actual']}")

cols = st.columns(len(forecast_horizons))
for col, row in zip(cols, forecast_horizons.to_dict("records")):
    with col:
        st.metric(row["horizonte"], row["fecha"].strftime("%Y-%m-%d"))
        st.write(f"Max: {format_metric(row['temp_max'], ' °C')}")
        st.write(f"Min: {format_metric(row['temp_min'], ' °C')}")
        st.write(f"Lluvia: {format_metric(row['rain_total'], ' mm')}")

col1, col2 = st.columns(2)
with col1:
    st.plotly_chart(forecast_temperature_chart(forecast_horizons), use_container_width=True)
with col2:
    st.plotly_chart(forecast_rain_chart(forecast_horizons), use_container_width=True)

with st.expander("Ver fila original"):
    st.dataframe(forecast_tomorrow_renamed, use_container_width=True, hide_index=True)

st.subheader("Prediccion vs realidad")
try:
    daily_stats = prepare_daily_statistics(load_daily_stats_data())
    forecast_accuracy = prepare_forecast_accuracy(forecast_data, daily_stats)
    accuracy_summary = forecast_accuracy_summary(forecast_accuracy)
except ValueError as exc:
    st.info(f"No se puede calcular la precision todavia: {exc}")
    forecast_accuracy = None
    accuracy_summary = None

if accuracy_summary is None:
    pass
elif accuracy_summary.empty:
    st.info("Todavia no hay predicciones con dia real observado para comparar.")
else:
    metric_cols = st.columns(4)
    metric_cols[0].metric("Predicciones verificadas", len(forecast_accuracy))
    metric_cols[1].metric("MAE Tmax", format_metric(accuracy_summary["mae_temp_max"].mean(), " °C"))
    metric_cols[2].metric("MAE Tmin", format_metric(accuracy_summary["mae_temp_min"].mean(), " °C"))
    metric_cols[3].metric("MAE lluvia", format_metric(accuracy_summary["mae_rain_total"].mean(), " mm"))

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(forecast_temperature_accuracy_chart(accuracy_summary), use_container_width=True)
    with col2:
        st.plotly_chart(forecast_rain_accuracy_chart(accuracy_summary), use_container_width=True)

    st.dataframe(
        accuracy_summary[
            [
                "horizonte",
                "samples",
                "mae_temp_max",
                "mae_temp_min",
                "mae_rain_total",
                "bias_temp_max",
                "bias_temp_min",
                "bias_rain_total",
            ]
        ],
        use_container_width=True,
        hide_index=True,
    )

    with st.expander("Ver comparaciones individuales"):
        st.dataframe(
            forecast_accuracy[
                [
                    "forecast_date",
                    "target_date",
                    "horizonte",
                    "pred_temp_max",
                    "real_temp_max",
                    "error_temp_max",
                    "pred_temp_min",
                    "real_temp_min",
                    "error_temp_min",
                    "pred_rain_total",
                    "real_rain_total",
                    "error_rain_total",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )

st.caption(
    "Interpretacion: MAE es el error absoluto medio, cuanto mas cerca de 0 mejor. "
    "Bias es el error medio con signo: positivo significa que la prediccion suele quedar por encima "
    "del valor real y negativo que suele quedar por debajo. Temperatura en °C y lluvia en mm."
)
