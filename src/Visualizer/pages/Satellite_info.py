import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import SATELLITE_STATUS
from Visualizer.dashboard_data import load_csv_file, satellite_state_counts, satellite_state_style


st.set_page_config(page_title="Satellites", layout="wide")
st.title("Satelites")


@st.cache_data
def load_stats_data():
    return load_csv_file(SATELLITE_STATUS, "Satellite_status.csv")


try:
    data = load_stats_data()
except ValueError as exc:
    st.warning(str(exc))
    st.stop()
counts = satellite_state_counts(data)

if counts:
    cols = st.columns(len(counts))
    for col, (state, count) in zip(cols, counts.items()):
        col.metric(state, count)

if data.empty:
    st.warning("No hay datos de satelites.")
else:
    st.dataframe(data.style.applymap(satellite_state_style, subset=["state"]), use_container_width=True)
