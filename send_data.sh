#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CURRENT_DIR="$SCRIPT_DIR"
DEPLOY_ENV="${CURRENT_DIR}/deploy.meteo.env"

if [ -f "$DEPLOY_ENV" ]; then
  # shellcheck disable=SC1090
  source "$DEPLOY_ENV"
fi

require_config() {
  local name="$1"
  if [ -z "${!name:-}" ]; then
    echo "ERROR: falta configurar ${name} en ${DEPLOY_ENV}"
    exit 1
  fi
}

require_config REMOTE_USER
require_config REMOTE_HOST
require_config REMOTE_DIR

REMOTE_STORAGE_DIR="${REMOTE_STORAGE_DIR:-${REMOTE_DIR}/src/Data_storage/Storage}"
REMOTE_PATH="${REMOTE_PATH:-${REMOTE_STORAGE_DIR%/}/}"
LOCAL_PATH="${CURRENT_DIR}/src/Data_storage/Storage/"
LOG_DIR="${CURRENT_DIR}/src/Logs"
LOG_FILE="${LOG_DIR}/pull_data_$(date +'%Y-%m-%d_%H-%M-%S').log"

# Crear la carpeta de logs si no existe
mkdir -p "$LOG_DIR" "$LOCAL_PATH"

log() {
  echo "$*" | tee -a "$LOG_FILE"
}

log "--------- INICIANDO TRANSFERENCIA DE DATOS ---------"
log "$(date): Iniciando sincronización de archivos..."

# Lista de archivos a transferir
FILES=(
  "Historical_weather.csv"
  "Statistics_day.csv"
  "Statistics_month.csv"
  "Historical_weather_forecast.csv"
  "Electricity_consumption.csv"
  "Electricity_production.csv"
  "Statistics_consumption.csv"
  "Statistics_production.csv"
  "Water_reserve.csv"
  "Season_prediction.csv"
)
# Verificar que se haya proporcionado un argumento
if [ "$#" -ne 1 ]; then
  echo "Uso: $0 [toPC|toPi]"
  exit 1
fi

DIRECTION=$1

if [ "$DIRECTION" != "toPC" ] && [ "$DIRECTION" != "toPi" ]; then
  echo "Argumento inválido: $DIRECTION. Use 'toPC' o 'toPi'."
  exit 1
fi

ssh -o BatchMode=yes -o ConnectTimeout=10 "${REMOTE_USER}@${REMOTE_HOST}" "test -d '${REMOTE_PATH}'"

if [ "$DIRECTION" == "toPC" ]; then
  for FILE in "${FILES[@]}"; do
    REMOTE_FILE="$FILE"
    LEGACY_FILE="${FILE/Statistics/Sta"distics"}"
    if ! ssh -o BatchMode=yes -o ConnectTimeout=10 "${REMOTE_USER}@${REMOTE_HOST}" "test -f '${REMOTE_PATH}${REMOTE_FILE}'" \
      && [ "$LEGACY_FILE" != "$FILE" ] \
      && ssh -o BatchMode=yes -o ConnectTimeout=10 "${REMOTE_USER}@${REMOTE_HOST}" "test -f '${REMOTE_PATH}${LEGACY_FILE}'"; then
      REMOTE_FILE="$LEGACY_FILE"
    fi

    log "Sincronizando $FILE..."
    rsync -avz --progress "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}${REMOTE_FILE}" "${LOCAL_PATH}${FILE}" | tee -a "$LOG_FILE"
    log "$FILE sincronizado correctamente."
  done
else
  for FILE in "${FILES[@]}"; do
    LOCAL_FILE="${LOCAL_PATH}${FILE}"
    LEGACY_FILE="${FILE/Statistics/Sta"distics"}"
    if [ ! -f "$LOCAL_FILE" ] && [ "$LEGACY_FILE" != "$FILE" ] && [ -f "${LOCAL_PATH}${LEGACY_FILE}" ]; then
      LOCAL_FILE="${LOCAL_PATH}${LEGACY_FILE}"
    fi

    if [ ! -f "$LOCAL_FILE" ]; then
      log "ERROR: no existe ${LOCAL_PATH}${FILE}"
      exit 1
    fi
    log "Sincronizando $FILE a Raspberry Pi..."
    rsync -avz --progress "$LOCAL_FILE" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_PATH}${FILE}" | tee -a "$LOG_FILE"
    log "$FILE sincronizado correctamente a Raspberry Pi."
  done
fi
