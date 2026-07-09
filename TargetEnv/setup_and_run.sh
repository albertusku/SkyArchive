#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOY_ENV="${REPO_DIR}/deploy.meteo.env"

if [ -f "${DEPLOY_ENV}" ]; then
  # shellcheck disable=SC1090
  source "${DEPLOY_ENV}"
fi

APP_DIR="${APP_DIR:-${REPO_DIR}}"
METEO_VENV_DIR="${METEO_VENV_DIR:-${VENV_DIR:-${APP_DIR}/meteo_python}}"
PYTHON_BIN="${METEO_VENV_DIR}/bin/python"

cd "${REPO_DIR}"

echo "Repositorio: ${REPO_DIR}"
echo "Entorno virtual: ${METEO_VENV_DIR}"

if [ ! -x "${PYTHON_BIN}" ]; then
  python3 -m venv "${METEO_VENV_DIR}"
fi

"${PYTHON_BIN}" -m pip install --upgrade pip
"${PYTHON_BIN}" -m pip install -r "${REPO_DIR}/requirements.txt"

if [ ! -f "${REPO_DIR}/src/API/data.json" ]; then
  cat <<EOF

Falta src/API/data.json.
Crea el archivo a partir de src/API/data.example.json y rellena tus credenciales antes de esperar datos reales:

  cp src/API/data.example.json src/API/data.json
  nano src/API/data.json

EOF
fi

"${SCRIPT_DIR}/install_services.sh"

sudo systemctl enable --now streamlit-dashboard.service
sudo systemctl enable --now 30min.timer

cat <<EOF

Setup completado.

Comprobaciones utiles:
  systemctl status streamlit-dashboard.service
  systemctl status 30min.timer
  journalctl -u streamlit-dashboard.service -f
  journalctl -u meteo_stats.service -f

EOF
