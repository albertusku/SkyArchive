#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
METEO_VENV_DIR="${METEO_VENV_DIR:-${REPO_DIR}/meteo_python}"

source "${METEO_VENV_DIR}/bin/activate"
streamlit run "${REPO_DIR}/src/Visualizer/Today_page.py" --server.port 8502 --server.address 0.0.0.0
deactivate
