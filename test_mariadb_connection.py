#!/usr/bin/env python3
"""
MariaDB 연결 테스트 스크립트
"""

import mysql.connector
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def test_mariadb_connection():
    """MariaDB 연결 테스트"""
    try:
        # MariaDB 연결 설정
        connection = mysql.connector.connect(
            host="192.168.0.102",  # 다른 PC의 MariaDB 서버
            port=3306,
            user="vaccine",  # 사용자명
            password="dlsvmfk0331",  # 비밀번호
            database="truck",  # 실제 데이터베이스 이름
            auth_plugin='mysql_native_password'  # 인증 플러그인 명시
        )

        logger.info("✅ MariaDB 연결 성공!")

        # 커서 생성
        cursor = connection.cursor()

        # 테이블 목록 확인
        cursor.execute("SHOW TABLES;")
        tables = cursor.fetchall()
        logger.info("📋 존재하는 테이블 목록:")
        for table in tables:
            logger.info(f"  - {table[0]}")

        # gps_temperature_data 테이블 구조 확인
        try:
            cursor.execute("DESCRIBE gps_temperature_data;")
            columns = cursor.fetchall()
            logger.info("\n📊 gps_temperature_data 테이블 구조:")
            for column in columns:
                logger.info(f"  {column[0]}: {column[1]} ({'NULL' if column[2] == 'YES' else 'NOT NULL'})")
        except mysql.connector.Error as e:
            logger.warning(f"⚠️ gps_temperature_data 테이블이 존재하지 않거나 접근할 수 없습니다: {e}")

            # 테이블 생성 SQL 제안
            logger.info("\n💡 테이블이 없는 경우 다음 SQL로 생성하세요:")
            logger.info("""
CREATE TABLE gps_temperature_data (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vehicle_id VARCHAR(50) NOT NULL,
    timestamp DATETIME NOT NULL,
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    altitude DECIMAL(8, 2),
    speed DECIMAL(5, 2),
    heading DECIMAL(5, 2),
    temperature DECIMAL(5, 2),
    status VARCHAR(20),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_vehicle_timestamp (vehicle_id, timestamp),
    INDEX idx_timestamp (timestamp)
);
            """)

        # 연결 종료
        cursor.close()
        connection.close()
        logger.info("🔌 MariaDB 연결 종료")

        return True

    except mysql.connector.Error as e:
        logger.error(f"❌ MariaDB 연결 실패: {e}")
        return False

if __name__ == "__main__":
    logger.info("🔗 MariaDB 연결 테스트 시작...")
    success = test_mariadb_connection()

    if success:
        logger.info("✅ 테스트 완료!")
    else:
        logger.error("❌ 테스트 실패!")
