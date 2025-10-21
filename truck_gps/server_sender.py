#!/usr/bin/env python3
"""
서버로 GPS + 온도 데이터를 전송하는 클래스
MySQL 데이터베이스 또는 HTTP API를 통한 데이터 전송
"""

import requests
import json
import time
import logging
import threading
from datetime import datetime, timedelta
from config import (SERVER_HOST, SERVER_PORT, SERVER_DATABASE, SERVER_USERNAME, SERVER_PASSWORD,
                   SERVER_API_URL, SERVER_API_KEY, VEHICLE_ID, SEND_INTERVAL, BATCH_SIZE,
                   RETRY_ATTEMPTS, RETRY_DELAY)

logger = logging.getLogger(__name__)


class ServerSender:
    """서버로 데이터를 전송하는 클래스"""

    def __init__(self, db_path):
        self.db_path = db_path  # 데이터베이스 경로만 저장
        self.vehicle_id = VEHICLE_ID
        self.send_interval = SEND_INTERVAL
        self.batch_size = BATCH_SIZE
        self.retry_attempts = RETRY_ATTEMPTS
        self.retry_delay = RETRY_DELAY

        self.running = False
        self.last_send_time = None
        self.send_thread = None

        # 전송 통계
        self.stats = {
            'total_sent': 0,
            'send_failures': 0,
            'last_success': None
        }

        # 온도 상태 범위 설정
        self.temp_ranges = {
            'critical_cold': (-float('inf'), 2.0),
            'cold': (2.0, 2.5),
            'normal': (2.5, 7.5),
            'warm': (7.5, 8.0),
            'critical_hot': (8.0, float('inf'))
        }

    def start(self):
        """서버 전송 시작"""
        if self.running:
            logger.warning("서버 전송이 이미 실행 중입니다")
            return

        self.running = True
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()
        logger.info(f"서버 전송 시작 (인터벌: {self.send_interval}초)")

    def stop(self):
        """서버 전송 중지"""
        if not self.running:
            return

        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=5)
        logger.info("서버 전송 중지")

    def _send_loop(self):
        """전송 루프 (백그라운드 스레드)"""
        while self.running:
            try:
                current_time = time.time()

                # 전송 간격 확인
                if (self.last_send_time is None or
                    current_time - self.last_send_time >= self.send_interval):

                    self._send_batch()
                    self.last_send_time = current_time

                time.sleep(10)  # 10초마다 체크

            except Exception as e:
                logger.error(f"전송 루프 오류: {e}")
                time.sleep(30)  # 오류 발생 시 30초 대기

    def _send_batch(self):
        """배치 데이터 전송"""
        try:
            # 전송할 데이터 조회
            data_to_send = self._get_unsent_data()
            if not data_to_send:
                logger.debug("전송할 새 데이터가 없습니다")
                return

            logger.info(f"{len(data_to_send)}개의 데이터를 서버로 전송합니다")

            # 서버로 전송 (두 가지 방법 모두 시도)
            success = self._send_to_mysql(data_to_send) or self._send_to_api(data_to_send)

            if success:
                # 성공 시 전송 완료 표시
                self._mark_data_as_sent([item['id'] for item in data_to_send])
                self.stats['total_sent'] += len(data_to_send)
                self.stats['last_success'] = datetime.now()
                logger.info(f"✅ {len(data_to_send)}개 데이터 전송 성공")
            else:
                self.stats['send_failures'] += 1
                logger.error("❌ 데이터 전송 실패")

        except Exception as e:
            logger.error(f"배치 전송 오류: {e}")
            self.stats['send_failures'] += 1

    def _get_unsent_data(self):
        """전송하지 않은 GPS+온도 데이터 조회 (중복 전송 방지)"""
        try:
            # 각 스레드에서 독립적인 데이터베이스 연결 생성
            import sqlite3
            from database import GPSDatabase

            db = GPSDatabase(self.db_path)
            db.connect()

            # 전송하지 않은 GPS+온도 데이터만 조회
            unsent_data = db.get_unsent_gps_temperature_data(limit=self.batch_size)

            # 데이터를 서버 전송 형식으로 변환
            formatted_data = []
            for row in unsent_data:
                formatted_data.append(self._format_gps_temperature_data_for_server(row))

            db.close()
            return formatted_data

        except Exception as e:
            logger.error(f"GPS+온도 데이터 조회 오류: {e}")
            return []

    def _format_gps_temperature_data_for_server(self, row):
        """GPS+온도 데이터베이스 행을 서버 형식으로 변환"""
        # row: (id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status, sent, sent_at, created_at)

        # 온도 상태 재확인 (데이터베이스에 저장된 상태 우선 사용)
        temperature = row[9]   # temperature 필드 (인덱스 9)
        db_status = row[10]    # status 필드 (인덱스 10)

        # 데이터베이스에 상태가 없거나 unknown인 경우에만 재계산
        if not db_status or db_status == 'unknown':
            temp_status = self._get_temperature_status(temperature)
        else:
            temp_status = db_status

        return {
            'vehicle_id': row[1],  # vehicle_id 필드 (인덱스 1)
            'timestamp': datetime.fromtimestamp(row[2]).isoformat() + 'Z',  # timestamp 필드 (인덱스 2)
            'latitude': row[4],    # latitude 필드 (인덱스 4)
            'longitude': row[5],   # longitude 필드 (인덱스 5)
            'altitude': row[6],    # altitude 필드 (인덱스 6)
            'speed': row[7],       # speed 필드 (인덱스 7)
            'heading': row[8],     # heading 필드 (인덱스 8)
            'temperature': temperature,
            'status': temp_status
        }

    def _get_temperature_status(self, temperature):
        """온도값에 따른 상태 판단"""
        if temperature is None:
            return 'unknown'

        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return 'normal'

    def _send_to_mysql(self, data):
        """MySQL 데이터베이스에 직접 저장"""
        try:
            import mysql.connector

            # MySQL 연결
            conn = mysql.connector.connect(
                host=SERVER_HOST,
                port=SERVER_PORT,
                database=SERVER_DATABASE,
                user=SERVER_USERNAME,
                password=SERVER_PASSWORD
            )

            cursor = conn.cursor()

            # GPS + 온도 데이터 저장 (사용자 서버 구조에 맞춤)
            insert_query = """
                INSERT INTO gps_temperature_data
                (vehicle_id, timestamp, latitude, longitude, altitude, speed, heading, temperature, status)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            for item in data:
                cursor.execute(insert_query, (
                    item['vehicle_id'],
                    item['timestamp'].replace('Z', ''),  # Z 제거
                    item.get('latitude'),
                    item.get('longitude'),
                    item.get('altitude'),
                    item.get('speed'),
                    item.get('heading'),
                    item['temperature'],
                    item['status']
                ))

            conn.commit()
            cursor.close()
            conn.close()

            logger.info(f"MySQL 데이터베이스에 {len(data)}개 데이터 저장 완료")
            return True

        except ImportError:
            logger.warning("mysql-connector-python이 설치되지 않았습니다")
            return False
        except Exception as e:
            logger.error(f"MySQL 저장 실패: {e}")
            return False

    def _send_to_api(self, data):
        """HTTP API로 서버에 데이터 전송"""
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {SERVER_API_KEY}',
            'User-Agent': 'TruckGPS/1.0'
        }

        payload = {
            'vehicle_id': self.vehicle_id,
            'data': data,
            'sent_at': datetime.now().isoformat()
        }

        for attempt in range(self.retry_attempts):
            try:
                response = requests.post(
                    SERVER_API_URL,
                    json=payload,
                    headers=headers,
                    timeout=30
                )

                if response.status_code == 200:
                    logger.debug(f"서버 응답: {response.json()}")
                    return True
                else:
                    logger.warning(f"서버 오류 응답: {response.status_code} - {response.text}")

            except requests.exceptions.RequestException as e:
                logger.warning(f"전송 시도 {attempt + 1} 실패: {e}")

                if attempt < self.retry_attempts - 1:
                    logger.info(f"{self.retry_delay}초 후 재시도...")
                    time.sleep(self.retry_delay)

        return False

    def _mark_data_as_sent(self, data_ids):
        """전송 완료된 GPS+온도 데이터 표시 (중복 전송 방지)"""
        try:
            # 각 스레드에서 독립적인 데이터베이스 연결 생성
            import sqlite3
            from database import GPSDatabase

            db = GPSDatabase(self.db_path)
            db.connect()
            db.mark_gps_temperature_data_as_sent(data_ids)
            db.close()
        except Exception as e:
            logger.error(f"GPS+온도 데이터 전송 완료 표시 실패: {e}")

    def get_stats(self):
        """전송 통계 반환"""
        return {
            **self.stats,
            'is_running': self.running,
            'next_send_in': max(0, self.send_interval - (time.time() - (self.last_send_time or 0)))
        }

    def force_send_now(self):
        """즉시 데이터 전송 (수동 실행용)"""
        logger.info("수동 데이터 전송 시작")
        self._send_batch()

    def test_connection(self):
        """서버 연결 테스트"""
        logger.info("서버 연결 테스트 중...")

        test_data = [{
            'id': 999999,
            'vehicle_id': self.vehicle_id,
            'timestamp': datetime.now().isoformat() + 'Z',
            'latitude': 0.0,
            'longitude': 0.0,
            'temperature': 5.0,
            'status': 'normal',
            'test': True
        }]

        try:
            # MySQL 연결 시도
            mysql_success = self._send_to_mysql(test_data)

            # API 연결 시도
            api_success = self._send_to_api(test_data)

            if mysql_success or api_success:
                logger.info("✅ 서버 연결 테스트 성공")
                return True
            else:
                logger.error("❌ 서버 연결 테스트 실패")
                return False
        except Exception as e:
            logger.error(f"연결 테스트 오류: {e}")
            return False


def test_server_connection():
    """서버 연결 테스트 함수"""
    print("🔗 서버 연결 테스트 시작...")

    # 임시 데이터베이스 연결 (테스트용)
    class MockDB:
        def get_latest_data(self, limit): return []

    mock_db = MockDB()
    sender = ServerSender(mock_db)

    success = sender.test_connection()

    if success:
        print("✅ 서버 연결 성공!")
        print(f"차량 ID: {sender.vehicle_id}")
        print(f"전송 설정: {sender.send_interval}초 간격, 배치 크기: {sender.batch_size}")
    else:
        print("❌ 서버 연결 실패!")
        print("서버 설정을 확인해주세요.")

    return success


if __name__ == "__main__":
    """단독 실행 시 연결 테스트"""
    test_server_connection()
