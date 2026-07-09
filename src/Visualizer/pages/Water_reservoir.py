import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import WATER_RESERVE
from Visualizer.dashboard_charts import water_reserve_chart
from Visualizer.dashboard_data import format_metric, load_csv_file, prepare_water_reserve, water_reserve_summary


st.set_page_config(page_title="Water reservoir", layout="wide")
st.title("Reservas de agua")

try:
    data = prepare_water_reserve(load_csv_file(WATER_RESERVE, "Water_reserve.csv"))
except ValueError as exc:
    st.error(str(exc))
    st.stop()

if data.empty:
    st.warning("No hay datos de reservas de agua.")
    st.stop()

summary = water_reserve_summary(data)
st.caption(f"Ultimo dato: {summary['last_label']}")

metric_cols = st.columns(4)
metric_cols[0].metric("Agua embalsada", format_metric(summary["last_hm3"], " hm3", decimals=0))
metric_cols[1].metric("Porcentaje", format_metric(summary["last_percent"], " %"))
metric_cols[2].metric("Cambio hm3", format_metric(summary["hm3_change"], " hm3", decimals=0))
metric_cols[3].metric("Cambio %", format_metric(summary["percent_change"], " %"))

st.plotly_chart(water_reserve_chart(data), use_container_width=True)

with st.expander("Ver datos"):
    st.dataframe(data, use_container_width=True, hide_index=True)
