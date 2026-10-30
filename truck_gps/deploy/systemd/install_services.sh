#!/usr/bin/env bash
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
USER_NAME="$(whoami)"
HOME_DIR="${HOME}"
PYTHON_BIN="${PROJECT_DIR}/gps_env/bin/python"

if [[ ! -x "${PYTHON_BIN}" ]]; then
  echo "가상환경이 없습니다: ${PYTHON_BIN}"
  echo "먼저: python3 -m venv gps_env && pip install -r requirements.txt"
  exit 1
fi

write_unit() {
  local name="$1"
  local exec_cmd="$2"
  local after="${3:-network-online.target}"
  sudo tee "/etc/systemd/system/${name}" >/dev/null <<EOF
[Unit]
Description=${name%.service}
After=${after}
Wants=network-online.target

[Service]
Type=simple
User=${USER_NAME}
Group=${USER_NAME}
WorkingDirectory=${PROJECT_DIR}
ExecStart=${exec_cmd}
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF
}

echo "[1/5] Installing unit files (${USER_NAME}, ${PROJECT_DIR})..."
write_unit "gps-tracker.service" "${PYTHON_BIN} ${PROJECT_DIR}/gps_tracker.py"
write_unit "dashboard-server.service" "${PYTHON_BIN} ${PROJECT_DIR}/dashboard_server.py" "network-online.target gps-tracker.service"

echo "[2/5] Installing kiosk autostart entry..."
mkdir -p "${HOME_DIR}/.config/autostart"
DESKTOP_FILE="${HOME_DIR}/.config/autostart/truck-gps-dashboard.desktop"
sed "s|@HOME@|${HOME_DIR}|g" "${PROJECT_DIR}/deploy/systemd/truck-gps-dashboard.desktop" > "${DESKTOP_FILE}"
chmod +x "${PROJECT_DIR}/deploy/systemd/start-dashboard-kiosk.sh"

echo "[3/5] Reloading systemd daemon..."
sudo systemctl daemon-reload

echo "[4/5] Enabling services at boot..."
sudo systemctl enable gps-tracker.service dashboard-server.service

echo "[5/5] Done."
echo
echo "Enabled services:"
sudo systemctl is-enabled gps-tracker.service dashboard-server.service
echo
echo "Tip: start immediately (without reboot):"
echo "  sudo systemctl start gps-tracker.service dashboard-server.service"
echo "Desktop autostart:"
echo "  ${DESKTOP_FILE}"
