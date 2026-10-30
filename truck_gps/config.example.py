# GPS 트럭 위치 추적 시스템 설정 (템플릿)
# 사용: cp config.example.py config.py  후 아래 빈 문자열("") 항목을 실제 값으로 채우세요.

# 데이터베이스 설정
DB_PATH = "truck_gps.db"

# GPS 설정
# NK-GPS-U는 보통 /dev/ttyACM0 또는 /dev/ttyUSB0로 인식됩니다
# 실제 포트는 'ls -l /dev/ttyACM* /dev/ttyUSB*' 명령으로 확인하세요
GPS_PORT = "/dev/ttyACM0"  # 우선 시도 포트 (고정 전용이 아님)
# 재연결 시 GPS_PORT 다음으로 순회. NMEA($GP/$GN)가 나오는 포트를 사용
GPS_PORT_GLOBS = ["/dev/ttyACM*", "/dev/ttyUSB*"]
GPS_BAUDRATE = 9600        # NK-GPS-U 기본 통신 속도 (9600 또는 38400)

# 데이터 수집 설정
# GPS가 초당 1개만 보내더라도 마지막 데이터를 반복 저장
SAMPLE_RATE = 10  # 초당 샘플 수
INTERVAL = 1.0 / SAMPLE_RATE  # 샘플 간격 (0.1초)

# 보관(정리) 설정
RETENTION_SECONDS = 1200  # SQLite 저장 데이터 보관 기간(초) = 20분

# 대시보드 온도 차트에 표시할 최근 구간(초). 짧을수록 변화가 잘 보임 (권장 60~120)
DASHBOARD_TEMP_CHART_SECONDS = 90

# 온도 센서 설정
TEMP_SENSOR_TYPE = "MCP9600"  # MCP9600, DS18B20, DHT22
# MCP9600: K·J 등 열전대 + I2C 증폭기 (코드는 핫 접합 온도만 사용, Adafruit 드라이버 파싱)
# DS18B20: 1-Wire | DHT22: GPIO4

# MCP9600 전용 (TEMP_SENSOR_TYPE == "MCP9600" 일 때)
MCP9600_THERMOCOUPLE_TYPE = "K"  # "K", "J", "T" … 실제 프로브와 동일해야 함
MCP9600_I2C_ADDRESS = None  # None이면 후보 주소 순으로 탐색. i2cdetect 값이 하나면 0x60 등으로 고정 권장
MCP9600_I2C_ADDRESS_CANDIDATES = [0x60, 0x67, 0x66, 0x61, 0x65, 0x62, 0x64, 0x63]
MCP9600_TC_FILTER = 1  # 0~7, 급격한 스파이크 완화 (0=필터 없음)

# 온도 상태 범위 설정 (백신 운송 기준)
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

# ========== AWS IoT 장치 등록 ==========
# python3 provision_iot_cert.py 로 인증서를 받을 때 사용합니다.
IOT_CERT_API_URL = ""  # 인증서 발급 API 주소 (담당자에게 받은 URL)
DEVICE_ID = ""  # 이 장치의 이름. AWS IoT Thing 이름과 같게 넣는 것을 권장
DEVICE_MAC = "auto"  # "auto"면 wlan0/eth0 MAC을 자동으로 씀. 고정하려면 "aa:bb:cc:dd:ee:ff" 형식
AMAZON_ROOT_CA_URL = "https://www.amazontrust.com/repository/AmazonRootCA1.pem"  # 아마존 공개 Root CA. 보통 그대로 둠

# ========== MQTT 전송 ==========
# True  → AWS IoT Core (보통 포트 8883, certs/ 인증서 필요)
# False → 일반 MQTT 브로커 (보통 포트 1883, 인증서 없음)
MQTT_USE_TLS = True

MQTT_BROKER_HOST = ""  # 브로커 주소. AWS면 IoT 엔드포인트, 일반 MQTT면 서버 IP 또는 도메인
MQTT_BROKER_PORT = 8883  # AWS IoT는 8883, 일반 MQTT는 1883
MQTT_TOPIC = ""  # 발행 토픽. 예: 프로젝트명/장치ID/out
MQTT_CLIENT_ID = ""  # MQTT 접속 이름. AWS IoT면 DEVICE_ID와 같게
MQTT_QOS = 1  # 0: 최대 한 번, 1: 최소 한 번 (권장)
MQTT_RETAIN = False  # True면 브로커가 마지막 메시지를 보관

# TLS 인증서 파일 경로. provision_iot_cert.py 또는 save_iot_certs.py 가 certs/ 에 만듦
MQTT_CA_CERT = os.path.join(IOT_CERTS_DIR, "AmazonRootCA1.pem")
MQTT_DEVICE_CERT = os.path.join(IOT_CERTS_DIR, "device-cert.pem")
MQTT_PRIVATE_KEY = os.path.join(IOT_CERTS_DIR, "private-key.pem")

# 차량 ID. 대시보드·DB에 표시됨. DEVICE_ID와 맞추는 것을 권장
VEHICLE_ID = ""

# 전송 설정
SEND_INTERVAL = 60  # 서버 전송 간격 (초), 실시간 전송(초당 10회) 목표
BATCH_SIZE = 1  # 한 번에 전송할 데이터 개수 (가장 최신 1개)

# 대시보드 서버 설정
DASHBOARD_HOST = "0.0.0.0"  # 대시보드 서버 바인드 주소 (0.0.0.0 = 모든 인터페이스)
DASHBOARD_PORT = 5001  # 대시보드 서버 포트

# 외부 API 설정 (리버스 지오코딩 등)
REVERSE_GEOCODE_API_URL = "http://api.bigdatacloud.net/data/reverse-geocode-client"
REVERSE_GEOCODE_API_LANGUAGE = "ko"  # 한국어
CONNECTIVITY_CHECK_URL = "http://connectivitycheck.gstatic.com/generate_204"

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FILE = "gps_tracker.log"
# True면 반복 로그를 매번 출력. False면 장애 로그는 LOG_REPEAT_INTERVAL 초마다 최대 1회
VERBOSE_LOGS = False
LOG_REPEAT_INTERVAL = 30

