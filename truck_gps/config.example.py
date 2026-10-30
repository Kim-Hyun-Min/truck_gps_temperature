# GPS 트럭 위치 추적 시스템 설정 (템플릿)
# Pi 배포 시:  cp config.example.py config.py  후  ★ 표시 항목만 수정

# 데이터베이스 설정
DB_PATH = "truck_gps.db"

# GPS 설정
GPS_PORT = "/dev/ttyACM0"
GPS_BAUDRATE = 9600

# 데이터 수집 설정
SAMPLE_RATE = 10
INTERVAL = 1.0 / SAMPLE_RATE

RETENTION_SECONDS = 1200
DASHBOARD_TEMP_CHART_SECONDS = 90

# 온도 센서 설정
TEMP_SENSOR_TYPE = "MCP9600"
MCP9600_THERMOCOUPLE_TYPE = "K"
MCP9600_I2C_ADDRESS = 0x67          # ★ i2cdetect 결과 (예: 0x67). 모르면 None
MCP9600_I2C_ADDRESS_CANDIDATES = [0x60, 0x67, 0x66, 0x61, 0x65, 0x62, 0x64, 0x63]
MCP9600_TC_FILTER = 1

TEMP_RANGES = {
    'critical_cold': (-float('inf'), 2.0),
    'cold': (2.0, 2.5),
    'normal': (2.5, 7.5),
    'warm': (7.5, 8.0),
    'critical_hot': (8.0, float('inf'))
}

import os

_PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
IOT_CERTS_DIR = os.path.join(_PROJECT_DIR, "certs")

# ========== ★ AWS IoT 장치 등록 (Pi마다 다름) ==========
IOT_CERT_API_URL = "https://nvtd07etc1.execute-api.ap-northeast-2.amazonaws.com/dev/cert"
DEVICE_ID = "testId"                # ★ 장치명 (cert API deviceId)
DEVICE_MAC = "02:03:04:05:06:07"    # ★ MAC (비우면 wlan0/eth0 자동)
AMAZON_ROOT_CA_URL = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"

# ========== ★ MQTT 전송 설정 ==========
# AWS IoT Core 사용: MQTT_USE_TLS = True
# 일반 브로커(13.125.57.204:1883) 사용: MQTT_USE_TLS = False
MQTT_USE_TLS = True

MQTT_BROKER_HOST = "a3mec6722qtch0-ats.iot.ap-northeast-2.amazonaws.com"
MQTT_BROKER_PORT = 8883
# 일반 MQTT만 쓸 때:
# MQTT_USE_TLS = False
# MQTT_BROKER_HOST = "13.125.57.204"
# MQTT_BROKER_PORT = 1883

MQTT_TOPIC = "truck/gps_temp"
MQTT_CLIENT_ID = "testId"           # ★ DEVICE_ID 와 동일 권장
MQTT_QOS = 1
MQTT_RETAIN = False

MQTT_CA_CERT = os.path.join(IOT_CERTS_DIR, "AmazonRootCA1.pem")
MQTT_DEVICE_CERT = os.path.join(IOT_CERTS_DIR, "device-cert.pem")
MQTT_PRIVATE_KEY = os.path.join(IOT_CERTS_DIR, "private-key.pem")

# ========== ★ 차량 ID (대시보드 표시) ==========
VEHICLE_ID = "testId"               # ★ Pi마다 V001, V002, V003 ... (인증서와 동일)

SEND_INTERVAL = 0.1
BATCH_SIZE = 1

DASHBOARD_HOST = "0.0.0.0"
DASHBOARD_PORT = 5001

REVERSE_GEOCODE_API_URL = "http://api.bigdatacloud.net/data/reverse-geocode-client"
REVERSE_GEOCODE_API_LANGUAGE = "ko"
CONNECTIVITY_CHECK_URL = "http://connectivitycheck.gstatic.com/generate_204"

LOG_LEVEL = "INFO"
LOG_FILE = "gps_tracker.log"
VERBOSE_LOGS = False
LOG_REPEAT_INTERVAL = 30
