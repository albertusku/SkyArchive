import sys
from pathlib import Path

import streamlit as st

SRC_DIR = next(parent for parent in Path(__file__).resolve().parents if (parent / "config.py").exists())
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from config import TODO_FILE_DIR
from Visualizer.dashboard_data import read_text_file, write_text_file


st.set_page_config(page_title="TODO", layout="wide")
st.title("TODO")

content = read_text_file(TODO_FILE_DIR)
edited_text = st.text_area("Editar contenido", value=content, height=420)

col1, col2 = st.columns([1, 1])
with col1:
    if st.button("Guardar cambios", use_container_width=True):
        write_text_file(TODO_FILE_DIR, edited_text)
        st.success("Archivo guardado correctamente.")

with col2:
    if st.button("Recargar archivo", use_container_width=True):
        st.rerun()
