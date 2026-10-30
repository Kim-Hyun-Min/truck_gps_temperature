#!/usr/bin/env python3
"""Truck GPS + temperature tracker."""

import logging
from logging.handlers import RotatingFileHandler
import signal
import sys
import threading
import time
from collections import deque

from config import (
    DB_PATH,
    INTERVAL,
    LOG_FILE,
    LOG_LEVEL,
    RETENTION_SECONDS,
    SAMPLE_RATE,
    TEMP_RANGES,
    TEMP_SENSOR_TYPE,
    VEHICLE_ID,
)
from database import GPSDatabase
from log_utils import log_repeat, verbose
from server_sender import ServerSender


LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format=LOG_FORMAT,
    handlers=[
        RotatingFileHandler(
            LOG_FILE,
            maxBytes=5 * 1024 * 1024,
            backupCount=3,
            encoding="utf-8",
        ),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


class GPSTracker:
    """Collect latest sensor values, store them locally, and start sender."""

    TEMP_STALE_SECONDS = 10.0

    def __init__(self):
        self.running = False
        self.db = None
        self.gps_reader = None
        self.temp_reader = None
        self.server_sender = None

        self.gps_buffer = deque(maxlen=100)
        self.temp_buffer = deque(maxlen=100)
        self.buffer_lock = threading.Lock()

        self.gps_reader_thread = None
        self.temp_reader_thread = None
        self.temp_ranges = TEMP_RANGES

    def get_temperature_status(self, temperature):
        """Return status label for a temperature value."""
        if temperature is None:
            return "unknown"

        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return "normal"

    def check_gps_connection(self):
        """Check GPS connection and attempt reconnect if needed."""
        if not self.gps_reader:
            return
        try:
            if hasattr(self.gps_reader, "ensure_connected"):
                self.gps_reader.ensure_connected()
                return
            if hasattr(self.gps_reader, "get_status"):
                gps_status = self.gps_reader.get_status()
                if not gps_status.get("connected") and hasattr(self.gps_reader, "reconnect"):
                    self.gps_reader.reconnect()
        except Exception as e:
            log_repeat(logger, "gps_tracker.gps_check", logging.ERROR, "GPS connection check error: %s", e)

    def check_temp_connection(self):
        """Check temperature sensor connection and attempt reconnect if needed."""
        if not self.temp_reader:
            return
        try:
            if hasattr(self.temp_reader, "ensure_connected"):
                self.temp_reader.ensure_connected()
        except Exception as e:
            log_repeat(
                logger,
                "gps_tracker.temp_check",
                logging.ERROR,
                "Temperature sensor connection check error: %s",
                e,
            )

    def setup(self):
        """Initialize database, sensors, and sender."""
        logger.info("Initializing GPS tracker")

        self.db = GPSDatabase()
        self.db.connect()
        self.db.create_tables()

        from adaptive_sensors import OptionalGPSReader, OptionalTemperatureReader

        self.gps_reader = OptionalGPSReader()
        self.gps_reader.ensure_connected()
        logger.debug("GPS reader ready")

        self.temp_reader = OptionalTemperatureReader(sensor_type=TEMP_SENSOR_TYPE)
        self.temp_reader.ensure_connected()
        logger.debug(f"Temperature reader ready ({TEMP_SENSOR_TYPE})")

        self.server_sender = ServerSender(DB_PATH)
        logger.debug("Server sender initialized")

    def gps_reader_loop(self):
        """Continuously read GPS data into a small latest-value buffer."""
        while self.running:
            try:
                gps_data = self.gps_reader.read()
                if gps_data and gps_data.get("latitude") and gps_data.get("longitude"):
                    with self.buffer_lock:
                        self.gps_buffer.append({"data": gps_data, "timestamp": time.time()})
            except Exception as e:
                log_repeat(logger, "gps_tracker.gps_read", logging.ERROR, "GPS read error: %s", e)
            time.sleep(0.01)

    def temp_reader_loop(self):
        """Continuously read temperature data into a small latest-value buffer."""
        while self.running:
            try:
                temperature = self.temp_reader.read()
                if temperature is not None:
                    with self.buffer_lock:
                        self.temp_buffer.append({"data": temperature, "timestamp": time.time()})
            except Exception as e:
                log_repeat(
                    logger, "gps_tracker.temp_read", logging.ERROR, "Temperature read error: %s", e
                )
            time.sleep(0.01)

    def get_data_rate_per_second(self, buffer):
        """Return number of samples appended in the last second."""
        with self.buffer_lock:
            if not buffer:
                return 0
            now = time.time()
            buffer_copy = list(buffer)
        return sum(1 for item in buffer_copy if now - item["timestamp"] <= 1.0)

    def get_latest_data(self, buffer):
        """Return latest data value from a buffer."""
        with self.buffer_lock:
            if buffer:
                return buffer[-1]["data"]
        return None

    def get_latest_sample(self, buffer):
        """Return latest data value and its read timestamp."""
        with self.buffer_lock:
            if buffer:
                item = buffer[-1]
                return item["data"], item["timestamp"]
        return None, None

    def get_current_temperature(self, last_temp_data, last_temp_time):
        """Return a fresh temperature, a short-lived cached value, or None."""
        temperature, sample_time = self.get_latest_sample(self.temp_buffer)
        now = time.time()

        if (
            temperature is not None
            and sample_time is not None
            and now - sample_time <= self.TEMP_STALE_SECONDS
        ):
            return temperature, temperature, sample_time

        if (
            last_temp_data is not None
            and last_temp_time is not None
            and now - last_temp_time <= self.TEMP_STALE_SECONDS
        ):
            return last_temp_data, last_temp_data, last_temp_time

        return None, last_temp_data, last_temp_time

    def start(self):
        """Start collection, storage, and sender loops."""
        self.running = True
        logger.info(f"GPS + temperature collection started (target: {SAMPLE_RATE}/sec)")

        self.gps_reader_thread = threading.Thread(target=self.gps_reader_loop, daemon=True)
        self.temp_reader_thread = threading.Thread(target=self.temp_reader_loop, daemon=True)
        self.gps_reader_thread.start()
        self.temp_reader_thread.start()
        logger.debug("Sensor reader threads started")

        if self.server_sender:
            try:
                self.server_sender.start()
                logger.debug("Server sender started")
            except Exception as e:
                logger.error(f"Server sender start failed: {e}")

        sample_count = 0
        loop_count = 0
        start_time = time.time()
        last_check_time = 0.0
        last_purge_time = 0.0
        last_gps_data = None
        last_temp_data = None
        last_temp_time = None

        try:
            while self.running:
                now = time.time()

                if now - last_check_time >= 10.0:
                    self.check_gps_connection()
                    self.check_temp_connection()
                    last_check_time = now

                if self.db and now - last_purge_time >= 60.0:
                    try:
                        self.db.purge_older_than_seconds(RETENTION_SECONDS)
                    except Exception:
                        pass
                    last_purge_time = now

                target_time = start_time + (loop_count * INTERVAL)
                sleep_time = target_time - time.time()
                if sleep_time > 0:
                    time.sleep(sleep_time)

                gps_rate = self.get_data_rate_per_second(self.gps_buffer)
                temp_rate = self.get_data_rate_per_second(self.temp_buffer)

                gps_data = self.get_latest_data(self.gps_buffer)
                if gps_data:
                    last_gps_data = gps_data
                elif last_gps_data:
                    gps_data = last_gps_data

                temperature, last_temp_data, last_temp_time = self.get_current_temperature(
                    last_temp_data,
                    last_temp_time,
                )

                has_gps = bool(gps_data and gps_data.get("latitude") and gps_data.get("longitude"))
                has_temp = temperature is not None

                if has_gps or has_temp:
                    temp_status = self.get_temperature_status(temperature)

                    self.db.insert_gps_temperature_data(
                        latitude=gps_data["latitude"] if has_gps else None,
                        longitude=gps_data["longitude"] if has_gps else None,
                        altitude=gps_data.get("altitude") if has_gps else None,
                        speed=gps_data.get("speed") if has_gps else None,
                        heading=gps_data.get("heading") if has_gps else None,
                        temperature=temperature,
                        vehicle_id=VEHICLE_ID,
                        status=temp_status,
                    )

                    sample_count += 1
                    if sample_count % 10 == 0:
                        elapsed = time.time() - start_time
                        save_rate = sample_count / elapsed if elapsed > 0 else 0
                        temp_str = f"{temperature:.1f}C" if temperature is not None else "N/A"
                        if has_gps:
                            gps_str = (
                                f"lat={gps_data['latitude']:.6f}, "
                                f"lon={gps_data['longitude']:.6f}, "
                                f"speed={gps_data.get('speed', 0):.1f}km/h, "
                                f"sat={gps_data.get('satellites', 0)}"
                            )
                        else:
                            gps_str = "GPS=N/A"
                        verbose(
                            logger,
                            "sample #%s | GPS=%s/sec, TEMP=%s/sec | %s | temp=%s | save_rate=%.2f/sec",
                            sample_count,
                            gps_rate,
                            temp_rate,
                            gps_str,
                            temp_str,
                            save_rate,
                        )
                else:
                    verbose(
                        logger,
                        "Waiting for data. GPS=%s/sec, TEMP=%s/sec",
                        gps_rate,
                        temp_rate,
                    )

                loop_count += 1

        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Tracker error: {e}", exc_info=True)
        finally:
            self.stop()

    def stop(self):
        """Stop collection and close resources."""
        if not self.running:
            return

        self.running = False

        if self.server_sender:
            self.server_sender.stop()
            self.server_sender = None

        if self.db:
            try:
                total_count = self.db.get_gps_temperature_data_count()
                logger.info(f"Total saved rows: {total_count}")
            except Exception:
                pass
            self.db.close()
            self.db = None

        if self.gps_reader:
            self.gps_reader.close()
            self.gps_reader = None

        if self.temp_reader:
            self.temp_reader.close()
            self.temp_reader = None

        logger.info("GPS + temperature tracker stopped")

    def signal_handler(self, signum, frame):
        """Handle system signals."""
        logger.info(f"Signal received: {signum}")
        self.stop()
        sys.exit(0)


def main():
    tracker = GPSTracker()
    signal.signal(signal.SIGINT, tracker.signal_handler)
    signal.signal(signal.SIGTERM, tracker.signal_handler)
    tracker.setup()
    tracker.start()


if __name__ == "__main__":
    main()
