#!/usr/bin/env python3
"""
certs/iot_credentials.json 에 붙여넣은 인증서를 PEM 파일로 저장합니다.

사용 (Pi에서):
  1) cp certs/iot_credentials.json.example certs/iot_credentials.json
  2) nano certs/iot_credentials.json  ← API 응답 값 붙여넣기
  3) python3 save_iot_certs.py
"""

import json
import os
import sys
import urllib.request

from config import (
    AMAZON_ROOT_CA_URL,
    IOT_CERTS_DIR,
    MQTT_CA_CERT,
    MQTT_DEVICE_CERT,
    MQTT_PRIVATE_KEY,
)

CREDENTIALS_JSON = os.path.join(IOT_CERTS_DIR, "iot_credentials.json")


def download_file(url, dest):
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


def load_credentials():
    if not os.path.isfile(CREDENTIALS_JSON):
        example = os.path.join(IOT_CERTS_DIR, "iot_credentials.json.example")
        print(f"{CREDENTIALS_JSON} 이 없습니다.", file=sys.stderr)
        print(f"  cp {example} {CREDENTIALS_JSON}", file=sys.stderr)
        print("  nano 로 certificatePem, privateKey 를 붙여넣으세요.", file=sys.stderr)
        sys.exit(1)
    with open(CREDENTIALS_JSON, encoding="utf-8") as f:
        return json.load(f)


def main():
    body = load_credentials()

    cert_pem = body.get("certificatePem")
    private_key = body.get("privateKey")
    if not private_key and isinstance(body.get("keyPair"), dict):
        private_key = body["keyPair"].get("PrivateKey")

    if not cert_pem or "붙여넣기" in cert_pem:
        print("certificatePem 을 iot_credentials.json 에 입력하세요.", file=sys.stderr)
        sys.exit(1)
    if not private_key or "붙여넣기" in private_key:
        print("privateKey 를 iot_credentials.json 에 입력하세요.", file=sys.stderr)
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
    if body.get("deviceId"):
        print(f"  deviceId: {body['deviceId']}")
    print("\n다음: config.py 에 MQTT_USE_TLS = True 확인 후 gps-tracker 재시작")


if __name__ == "__main__":
    main()
