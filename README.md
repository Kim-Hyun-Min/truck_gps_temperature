# 백신 운송 차량 모니터링

라즈베리파이에서 트럭 GPS와 냉장고 온도를 수집하고, 로컬 SQLite에 저장한 뒤 AWS IoT(MQTT)로 전송하며, 웹 대시보드로 상태를 확인하는 시스템입니다.

상세 설치·실행 방법은 [`truck_gps/README.md`](truck_gps/README.md)를 참고하세요.

```
python gps_tracker.py        # GPS·온도 수집 및 MQTT 전송
python dashboard_server.py   # 웹 대시보드
```
