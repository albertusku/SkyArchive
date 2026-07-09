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

METEO_VENV_DIR="${METEO_VENV_DIR:-${VENV_DIR:-${REMOTE_DIR}/meteo_python}}"
VENV_EXCLUDE_NAME="$(basename "$METEO_VENV_DIR")"

LOCAL_BACKUP_DIR="${CURRENT_DIR}/BK"
LOCAL_LOG_DIR="${CURRENT_DIR}/src/Logs"
REMOTE_LOG_DIR="${REMOTE_LOG_DIR:-${REMOTE_DIR}/src/Logs}"
LOG_FILE="${LOCAL_LOG_DIR}/deploy_$(date +'%Y-%m-%d_%H-%M-%S').log"

# Crear la carpeta de logs si no existe
mkdir -p "$LOCAL_LOG_DIR" "$LOCAL_BACKUP_DIR"

log() {
  echo "$*" | tee -a "$LOG_FILE"
}

CURRENT_TIME=$(date "+%Y-%m-%d %H:%M:%S")
FILENAME_TIME=$(date "+%Y%m%d_%H%M%S")  # Formato para el nombre de archivo
GIT_BRANCH=$(git rev-parse --abbrev-ref HEAD)
GIT_COMMIT=$(git log -1 --pretty=format:"%h - %s")

log "---------INICIANDO PROCESO DE DESPLIEGUE--------"
log "$(date): Iniciando despliegue..."

ssh -o BatchMode=yes -o ConnectTimeout=10 "${REMOTE_USER}@${REMOTE_HOST}" "test -d '${REMOTE_DIR}'"

log "---------CREANDO BACKUP DE LA RASPI--------"
TIMESTAMP=$(date +'%Y-%m-%d_%H-%M-%S')
BACKUP_TARGET="${LOCAL_BACKUP_DIR}/meteo_${TIMESTAMP}"
mkdir -p "$BACKUP_TARGET"
ssh "${REMOTE_USER}@${REMOTE_HOST}" "tar --exclude='./${VENV_EXCLUDE_NAME}' --exclude='./BK' -czf - -C '${REMOTE_DIR}' ." | tar -xzf - -C "$BACKUP_TARGET"

log "---------GUARDANDO DATOS IMPORTANTES--------"
"${CURRENT_DIR}/send_data.sh" toPC | tee -a "$LOG_FILE"
log "Copiando Procces.log desde la Raspberry Pi..."
scp "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_LOG_DIR}/Procces.log" "$LOCAL_LOG_DIR/" | tee -a "$LOG_FILE"

log "Eliminando marcas de despliegue antiguas..."
find "$CURRENT_DIR" -maxdepth 1 -type f -name "deployment_*.txt" -exec rm -v {} \; | tee -a "$LOG_FILE"

DEPLOYMENT_INFO_FILE="${CURRENT_DIR}/deployment_${FILENAME_TIME}.txt"
echo "Hora del lanzamiento: $CURRENT_TIME" > "$DEPLOYMENT_INFO_FILE"
echo "Rama de git: $GIT_BRANCH" >> "$DEPLOYMENT_INFO_FILE"
echo "Último commit: $GIT_COMMIT" >> "$DEPLOYMENT_INFO_FILE"

cat "$DEPLOYMENT_INFO_FILE" | tee -a "$LOG_FILE"

log "Creando archivo de marca de tiempo..."
touch "${LOCAL_BACKUP_DIR}/${TIMESTAMP}.txt"

log "---------GENERANDO UNIDADES SYSTEMD--------"
"${CURRENT_DIR}/TargetEnv/render_services.sh" | tee -a "$LOG_FILE"

log "---------SUBIENDO DATOS A LA RASPBERRY--------"
rsync -av \
  --exclude='.git/' \
  --exclude='BK/' \
  --exclude="${VENV_EXCLUDE_NAME}/" \
  --exclude='deploy.meteo.env' \
  --exclude='__pycache__/' \
  --exclude='*.pyc' \
  --exclude='src/Logs/*.log' \
  --exclude='src/Data_storage/Storage/Procces.log' \
  "$CURRENT_DIR/" "${REMOTE_USER}@${REMOTE_HOST}:${REMOTE_DIR}/" | tee -a "$LOG_FILE"

log "---------DESPLEGANDO UNIDADES SYSTEMD--------"
ssh "${REMOTE_USER}@${REMOTE_HOST}" \
  "sudo install -m 0644 '${REMOTE_DIR}/TargetEnv/generated/'*.service /etc/systemd/system/ && sudo install -m 0644 '${REMOTE_DIR}/TargetEnv/'*.timer /etc/systemd/system/ && sudo systemctl daemon-reload" | tee -a "$LOG_FILE"

log "---------DESPLIEGUE COMPLETADO--------"
log "$(date): Despliegue finalizado correctamente."
