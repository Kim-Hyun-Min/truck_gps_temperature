# 백신 운송 차량 모니터링

라즈베리파이에서 트럭 GPS와 냉장고 온도를 수집합니다. 로컬 SQLite에 저장하고, MQTT(AWS IoT)로 보내며, 웹 대시보드로 상태를 봅니다.

## 목차

- [동작 요약](#동작-요약)
- [요구사항](#요구사항)
- [설치](#설치)
- [설정](#설정)
- [실행](#실행)
- [웹 대시보드](#웹-대시보드)
- [파일 구성](#파일-구성)
- [데이터](#데이터)
- [문제 해결](#문제-해결)

---

## 동작 요약

| 항목 | 내용 |
|------|------|
| 수집 | GPS(위도, 경도, 속도 등), 온도(MCP9600 등) |
| 로컬 저장 | 0.1초마다 SQLite (`truck_gps.db`), 20분 지난 행 삭제 |
| 서버 전송 | 60초마다 최신 1건을 MQTT로 발행 |
| 온도 구간 | 2°C ~ 8°C 기준 (`critical_cold` / `cold` / `normal` / `warm` / `critical_hot`) |
| 대시보드 | 온도 그래프, GPS, 로컬망(와이파이/랜) 연결 표시 |

```
센서 → gps_tracker.py → SQLite
                         ├→ MQTT (60초마다 최신 1건)
                         └→ dashboard_server.py (브라우저)
```

---

## 요구사항

**하드웨어**

- 라즈베리파이 3 / 4 / Zero W 등
- GPS: USB (`/dev/ttyACM0`, `/dev/ttyUSB0`) 또는 UART
- 온도: MCP9600(권장), DS18B20, DHT22

**소프트웨어**

- Python 3.7 이상
- 라즈베리파이 OS

---

## 설치

```bash
cd ~/truck_gps
python3 -m venv gps_env
source gps_env/bin/activate
pip install -r requirements.txt
```

GPS 포트 확인:

```bash
ls /dev/ttyUSB* /dev/ttyACM* /dev/serial*
sudo usermod -a -G dialout $USER
```

(권한 변경 후 다시 로그인)

AWS IoT를 쓰면 인증서를 한 번 발급합니다.

```bash
cp config.example.py config.py
# config.py 의 DEVICE_ID, MQTT_BROKER_HOST 등을 채운 뒤
python3 provision_iot_cert.py
```

---

## 설정

`config.example.py`를 복사해 `config.py`로 만든 뒤, 빈 문자열 항목을 채웁니다.

```bash
cp config.example.py config.py
nano config.py
```

반드시 넣을 값:

| 항목 | 설명 |
|------|------|
| `IOT_CERT_API_URL` | 인증서 발급 API 주소 |
| `DEVICE_ID` | 장치 이름 (AWS Thing과 같게) |
| `MQTT_BROKER_HOST` | AWS IoT 엔드포인트 또는 MQTT 서버 |
| `MQTT_BROKER_PORT` | AWS는 8883, 일반 MQTT는 1883 |
| `MQTT_TOPIC` | 발행 토픽 |
| `MQTT_CLIENT_ID` / `VEHICLE_ID` | 장치 ID와 맞추는 것을 권장 |

기타:

- `SAMPLE_RATE = 10` — 초당 저장 횟수
- `SEND_INTERVAL = 60` — AWS 전송 간격(초)
- `VERBOSE_LOGS = False` — True면 반복 로그를 매번 출력
- `DASHBOARD_PORT = 5001`

실기기 `config.py`와 인증서 PEM은 Git에 올리지 않습니다.

---

## 실행

수집·전송:

```bash
cd ~/truck_gps
source gps_env/bin/activate
python gps_tracker.py
```

종료: `Ctrl+C`

백그라운드:

```bash
nohup python gps_tracker.py > output.log 2>&1 &
tail -f gps_tracker.log
```

부팅 시 자동 실행은 `deploy/systemd/` 와 `install_services.sh`를 사용합니다.

---

## 웹 대시보드

수집기와 별도 프로세스로 띄웁니다.

```bash
python dashboard_server.py
```

브라우저: `http://라즈베리파이IP:5001`

표시 내용:

- 냉장고 온도, 2~8°C 범위 경고
- 위도/경도, 주소(역지오코딩)
- 로컬망 연결: `wlan0` 또는 `eth0`에 IP가 있으면 연결됨
- 온도 센서 최근 수신 여부
- 최근 90초 온도 차트

포트는 `config.py`의 `DASHBOARD_PORT` 또는 `--port`로 바꿉니다.

```bash
python dashboard_server.py --port 5001
```

---

## 파일 구성

| 파일 | 역할 |
|------|------|
| `config.example.py` | 설정 템플릿. 복사해서 `config.py`로 사용 |
| `gps_tracker.py` | 메인. 수집·저장·전송 기동 |
| `adaptive_sensors.py` | GPS/온도가 없어도 대기, 연결되면 실측 |
| `gps_reader.py` | USB GPS NMEA 파싱 |
| `temperature_reader.py` | MCP9600 / DS18B20 / DHT22 |
| `database.py` | SQLite |
| `server_sender.py` | MQTT 발행 |
| `dashboard_server.py` | Flask 대시보드 |
| `Templates/index.html` | 대시보드 화면 |
| `log_utils.py` | 반복 로그 스로틀 |
| `provision_iot_cert.py` | AWS 인증서 발급 |

---

## 데이터

테이블 `gps_temperature_data`

| 컬럼 | 설명 |
|------|------|
| `vehicle_id` | 차량 ID |
| `timestamp` / `datetime` | 시각 |
| `latitude`, `longitude` | 위치 |
| `speed`, `heading`, `altitude` | 속도, 방향, 고도 |
| `temperature` | 온도(°C) |
| `status` | 온도 구간 |

보관: 약 20분 (`RETENTION_SECONDS = 1200`).

MQTT로 보내는 JSON 한 건 예:

```json
{
  "cmd": "LTE",
  "serial": "장치ID",
  "eventDT": "2026-04-27 13:45:00",
  "temperature": 5.2,
  "lat": 37.5665,
  "lng": 126.978,
  "battery": 100
}
```

---

## 문제 해결

**GPS가 안 잡힘**

```bash
lsusb
ls -l /dev/ttyUSB* /dev/ttyACM*
sudo usermod -a -G dialout $USER
```

**MCP9600 (I2C) 실패**

```bash
sudo raspi-config   # Interface Options → I2C → Enable
sudo apt-get install i2c-tools
sudo i2cdetect -y 1
```

**pip 설치 오류 (externally-managed-environment)**

가상환경을 쓰거나:

```bash
pip3 install -r requirements.txt --break-system-packages
```

**대시보드가 안 열림**

```bash
ps aux | grep dashboard_server
ss -lntp | grep 5001
python dashboard_server.py
```

**모니터에 연결안됨**

대시보드는 서버(AWS)가 아니라 와이파이(`wlan0`) 또는 랜(`eth0`) IP 유무를 봅니다. 공유기에만 붙어 있으면 연결됨입니다.

**로그가 너무 많음**

`config.py`에서 `VERBOSE_LOGS = False`이면 같은 오류는 30초에 최대 1줄입니다. 자세히 보려면 `True`로 바꿉니다.
