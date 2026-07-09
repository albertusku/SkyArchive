#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

"${SCRIPT_DIR}/render_services.sh"

sudo install -m 0644 "${SCRIPT_DIR}/generated/"*.service /etc/systemd/system/
sudo install -m 0644 "${SCRIPT_DIR}/"*.timer /etc/systemd/system/
sudo systemctl daemon-reload

echo "Unidades systemd instaladas. Activa el timer con:"
echo "  sudo systemctl enable --now 30min.timer"
