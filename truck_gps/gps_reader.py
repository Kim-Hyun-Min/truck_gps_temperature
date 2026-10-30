#!/usr/bin/env python3
"""
실제 GPS 모듈에서 데이터를 읽는 클래스
시리얼 포트를 통해 NMEA 데이터 수신.
설정 포트와 /dev/ttyACM*·/dev/ttyUSB* 후보를 순회해 NMEA가 나오는 포트를 사용한다.
"""

import glob
import logging
import serial
import time

from config import GPS_PORT, GPS_BAUDRATE
from log_utils import log_repeat

try:
    from config import GPS_PORT_GLOBS
except ImportError:
    GPS_PORT_GLOBS = ["/dev/ttyACM*", "/dev/ttyUSB*"]

logger = logging.getLogger(__name__)

# 포트 후보에서 NMEA($GP/$GN)가 나오는지 확인할 대기 시간
PROBE_TIMEOUT_SEC = 2.0


class GPSReader:
    """GPS 모듈에서 NMEA 데이터를 읽는 클래스"""

    def __init__(self, max_connection_attempts=5):
        self.serial_conn = None
        self.port = GPS_PORT
        self.last_successful_read = None
        self.last_io_time = None
        self.connection_attempts = 0
        self.max_connection_attempts = max_connection_attempts
        self.connect()

    @staticmethod
    def _is_nmea_line(line):
        return bool(line) and (line.startswith("$GP") or line.startswith("$GN"))

    @staticmethod
    def candidate_ports():
        """설정 포트 + ACM/USB glob 후보 (중복 제거, 설정 포트 우선)."""
        candidates = []
        if GPS_PORT:
            candidates.append(GPS_PORT)
        for pattern in GPS_PORT_GLOBS:
            for path in sorted(glob.glob(pattern)):
                if path not in candidates:
                    candidates.append(path)
        return candidates

    def _close_serial(self):
        if self.serial_conn:
            try:
                if self.serial_conn.is_open:
                    self.serial_conn.close()
            except Exception:
                pass
        self.serial_conn = None

    def _open_port(self, port):
        """포트를 열고 NMEA($GP/$GN) 문장이 나오는지 확인한다."""
        ser = serial.Serial(
            port,
            baudrate=GPS_BAUDRATE,
            timeout=0.2,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            bytesize=serial.EIGHTBITS,
        )
        deadline = time.time() + PROBE_TIMEOUT_SEC
        try:
            while time.time() < deadline:
                raw = ser.readline()
                if not raw:
                    continue
                line = raw.decode("ascii", errors="ignore").strip()
                if self._is_nmea_line(line):
                    ser.timeout = 1
                    return ser
        except serial.SerialException:
            try:
                ser.close()
            except Exception:
                pass
            raise

        try:
            ser.close()
        except Exception:
            pass
        return None

    def connect(self):
        """설정·후보 포트에서 NMEA가 나오는 GPS에 연결"""
        self._close_serial()

        candidates = self.candidate_ports()
        if not candidates:
            self.connection_attempts += 1
            err = serial.SerialException("GPS 포트 후보가 없습니다")
            if self.connection_attempts >= self.max_connection_attempts:
                log_repeat(
                    logger, "gps.max_attempts_no_port", logging.ERROR, "GPS 최대 연결 시도 초과. 포트 후보 없음"
                )
                raise err
            time.sleep(2)
            return self.connect()

        last_error = None
        for port in candidates:
            try:
                ser = self._open_port(port)
                if ser is None:
                    logger.debug("GPS NMEA 없음, 다음 포트: %s", port)
                    continue
                self.serial_conn = ser
                self.port = port
                self.connection_attempts = 0
                self.last_io_time = time.time()
                logger.debug("GPS 모듈 연결 성공: %s", port)
                return
            except serial.SerialException as e:
                last_error = e
                logger.debug("GPS 포트 열기 실패 (%s): %s", port, e)
                continue

        self.connection_attempts += 1
        detail = last_error or "NMEA($GP/$GN) 응답 없음"
        logger.debug(
            "GPS 연결 실패 (시도 %s/%s): %s",
            self.connection_attempts,
            self.max_connection_attempts,
            detail,
        )

        if self.connection_attempts >= self.max_connection_attempts:
            log_repeat(
                logger,
                "gps.max_attempts",
                logging.ERROR,
                "GPS 최대 연결 시도 초과. 모듈/포트 확인 필요 (후보: %s)",
                ", ".join(candidates),
            )
            raise serial.SerialException(f"GPS 연결 실패: {detail}")

        time.sleep(2)
        self.connect()

    def is_connected(self):
        """연결 상태 확인"""
        return self.serial_conn is not None and self.serial_conn.is_open

    def reconnect(self):
        """연결 재시도 (포트 재탐색 포함)"""
        logger.debug("GPS 모듈 재연결을 시도합니다...")
        self.connect()

    def parse_nmea_gga(self, sentence):
        """GPGGA NMEA 문장 파싱"""
        try:
            parts = sentence.split(',')

            if len(parts) < 15 or parts[0] not in ['$GPGGA', '$GNGGA']:
                return None

            # 위도 파싱
            if parts[2] and parts[3]:
                lat_deg = float(parts[2][:2])
                lat_min = float(parts[2][2:])
                latitude = lat_deg + lat_min / 60.0
                if parts[3] == 'S':
                    latitude = -latitude
            else:
                return None

            # 경도 파싱
            if parts[4] and parts[5]:
                lon_deg = float(parts[4][:3])
                lon_min = float(parts[4][3:])
                longitude = lon_deg + lon_min / 60.0
                if parts[5] == 'W':
                    longitude = -longitude
            else:
                return None

            # 추가 정보
            fix_quality = int(parts[6]) if parts[6] else 0
            satellites = int(parts[7]) if parts[7] else 0
            altitude = float(parts[9]) if parts[9] else None

            return {
                'latitude': latitude,
                'longitude': longitude,
                'altitude': altitude,
                'satellites': satellites,
                'fix_quality': fix_quality
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"NMEA 파싱 오류: {e}")
            return None

    def parse_nmea_rmc(self, sentence):
        """GPRMC NMEA 문장 파싱 (속도, 방향 정보)"""
        try:
            parts = sentence.split(',')

            if len(parts) < 12 or parts[0] not in ['$GPRMC', '$GNRMC']:
                return None

            # 속도 (노트를 km/h로 변환)
            speed = float(parts[7]) * 1.852 if parts[7] else None

            # 방향 (도)
            heading = float(parts[8]) if parts[8] else None

            return {
                'speed': speed,
                'heading': heading
            }
        except (ValueError, IndexError) as e:
            logger.debug(f"NMEA 파싱 오류: {e}")
            return None

    def read(self):
        """GPS 데이터 읽기. 포트가 닫혀 있거나 시리얼 오류면 예외를 올린다."""
        if not self.is_connected():
            raise serial.SerialException(
                f"GPS 시리얼 포트가 닫혀 있습니다: {self.port}"
            )

        gps_data = {}

        try:
            for _ in range(15):
                try:
                    if self.serial_conn.in_waiting > 0:
                        line = self.serial_conn.readline().decode(
                            'ascii', errors='ignore'
                        ).strip()

                        if not line:
                            continue

                        if self._is_nmea_line(line):
                            self.last_io_time = time.time()

                        if line.startswith('$GPGGA') or line.startswith('$GNGGA'):
                            gga_data = self.parse_nmea_gga(line)
                            if gga_data:
                                gps_data.update(gga_data)

                        elif line.startswith('$GPRMC') or line.startswith('$GNRMC'):
                            rmc_data = self.parse_nmea_rmc(line)
                            if rmc_data:
                                gps_data.update(rmc_data)

                        if 'latitude' in gps_data and 'longitude' in gps_data:
                            self.last_successful_read = time.time()
                            return gps_data
                    else:
                        time.sleep(0.05)
                        continue

                except UnicodeDecodeError as e:
                    logger.debug(f"데이터 디코딩 오류: {e}")
                    continue
                except serial.SerialException:
                    raise
                except Exception as e:
                    logger.debug(f"데이터 읽기 중 오류: {e}")
                    break

            if gps_data:
                missing_fields = []
                if 'latitude' not in gps_data:
                    missing_fields.append('위도')
                if 'longitude' not in gps_data:
                    missing_fields.append('경도')
                if missing_fields:
                    logger.debug(
                        f"불완전한 GPS 데이터 수신: {', '.join(missing_fields)} 누락"
                    )

            return gps_data if gps_data else None

        except serial.SerialException:
            self.close()
            raise
        except Exception:
            self.close()
            raise

    def close(self):
        """연결 종료"""
        if self.serial_conn:
            try:
                self.serial_conn.close()
                logger.debug("GPS 모듈 연결 종료")
            except Exception as e:
                logger.warning(f"연결 종료 중 오류 발생: {e}")
            finally:
                self.serial_conn = None

    def get_status(self):
        """GPS 상태 정보 반환"""
        return {
            'connected': self.is_connected(),
            'last_successful_read': self.last_successful_read,
            'last_io_time': self.last_io_time,
            'connection_attempts': self.connection_attempts,
            'port': self.port,
            'baudrate': GPS_BAUDRATE
        }
