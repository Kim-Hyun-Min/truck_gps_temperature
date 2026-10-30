#!/usr/bin/env python3
"""
AWS IoT 장치 인증서 발급 API를 호출해 certs/ 폴더에 PEM 파일을 저장합니다.

사용 (Pi에서):
  1) config.py 에 DEVICE_ID, DEVICE_MAC 설정
  2) python3 provision_iot_cert.py
"""

import json
import os
import sys
import urllib.parse
import urllib.request

from config import (
    DEVICE_ID,
    DEVICE_MAC,
    IOT_CERT_API_URL,
    IOT_CERTS_DIR,
    MQTT_CA_CERT,
    MQTT_DEVICE_CERT,
    MQTT_PRIVATE_KEY,
    AMAZON_ROOT_CA_URL,
)


def detect_mac():
    """wlan0 → eth0 순으로 MAC 주소 자동 감지."""
    for iface in ("wlan0", "eth0"):
        path = f"/sys/class/net/{iface}/address"
        if os.path.isfile(path):
            with open(path, encoding="utf-8") as f:
                mac = f.read().strip().lower()
            if mac and mac != "00:00:00:00:00:00":
                return mac
    return None


def fetch_json(url):
    req = urllib.request.Request(url, method="GET")
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def download_file(url, dest):
    os.makedirs(os.path.dirname(dest), exist_ok=True)
    with urllib.request.urlopen(url, timeout=30) as resp:
        data = resp.read()
    with open(dest, "wb") as f:
        f.write(data)


def write_pem(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    text = content.strip() + "\n"
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    os.chmod(path, 0o600 if "key" in os.path.basename(path) else 0o644)


def main():
    device_id = (DEVICE_ID or "").strip()
    if not device_id:
        print("config.py 의 DEVICE_ID 를 설정하세요.", file=sys.stderr)
        sys.exit(1)

    mac = (DEVICE_MAC or "").strip().lower()
    if not mac or mac == "auto":
        mac = detect_mac()
    if not mac:
        print("MAC 주소를 config.py DEVICE_MAC 에 입력하거나 네트워크 인터페이스를 확인하세요.", file=sys.stderr)
        sys.exit(1)

    query = urllib.parse.urlencode({"deviceId": device_id, "mac": mac})
    url = f"{IOT_CERT_API_URL}?{query}"
    print(f"인증서 요청: deviceId={device_id}, mac={mac}")

    try:
        body = fetch_json(url)
    except Exception as e:
        print(f"API 호출 실패: {e}", file=sys.stderr)
        sys.exit(1)

    cert_pem = body.get("certificatePem")
    private_key = (body.get("keyPair") or {}).get("PrivateKey")
    if not cert_pem or not private_key:
        print(f"응답에 인증서가 없습니다: {json.dumps(body, ensure_ascii=False)[:500]}", file=sys.stderr)
        sys.exit(1)

    os.makedirs(IOT_CERTS_DIR, exist_ok=True)
    write_pem(MQTT_DEVICE_CERT, cert_pem)
    write_pem(MQTT_PRIVATE_KEY, private_key)

    if not os.path.isfile(MQTT_CA_CERT):
        print(f"Amazon Root CA 다운로드 → {MQTT_CA_CERT}")
        download_file(AMAZON_ROOT_CA_URL, MQTT_CA_CERT)

    print("저장 완료:")
    print(f"  {MQTT_DEVICE_CERT}")
    print(f"  {MQTT_PRIVATE_KEY}")
    print(f"  {MQTT_CA_CERT}")
    if body.get("certificateId"):
        print(f"  certificateId: {body['certificateId']}")
    print("\n다음: config.py 에 MQTT_USE_TLS = True 확인 후 gps-tracker 재시작")


if __name__ == "__main__":
    main()
