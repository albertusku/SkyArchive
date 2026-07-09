import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import METEO_LOG_DIR
from Visualizer.dashboard_data import count_log_levels, filter_log_lines, format_log_message


st.set_page_config(page_title="Logs", layout="wide")
st.title("Logs")

if not Path(METEO_LOG_DIR).exists():
    st.warning("No existe el archivo de logs.")
    st.stop()

with open(METEO_LOG_DIR, "r") as file:
    log_content = file.readlines()[-500:]

counts = count_log_levels(log_content)

metric_cols = st.columns(4)
metric_cols[0].metric("INFO", counts["INFO"])
metric_cols[1].metric("ERROR", counts["ERROR"])
metric_cols[2].metric("WARNING", counts["WARNING"])
metric_cols[3].metric("DEBUG", counts["DEBUG"])

st.subheader("Filtros")
col1, col2, col3, col4 = st.columns(4)
with col1:
    show_info = st.checkbox("Info", value=True)
with col2:
    show_error = st.checkbox("Error", value=True)
with col3:
    show_warning = st.checkbox("Warning", value=True)
with col4:
    show_debug = st.checkbox("Debug", value=True)

filtered_log_content = filter_log_lines(
    log_content,
    show_info=show_info,
    show_error=show_error,
    show_warning=show_warning,
    show_debug=show_debug,
)
formatted_log_content = "".join(format_log_message(line) for line in filtered_log_content)
st.caption(f"Mostrando {len(filtered_log_content)} de {len(log_content)} lineas recientes")
st.markdown("".join(formatted_log_content.splitlines()[-500:]), unsafe_allow_html=True)
