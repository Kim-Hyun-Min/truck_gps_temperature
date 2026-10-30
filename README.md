# 백신 운송 차량 모니터링

라즈베리파이에서 트럭 GPS와 냉장고 온도를 수집합니다.  
로컬 SQLite에 저장하고, AWS IoT(MQTT)로 보내며, 웹 대시보드로 상태를 봅니다.

설치·설정·실행은 [truck_gps/README.md](truck_gps/README.md)를 보세요.

```
cd truck_gps
python gps_tracker.py         # GPS·온도 수집, MQTT 전송
python dashboard_server.py    # 웹 대시보드 (포트 5001)
```

설정은 `config.example.py`를 `config.py`로 복사한 뒤, 장치 ID와 브로커 주소를 채웁니다.
