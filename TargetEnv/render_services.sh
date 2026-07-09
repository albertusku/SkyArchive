#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
DEPLOY_ENV="${REPO_DIR}/deploy.meteo.env"
OUTPUT_DIR="${SCRIPT_DIR}/generated"

if [ -f "$DEPLOY_ENV" ]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV"
fi

SERVICE_USER="${SERVICE_USER:-${REMOTE_USER:-$(id -un)}}"
APP_DIR="${APP_DIR:-${REMOTE_DIR:-${REPO_DIR}}}"
METEO_VENV_DIR="${METEO_VENV_DIR:-${VENV_DIR:-${APP_DIR}/meteo_python}}"
VENV_DIR="${METEO_VENV_DIR}"
DASHBOARD_PORT="${DASHBOARD_PORT:-8502}"
DASHBOARD_ADDRESS="${DASHBOARD_ADDRESS:-0.0.0.0}"

escape_sed_replacement() {
  printf '%s' "$1" | sed 's/[|&\\]/\\&/g'
}

service_user="$(escape_sed_replacement "$SERVICE_USER")"
app_dir="$(escape_sed_replacement "$APP_DIR")"
venv_dir="$(escape_sed_replacement "$VENV_DIR")"
dashboard_port="$(escape_sed_replacement "$DASHBOARD_PORT")"
dashboard_address="$(escape_sed_replacement "$DASHBOARD_ADDRESS")"

mkdir -p "$OUTPUT_DIR"

for template in "${SCRIPT_DIR}"/*.service.template; do
  output="${OUTPUT_DIR}/$(basename "${template%.template}")"
  sed \
    -e "s|{{SERVICE_USER}}|${service_user}|g" \
    -e "s|{{APP_DIR}}|${app_dir}|g" \
    -e "s|{{VENV_DIR}}|${venv_dir}|g" \
    -e "s|{{DASHBOARD_PORT}}|${dashboard_port}|g" \
    -e "s|{{DASHBOARD_ADDRESS}}|${dashboard_address}|g" \
    "$template" > "$output"
done

echo "Unidades systemd generadas en ${OUTPUT_DIR}"
