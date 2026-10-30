import logging
import sqlite3
import time
from datetime import datetime

from config import DB_PATH, VEHICLE_ID
from log_utils import log_repeat

logger = logging.getLogger(__name__)


class GPSDatabase:
    """SQLite storage for GPS and temperature rows."""

    WRITE_RETRY_COUNT = 5
    WRITE_RETRY_BASE_DELAY = 0.2

    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.conn = None
        self.cursor = None

    def connect(self):
        """Connect to SQLite and enable settings that reduce writer lock failures."""
        try:
            self.conn = sqlite3.connect(self.db_path, timeout=30)
            self.conn.execute("PRAGMA busy_timeout = 30000")
            self.conn.execute("PRAGMA journal_mode = WAL")
            self.conn.execute("PRAGMA synchronous = NORMAL")
            self.cursor = self.conn.cursor()
            logger.debug(f"Database connected: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection failed: {e}")
            raise

    def _rollback_quietly(self):
        try:
            if self.conn:
                self.conn.rollback()
        except sqlite3.Error:
            pass

    def _is_locked_error(self, error):
        return "database is locked" in str(error).lower()

    def _write_with_retry(self, operation, error_message, default=None):
        for attempt in range(self.WRITE_RETRY_COUNT):
            try:
                result = operation()
                self.conn.commit()
                return result
            except sqlite3.Error as e:
                self._rollback_quietly()
                if self._is_locked_error(e) and attempt < self.WRITE_RETRY_COUNT - 1:
                    delay = self.WRITE_RETRY_BASE_DELAY * (attempt + 1)
                    log_repeat(
                        logger,
                        "db.locked",
                        logging.WARNING,
                        "%s: database is locked; retrying in %.1fs",
                        error_message,
                        delay,
                    )
                    time.sleep(delay)
                    continue

                log_repeat(logger, "db.write", logging.ERROR, "%s: %s", error_message, e)
                return default

    def create_tables(self):
        """Create the GPS temperature table and indexes."""
        try:
            self.cursor.execute(f"""
                CREATE TABLE IF NOT EXISTS gps_temperature_data (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    vehicle_id TEXT NOT NULL DEFAULT '{VEHICLE_ID}',
                    timestamp REAL NOT NULL,
                    datetime TEXT NOT NULL,
                    latitude REAL,
                    longitude REAL,
                    altitude REAL,
                    speed REAL,
                    heading REAL,
                    temperature REAL,
                    status TEXT DEFAULT 'normal',
                    sent BOOLEAN DEFAULT FALSE,
                    sent_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp
                ON gps_temperature_data(timestamp)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_datetime
                ON gps_temperature_data(datetime)
            """)

            self.cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sent_timestamp
                ON gps_temperature_data(sent, timestamp)
            """)

            self.conn.commit()
            logger.debug("Database tables are ready")
        except sqlite3.Error as e:
            logger.error(f"Table creation failed: {e}")
            raise

    def insert_gps_temperature_data(self, latitude=None, longitude=None, altitude=None,
                                    speed=None, heading=None, temperature=None,
                                    vehicle_id=VEHICLE_ID, status="normal"):
        """Insert one GPS + temperature row."""
        timestamp = datetime.now().timestamp()
        datetime_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")

        def operation():
            self.cursor.execute("""
                INSERT INTO gps_temperature_data
                (vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                vehicle_id,
                timestamp,
                datetime_str,
                latitude,
                longitude,
                altitude,
                speed,
                heading,
                temperature,
                status,
            ))
            return self.cursor.lastrowid

        return self._write_with_retry(operation, "GPS temperature insert failed", default=None)

    def get_latest_gps_temperature_data(self, limit=10):
        """Load the latest GPS + temperature rows."""
        try:
            self.cursor.execute("""
                SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status, sent, sent_at, created_at
                FROM gps_temperature_data
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"GPS temperature query failed: {e}")
            return []

    def get_unsent_gps_temperature_data(self, limit=15):
        """Load the latest rows using the configured batch size.

        The method name is kept for compatibility with server_sender.py. It no longer
        filters by sent status because the sender is configured to always publish the
        latest rows.
        """
        try:
            self.cursor.execute("""
                SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status, sent, sent_at, created_at
                FROM gps_temperature_data
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            logger.error(f"Latest GPS temperature query failed: {e}")
            return []

    def get_gps_temperature_data_count(self):
        """Return total stored row count."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM gps_temperature_data")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"GPS temperature count query failed: {e}")
            return 0

    def mark_gps_temperature_data_as_sent(self, data_ids):
        """Mark rows as sent after a successful publish."""
        if not data_ids:
            return

        placeholders = ",".join(["?"] * len(data_ids))

        def operation():
            self.cursor.execute(f"""
                UPDATE gps_temperature_data SET sent = TRUE, sent_at = ?
                WHERE id IN ({placeholders})
            """, [datetime.now()] + data_ids)
            logger.debug(f"Marked {len(data_ids)} GPS temperature rows as sent")
            return None

        self._write_with_retry(operation, "GPS temperature sent mark failed", default=None)

    def get_sent_gps_temperature_count(self):
        """Return sent row count."""
        try:
            self.cursor.execute("SELECT COUNT(*) FROM gps_temperature_data WHERE sent = TRUE")
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Sent GPS temperature count query failed: {e}")
            return 0

    def get_unsent_gps_temperature_count(self):
        """Return unsent row count."""
        try:
            self.cursor.execute(
                "SELECT COUNT(*) FROM gps_temperature_data WHERE sent = FALSE OR sent IS NULL"
            )
            return self.cursor.fetchone()[0]
        except sqlite3.Error as e:
            logger.error(f"Unsent GPS temperature count query failed: {e}")
            return 0

    def purge_older_than_seconds(self, max_age_seconds: float) -> int:
        """Delete rows older than max_age_seconds and return the deleted count."""
        cutoff = time.time() - float(max_age_seconds)

        def operation():
            self.cursor.execute("DELETE FROM gps_temperature_data WHERE timestamp < ?", (cutoff,))
            deleted = self.cursor.rowcount if self.cursor.rowcount is not None else 0
            if deleted:
                logger.debug(f"Purged {deleted} old rows older than {int(max_age_seconds)}s")
            return deleted

        return self._write_with_retry(operation, "Old GPS temperature purge failed", default=0)

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            self.cursor = None
            logger.debug("Database connection closed")

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
