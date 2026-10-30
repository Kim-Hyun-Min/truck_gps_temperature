# 🚛 백신 운송 차량 모니터링 시스템

라즈베리파이에서 실시간으로 트럭의 GPS 위치와 냉장고 온도를 수집하고, 로컬 데이터베이스에 저장하며 MQTT로 전송하는 시스템입니다.

## 📋 목차
- [주요 기능](#주요-기능)
- [시스템 구조](#시스템-구조)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)
- [웹 대시보드](#웹-대시보드)
- [코드 구조 상세 설명](#코드-구조-상세-설명)
- [데이터베이스](#데이터베이스)
- [문제 해결](#문제-해결)

---

## 주요 기능

### ✅ 실시간 GPS + 온도 데이터 수집/전송
- **GPS 데이터**: 위도, 경도, 고도, 속도, 방향
- **온도 데이터**: MCP9600 센서 또는 시뮬레이터 (백신 운송용 2°C ~ 8°C 범위)
- **데이터 저장/전송**: 0.1초 간격(초당 10회)으로 수집·저장, 저장 직후 MQTT로 즉시 전송
- **자동 데이터 관리**: 20분 이후 데이터 자동 삭제

### ✅ 웹 대시보드 (Flask + Chart.js)
- **실시간 모니터링**: 온도 그래프, GPS 위치, 상태 표시
- **역지오코딩**: 위도/경도를 주소로 변환 (BigDataCloud API)
- **상태 표시**: 인터넷 연결, 온도 센서 연결 상태
- **온도 경고**: 적정 범위(2~8°C)를 벗어나면 시각적 경고
- **모니터 출력 최적화**: 10.1인치 디스플레이에 맞춘 UI

### ✅ 온도 상태 모니터링 (백신 운송용)
- **온도 범위**: 2°C ~ 8°C (백신 적정 보관 온도)
- **상태 분류**:
  - `critical_cold`: < 2.0°C (위험한 추위)
  - `cold`: 2.0°C ~ 2.5°C (추위)
  - `normal`: 2.5°C ~ 7.5°C (정상)
  - `warm`: 7.5°C ~ 8.0°C (따뜻함)
  - `critical_hot`: > 8.0°C (위험한 더위)

### ✅ 서버 전송 시스템 (MQTT 전용)
- **자동 전송**: 0.1초마다 1개 메시지 발행(QoS 1)
- **중복 방지**: 로컬 DB에 `sent` 플래그로 전송 완료 상태 저장
- **모니터링**: 로그로 전송 성공/실패 확인

---

## 시스템 구조

### 📁 파일 구조

```
truck_gps/
├── config.py              # 설정 파일 (MQTT, GPS, 온도 센서 등)
├── database.py            # SQLite 데이터베이스 관리 클래스
├── gps_tracker.py         # 메인 프로그램 (실행 파일)
├── gps_reader.py          # 실제 GPS 하드웨어 인터페이스
├── gps_simulator.py       # GPS 시뮬레이터 (테스트용)
├── temperature_reader.py  # 실제 온도 센서 인터페이스 (MCP9600)
├── temperature_simulator.py # 온도 시뮬레이터
├── server_sender.py       # MQTT 서버 전송 클래스
├── dashboard_server.py    # 웹 대시보드 Flask 서버
├── templates/
│   └── index.html         # 대시보드 HTML/JS/CSS
├── requirements.txt       # Python 패키지 의존성
├── README.md              # 이 문서
├── gps_tracker.log        # 로그 파일
└── truck_gps.db           # SQLite 데이터베이스
```

### 🔄 데이터 흐름

```
┌─────────────────────────────────────────────────────┐
│           gps_tracker.py (메인 프로그램)              │
│  ┌─────────────────────────────────────────────┐    │
│  │  1. setup()                                 │    │
│  │     - 데이터베이스 초기화                   │    │
│  │     - GPS 리더 선택 (실제/시뮬레이터)       │    │
│  │     - 온도 리더 초기화                      │    │
│  │     - MQTT 전송기 시작                      │    │
│  │                                             │    │
│  │  2. start() - 메인 루프                     │    │
│  │     ┌─────────────────────────────────┐    │    │
│  │     │  While running:                 │    │    │
│  │     │    → GPS 데이터 읽기            │    │    │
│  │     │    → 온도 데이터 읽기           │    │    │
│  │     │    → 유효성 검증                │    │    │
│  │     │    → DB에 저장                  │    │    │
│  │     │    → MQTT로 전송                │    │    │
│  │     │    → 20분 이상 데이터 삭제      │    │    │
│  │     │    → 로그 출력 (100개마다)      │    │    │
│  │     │    → 타이밍 조정 (0.1초 간격)   │    │    │
│  │     └─────────────────────────────────┘    │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         ↓                         ↓              ↓
    ┌──────────┐             ┌──────────┐   ┌──────────┐
    │ GPS      │             │ 온도     │   │ MQTT     │
    │ Reader   │             │ Reader   │   │ Broker   │
    └──────────┘             └──────────┘   └──────────┘
         ↓                         ↓              ↑
         └─────────────────────────┴──────────────┘
                         ↓
                  SQLite DB 저장
```

---

## 시스템 요구사항

### 하드웨어
- **라즈베리파이**: 3, 4, Zero W 등 모든 모델
- **GPS 모듈** (선택사항):
  - **USB GPS**: NK-GPS-U, NEO-6M, NEO-7M, BU-353S4
  - **UART GPS**: GPIO 연결 가능 모듈
- **온도 센서** (선택사항):
  - **MCP9600**: I2C 열전대 증폭기 (권장)
  - **DS18B20**: 1-Wire 온도 센서
  - **DHT22**: 온습도 센서
- **메모리**: 최소 512MB RAM
- **저장 공간**: 약 50-100MB (20분 데이터)

### 소프트웨어
- **Python**: 3.7 이상
- **OS**: 라즈베리파이 OS (Raspbian) 또는 다른 리눅스 배포판

---

## 설치 방법

### 1️⃣ 라즈베리파이 SSH 접속

```bash
ssh 사용자명@라즈베리파이IP
```

### 2️⃣ 가상환경 생성 및 패키지 설치

```bash
cd ~/truck_gps

# 가상환경 생성
python3 -m venv gps_env

# 가상환경 활성화
source gps_env/bin/activate

# 패키지 설치
pip install -r requirements.txt
```

**또는 시스템 전역 설치:**
```bash
pip3 install -r requirements.txt --break-system-packages
```

### 3️⃣ GPS 포트 확인 (실제 GPS 사용 시)

```bash
# 연결된 포트 확인
ls /dev/ttyUSB* /dev/ttyACM* /dev/serial*

# 포트 권한 설정 (필요시)
sudo usermod -a -G dialout $USER
# 재로그인 필요
```

### 4️⃣ 설정 파일 수정

```bash
nano config.py
```

**주요 설정:**
```python
# GPS 포트
GPS_PORT = "/dev/ttyACM0"  # 실제 포트로 변경

# MQTT 브로커 설정
MQTT_BROKER_HOST = "106.254.226.206"  # 브로커 IP
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "truck/gps_temp"

# 차량 ID
VEHICLE_ID = "V001"

# 온도 센서 타입
TEMP_SENSOR_TYPE = "MCP9600"  # MCP9600, DS18B20, DHT22, "SIMULATOR"
```

---

## 사용 방법

### ▶️ 기본 실행

**GPS + 온도 추적 시작:**
```bash
cd ~/truck_gps
source gps_env/bin/activate
python gps_tracker.py
```

**출력 예시:**
```
2025-10-15 13:47:35 - INFO - GPS 추적 시스템 초기화 중...
2025-10-15 13:47:35 - INFO - 데이터베이스 연결 성공: truck_gps.db
2025-10-15 13:47:35 - INFO - MQTT 전송기 초기화: truck/gps_temp
2025-10-15 13:47:35 - INFO - GPS 리더 초기화 완료
2025-10-15 13:47:35 - INFO - 온도 리더 초기화 완료 (MCP9600)
2025-10-15 13:47:35 - INFO - GPS 데이터 수집 시작 (초당 10개 샘플)
2025-10-15 13:47:45 - INFO - 샘플 #100 | 온도: 5.2°C | 상태: normal
```

### ⏹️ 종료

```bash
# Ctrl+C 누르기
# 또는
pkill -f gps_tracker.py
```

### 🔄 백그라운드 실행

```bash
# 백그라운드로 실행
nohup python gps_tracker.py > output.log 2>&1 &

# 프로세스 확인
ps aux | grep gps_tracker

# 로그 실시간 확인
tail -f gps_tracker.log
```

---

## 웹 대시보드

### 🖥️ 대시보드 서버 시작

**터미널 1 - GPS 추적:**
```bash
cd ~/truck_gps
source gps_env/bin/activate
python gps_tracker.py
```

**터미널 2 - 대시보드:**
```bash
cd ~/truck_gps
source gps_env/bin/activate
python dashboard_server.py
```

**브라우저 접속:**
```
http://localhost:5000
# 또는
http://라즈베리파이IP:5000
```

### 📊 대시보드 기능

1. **실시간 온도 그래프**
   - 최근 2분 온도 히스토리
   - 2°C, 8°C 임계선 표시
   - 현재 측정 온도 표시
   - 온도 범위에 따른 색상 표시

2. **현재 위치 표시**
   - 위도/경도 수치
   - 역지오코딩 주소 (예: "광주광역시 북구")
   - 갱신 시간 표시

3. **상태 표시**
   - 인터넷 연결 상태
   - 온도 센서 연결 상태
   - 온도 상태 (적정/경고/위험)
   - 저장된 데이터 개수

4. **디바이스 정보**
   - 차량 ID
   - 현재 시간
   - 연결 상태

### ⚙️ 대시보드 포트 변경

```bash
# dashboard_server.py 파일 수정
nano dashboard_server.py
```

```python
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)  # 5001로 변경
```

---

## 코드 구조 상세 설명

### 1️⃣ `config.py` - 설정 관리

**역할:** 시스템 전체의 설정을 중앙 관리

```python
# 데이터베이스 설정
DB_PATH = "truck_gps.db"
RETENTION_SECONDS = 1200  # 20분

# GPS 설정
GPS_PORT = "/dev/ttyACM0"
GPS_BAUDRATE = 9600

# 데이터 수집 설정
SAMPLE_RATE = 10  # 초당 10개
INTERVAL = 1.0 / SAMPLE_RATE

# 온도 센서 설정
TEMP_SENSOR_TYPE = "MCP9600"

# 온도 상태 범위 설정 (백신 운송 기준)
TEMP_RANGES = {
    'critical_cold': (-float('inf'), 2.0),
    'cold': (2.0, 2.5),
    'normal': (2.5, 7.5),
    'warm': (7.5, 8.0),
    'critical_hot': (8.0, float('inf'))
}

# MQTT 브로커 설정
MQTT_BROKER_HOST = "106.254.226.206"
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "truck/gps_temp"
MQTT_CLIENT_ID = "truck_gps_client"
MQTT_QOS = 1

# 차량 설정
VEHICLE_ID = "V001"

# 전송 설정
SEND_INTERVAL = 0.1  # 0.1초마다 전송
BATCH_SIZE = 1       # 1개씩 전송
RETRY_ATTEMPTS = 3
RETRY_DELAY = 1

# 로깅 설정
LOG_LEVEL = "INFO"
LOG_FILE = "gps_tracker.log"
```

---

### 2️⃣ `database.py` - 데이터베이스 관리

**역할:** SQLite 데이터베이스 CRUD 작업 및 자동 정리

```python
class GPSDatabase:
    def __init__(self, db_path=DB_PATH)
    def connect(self)
    def create_tables(self)
    def insert_gps_temperature_data(...)  # GPS + 온도 삽입
    def get_latest_data(self, limit=10)   # 최근 데이터 조회
    def get_unsent_gps_temperature_data(limit)  # 미전송 데이터 조회
    def mark_data_as_sent(data_ids)       # 전송 완료 표시
    def purge_older_than_seconds(max_age_seconds)  # 오래된 데이터 삭제
    def close(self)
```

**핵심 메서드:**
- `insert_gps_temperature_data()`: GPS + 온도 데이터 저장
- `get_unsent_gps_temperature_data()`: 전송 안 된 데이터만 조회
- `purge_older_than_seconds()`: RETENTION_SECONDS 이후 데이터 삭제

---

### 3️⃣ `gps_tracker.py` - 메인 프로그램

**역할:** 전체 시스템 통합 및 실행

```python
class GPSTracker:
    def __init__(self)
    def setup(self)              # 초기화
    def start(self)              # 메인 루프 시작
    def stop(self)               # 종료
    def signal_handler(...)      # Ctrl+C 처리
    
    # 온도 상태 판단
    def get_temperature_status(self, temperature)
```

**메인 루프 흐름:**
1. GPS 데이터 읽기
2. 온도 데이터 읽기
3. 유효성 검증
4. DB에 저장
5. 로그 출력 (100개마다)
6. 타이밍 조정 (0.1초 간격)
7. 20분 이상 데이터 자동 삭제

---

### 4️⃣ `server_sender.py` - MQTT 전송

**역할:** SQLite DB에서 미전송 데이터를 읽어 MQTT로 전송

```python
class ServerSender:
    def __init__(self, db_path)
    def start(self)              # 전송 스레드 시작
    def stop(self)
    def _get_unsent_data(limit)  # 미전송 데이터 조회
    def _send_data(data)         # MQTT 전송
    def _mark_data_as_sent(ids)  # 전송 완료 표시
    def _get_temperature_status(temp)  # 온도 상태 판단
```

**전송 데이터 형식:**
```json
{
  "vehicle_id": "V001",
  "timestamp": "2025-10-15T13:47:35.362449",
  "data": [
    {
      "id": 123,
      "vehicle_id": "V001",
      "timestamp": "2025-10-15T13:47:35.362449",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "altitude": 45.2,
      "speed": 60.5,
      "heading": 180.0,
      "temperature": 5.2,
      "status": "normal"
    }
  ]
}
```

---

### 5️⃣ `dashboard_server.py` - 웹 대시보드

**역할:** Flask 기반 웹 대시보드 제공

**API 엔드포인트:**
- `GET /`: 대시보드 HTML
- `GET /api/latest`: 최신 GPS+온도 데이터 1건
- `GET /api/temperature-series`: 최근 20분 온도 시리즈
- `GET /api/reverse-geocode`: 위도/경도 → 주소 변환
- `GET /api/health/internet`: 인터넷 연결 상태
- `GET /api/health/temperature`: 온도 센서 연결 상태

**데이터 정리:**
- `api_temperature_series`: RETENTION_SECONDS(20분) 기준 데이터만 조회
- 역지오코딩 캐싱: 3자리 위도/경도로 캐시하여 API 호출 최소화

---

### 6️⃣ `temperature_reader.py` - 온도 센서

**역할:** 실제 온도 센서에서 데이터 읽기

**지원 센서:**
- **MCP9600**: I2C 열전대 증폭기 (I2C 주소 0x67)
- **DS18B20**: 1-Wire 디지털 온도 센서
- **DHT22**: 온습도 센서

```python
class TemperatureReader:
    def __init__(self, sensor_type='MCP9600')
    def connect(self)
    def read(self)  # 온도 읽기
    def close()
    def get_temperature_status(temp)  # 상태 판단
```

---

## 데이터베이스

### 📊 테이블 구조: `gps_temperature_data`

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | INTEGER | 자동 증가 Primary Key | 1, 2, 3... |
| `vehicle_id` | TEXT | 차량 고유 식별자 | "V001" |
| `timestamp` | REAL | Unix 타임스탬프 | 1729004855.362 |
| `datetime` | TEXT | 날짜/시간 | "2025-10-15 13:47:35.362449" |
| `latitude` | REAL | 위도 | 37.5665 |
| `longitude` | REAL | 경도 | 126.9780 |
| `altitude` | REAL | 고도 (미터) | 45.2 |
| `speed` | REAL | 속도 (km/h) | 60.5 |
| `heading` | REAL | 방향 (도) | 180.0 |
| `temperature` | REAL | 온도 (°C) | 5.2 |
| `status` | TEXT | 온도 상태 | "normal" |
| `sent` | BOOLEAN | MQTT 전송 완료 여부 | TRUE/FALSE |
| `sent_at` | TIMESTAMP | 전송 완료 시간 | "2025-10-15 13:47:36" |
| `created_at` | TIMESTAMP | 데이터 생성 시간 | "2025-10-15 13:47:35" |

### 📈 성능 및 용량

| 항목 | 값 |
|------|------|
| 샘플링율 | 초당 10개 |
| 보관 기간 | 20분 (RETENTION_SECONDS) |
| 최대 데이터 개수 | 약 12,000개 |
| 레코드 크기 | 약 100-120 바이트 |
| DB 크기 | 1-2 MB |
| 자동 삭제 | 30초마다 오래된 데이터 정리 |

### 🔍 SQL 쿼리 예시

```sql
-- 최근 10개 데이터
SELECT datetime, latitude, longitude, temperature, status 
FROM gps_temperature_data 
ORDER BY timestamp DESC 
LIMIT 10;

-- 미전송 데이터
SELECT * FROM gps_temperature_data 
WHERE sent = FALSE OR sent IS NULL
ORDER BY timestamp DESC;

-- 온도 범위별 데이터 개수
SELECT status, COUNT(*) as count 
FROM gps_temperature_data 
GROUP BY status;

-- 평균 온도
SELECT AVG(temperature) as avg_temp 
FROM gps_temperature_data 
WHERE temperature IS NOT NULL;
```

---

## 자동 시작 설정 (systemd)

라즈베리파이 부팅 시 자동으로 GPS 추적 시작:

### 1️⃣ 서비스 파일 생성

```bash
sudo nano /etc/systemd/system/gps-tracker.service
```

### 2️⃣ 내용 입력

```ini
[Unit]
Description=Truck GPS Tracker
After=network.target

[Service]
Type=simple
User=infrac_vr_pc
WorkingDirectory=/home/infrax_vr_pc/truck_gps
ExecStart=/home/infrax_vr_pc/truck_gps/gps_env/bin/python /home/infrax_vr_pc/truck_gps/gps_tracker.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### 3️⃣ 서비스 활성화

```bash
sudo systemctl daemon-reload
sudo systemctl enable gps-tracker.service
sudo systemctl start gps-tracker.service
```

### 4️⃣ 서비스 관리 명령

```bash
# 상태 확인
sudo systemctl status gps-tracker.service

# 중지
sudo systemctl stop gps-tracker.service

# 재시작
sudo systemctl restart gps-tracker.service

# 로그 확인
sudo journalctl -u gps-tracker.service -f
```

---

## 문제 해결

### ❌ GPS 데이터를 수신하지 못함

**증상:** GPS 리더 연결 실패

**해결책:**
```bash
# GPS 포트 확인
lsusb
ls -l /dev/ttyUSB* /dev/ttyACM*

# 포트 권한 설정
sudo usermod -a -G dialout $USER
# 재로그인 필요
```

---

### ❌ I2C 온도 센서 연결 실패 (MCP9600)

**증상:** "I2C device not found"

**해결책:**
```bash
# I2C 활성화
sudo raspi-config
# Interface Options → I2C → Enable

# I2C 장치 스캔
sudo i2cdetect -y 1
# MCP9600 주소: 0x67

# i2c-tools 설치
sudo apt-get install i2c-tools
```

---

### ❌ 패키지 설치 오류 (externally-managed-environment)

**증상:** `pip install` 실패

**해결책:**
```bash
# 가상환경 사용 (권장)
python3 -m venv gps_env
source gps_env/bin/activate
pip install -r requirements.txt

# 또는 시스템 전역 설치
pip3 install -r requirements.txt --break-system-packages
```

---

### ❌ 대시보드 접속 불가

**증상:** Connection refused

**해결책:**
```bash
# 대시보드 프로세스 확인
ps aux | grep dashboard_server

# 포트 확인
netstat -an | grep 5000

# 대시보드 재시작
pkill -f dashboard_server
python dashboard_server.py
```

---

### ❌ 현재 위치 표시 안 됨

**증상:** "조회중..."이 계속 표시

**해결책:**
- 인터넷 연결 확인
- 방화벽 확인 (BigDataCloud API 접근 가능 여부)
- `dashboard_server.py` 로그 확인

---

### ❌ 데이터베이스 시간이 9분 느림

**증상:** DB 저장 시간이 실제 시간보다 느림

**해결책:**
- `database.py`에서 `zoneinfo.ZoneInfo('Asia/Seoul')` 사용
- 라즈베리파이 시간대 설정:
```bash
sudo timedatectl set-timezone Asia/Seoul
```
---

## 리팩토링 이력

### ✅ 완료된 리팩토링

1. **온도 범위 중앙화**
   - 이전: 4개 파일에서 하드코딩
   - 현재: `config.py`의 `TEMP_RANGES` 사용

2. **MQTT 설정 중앙화**
   - 이전: `server_sender.py`에서 하드코딩
   - 현재: `config.py`에서 관리

3. **차량 ID 중앙화**
   - 이전: 여러 파일에서 하드코딩
   - 현재: `config.py`의 `VEHICLE_ID` 사용

4. **SQL 인젝션 방지**
   - 이전: 문자열 병합
   - 현재: f-string 사용 (DDL은 허용됨)

---

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 자유롭게 사용할 수 있습니다.

---

## 기여 및 문의

문제나 개선 사항이 있으면 이슈를 등록해주세요.

**제작:** 백신 운송 차량 모니터링 시스템 v2.0  
**날짜:** 2025-10-15  
**플랫폼:** 라즈베리파이 + Python 3

