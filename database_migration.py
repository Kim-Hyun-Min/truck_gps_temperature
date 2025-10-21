#!/usr/bin/env python3
"""
데이터베이스 마이그레이션 스크립트
기존 데이터베이스에 새로운 컬럼들을 추가합니다.
"""

import sqlite3
import logging
import os
from config import DB_PATH

logger = logging.getLogger(__name__)

def migrate_database():
    """데이터베이스 스키마를 업데이트"""
    if not os.path.exists(DB_PATH):
        logger.info(f"데이터베이스 파일이 존재하지 않습니다: {DB_PATH}")
        return False

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # 현재 테이블 구조 확인
        cursor.execute("PRAGMA table_info(gps_data)")
        existing_columns = {row[1] for row in cursor.fetchall()}

        logger.info(f"현재 데이터베이스 컬럼들: {existing_columns}")

        # 필요한 새 컬럼들 (gps_temperature_data 테이블용)
        required_columns = {
            'vehicle_id', 'latitude', 'longitude', 'altitude', 'speed', 'heading',
            'temperature', 'status', 'sent', 'sent_at', 'created_at'
        }

        # 추가해야 할 컬럼들 찾기
        missing_columns = required_columns - existing_columns

        if not missing_columns:
            logger.info("데이터베이스 스키마가 이미 최신 상태입니다")
            return True

        logger.info(f"추가해야 할 컬럼들: {missing_columns}")

        # 컬럼 추가 (SQLite는 ALTER TABLE로 컬럼 추가 가능)
        for column in missing_columns:
            if column == 'vehicle_id':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN vehicle_id TEXT DEFAULT 'V001'")
            elif column == 'latitude':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN latitude REAL")
            elif column == 'longitude':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN longitude REAL")
            elif column == 'altitude':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN altitude REAL")
            elif column == 'speed':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN speed REAL")
            elif column == 'heading':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN heading REAL")
            elif column == 'temperature':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN temperature REAL")
            elif column == 'status':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN status TEXT DEFAULT 'normal'")
            elif column == 'sent':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN sent BOOLEAN DEFAULT FALSE")
            elif column == 'sent_at':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN sent_at TIMESTAMP")
            elif column == 'created_at':
                cursor.execute("ALTER TABLE gps_data ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")

        # 기존 데이터 업데이트 (vehicle_id 설정)
        cursor.execute("UPDATE gps_data SET vehicle_id = 'V001' WHERE vehicle_id IS NULL")

        conn.commit()

        # 업데이트된 테이블 구조 확인
        cursor.execute("PRAGMA table_info(gps_data)")
        updated_columns = {row[1] for row in cursor.fetchall()}
        logger.info(f"업데이트된 데이터베이스 컬럼들: {updated_columns}")

        cursor.close()
        conn.close()

        logger.info("✅ 데이터베이스 마이그레이션 완료!")
        return True

    except sqlite3.Error as e:
        logger.error(f"데이터베이스 마이그레이션 실패: {e}")
        return False
    except Exception as e:
        logger.error(f"마이그레이션 중 오류 발생: {e}")
        return False

def check_database_schema():
    """현재 데이터베이스 스키마 확인"""
    if not os.path.exists(DB_PATH):
        logger.info(f"데이터베이스 파일이 존재하지 않습니다: {DB_PATH}")
        return None

    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("PRAGMA table_info(gps_data)")
        columns = cursor.fetchall()

        print("\n=== 현재 데이터베이스 스키마 ===")
        print(f"{'컬럼명'"<15"} {'타입'"<10"} {'기본값'"<10"} {'NULL허용'"<8"}")
        print("-" * 50)

        for col in columns:
            col_name, col_type, _, _, _, default_value = col[:6]
            nullable = "YES" if col[3] == 0 else "NO"
            print(f"{col_name"<15"} {col_type"<10"} {str(default_value or '')"<10"} {nullable"<8"}")

        cursor.close()
        conn.close()

        return columns

    except Exception as e:
        logger.error(f"스키마 확인 실패: {e}")
        return None

def main():
    """메인 실행 함수"""
    print("🔄 데이터베이스 마이그레이션 시작...")

    # 현재 스키마 확인
    print("\n1️⃣ 현재 데이터베이스 구조 확인:")
    current_schema = check_database_schema()

    if current_schema is None:
        print("❌ 데이터베이스 연결 실패")
        return

    # 마이그레이션 실행
    print("\n2️⃣ 마이그레이션 실행:")
    success = migrate_database()

    if success:
        print("\n3️⃣ 마이그레이션 후 구조 확인:")
        check_database_schema()
    else:
        print("❌ 마이그레이션 실패")

if __name__ == "__main__":
    main()
