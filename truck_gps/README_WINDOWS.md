# 🪟 Windows 실행 메뉴얼

## 📋 목차
- [시스템 요구사항](#시스템-요구사항)
- [가상 환경 활성화](#가상-환경-활성화)
- [설정 파일 수정](#설정-파일-수정)
- [Windows COM 포트 확인](#windows-com-포트-확인)
- [프로그램 실행](#프로그램-실행)
- [종료 방법](#종료-방법)
- [로그 확인](#로그-확인)
- [웹 대시보드 실행](#웹-대시보드-실행)
- [문제 해결](#문제-해결)
- [데이터 확인](#데이터-확인)

---

## 시스템 요구사항

- **운영체제**: Windows 10 이상
- **Python**: 3.7 이상
- **인터넷 연결**: MQTT 브로커 접속용

---

## 가상 환경 활성화

### PowerShell에서 실행

```powershell
# 프로젝트 디렉토리로 이동
cd C:\work\truck_gps\truck_gps

# 가상 환경 활성화 (Linux 스타일 가상 환경인 경우)
.\gps_env\bin\Activate.ps1

# 또는
gps_env\bin\Activate.ps1
```

### 실행 정책 오류 발생 시

```powershell
# 현재 세션에만 적용 (임시)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
.\gps_env\bin\Activate.ps1
```

**참고**: 가상 환경이 활성화되면 프롬프트 앞에 `(gps_env)`가 표시됩니다.

---

## 설정 파일 수정

`config.py` 파일을 열어서 다음 설정을 확인/수정하세요:

### GPS 설정 (실제 GPS 사용 시)

```python
# Windows에서 실제 GPS 사용 시
GPS_PORT = "COM3"  # Windows COM 포트 (예: COM1, COM2, COM3 등)
GPS_BAUDRATE = 9600
```

**참고**: Windows에서는 하드웨어가 없어도 자동으로 시뮬레이터로 전환됩니다.

### MQTT 브로커 설정

```python
# MQTT 브로커 설정
MQTT_BROKER_HOST = "106.254.226.206"  # MQTT 브로커 IP 주소
MQTT_BROKER_PORT = 1883
MQTT_TOPIC = "truck/gps_temp"
```

### 차량 ID 설정

```python
# 차량 ID
VEHICLE_ID = "V001"
```

### 온도 센서 설정

```python
# 온도 센서 타입 (Windows에서는 자동으로 시뮬레이터로 전환됨)
TEMP_SENSOR_TYPE = "MCP9600"  # 실제 센서가 없으면 시뮬레이터로 자동 전환
```

---

## Windows COM 포트 확인

### 방법 1: 장치 관리자 사용

1. `Windows 키 + X` → **장치 관리자** 선택
2. **포트(COM & LPT)** 확장
3. GPS 장치의 COM 포트 번호 확인 (예: COM3, COM4)

### 방법 2: PowerShell 사용

```powershell
# 사용 가능한 COM 포트 확인
[System.IO.Ports.SerialPort]::getportnames()
```

---

## 프로그램 실행

### 기본 실행

```powershell
# 가상 환경이 활성화된 상태에서
python gps_tracker.py
```

### 정상 실행 시 출력 예시

```
2025-10-31 18:00:00 - INFO - GPS 추적 시스템 초기화 중...
2025-10-31 18:00:00 - INFO - 데이터베이스 연결 성공: truck_gps.db
2025-10-31 18:00:00 - WARNING - GPS 하드웨어 연결 실패. 시뮬레이터 모드로 전환합니다.
2025-10-31 18:00:00 - INFO - GPS 시뮬레이터 초기화 완료 - 테스트 데이터 생성 중
2025-10-31 18:00:00 - WARNING - 온도 센서 연결 실패. 시뮬레이터 모드로 전환합니다.
2025-10-31 18:00:00 - INFO - 온도 시뮬레이터 초기화 완료 - 냉장고 온도 시뮬레이션 중
2025-10-31 18:00:00 - INFO - 서버 전송기 초기화 완료
2025-10-31 18:00:00 - INFO - GPS + 온도 데이터 수집 시작 (목표: 초당 10개)
2025-10-31 18:00:00 - INFO - 센서 데이터 읽기 스레드 시작됨
2025-10-31 18:00:00 - INFO - 서버 데이터 전송 시작됨
2025-10-31 18:00:01 - INFO - 샘플 #10 | GPS율: 1/초, 온도율: 1/초 | 위도: 37.566535, 경도: 126.977969, 속도: 0.0km/h, 위성: 8개 | 온도: 5.2°C | 저장율: 10.00/초
```

### 자동 동작

Windows에서는 다음 상황에서 자동으로 시뮬레이터로 전환됩니다:

- ✅ GPS 하드웨어 없음 → GPS 시뮬레이터 사용
- ✅ 온도 센서 없음 → 온도 시뮬레이터 사용
- ✅ 시리얼 포트 오류 → 시뮬레이터로 자동 전환
- ✅ GPIO 라이브러리 오류 → 시뮬레이터로 자동 전환

---

## 종료 방법

```powershell
# Ctrl+C 누르기
```

프로그램이 정상적으로 종료되면 다음 메시지가 출력됩니다:

```
2025-10-31 18:05:00 - INFO - 사용자에 의해 중단됨
2025-10-31 18:05:00 - INFO - 총 저장된 데이터: 3000개
2025-10-31 18:05:00 - INFO - GPS + 온도 추적 시스템 종료
```

---

## 로그 확인

### 최근 로그 확인

```powershell
# 최근 50줄 확인 (UTF-8 인코딩)
Get-Content gps_tracker.log -Tail 50 -Encoding UTF8
```

### 실시간 로그 확인

```powershell
# 실시간 로그 모니터링
Get-Content gps_tracker.log -Wait -Encoding UTF8
```

### 로그 파일 위치

```
C:\work\truck_gps\truck_gps\gps_tracker.log
```

---

## 웹 대시보드 실행

### 대시보드 서버 시작

**새 PowerShell 창에서:**

```powershell
# 프로젝트 디렉토리로 이동
cd C:\work\truck_gps\truck_gps

# 가상 환경 활성화
.\gps_env\bin\Activate.ps1

# 대시보드 서버 실행
python dashboard_server.py
```

### 브라우저에서 접속

```
http://localhost:5001
```

또는

```
http://127.0.0.1:5001
```

### 대시보드 기능

- 📊 실시간 온도 그래프
- 🗺️ GPS 위치 표시
- 📍 역지오코딩 (주소 변환)
- ⚠️ 온도 경고 표시
- 🔌 연결 상태 모니터링

---

## 문제 해결

### 문제 1: 가상 환경 활성화 실패

**증상:**
```
.\gps_env\bin\Activate.ps1 : 이 스크립트를 실행할 수 없습니다.
```

**해결 방법:**

```powershell
# 실행 정책 확인
Get-ExecutionPolicy

# 임시로 실행 정책 변경 (현재 세션에만 적용)
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

# 가상 환경 활성화
.\gps_env\bin\Activate.ps1
```

### 문제 2: 콘솔에 한글이 깨져 보임

**해결 방법:**

```powershell
# PowerShell 인코딩 설정
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# 프로그램 재실행
python gps_tracker.py
```

### 문제 3: GPS 포트 오류

**증상:**
```
GPS 모듈 연결 실패: could not open port 'COM3'
```

**해결 방법:**

1. `config.py`에서 `GPS_PORT`를 올바른 COM 포트로 변경
2. 실제 GPS가 없으면 시뮬레이터로 자동 전환됨 (오류 무시 가능)

**COM 포트 확인:**
```powershell
[System.IO.Ports.SerialPort]::getportnames()
```

### 문제 4: MQTT 연결 실패

**증상:**
```
MQTT 브로커 연결 실패: [Errno 10061] 연결할 수 없습니다
```

**해결 방법:**

1. `config.py`의 `MQTT_BROKER_HOST`와 `MQTT_BROKER_PORT` 확인
2. 방화벽에서 포트 1883 허용 확인
3. MQTT 브로커가 실행 중인지 확인
4. 네트워크 연결 확인

### 문제 5: 패키지 import 오류

**증상:**
```
ModuleNotFoundError: No module named 'pyserial'
```

**해결 방법:**

```powershell
# 가상 환경 활성화 후
.\gps_env\bin\Activate.ps1

# 필요한 패키지 재설치
pip install pyserial paho-mqtt flask sqlite3
```

### 문제 6: 콘솔 출력이 안 나옴

**해결 방법:**

1. PowerShell 인코딩 설정:
```powershell
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
```

2. 로그 파일 확인:
```powershell
Get-Content gps_tracker.log -Tail 20 -Encoding UTF8
```

3. 프로그램이 실행 중인지 확인:
```powershell
Get-Process python
```

---

## 데이터 확인

### SQLite 데이터베이스 확인

**방법 1: Python 스크립트 사용**

```powershell
python view_data.py
```

**방법 2: SQLite 명령줄 도구 사용**

SQLite가 설치되어 있다면:

```powershell
sqlite3 truck_gps.db

# 최근 10개 데이터 조회
SELECT * FROM gps_temperature_data ORDER BY timestamp DESC LIMIT 10;

# 종료
.exit
```

### 데이터베이스 파일 위치

```
C:\work\truck_gps\truck_gps\truck_gps.db
```

---

## 백그라운드 실행 (선택사항)

### 방법 1: Start-Process 사용

```powershell
# 백그라운드 실행
Start-Process python -ArgumentList "gps_tracker.py" -WindowStyle Hidden

# 프로세스 확인
Get-Process python
```

### 방법 2: 작업 스케줄러 사용

1. Windows 작업 스케줄러 열기
2. 기본 작업 만들기
3. 프로그램: `python`
4. 인수: `gps_tracker.py`
5. 시작 위치: `C:\work\truck_gps\truck_gps`

---

## 빠른 시작 체크리스트

- [ ] Python 3.7 이상 설치 확인
- [ ] 프로젝트 디렉토리로 이동: `cd C:\work\truck_gps\truck_gps`
- [ ] 가상 환경 활성화: `.\gps_env\bin\Activate.ps1`
- [ ] `config.py`에서 MQTT 브로커 주소 확인
- [ ] 프로그램 실행: `python gps_tracker.py`
- [ ] 로그 확인: `Get-Content gps_tracker.log -Tail 20 -Encoding UTF8`

---

## 주요 파일 위치

```
C:\work\truck_gps\truck_gps\
├── config.py              # 설정 파일
├── gps_tracker.py         # 메인 프로그램
├── gps_tracker.log        # 로그 파일
├── truck_gps.db           # SQLite 데이터베이스
├── dashboard_server.py    # 웹 대시보드 서버
└── gps_env\               # 가상 환경
    └── bin\
        └── Activate.ps1   # 가상 환경 활성화 스크립트
```

---

## 추가 정보

### Windows에서의 자동 동작

Windows 환경에서는 라즈베리파이 하드웨어가 없어도 자동으로 시뮬레이터 모드로 동작합니다:

- **GPS 시뮬레이터**: 서울 지역 좌표를 시뮬레이션
- **온도 시뮬레이터**: 2°C ~ 8°C 범위의 냉장고 온도 시뮬레이션
- **데이터 저장**: 실제 하드웨어와 동일하게 SQLite에 저장
- **MQTT 전송**: 실제 하드웨어와 동일하게 MQTT로 전송

### 테스트 모드

Windows에서 테스트할 때는:

1. 실제 GPS/온도 센서 없이도 실행 가능
2. 시뮬레이터 데이터로 모든 기능 테스트 가능
3. MQTT 브로커만 연결되어 있으면 전송 테스트 가능

---

## 문의 및 지원

문제가 발생하면 다음을 확인하세요:

1. 로그 파일: `gps_tracker.log`
2. 설정 파일: `config.py`
3. 가상 환경 활성화 상태
4. 네트워크 연결 상태
5. MQTT 브로커 접근 가능 여부

---

**마지막 업데이트**: 2025-10-31

