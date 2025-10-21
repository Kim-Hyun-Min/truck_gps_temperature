# 🚛 트럭 GPS 위치 추적 시스템

라즈베리파이에서 실시간으로 트럭의 GPS 위치 정보를 수집하고 로컬 데이터베이스에 저장하는 시스템입니다.

## 📋 목차
- [주요 기능](#주요-기능)
- [시스템 구조](#시스템-구조)
- [설치 방법](#설치-방법)
- [사용 방법](#사용-방법)
- [코드 구조 상세 설명](#코드-구조-상세-설명)
- [데이터베이스](#데이터베이스)
- [문제 해결](#문제-해결)

---

## 주요 기능

### ✅ 실시간 GPS + 온도 데이터 수집
- **GPS 데이터**: 위도, 경도, 고도, 속도, 방향, 위성 수
- **온도 데이터**: 실제 센서 또는 시뮬레이터 (백신 운송용 2°C ~ 8°C 범위)
- **데이터 저장**: 0.1초마다 수집, 1초마다 10개 데이터 배치 저장

### ✅ 서버 전송 시스템
- **자동 전송**: 1초마다 최근 10개 데이터를 서버로 전송
- **중복 방지**: 전송 완료 데이터 추적 시스템
- **이중 전송**: MySQL 직접 저장 + HTTP API 백업
- **실시간 모니터링**: 전송 성공/실패 상태 실시간 확인

### ✅ 온도 상태 모니터링 (백신 운송용)
- **온도 범위**: 2°C ~ 8°C (백신 적정 보관 온도)
- **상태 분류**:
  - `critical_cold`: < 2.0°C (위험한 추위)
  - `cold`: 2.0°C ~ 2.5°C (추위)
  - `normal`: 2.5°C ~ 7.5°C (정상)
  - `warm`: 7.5°C ~ 8.0°C (따뜻함)
  - `critical_hot`: > 8.0°C (위험한 더위)

---

## 시스템 구조

### 📁 파일 구조

```
truck_gps/                    # 📍 GPS 추적 시스템 (라즈베리파이)
├── config.py              # 설정 파일 (샘플링율, GPS 포트 등)
├── database.py            # SQLite 데이터베이스 관리 클래스
├── gps_tracker.py         # 메인 프로그램 (실행 파일)
├── gps_reader.py          # 실제 GPS 하드웨어 인터페이스 (NMEA 파싱)
├── gps_simulator.py       # GPS 시뮬레이터 (테스트용)
├── temperature_reader.py  # 실제 온도 센서 인터페이스
├── temperature_simulator.py # 온도 데이터 시뮬레이터
├── server_sender.py       # 서버 전송 클래스
├── gpio_device_detector.py # GPIO 장치 감지 도구
├── database_migration.py  # 데이터베이스 스키마 업데이트 도구
├── view_data.py           # 데이터 조회 및 통계 유틸리티
├── requirements.txt       # Python 패키지 의존성
├── README.md              # 이 문서
├── gps_tracker.log        # 로그 파일 (자동 생성)
└── truck_gps.db           # SQLite 데이터베이스 (자동 생성)

mqtt_dashboard/               # 🌐 MQTT 서버 및 웹 대시보드 (PC)
├── mqtt_server.py         # MQTT 브로커 및 웹 서버
├── templates/             # Flask 템플릿 파일들
│   └── dashboard.html     # 웹 대시보드 페이지
├── static/                # 정적 파일들 (CSS, JS, 이미지)
├── truck_gps_dashboard.db # MQTT 서버용 데이터베이스
└── requirements.txt       # MQTT 서버 의존성
```

### 🔄 데이터 흐름

```
┌─────────────────────────────────────────────────────┐
│              gps_tracker.py (메인)                   │
│  ┌─────────────────────────────────────────────┐    │
│  │  1. setup()                                 │    │
│  │     - 데이터베이스 초기화                    │    │
│  │     - GPS 리더 선택 (실제/시뮬레이터)        │    │
│  │                                             │    │
│  │  2. start() - 메인 루프                     │    │
│  │     ┌─────────────────────────────────┐    │    │
│  │     │  While running:                 │    │    │
│  │     │    → GPS 데이터 읽기            │    │    │
│  │     │    → 유효성 검증                │    │    │
│  │     │    → DB에 저장                  │    │    │
│  │     │    → 로그 출력 (100개마다)      │    │    │
│  │     │    → 타이밍 조정 (정확한 간격)  │    │    │
│  │     └─────────────────────────────────┘    │    │
│  │                                             │    │
│  │  3. stop()                                  │    │
│  │     - 통계 출력                             │    │
│  │     - 리소스 정리                           │    │
│  └─────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────┘
         ↓                               ↓
    ┌──────────┐                  ┌─────────────┐
    │ GPS      │                  │  SQLite DB  │
    │ Reader   │                  │  (database) │
    │ 또는     │                  │             │
    │Simulator │                  │  gps_data   │
    └──────────┘                  └─────────────┘
```

---

## 시스템 요구사항

### 하드웨어
- **라즈베리파이**: 3, 4, Zero W 등 모든 모델
- **GPS 모듈** (선택사항):
  - **USB GPS** (권장): 
    - NK-GPS-U (테스트 완료 ✅)
    - NEO-6M, NEO-7M
    - BU-353S4
  - **UART GPS**: GPIO 연결 가능 모듈
- **메모리**: 최소 512MB RAM
- **저장 공간**: 하루 50-100MB (데이터 수집량에 따라)

### 소프트웨어
- **Python**: 3.7 이상
- **OS**: 라즈베리파이 OS (Raspbian) 또는 다른 리눅스 배포판
- **필수 패키지**:
  - `pyserial`: GPS 시리얼 통신
  - `gpsd-py3`: GPS 데몬 인터페이스 (선택)

---

## 설치 방법

### 1️⃣ Windows에서 라즈베리파이로 파일 전송

```powershell
# Windows PowerShell에서 실행
scp -r C:\work\truck_gps 사용자명@라즈베리파이IP:~/
```

**예시:**
```powershell
scp -r C:\work\truck_gps pi@192.168.0.141:~/
```

### 2️⃣ 라즈베리파이 SSH 접속

```bash
ssh 사용자명@라즈베리파이IP
```

### 3️⃣ 가상환경 생성 및 패키지 설치

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

### 4️⃣ GPS 포트 확인 (실제 GPS 사용 시)

```bash
# 연결된 포트 확인
ls /dev/ttyUSB* /dev/ttyAMA* /dev/serial*

# 포트 권한 설정 (필요시)
sudo usermod -a -G dialout $USER
# 재로그인 필요
```

### 5️⃣ 설정 파일 수정

```bash
nano config.py
```

```python
# GPS 포트를 실제 포트로 변경
GPS_PORT = "/dev/ttyUSB0"  # 또는 /dev/ttyAMA0, /dev/ttyACM0

# 샘플링율 조정 (초당 개수)
SAMPLE_RATE = 10  # 1~10 권장
```

### 6️⃣ NK-GPS-U 전용 설정 (실제 테스트 완료 ✅)

NK-GPS-U USB GPS 수신기를 사용하는 경우:

```bash
# 1. GPS 장치 인식 확인
ls -l /dev/ttyACM* /dev/ttyUSB*
# 출력 예시: crw-rw---- 1 root dialout 166, 0 Oct 15 14:49 /dev/ttyACM0

# 2. GPS 데이터 출력 테스트 (30초~2분 대기)
cat /dev/ttyACM0
# NMEA 데이터가 보이면 Ctrl+C로 중단

# 3. config.py 수정
nano config.py
```

**NK-GPS-U config.py 설정:**
```python
GPS_PORT = "/dev/ttyACM0"  # NK-GPS-U는 보통 ttyACM0
GPS_BAUDRATE = 9600        # NK-GPS-U 기본 속도
```

**실제 테스트 결과:**
- ✅ 포트: `/dev/ttyACM0`
- ✅ 위성 수신: 4~8개
- ✅ 정확도: ±3~7미터 (실내/창가)
- ✅ 데이터 수집율: 초당 10.7개

---

## 사용 방법

### ▶️ 기본 실행

```bash
cd ~/truck_gps
source gps_env/bin/activate
python gps_tracker.py
```

### 🔧 데이터베이스 마이그레이션 (서버 전송 기능 활성화)

기존 데이터베이스에 서버 전송 기능을 위한 새 컬럼을 추가하려면:

```bash
# 데이터베이스 스키마 확인
python3 database_migration.py

# 마이그레이션 실행 (새 컬럼 추가)
python3 database_migration.py
```

**기존 데이터베이스 백업 권장:**
```bash
cp truck_gps.db truck_gps_backup_$(date +%Y%m%d_%H%M%S).db
```

**출력 예시 (시뮬레이터 모드):**
```
2025-10-15 13:47:35 - INFO - GPS 추적 시스템 초기화 중...
2025-10-15 13:47:35 - INFO - 데이터베이스 연결 성공: truck_gps.db
2025-10-15 13:47:35 - WARNING - GPS 하드웨어 연결 실패. 시뮬레이터 모드로 전환합니다.
2025-10-15 13:47:35 - INFO - GPS 시뮬레이터 초기화 완료 - 테스트 데이터 생성 중
2025-10-15 13:47:35 - INFO - GPS 데이터 수집 시작 (초당 10개 샘플)
2025-10-15 13:47:45 - INFO - 샘플 #100 | 위도: 37.571898, 경도: 126.986424 | 평균 수집율: 10.08/초
```

**출력 예시 (실제 GPS - NK-GPS-U):**
```
2025-10-15 14:58:57 - INFO - GPS 추적 시스템 초기화 중...
2025-10-15 14:58:57 - INFO - 데이터베이스 연결 성공: truck_gps.db
2025-10-15 14:58:57 - INFO - 데이터베이스 테이블 생성 완료
2025-10-15 14:58:57 - INFO - GPS 모듈 연결 성공: /dev/ttyACM0
2025-10-15 14:58:57 - INFO - GPS 리더 초기화 완료 - 실제 GPS 모듈 사용 ✓
2025-10-15 14:58:57 - INFO - GPS 데이터 수집 시작 (초당 10개 샘플)
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

### 📊 데이터 조회

```bash
# 최근 10개 데이터 (기본값)
python view_data.py

# 최근 50개 데이터
python view_data.py --latest 50

# 통계 정보
python view_data.py --stats

# 총 데이터 개수
python view_data.py --count
```

**통계 출력 예시 (시뮬레이터):**
```
============================================================
GPS 데이터 통계
============================================================
총 레코드 수: 554

시간 범위:
  시작: 2025-10-15 13:47:35.362449
  종료: 2025-10-15 13:48:30.694398

위치 범위:
  위도: 37.556500 ~ 37.576500 (서울)
  경도: 126.968000 ~ 126.988000

속도 통계 (km/h):
  최소: 55.2
  최대: 64.8
  평균: 60.1

데이터베이스 크기: 0.12 MB
============================================================
```

**실제 GPS 데이터 조회 예시 (NK-GPS-U):**
```bash
python view_data.py --latest 5
```

```
========================================================================
ID   날짜/시간                   위도        경도       고도(m) 속도(km/h) 방향 위성
========================================================================
611  2025-10-15 14:59:54  35.081654  126.825275   33.6     0.4    N/A   4
610  2025-10-15 14:59:53  35.081654  126.825276   33.5     0.3    N/A   4
609  2025-10-15 14:59:52  35.081653  126.825273   33.1     0.5    N/A   4
608  2025-10-15 14:59:51  35.081652  126.825267   32.3     0.7    N/A   4
607  2025-10-15 14:59:50  35.081650  126.825257   31.3     0.6    N/A   4
========================================================================
```

**위치 확인:**
- 위도: 35.0816°N, 경도: 126.8252°E = 광주광역시 
- Google Maps: https://www.google.com/maps?q=35.081637,126.825214

---

## 코드 구조 상세 설명

### 1️⃣ `config.py` - 설정 관리

**역할:** 시스템 전체의 설정을 중앙 관리

```python
# 데이터베이스 설정
DB_PATH = "truck_gps.db"           # DB 파일명

# GPS 하드웨어 설정
GPS_PORT = "/dev/ttyUSB0"          # 시리얼 포트
GPS_BAUDRATE = 9600                # 통신 속도

# 데이터 수집 설정
SAMPLE_RATE = 10                   # 초당 샘플 수
INTERVAL = 1.0 / SAMPLE_RATE       # 샘플 간격 (0.1초)

# 로깅 설정
LOG_LEVEL = "INFO"                 # DEBUG/INFO/WARNING/ERROR
LOG_FILE = "gps_tracker.log"       # 로그 파일명
```

**설정 변경 예시:**
```python
SAMPLE_RATE = 5   # 초당 5개로 변경 (더 느리게)
SAMPLE_RATE = 20  # 초당 20개로 변경 (더 빠르게, CPU 사용 증가)
```

---

### 2️⃣ `database.py` - 데이터베이스 관리

**역할:** SQLite 데이터베이스 CRUD 작업

#### 클래스 구조

```python
class GPSDatabase:
    def __init__(self, db_path=DB_PATH)      # 초기화
    def connect(self)                         # DB 연결
    def create_tables(self)                   # 테이블 생성
    def insert_gps_data(...)                  # 데이터 삽입 ⭐
    def get_latest_data(self, limit=10)       # 최근 데이터 조회
    def get_data_count(self)                  # 총 개수 조회
    def close(self)                           # 연결 종료
```

#### 핵심 메서드: `insert_gps_data()`

```python
def insert_gps_data(self, latitude, longitude, altitude=None, 
                   speed=None, heading=None, satellites=None, 
                   fix_quality=None):
    """
    GPS 데이터를 데이터베이스에 삽입
    
    Args:
        latitude: 위도 (필수)
        longitude: 경도 (필수)
        altitude: 고도 (선택)
        speed: 속도 km/h (선택)
        heading: 방향 0-360도 (선택)
        satellites: 수신 위성 수 (선택)
        fix_quality: GPS 품질 0-9 (선택)
    
    Returns:
        삽입된 레코드의 ID 또는 None (실패 시)
    """
    # 현재 시간 저장 (Unix timestamp + 문자열)
    timestamp = datetime.now().timestamp()
    datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
    
    # SQL 실행 (파라미터 바인딩으로 안전)
    self.cursor.execute("""
        INSERT INTO gps_data 
        (timestamp, datetime, latitude, longitude, altitude, 
         speed, heading, satellites, fix_quality)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (timestamp, datetime_str, latitude, longitude, 
          altitude, speed, heading, satellites, fix_quality))
    
    self.conn.commit()  # 변경사항 저장
    return self.cursor.lastrowid
```

**인덱스 최적화:**
```sql
-- timestamp와 datetime에 인덱스 생성하여 검색 속도 향상
CREATE INDEX idx_timestamp ON gps_data(timestamp);
CREATE INDEX idx_datetime ON gps_data(datetime);
```

---

### 3️⃣ `gps_reader.py` - GPS 하드웨어 인터페이스

**역할:** 실제 GPS 모듈에서 NMEA 데이터를 읽고 파싱

#### NMEA 프로토콜이란?

GPS 모듈이 출력하는 표준 텍스트 형식입니다.

**NMEA 문장 예시:**
```
$GPGGA,123519,3751.65,N,12658.68,E,1,08,0.9,545.4,M,46.9,M,,*47
```

**구조:**
- `$GPGGA`: 문장 타입 (위치 정보)
- `123519`: UTC 시간 (12:35:19)
- `3751.65,N`: 위도 37° 51.65' 북위
- `12658.68,E`: 경도 126° 58.68' 동경
- `1`: Fix 품질 (1=GPS fix)
- `08`: 수신 위성 수
- `0.9`: HDOP (정확도)
- `545.4,M`: 고도 545.4미터

#### 핵심 메서드: `parse_nmea_gga()`

```python
def parse_nmea_gga(self, sentence):
    """
    GPGGA NMEA 문장을 파싱하여 위치 데이터 추출
    
    NMEA 형식: DDMM.MMMM (도분) → DD.DDDD (십진도) 변환
    예: 3751.65 → 37 + 51.65/60 = 37.8608도
    """
    parts = sentence.split(',')
    
    # 위도 변환
    if parts[2] and parts[3]:
        lat_deg = float(parts[2][:2])      # 37
        lat_min = float(parts[2][2:])      # 51.65
        latitude = lat_deg + lat_min / 60.0
        if parts[3] == 'S':  # 남반구
            latitude = -latitude
    
    # 경도 변환
    if parts[4] and parts[5]:
        lon_deg = float(parts[4][:3])      # 126
        lon_min = float(parts[4][3:])      # 58.68
        longitude = lon_deg + lon_min / 60.0
        if parts[5] == 'W':  # 서반구
            longitude = -longitude
    
    return {
        'latitude': latitude,
        'longitude': longitude,
        'altitude': float(parts[9]),
        'satellites': int(parts[7]),
        'fix_quality': int(parts[6])
    }
```

#### 시리얼 통신 흐름

```python
def read(self):
    """GPS 데이터 읽기 - 완전한 데이터 구성"""
    gps_data = {}
    
    # 여러 NMEA 문장을 읽어서 통합
    for _ in range(10):
        if self.serial_conn.in_waiting:
            line = self.serial_conn.readline().decode('ascii').strip()
            
            if line.startswith('$GPGGA'):
                # 위치 데이터
                gga_data = self.parse_nmea_gga(line)
                gps_data.update(gga_data)
            
            elif line.startswith('$GPRMC'):
                # 속도/방향 데이터
                rmc_data = self.parse_nmea_rmc(line)
                gps_data.update(rmc_data)
            
            # 위도/경도가 모두 있으면 반환
            if 'latitude' in gps_data and 'longitude' in gps_data:
                return gps_data
    
    return gps_data
```

---

### 4️⃣ `gps_simulator.py` - GPS 시뮬레이터

**역할:** GPS 하드웨어 없이 테스트용 가상 데이터 생성

#### 시뮬레이션 로직

```python
class GPSSimulator:
    def __init__(self):
        # 시작 위치: 서울 시청
        self.base_lat = 37.5665
        self.base_lon = 126.9780
        self.speed_kmh = 60.0  # 평균 속도
        self.update_count = 0
    
    def read(self):
        """원형 경로를 따라 이동하는 트럭 시뮬레이션"""
        self.update_count += 1
        
        # 원형 경로 계산 (반지름 약 1km)
        angle = (self.update_count * 0.01) % (2 * math.pi)
        radius = 0.01
        
        # 삼각함수로 원 그리기
        self.current_lat = self.base_lat + radius * math.cos(angle)
        self.current_lon = self.base_lon + radius * math.sin(angle)
        
        # 속도 변화 (55-65 km/h)
        self.current_speed = 60.0 + random.uniform(-5, 5)
        
        # 방향 계산
        self.current_heading = (math.degrees(angle) + 90) % 360
        
        # 실제 GPS처럼 약간의 노이즈 추가
        return {
            'latitude': self.current_lat + random.uniform(-0.00001, 0.00001),
            'longitude': self.current_lon + random.uniform(-0.00001, 0.00001),
            'altitude': 50.0 + random.uniform(-5, 5),
            'speed': max(0, self.current_speed),
            'heading': self.current_heading,
            'satellites': random.randint(8, 12),
            'fix_quality': 1
        }
```

**시뮬레이션 경로 시각화:**
```
        북(0°)
          ↑
    (lat+r)|
          |
서 ←------+------→ 동
(lon-r)   |    (lon+r)
          |
    (lat-r)↓
        남(180°)

트럭이 시계 반대 방향으로 원형 이동
```

---

### 5️⃣ `gps_tracker.py` - 메인 프로그램 ⭐

**역할:** 전체 시스템 통합 및 실행

#### 클래스 구조

```python
class GPSTracker:
    def __init__(self)           # 초기화
    def setup(self)              # 시스템 설정
    def start(self)              # 메인 루프 시작 ⭐⭐⭐
    def stop(self)               # 우아한 종료
    def signal_handler(...)      # 시그널 처리 (Ctrl+C)
```

#### 핵심: `setup()` - 자동 폴백

```python
def setup(self):
    """초기화 및 자동 폴백 메커니즘"""
    # 1. 데이터베이스 준비
    self.db = GPSDatabase()
    self.db.connect()
    self.db.create_tables()
    
    # 2. GPS 리더 선택 (자동 폴백)
    try:
        # 실제 GPS 모듈 시도
        from gps_reader import GPSReader
        self.gps_reader = GPSReader()
        logger.info("실제 GPS 모듈 사용")
    except (ImportError, Exception) as e:
        # 실패 시 자동으로 시뮬레이터로 전환
        logger.warning(f"GPS 연결 실패. 시뮬레이터 모드로 전환")
        from gps_simulator import GPSSimulator
        self.gps_reader = GPSSimulator()
```

#### 핵심: `start()` - 메인 루프

```python
def start(self):
    """정밀한 타이밍 제어를 가진 메인 데이터 수집 루프"""
    self.running = True
    sample_count = 0
    start_time = time.time()
    
    while self.running:
        loop_start = time.time()  # 이번 루프 시작 시간
        
        # ━━━━━ 1단계: GPS 데이터 읽기 ━━━━━
        gps_data = self.gps_reader.read()
        
        # ━━━━━ 2단계: 유효성 검증 ━━━━━
        if gps_data and gps_data.get('latitude') and gps_data.get('longitude'):
            
            # ━━━━━ 3단계: 데이터베이스 저장 ━━━━━
            record_id = self.db.insert_gps_data(
                latitude=gps_data['latitude'],
                longitude=gps_data['longitude'],
                altitude=gps_data.get('altitude'),
                speed=gps_data.get('speed'),
                heading=gps_data.get('heading'),
                satellites=gps_data.get('satellites'),
                fix_quality=gps_data.get('fix_quality')
            )
            
            sample_count += 1
            
            # ━━━━━ 4단계: 진행상황 로깅 (100개마다) ━━━━━
            if sample_count % 100 == 0:
                elapsed = time.time() - start_time
                rate = sample_count / elapsed
                logger.info(
                    f"샘플 #{sample_count} | "
                    f"위도: {gps_data['latitude']:.6f}, "
                    f"경도: {gps_data['longitude']:.6f} | "
                    f"평균 수집율: {rate:.2f}/초"
                )
        
        # ━━━━━ 5단계: 정밀한 타이밍 제어 ━━━━━
        elapsed = time.time() - loop_start  # 실제 처리 시간
        sleep_time = max(0, INTERVAL - elapsed)  # 남은 시간 계산
        time.sleep(sleep_time)
```

**타이밍 제어 원리:**
```
목표: SAMPLE_RATE = 10 → INTERVAL = 0.1초

┌─────────────────────────────────────┐
│ 루프 1:                              │
│   처리 시간: 0.03초                  │
│   Sleep: 0.1 - 0.03 = 0.07초        │
│   총 소요: 0.10초 ✓                  │
└─────────────────────────────────────┘
┌─────────────────────────────────────┐
│ 루프 2:                              │
│   처리 시간: 0.05초                  │
│   Sleep: 0.1 - 0.05 = 0.05초        │
│   총 소요: 0.10초 ✓                  │
└─────────────────────────────────────┘

결과: 정확히 초당 10개 수집
```

#### 우아한 종료: `stop()`

```python
def stop(self):
    """안전한 종료 처리"""
    if not self.running:
        return  # 중복 호출 방지 (버그 수정)
    
    self.running = False
    
    # 최종 통계 출력
    if self.db:
        try:
            total_count = self.db.get_data_count()
            logger.info(f"총 저장된 데이터: {total_count}개")
        except Exception:
            pass  # 이미 닫힌 경우 무시
        self.db.close()
        self.db = None
    
    # GPS 리더 종료
    if self.gps_reader:
        self.gps_reader.close()
        self.gps_reader = None
    
    logger.info("GPS 추적 시스템 종료")
```

#### 시그널 처리

```python
def signal_handler(self, signum, frame):
    """Ctrl+C 또는 kill 명령 처리"""
    logger.info(f"시그널 {signum} 수신")
    self.stop()
    sys.exit(0)

# 메인 함수에서 등록
signal.signal(signal.SIGINT, tracker.signal_handler)   # Ctrl+C
signal.signal(signal.SIGTERM, tracker.signal_handler)  # kill
```

---

### 6️⃣ `view_data.py` - 데이터 조회 도구

**역할:** 저장된 GPS 데이터를 다양한 형식으로 조회

#### 주요 기능

```python
def show_latest(db_path, limit):
    """최근 N개 데이터를 테이블 형식으로 출력"""

def show_count(db_path):
    """총 데이터 개수 및 시간 범위 출력"""

def show_stats(db_path):
    """통계 정보 출력 (위치 범위, 평균 속도, 고도 등)"""
```

#### 통계 쿼리 예시

```python
# 위치 범위 계산
cursor.execute("""
    SELECT 
        MIN(latitude), MAX(latitude),
        MIN(longitude), MAX(longitude)
    FROM gps_data
""")

# 속도 통계
cursor.execute("""
    SELECT 
        MIN(speed), MAX(speed), AVG(speed)
    FROM gps_data
    WHERE speed IS NOT NULL
""")

# 데이터베이스 크기
cursor.execute("""
    SELECT page_count * page_size as size 
    FROM pragma_page_count(), pragma_page_size()
""")
```

---

## 데이터베이스

### 📊 테이블 구조: `gps_temperature_data`

| 컬럼 | 타입 | 설명 | 예시 |
|------|------|------|------|
| `id` | INTEGER | 자동 증가 Primary Key | 1, 2, 3... |
| `vehicle_id` | TEXT | 차량 고유 식별자 | "V001" |
| `timestamp` | REAL | Unix 타임스탬프 (숫자) | 1729004855.362 |
| `datetime` | TEXT | 읽기 쉬운 날짜/시간 | "2025-10-15 13:47:35.362449" |
| `latitude` | REAL | 위도 (도) | 37.5665 |
| `longitude` | REAL | 경도 (도) | 126.9780 |
| `altitude` | REAL | 고도 (미터) | 45.2 |
| `speed` | REAL | 속도 (km/h) | 60.5 |
| `heading` | REAL | 방향 (도) | 180.0 |
| `temperature` | REAL | 온도 (°C) | 5.2 |
| `status` | TEXT | 온도 상태 | "normal" |
| `sent` | BOOLEAN | 전송 완료 여부 | TRUE/FALSE |
| `sent_at` | TIMESTAMP | 전송 완료 시간 | "2025-10-15 13:47:36" |
| `created_at` | TIMESTAMP | 데이터 생성 시간 | "2025-10-15 13:47:35" |

### 🔍 SQL 쿼리 예시

```sql
-- 최근 10개 데이터
SELECT datetime, latitude, longitude, speed 
FROM gps_data 
ORDER BY timestamp DESC 
LIMIT 10;

-- 특정 날짜 데이터
SELECT * FROM gps_data 
WHERE datetime LIKE '2025-10-15%';

-- 평균 속도 계산
SELECT AVG(speed) as avg_speed 
FROM gps_data 
WHERE speed IS NOT NULL;

-- 시간대별 데이터 개수
SELECT strftime('%H', datetime) as hour, COUNT(*) as count 
FROM gps_data 
GROUP BY hour;

-- 이동 거리 계산 (Haversine 공식)
SELECT 
    6371 * 2 * ASIN(SQRT(
        POWER(SIN((RADIANS(lat2) - RADIANS(lat1)) / 2), 2) +
        COS(RADIANS(lat1)) * COS(RADIANS(lat2)) *
        POWER(SIN((RADIANS(lon2) - RADIANS(lon1)) / 2), 2)
    )) as distance_km
FROM (
    SELECT 
        LAG(latitude) OVER (ORDER BY timestamp) as lat1,
        LAG(longitude) OVER (ORDER BY timestamp) as lon1,
        latitude as lat2,
        longitude as lon2
    FROM gps_data
);
```

### 📈 성능 및 용량

| 항목 | 값 |
|------|------|
| 샘플링율 | 초당 10개 (설정 가능) |
| 하루 데이터량 | 864,000개 레코드 |
| 레코드 크기 | 약 100-120 바이트 |
| 하루 DB 크기 | 50-100 MB |
| 한 달 DB 크기 | 1.5-3 GB |
| 메모리 사용 | 20-30 MB |
| CPU 사용 | 1% 미만 |

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
User=pi
WorkingDirectory=/home/pi/truck_gps
ExecStart=/home/pi/truck_gps/gps_env/bin/python /home/pi/truck_gps/gps_tracker.py
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

## 📡 GPS 정확도와 오차 이해하기

### GPS 정확도 범위

**민간용 GPS 정확도:**
| 환경 | 위성 수 | 정확도 | 설명 |
|------|---------|--------|------|
| 이상적 (야외) | 8~12개 | ±3~5m | 하늘이 잘 보이는 개활지 |
| 일반 (창가) | 4~8개 | ±5~10m | 건물 근처, 창문을 통한 수신 |
| 실내/도심 | 4개 이하 | ±10~50m | 신호 반사, 다중 경로 오차 |

### 🔍 정지 상태 위치 흔들림 (정상)

**실제 테스트 결과 (NK-GPS-U, 벽에 고정):**
```
위도 범위: 35.081637 ~ 35.081654  (차이: 0.000017도 ≈ 1.9m)
경도 범위: 126.825214 ~ 126.825276 (차이: 0.000062도 ≈ 6.9m)
→ 총 흔들림: 3~7미터 반경 ✅ 정상!
```

**왜 고정되어 있는데 위치가 변하나요?**

1. **GPS 자체 오차**
   - 대기권 통과 시 신호 굴절
   - 위성 시계 오차
   - 전리층 간섭

2. **위성 배치 변화**
   - 위성은 계속 움직임
   - 매 순간 삼각측량 각도 변화
   - 계산된 위치도 미세하게 변동

3. **다중 경로 오차 (Multipath)**
   - 건물/벽에 신호 반사
   - 직접 신호와 반사 신호 혼재

4. **수신 위성 수**
   - 4개: 최소 조건 (오차 ↑)
   - 8~12개: 이상적 (오차 ↓)

### ✅ 정상 vs ❌ 비정상 판단

**정상 (걱정 안 해도 됨):**
- ✅ **정지 시 3~10m 흔들림**
- ✅ 속도 0~2 km/h
- ✅ 위성 4개 이상
- ✅ 고도 변화 ±5m 이내

**비정상 (문제 있음):**
- ❌ 수십~수백 미터 점프
- ❌ 갑자기 다른 도시로 이동
- ❌ 위성 0~2개
- ❌ 위도/경도가 null 또는 0.0

### 🚛 실제 트럭 운행 시

**정지 상태:**
- 3~7m 흔들림 발생 (정상)
- 평균 위치를 사용하면 더 정확

**이동 중 (20km/h 이상):**
- 경로가 명확하게 표시됨
- 상대적으로 흔들림이 적어 보임
- 이동 거리가 오차보다 훨씬 큼

**야외 (하늘이 잘 보임):**
- 위성 8~12개 수신
- 정확도 ±3~5m로 개선

### 💡 정확도 개선 방법

#### 1. 안테나 위치 최적화
```
❌ 실내 → GPS 신호 수신 불가
❌ 차량 내부 → 신호 약화
✅ 지붕/대시보드 → 최적
✅ 야외/창가 → 양호
```

#### 2. Warm-up 시간 확보
```
0~2분: 위성 탐색 중 (오차 큼)
2~5분: 위성 확보 중 (오차 감소)
5분 후: 최적 상태 (오차 최소)
```

#### 3. 후처리 필터링

**정지 상태 평균 위치 계산:**
```sql
-- 최근 100개 데이터의 평균 (속도 < 2km/h)
SELECT 
    AVG(latitude) as avg_lat, 
    AVG(longitude) as avg_lon,
    COUNT(*) as samples
FROM (
    SELECT latitude, longitude, speed
    FROM gps_data 
    WHERE speed < 2
    ORDER BY timestamp DESC 
    LIMIT 100
);
```

**칼만 필터 적용 (고급):**
- 연속된 위치 데이터를 평활화
- 급격한 점프 제거
- 더 부드러운 경로 생성

### 📊 실제 정확도 테스트

**테스트 환경:**
- GPS: NK-GPS-U
- 위치: 실내 벽 근처
- 위성: 4개
- 시간: 57초

**측정 결과:**
| 항목 | 값 | 평가 |
|------|-----|------|
| 평균 위도 | 35.081650 | ✅ |
| 평균 경도 | 126.825255 | ✅ |
| 위도 변동 | ±0.000008도 (±0.9m) | ✅ 우수 |
| 경도 변동 | ±0.000030도 (±3.3m) | ✅ 양호 |
| 총 오차 | 3.5m 반경 | ✅ 정상 |
| 데이터 수집율 | 10.7/초 | ✅ 목표 달성 |

**결론:** 실내 환경 치고 우수한 정확도! 야외에서는 더 개선됩니다.

---

## 문제 해결

### ❌ GPS 데이터를 수신하지 못함

**증상:** GPS 리더 연결 실패 에러

**해결책:**

1. **GPS 모듈 연결 확인**
   ```bash
   lsusb  # USB GPS 확인
   ls -l /dev/ttyUSB* /dev/ttyAMA*
   ```

2. **포트 권한 설정**
   ```bash
   sudo usermod -a -G dialout $USER
   # 재로그인 필요
   ```

3. **GPS 안테나 위치**
   - 하늘이 보이는 야외에 설치
   - 실내에서는 GPS 신호 수신 불가
   - 초기 위치 확정에 1-5분 소요 (Cold Start)

4. **로그 확인**
   ```bash
   tail -f gps_tracker.log
   ```

---

### ❌ 데이터베이스 오류

**증상:** `database is locked` 또는 권한 에러

**해결책:**

```bash
# 파일 권한 확인
ls -l truck_gps.db

# 권한 수정
chmod 664 truck_gps.db

# 백업
cp truck_gps.db truck_gps_backup_$(date +%Y%m%d_%H%M%S).db

# 데이터베이스 무결성 검사
sqlite3 truck_gps.db "PRAGMA integrity_check;"
```

---

### ❌ 메모리 부족

**증상:** 시스템 느려짐, Out of Memory

**해결책:**

```bash
# 데이터베이스 크기 확인
du -h truck_gps.db

# 오래된 데이터 삭제 (30일 이전)
sqlite3 truck_gps.db "DELETE FROM gps_data WHERE datetime < date('now', '-30 days');"

# VACUUM으로 공간 회수
sqlite3 truck_gps.db "VACUUM;"

# 스왑 메모리 확인
free -h
```

---

## 🌐 서버 전송 시스템

### 📤 자동 데이터 전송

시스템은 **1초마다 최근 10개 데이터를 서버로 자동 전송**합니다:

```python
# 설정 (config.py)
SEND_INTERVAL = 1     # 1초마다 전송
BATCH_SIZE = 10       # 최근 10개 데이터 전송
RETRY_ATTEMPTS = 3    # 실패시 최대 3번 재시도
RETRY_DELAY = 1       # 재시도 간격 1초
```

### 🔄 전송 방식

#### **1️⃣ MySQL 직접 저장 (주요 방식)**
```python
# 서버 정보 (config.py)
SERVER_HOST = "192.168.0.3"
SERVER_PORT = 3306
SERVER_DATABASE = "vaccine_logistics"
SERVER_USERNAME = "vaccine"
SERVER_PASSWORD = "dlsvmfk0331"
```

#### **2️⃣ HTTP API 백업 (보조 방식)**
```python
# API 정보 (config.py)
SERVER_API_URL = "https://your-server.com/api/gps-data"
SERVER_API_KEY = "your-api-key"
```

### 🚫 중복 전송 방지

데이터베이스에 전송 상태 추적 컬럼을 추가하여 중복 전송을 방지합니다:

```sql
-- 전송하지 않은 데이터만 조회
SELECT * FROM gps_data
WHERE sent = FALSE OR sent IS NULL
ORDER BY timestamp ASC
LIMIT 10;

-- 전송 완료 표시
UPDATE gps_data SET sent = TRUE, sent_at = CURRENT_TIMESTAMP
WHERE id IN (전송한_ID들);
```

### 📊 전송 데이터 형식

#### **HTTP API 전송 구조:**
```json
{
  "vehicle_id": "V001",
  "data": [
    {
      "vehicle_id": "V001",
      "timestamp": "2024-01-01T00:00:00.000Z",
      "latitude": 37.5665,
      "longitude": 126.9780,
      "altitude": 45.2,
      "speed": 60.5,
      "heading": 180.0,
      "temperature": 5.2,
      "status": "normal"
    },
    {
      "vehicle_id": "V001",
      "timestamp": "2024-01-01T00:00:00.100Z",
      "latitude": 37.5666,
      "longitude": 126.9781,
      "altitude": 45.3,
      "speed": 60.7,
      "heading": 180.2,
      "temperature": 5.1,
      "status": "normal"
    }
    // ... 최근 10개 데이터
  ],
  "sent_at": "2024-01-01T00:00:01.000Z"
}
```

#### **MySQL 직접 저장 구조:**
```sql
INSERT INTO gps_temperature_data
(vehicle_id, timestamp, latitude, longitude, altitude, speed, heading, temperature, status)
VALUES
('V001', '2024-01-01 00:00:00', 37.5665, 126.9780, 45.2, 60.5, 180.0, 5.2, 'normal'),
('V001', '2024-01-01 00:00:00', 37.5666, 126.9781, 45.3, 60.7, 180.2, 5.1, 'normal');
```

### 🔧 서버 전송 테스트

서버 연결을 테스트하려면:

```bash
# 단독 테스트
python3 server_sender.py

# 메인 시스템 실행 (서버 전송 포함)
python3 gps_tracker.py
```

### 📈 전송 통계 모니터링

서버 전송기는 다음과 같은 통계를 제공합니다:
- 총 전송 성공 횟수
- 전송 실패 횟수
- 마지막 성공 시간
- 다음 전송 예정 시간

### ⚙️ 설정 변경

`config.py`에서 전송 관련 설정을 변경할 수 있습니다:

```python
# 차량 ID 변경
VEHICLE_ID = "V002"

# 전송 간격 변경 (초)
SEND_INTERVAL = 5

# 배치 크기 변경
BATCH_SIZE = 20

# 서버 정보 변경
SERVER_HOST = "새로운_서버_IP"
```

---

### ❌ 패키지 설치 오류 (externally-managed-environment)

**증상:** `pip install` 실패

**해결책 1: 가상환경 사용 (권장)**
```bash
python3 -m venv gps_env
source gps_env/bin/activate
pip install -r requirements.txt
```

**해결책 2: 시스템 전역 설치**
```bash
pip3 install -r requirements.txt --break-system-packages
```

---

### ❌ 샘플링율이 목표에 도달하지 못함

**증상:** 평균 수집율이 10/초보다 낮음

**원인 및 해결:**

1. **CPU 과부하**
   ```bash
   # CPU 사용률 확인
   top
   
   # 샘플링율 낮추기
   # config.py에서 SAMPLE_RATE = 5로 변경
   ```

2. **SD 카드 속도**
   - Class 10 이상 SD 카드 사용 권장
   - DB 쓰기 속도가 느릴 수 있음

3. **다른 프로세스**
   ```bash
   # 불필요한 서비스 종료
   sudo systemctl stop <서비스명>
   ```

---

## 고급 기능

### 🗺️ GPS 데이터를 CSV로 내보내기

```bash
sqlite3 -header -csv truck_gps.db "SELECT * FROM gps_data;" > gps_export.csv
```

### 📍 Google Maps에서 경로 보기

Python 스크립트로 KML 파일 생성:

```python
import sqlite3

conn = sqlite3.connect('truck_gps.db')
cursor = conn.cursor()

cursor.execute("SELECT latitude, longitude FROM gps_data ORDER BY timestamp")

with open('route.kml', 'w') as f:
    f.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    f.write('<kml xmlns="http://www.opengis.net/kml/2.2">\n')
    f.write('<Document><Placemark><LineString><coordinates>\n')
    
    for lat, lon in cursor.fetchall():
        f.write(f'{lon},{lat},0\n')
    
    f.write('</coordinates></LineString></Placemark></Document></kml>')

conn.close()
```

Google Maps에서 `route.kml` 파일을 열어 경로 확인

---

## 라이선스

이 프로젝트는 교육 및 연구 목적으로 자유롭게 사용할 수 있습니다.

---

## 기여 및 문의

문제나 개선 사항이 있으면 이슈를 등록해주세요.

**제작:** 트럭 GPS 추적 시스템 v1.0  
**날짜:** 2025-10-15  
**플랫폼:** 라즈베리파이 + Python 3
