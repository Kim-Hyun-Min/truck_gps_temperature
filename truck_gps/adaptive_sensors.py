#!/usr/bin/env python3
"""
하드웨어가 없어도 프로그램은 계속 실행하고,
GPS/온도 센서가 나중에 연결되면 자동으로 실제 센서를 사용합니다.
"""

import logging
import time

from log_utils import log_repeat, verbose

logger = logging.getLogger(__name__)

RECONNECT_INTERVAL_SEC = 10
# 시리얼 is_open이어도 NMEA 수신이 이 시간 이상 없으면 죽은 연결로 본다
# (gps_tracker의 마지막 좌표 재사용 저장 정책과는 별개)
GPS_IO_STALE_SECONDS = 10


class OptionalGPSReader:
    """GPS 없으면 None 반환, 주기적으로 실제 GPS 연결 시도."""

    def __init__(self, reconnect_interval=RECONNECT_INTERVAL_SEC):
        self.reconnect_interval = reconnect_interval
        self._reader = None
        self._last_attempt = 0.0
        self._announced_waiting = False
        self._stale_announced = False

    def _close_reader(self):
        if self._reader:
            try:
                self._reader.close()
            except Exception:
                pass
        self._reader = None

    def _try_connect(self):
        from gps_reader import GPSReader

        try:
            reader = GPSReader(max_connection_attempts=1)
            self._close_reader()
            self._reader = reader
            if self._announced_waiting:
                logger.debug("GPS 하드웨어 연결됨 — 실측 데이터 사용 시작")
            self._announced_waiting = False
            self._stale_announced = False
            return True
        except Exception as e:
            if not self._announced_waiting:
                log_repeat(
                    logger,
                    "adaptive.gps_waiting",
                    logging.WARNING,
                    "GPS 미연결 — 대기 모드 (%s). USB 연결 시 자동으로 사용합니다.",
                    e,
                )
                self._announced_waiting = True
            self._close_reader()
            return False

    def _io_is_stale(self):
        """열린 포트라도 NMEA 수신이 끊겼으면 True."""
        if not self._reader:
            return True
        try:
            status = self._reader.get_status()
        except Exception:
            return True
        if not status.get("connected"):
            return True
        last_io = status.get("last_io_time")
        if last_io is None:
            return False
        return time.time() - last_io >= GPS_IO_STALE_SECONDS

    def ensure_connected(self):
        if self._reader:
            if self._io_is_stale():
                if not self._stale_announced:
                    log_repeat(
                        logger,
                        "adaptive.gps_stale",
                        logging.WARNING,
                        "GPS 수신이 %s초 이상 없어 포트를 닫고 재탐색합니다",
                        GPS_IO_STALE_SECONDS,
                    )
                    self._stale_announced = True
                self._close_reader()
                self._announced_waiting = True
            else:
                try:
                    status = self._reader.get_status()
                    if status.get("connected"):
                        return True
                except Exception:
                    self._close_reader()

        now = time.time()
        if now - self._last_attempt >= self.reconnect_interval:
            self._last_attempt = now
            self._try_connect()
        return self._reader is not None

    def read(self):
        if not self._reader:
            self.ensure_connected()
            return None
        if self._io_is_stale():
            if not self._stale_announced:
                log_repeat(
                    logger,
                    "adaptive.gps_stale",
                    logging.WARNING,
                    "GPS 수신이 %s초 이상 없어 포트를 닫고 재탐색합니다",
                    GPS_IO_STALE_SECONDS,
                )
                self._stale_announced = True
            self._close_reader()
            self._announced_waiting = True
            return None
        try:
            data = self._reader.read()
            self._stale_announced = False
            if data and data.get("latitude") and data.get("longitude"):
                return data
            return data if data else None
        except Exception as e:
            log_repeat(
                logger, "adaptive.gps_read", logging.WARNING, "GPS 읽기 오류로 연결을 닫습니다: %s", e
            )
            self._close_reader()
            self._announced_waiting = True
            return None

    def reconnect(self):
        self._last_attempt = 0
        self._close_reader()
        return self._try_connect()

    def get_status(self):
        if self._reader and hasattr(self._reader, "get_status"):
            try:
                return self._reader.get_status()
            except Exception:
                pass
        return {"connected": False}

    def close(self):
        self._close_reader()



class OptionalTemperatureReader:
    """온도 센서 없으면 None 반환, 주기적으로 실제 센서 연결 시도."""

    def __init__(self, sensor_type="MCP9600", reconnect_interval=RECONNECT_INTERVAL_SEC):
        self.sensor_type = sensor_type
        self.reconnect_interval = reconnect_interval
        self._reader = None
        self._last_attempt = 0.0
        self._announced_waiting = False

    def _close_reader(self):
        if self._reader:
            try:
                self._reader.close()
            except Exception:
                pass
        self._reader = None

    def _try_connect(self):
        from temperature_reader import TemperatureReader

        try:
            reader = TemperatureReader(sensor_type=self.sensor_type)
            self._close_reader()
            self._reader = reader
            if self._announced_waiting:
                logger.debug("온도 센서 연결됨 (%s) — 실측 데이터 사용 시작", self.sensor_type)
            self._announced_waiting = False
            return True
        except Exception as e:
            if not self._announced_waiting:
                log_repeat(
                    logger,
                    "adaptive.temp_waiting",
                    logging.WARNING,
                    "온도 센서 미연결 — 대기 모드 (%s). 연결되면 자동으로 사용합니다.",
                    e,
                )
                self._announced_waiting = True
            self._close_reader()
            return False

    def ensure_connected(self):
        if self._reader:
            return True
        now = time.time()
        if now - self._last_attempt >= self.reconnect_interval:
            self._last_attempt = now
            self._try_connect()
        return self._reader is not None

    def read(self):
        if not self._reader:
            self.ensure_connected()
            if not self._reader:
                return None
        try:
            return self._reader.read()
        except Exception as e:
            verbose(logger, "온도 읽기 실패, 재연결 대기: %s", e)
            self._close_reader()
            return None

    def is_connected(self):
        return self._reader is not None

    def close(self):
        self._close_reader()
