import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import ELECTRICITY_DIR_CONSUMPTION, ELECTRICITY_DIR_PRODUCTION, now
from Visualizer.dashboard_charts import electricity_mix_chart
from Visualizer.dashboard_data import (
    electricity_breakdown_values,
    electricity_summary,
    filter_current_electricity_day,
    format_metric,
    load_csv_file,
)


ELECTRICITY_UNIT = " MW"


st.set_page_config(page_title="Electricity", layout="wide")
st.title("Electricidad")

csv_files = {
    "production": ELECTRICITY_DIR_PRODUCTION,
    "consumption": ELECTRICITY_DIR_CONSUMPTION,
}

selected_sheet = st.radio(
    "Tipo de datos",
    list(csv_files.keys()),
    format_func=lambda value: "Produccion" if value == "production" else "Consumo",
    horizontal=True,
)
try:
    data = load_csv_file(csv_files[selected_sheet], Path(csv_files[selected_sheet]).name)
except ValueError as exc:
    st.warning(str(exc))
    st.stop()

current_month = now.month
current_day = now.day
filtered_data = filter_current_electricity_day(data, current_month, current_day)

if filtered_data.empty:
    st.warning(
        f"No hay datos disponibles para el día actual en {selected_sheet} ({current_day}/{current_month})."
    )
else:
    values = electricity_breakdown_values(filtered_data)
    summary = electricity_summary(filtered_data)

    metric_cols = st.columns(4)
    metric_cols[0].metric("Total", format_metric(summary["total"], ELECTRICITY_UNIT, decimals=0))
    metric_cols[1].metric("Fuente principal", summary["main_source"])
    metric_cols[2].metric("Valor principal", format_metric(summary["main_value"], ELECTRICITY_UNIT, decimals=0))
    metric_cols[3].metric("Fuentes activas", summary["sources"])

    st.plotly_chart(electricity_mix_chart(values), use_container_width=True)
    st.dataframe(values.rename_axis("fuente").reset_index(name="total (MW)"), use_container_width=True)
