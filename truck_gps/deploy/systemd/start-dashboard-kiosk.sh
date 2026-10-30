#!/usr/bin/env bash
set -euo pipefail

URL="${TRUCK_GPS_DASHBOARD_URL:-http://127.0.0.1:5001}"
WAIT_SECONDS="${TRUCK_GPS_DASHBOARD_WAIT_SECONDS:-60}"
PROFILE_DIR="${HOME}/.config/chromium-truck-gps-kiosk"
PREF_DIR="${PROFILE_DIR}/Default"
PREF_FILE="${PREF_DIR}/Preferences"

if command -v chromium >/dev/null 2>&1; then
  BROWSER_BIN="chromium"
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER_BIN="chromium-browser"
else
  echo "Chromium not found" >&2
  exit 1
fi

# dashboard-server 서비스가 완전히 뜰 때까지 대기
for _ in $(seq 1 "${WAIT_SECONDS}"); do
  if curl -fsS "${URL}/api/latest" >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

mkdir -p "${PREF_DIR}"

# Chromium 번역/언어 제안 끄기 (플래그만으로는 Debian Chromium에서 부족한 경우 많음)
python3 - "${PREF_FILE}" <<'PY'
import json, os, sys

path = sys.argv[1]
data = {}
if os.path.exists(path):
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        data = {}

data.setdefault("translate", {})["enabled"] = False
data.setdefault("browser", {})["has_seen_welcome_page"] = True
data.setdefault("intl", {})
data["intl"]["accept_languages"] = "en-GB,en,ko-KR,ko"
data["intl"]["selected_languages"] = "en-GB,en"

with open(path, "w", encoding="utf-8") as f:
    json.dump(data, f, separators=(",", ":"))
PY

exec "${BROWSER_BIN}" \
  --kiosk \
  --app="${URL}" \
  --start-fullscreen \
  --force-device-scale-factor=1 \
  --high-dpi-support=1 \
  --window-size=1280,800 \
  --noerrdialogs \
  --disable-infobars \
  --disable-session-crashed-bubble \
  --no-first-run \
  --no-default-browser-check \
  --disable-default-apps \
  --disable-features=Translate,TranslateUI \
  --disable-translate \
  --lang=en-GB \
  --check-for-update-interval=31536000 \
  --user-data-dir="${PROFILE_DIR}"
