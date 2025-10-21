#!/usr/bin/env python3
"""
MQTT 서버 및 웹 대시보드
라즈베리파이에서 전송된 GPS + 온도 데이터를 실시간으로 수신하고 조회합니다.
"""

import json
import time
import logging
import sqlite3
import threading
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request
import paho.mqtt.client as mqtt

# 로깅 설정
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MQTTDataServer:
    """MQTT 서버 및 데이터 관리 클래스"""

    def __init__(self, host='localhost', port=1883, db_path='truck_gps.db'):
        self.host = host
        self.port = port
        self.db_path = db_path

        # MQTT 클라이언트 설정
        self.mqtt_client = mqtt.Client(client_id="truck_gps_server", clean_session=True)
        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect

        # 데이터 저장소
        self.data_buffer = []
        self.last_update = None

        # Flask 웹 서버
        self.app = Flask(__name__)
        self.setup_routes()

    def setup_routes(self):
        """Flask 라우트 설정"""

        @self.app.route('/')
        def dashboard():
            """메인 대시보드"""
            return render_template('dashboard.html')

        @self.app.route('/api/data/latest')
        def get_latest_data():
            """최신 데이터 조회 API"""
            try:
                limit = request.args.get('limit', 10, type=int)
                data = self.get_latest_gps_temperature_data(limit)

                return jsonify({
                    'success': True,
                    'data': data,
                    'count': len(data),
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"데이터 조회 오류: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/data/stats')
        def get_stats():
            """통계 데이터 조회 API"""
            try:
                stats = self.get_data_statistics()
                return jsonify({
                    'success': True,
                    'stats': stats,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"통계 조회 오류: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

        @self.app.route('/api/data/history')
        def get_history():
            """시간별 히스토리 데이터 조회"""
            try:
                hours = request.args.get('hours', 24, type=int)
                data = self.get_history_data(hours)

                return jsonify({
                    'success': True,
                    'data': data,
                    'hours': hours,
                    'timestamp': datetime.now().isoformat()
                })
            except Exception as e:
                logger.error(f"히스토리 조회 오류: {e}")
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500

    def on_connect(self, client, userdata, flags, rc):
        """MQTT 연결 콜백"""
        if rc == 0:
            logger.info("✅ MQTT 브로커에 연결됨")
            # 토픽 구독
            client.subscribe("truck_gps/+/data")  # truck_gps/{vehicle_id}/data
            client.subscribe("truck_gps/status")
        else:
            logger.error(f"❌ MQTT 연결 실패: {rc}")

    def on_disconnect(self, client, userdata, rc):
        """MQTT 연결 해제 콜백"""
        logger.warning(f"MQTT 연결 해제: {rc}")
        if rc != 0:
            logger.info("재연결 시도 중...")
            time.sleep(5)
            client.reconnect()

    def on_message(self, client, userdata, msg):
        """MQTT 메시지 수신 콜백"""
        try:
            # 메시지 파싱
            payload = json.loads(msg.payload.decode('utf-8'))

            if msg.topic.startswith("truck_gps/") and msg.topic.endswith("/data"):
                # GPS + 온도 데이터 처리
                self.process_gps_temperature_data(payload)
            elif msg.topic == "truck_gps/status":
                # 상태 메시지 처리
                logger.info(f"차량 상태 업데이트: {payload}")

        except json.JSONDecodeError as e:
            logger.error(f"JSON 파싱 오류: {e}")
        except Exception as e:
            logger.error(f"메시지 처리 오류: {e}")

    def process_gps_temperature_data(self, data):
        """GPS + 온도 데이터 처리 및 저장"""
        try:
            # 데이터베이스에 저장
            self.save_gps_temperature_data(data)

            # 버퍼에 추가 (실시간 조회용)
            self.data_buffer.append(data)

            # 버퍼 크기 제한 (최근 1000개만 유지)
            if len(self.data_buffer) > 1000:
                self.data_buffer = self.data_buffer[-1000:]

            self.last_update = datetime.now()
            logger.info(f"데이터 저장 완료: {data.get('vehicle_id', 'unknown')}")

        except Exception as e:
            logger.error(f"데이터 처리 오류: {e}")

    def save_gps_temperature_data(self, data):
        """데이터베이스에 GPS + 온도 데이터 저장"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 데이터베이스 테이블 생성 (없으면 자동 생성)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS gps_temperature_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT NOT NULL,
                    timestamp TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    speed REAL,
                    heading REAL,
                    temperature REAL,
                    status TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # 데이터 삽입
            cursor.execute("""
                INSERT INTO gps_temperature_data
                (vehicle_id, timestamp, latitude, longitude, altitude, speed, heading, temperature, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                data.get('vehicle_id', 'V001'),
                data.get('timestamp', datetime.now().isoformat()),
                data.get('latitude'),
                data.get('longitude'),
                data.get('altitude'),
                data.get('speed'),
                data.get('heading'),
                data.get('temperature'),
                data.get('status', 'normal')
            ))

            conn.commit()
            cursor.close()
            conn.close()

        except sqlite3.Error as e:
            logger.error(f"데이터베이스 저장 오류: {e}")

    def get_latest_gps_temperature_data(self, limit=10):
        """최신 GPS + 온도 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            cursor.execute("""
                SELECT vehicle_id, timestamp, latitude, longitude, altitude,
                       speed, heading, temperature, status, created_at
                FROM gps_temperature_data
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            # 결과를 딕셔너리 리스트로 변환
            result = []
            for row in rows:
                result.append({
                    'vehicle_id': row[0],
                    'timestamp': row[1],
                    'latitude': row[2],
                    'longitude': row[3],
                    'altitude': row[4],
                    'speed': row[5],
                    'heading': row[6],
                    'temperature': row[7],
                    'status': row[8],
                    'created_at': row[9]
                })

            return result

        except sqlite3.Error as e:
            logger.error(f"데이터 조회 오류: {e}")
            return []

    def get_data_statistics(self):
        """데이터 통계 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 전체 데이터 개수
            cursor.execute("SELECT COUNT(*) FROM gps_temperature_data")
            total_count = cursor.fetchone()[0]

            # 차량별 데이터 개수
            cursor.execute("""
                SELECT vehicle_id, COUNT(*) as count
                FROM gps_temperature_data
                GROUP BY vehicle_id
                ORDER BY count DESC
            """)
            vehicle_stats = cursor.fetchall()

            # 시간별 데이터 개수 (최근 24시간)
            cursor.execute("""
                SELECT strftime('%H', created_at) as hour, COUNT(*) as count
                FROM gps_temperature_data
                WHERE created_at >= datetime('now', '-24 hours')
                GROUP BY hour
                ORDER BY hour
            """)
            hourly_stats = cursor.fetchall()

            # 온도 상태별 개수
            cursor.execute("""
                SELECT status, COUNT(*) as count
                FROM gps_temperature_data
                GROUP BY status
                ORDER BY count DESC
            """)
            status_stats = cursor.fetchall()

            cursor.close()
            conn.close()

            return {
                'total_records': total_count,
                'vehicle_stats': [{'vehicle_id': v[0], 'count': v[1]} for v in vehicle_stats],
                'hourly_stats': [{'hour': h[0], 'count': h[1]} for h in hourly_stats],
                'status_stats': [{'status': s[0], 'count': s[1]} for s in status_stats],
                'last_update': self.last_update.isoformat() if self.last_update else None
            }

        except sqlite3.Error as e:
            logger.error(f"통계 조회 오류: {e}")
            return {}

    def get_history_data(self, hours=24):
        """시간별 히스토리 데이터 조회"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()

            # 시간별 평균 데이터 조회
            cursor.execute(f"""
                SELECT
                    strftime('%Y-%m-%d %H:00:00', created_at) as time_group,
                    AVG(temperature) as avg_temp,
                    MIN(temperature) as min_temp,
                    MAX(temperature) as max_temp,
                    AVG(latitude) as avg_lat,
                    AVG(longitude) as avg_lng,
                    COUNT(*) as data_count
                FROM gps_temperature_data
                WHERE created_at >= datetime('now', '-{hours} hours')
                GROUP BY time_group
                ORDER BY time_group
            """)

            rows = cursor.fetchall()
            cursor.close()
            conn.close()

            # 결과를 딕셔너리 리스트로 변환
            result = []
            for row in rows:
                result.append({
                    'timestamp': row[0],
                    'avg_temperature': round(row[1], 2) if row[1] else None,
                    'min_temperature': round(row[2], 2) if row[2] else None,
                    'max_temperature': round(row[3], 2) if row[3] else None,
                    'avg_latitude': round(row[4], 6) if row[4] else None,
                    'avg_longitude': round(row[5], 6) if row[5] else None,
                    'data_count': row[6]
                })

            return result

        except sqlite3.Error as e:
            logger.error(f"히스토리 조회 오류: {e}")
            return []

    def start_mqtt_server(self):
        """MQTT 서버 시작"""
        try:
            logger.info(f"MQTT 브로커 시작: {self.host}:{self.port}")
            self.mqtt_client.connect(self.host, self.port, 60)
            self.mqtt_client.loop_start()
            return True
        except Exception as e:
            logger.error(f"MQTT 서버 시작 실패: {e}")
            return False

    def start_web_server(self, host='0.0.0.0', port=5000):
        """웹 서버 시작"""
        try:
            logger.info(f"웹 서버 시작: http://{host}:{port}")
            self.app.run(host=host, port=port, debug=False, threaded=True)
        except Exception as e:
            logger.error(f"웹 서버 시작 실패: {e}")

    def run(self):
        """MQTT 서버와 웹 서버 동시 실행"""
        # MQTT 서버 시작
        mqtt_success = self.start_mqtt_server()

        if mqtt_success:
            # 웹 서버 시작 (별도 스레드에서)
            web_thread = threading.Thread(
                target=self.start_web_server,
                daemon=True
            )
            web_thread.start()

            logger.info("🚀 MQTT 서버 및 웹 대시보드 시작 완료!")
            logger.info("📊 웹 대시보드: http://localhost:5000")
            logger.info("📡 MQTT 브로커: localhost:1883")

            try:
                # 메인 스레드는 웹 서버를 실행
                self.start_web_server()
            except KeyboardInterrupt:
                logger.info("사용자에 의해 종료")
            finally:
                self.mqtt_client.loop_stop()
                self.mqtt_client.disconnect()
        else:
            logger.error("MQTT 서버 시작 실패로 인해 시스템을 종료합니다.")


def create_dashboard_template():
    """대시보드 HTML 템플릿 생성"""
    template = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>트럭 GPS + 온도 모니터링 대시보드</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .header {
            text-align: center;
            margin-bottom: 30px;
            border-bottom: 2px solid #007bff;
            padding-bottom: 20px;
        }
        .stats-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }
        .stat-card {
            background: linear-gradient(135deg, #007bff, #0056b3);
            color: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }
        .stat-card h3 {
            margin: 0 0 10px 0;
            font-size: 14px;
            opacity: 0.9;
        }
        .stat-card .value {
            font-size: 24px;
            font-weight: bold;
            margin: 0;
        }
        .chart-container {
            position: relative;
            height: 400px;
            margin-bottom: 30px;
        }
        .controls {
            margin-bottom: 20px;
            text-align: center;
        }
        .btn {
            background: #007bff;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            cursor: pointer;
            margin: 0 5px;
        }
        .btn:hover {
            background: #0056b3;
        }
        .status-indicator {
            display: inline-block;
            width: 12px;
            height: 12px;
            border-radius: 50%;
            margin-right: 8px;
        }
        .status-normal { background-color: #28a745; }
        .status-cold { background-color: #17a2b8; }
        .status-warm { background-color: #ffc107; }
        .status-critical { background-color: #dc3545; }
        .data-table {
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }
        .data-table th, .data-table td {
            border: 1px solid #ddd;
            padding: 12px;
            text-align: left;
        }
        .data-table th {
            background-color: #f8f9fa;
            font-weight: bold;
        }
        .data-table tr:nth-child(even) {
            background-color: #f8f9fa;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🚛 트럭 GPS + 온도 모니터링 대시보드</h1>
            <p>실시간 위치 및 온도 데이터를 확인하세요</p>
            <div id="lastUpdate">마지막 업데이트: 로딩 중...</div>
        </div>

        <div class="controls">
            <button class="btn" onclick="refreshData()">새로고침</button>
            <button class="btn" onclick="loadHistory()">24시간 히스토리</button>
            <button class="btn" onclick="loadStats()">통계 보기</button>
        </div>

        <div class="stats-grid">
            <div class="stat-card">
                <h3>총 데이터 수</h3>
                <p class="value" id="totalRecords">-</p>
            </div>
            <div class="stat-card">
                <h3>차량 수</h3>
                <p class="value" id="vehicleCount">-</p>
            </div>
            <div class="stat-card">
                <h3>평균 온도</h3>
                <p class="value" id="avgTemperature">-</p>
            </div>
            <div class="stat-card">
                <h3>정상 상태 비율</h3>
                <p class="value" id="normalStatusRate">-</p>
            </div>
        </div>

        <div class="chart-container">
            <canvas id="temperatureChart"></canvas>
        </div>

        <div class="chart-container">
            <canvas id="locationChart"></canvas>
        </div>

        <h3>📋 최근 데이터</h3>
        <table class="data-table" id="dataTable">
            <thead>
                <tr>
                    <th>차량 ID</th>
                    <th>시간</th>
                    <th>위도</th>
                    <th>경도</th>
                    <th>온도</th>
                    <th>상태</th>
                </tr>
            </thead>
            <tbody id="dataTableBody">
                <tr>
                    <td colspan="6">데이터 로딩 중...</td>
                </tr>
            </tbody>
        </table>
    </div>

    <script>
        let temperatureChart = null;
        let locationChart = null;

        // 페이지 로드 시 데이터 자동 조회
        window.onload = function() {
            refreshData();
            // 30초마다 자동 새로고침
            setInterval(refreshData, 30000);
        };

        function refreshData() {
            loadLatestData();
            loadStats();
        }

        function loadLatestData() {
            fetch('/api/data/latest?limit=10')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateDataTable(data.data);
                        updateCharts(data.data);
                        document.getElementById('lastUpdate').textContent =
                            '마지막 업데이트: ' + new Date().toLocaleString();
                    } else {
                        console.error('데이터 조회 실패:', data.error);
                    }
                })
                .catch(error => {
                    console.error('데이터 조회 오류:', error);
                });
        }

        function loadStats() {
            fetch('/api/data/stats')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateStats(data.stats);
                    } else {
                        console.error('통계 조회 실패:', data.error);
                    }
                })
                .catch(error => {
                    console.error('통계 조회 오류:', error);
                });
        }

        function loadHistory() {
            fetch('/api/data/history?hours=24')
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        updateHistoryChart(data.data);
                    } else {
                        console.error('히스토리 조회 실패:', data.error);
                    }
                })
                .catch(error => {
                    console.error('히스토리 조회 오류:', error);
                });
        }

        function updateStats(stats) {
            document.getElementById('totalRecords').textContent = stats.total_records || 0;
            document.getElementById('avgTemperature').textContent =
                (stats.status_stats.find(s => s.status === 'normal') ?
                 Math.round(stats.status_stats.find(s => s.status === 'normal').count / stats.total_records * 100) : 0) + '%';

            const vehicleCount = stats.vehicle_stats ? stats.vehicle_stats.length : 0;
            document.getElementById('vehicleCount').textContent = vehicleCount;

            const normalCount = stats.status_stats ?
                stats.status_stats.find(s => s.status === 'normal')?.count || 0 : 0;
            const normalRate = stats.total_records > 0 ?
                Math.round(normalCount / stats.total_records * 100) : 0;
            document.getElementById('normalStatusRate').textContent = normalRate + '%';
        }

        function updateDataTable(data) {
            const tbody = document.getElementById('dataTableBody');

            if (!data || data.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6">데이터가 없습니다</td></tr>';
                return;
            }

            tbody.innerHTML = '';
            data.forEach(item => {
                const row = tbody.insertRow();
                row.innerHTML = `
                    <td>${item.vehicle_id}</td>
                    <td>${new Date(item.timestamp).toLocaleString()}</td>
                    <td>${item.latitude ? item.latitude.toFixed(6) : '-'}</td>
                    <td>${item.longitude ? item.longitude.toFixed(6) : '-'}</td>
                    <td>${item.temperature ? item.temperature + '°C' : '-'}</td>
                    <td><span class="status-indicator status-${item.status}"></span>${item.status}</td>
                `;
            });
        }

        function updateCharts(data) {
            updateTemperatureChart(data);
            updateLocationChart(data);
        }

        function updateTemperatureChart(data) {
            const ctx = document.getElementById('temperatureChart').getContext('2d');

            if (temperatureChart) {
                temperatureChart.destroy();
            }

            const labels = data.map(item => new Date(item.timestamp).toLocaleTimeString());
            const temperatures = data.map(item => item.temperature).filter(t => t !== null);

            temperatureChart = new Chart(ctx, {
                type: 'line',
                data: {
                    labels: labels,
                    datasets: [{
                        label: '온도 (°C)',
                        data: temperatures,
                        borderColor: 'rgb(75, 192, 192)',
                        backgroundColor: 'rgba(75, 192, 192, 0.2)',
                        tension: 0.1,
                        fill: true
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        y: {
                            beginAtZero: false,
                            title: {
                                display: true,
                                text: '온도 (°C)'
                            }
                        },
                        x: {
                            title: {
                                display: true,
                                text: '시간'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }

        function updateLocationChart(data) {
            const ctx = document.getElementById('locationChart').getContext('2d');

            if (locationChart) {
                locationChart.destroy();
            }

            const locations = data.filter(item => item.latitude && item.longitude);

            if (locations.length === 0) {
                return;
            }

            locationChart = new Chart(ctx, {
                type: 'scatter',
                data: {
                    datasets: [{
                        label: '차량 위치',
                        data: locations.map(item => ({
                            x: item.longitude,
                            y: item.latitude
                        })),
                        backgroundColor: 'rgba(255, 99, 132, 0.6)',
                        borderColor: 'rgba(255, 99, 132, 1)',
                        borderWidth: 1,
                        pointRadius: 5
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: {
                            title: {
                                display: true,
                                text: '경도'
                            }
                        },
                        y: {
                            title: {
                                display: true,
                                text: '위도'
                            }
                        }
                    },
                    plugins: {
                        legend: {
                            display: true,
                            position: 'top'
                        }
                    }
                }
            });
        }
    </script>
</body>
</html>
    """
    return template


def main():
    """MQTT 서버 및 웹 대시보드 실행"""
    print("🚀 MQTT 서버 및 웹 대시보드 시작...")

    # MQTT 서버용 데이터베이스 파일
    db_path = "truck_gps_dashboard.db"

    # 대시보드 템플릿 파일 생성
    template_dir = "templates"
    import os
    os.makedirs(template_dir, exist_ok=True)

    with open(f"{template_dir}/dashboard.html", "w", encoding="utf-8") as f:
        f.write(create_dashboard_template())

    # MQTT 서버 시작
    server = MQTTDataServer(db_path=db_path)
    server.run()


if __name__ == "__main__":
    main()
