#!/usr/bin/env python3
"""
냉장고 온도 센서 읽기 — MCP9600, DS18B20, DHT22
"""

import logging
import subprocess
import gpiozero
import time
import sys
from config import (
    TEMP_RANGES,
    MCP9600_THERMOCOUPLE_TYPE,
    MCP9600_I2C_ADDRESS,
    MCP9600_I2C_ADDRESS_CANDIDATES,
    MCP9600_TC_FILTER,
)
from log_utils import log_repeat, verbose

logger = logging.getLogger(__name__)


class TemperatureReader:
    """실제 온도 센서에서 데이터를 읽는 클래스"""

    def __init__(self, sensor_type="MCP9600"):
        self.sensor_type = sensor_type
        self.sensor = None
        self.temp_ranges = TEMP_RANGES
        self._mcp9600_junctions_logged = False
        self.connect()

    def get_temperature_status(self, temperature):
        if temperature is None:
            return "unknown"
        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return "normal"

    def connect(self):
        try:
            if self.sensor_type == "MCP9600":
                import adafruit_mcp9600
                import board
                import busio

                i2c = None
                for freq in [100000, 10000, 400000]:
                    try:
                        i2c = busio.I2C(board.SCL, board.SDA, frequency=freq)
                        break
                    except Exception:
                        if freq == 400000:
                            raise

                tc_type = MCP9600_THERMOCOUPLE_TYPE
                tc_filt = max(0, min(7, int(MCP9600_TC_FILTER)))
                addrs = (
                    [MCP9600_I2C_ADDRESS]
                    if MCP9600_I2C_ADDRESS is not None
                    else list(MCP9600_I2C_ADDRESS_CANDIDATES)
                )

                last_err = None
                for address in addrs:
                    try:
                        self.sensor = adafruit_mcp9600.MCP9600(
                            i2c,
                            address=address,
                            tctype=tc_type,
                            tcfilter=tc_filt,
                        )
                        logger.debug(
                            f"MCP9600 연결 (I2C 0x{address:02X}, 열전대={tc_type}, 필터={tc_filt})"
                        )
                        break
                    except Exception as e:
                        last_err = e
                        continue
                else:
                    raise Exception(f"MCP9600 주소 시도 실패: {last_err}") from last_err

            elif self.sensor_type == "DS18B20":
                import glob

                device_folders = glob.glob("/sys/bus/w1/devices/28*")
                if device_folders:
                    self.sensor_file = device_folders[0] + "/w1_slave"
                    logger.debug(f"DS18B20 연결: {device_folders[0]}")
                else:
                    raise FileNotFoundError(
                        "DS18B20 없음. 1-Wire 활성화와 /sys/bus/w1/devices 를 확인하세요."
                    )

            elif self.sensor_type == "DHT22":
                import adafruit_dht
                import board

                self.sensor = adafruit_dht.DHT22(board.D4)
                logger.debug("DHT22 연결 (GPIO4)")
            else:
                raise ValueError(f"지원하지 않는 센서: {self.sensor_type}")

        except Exception as e:
            log_repeat(logger, "temp.connect", logging.ERROR, "온도 센서 연결 실패: %s", e)
            raise

    def read_mcp9600(self):
        """
        Adafruit 드라이버: temperature = 핫 접합(열전대 측), ambient_temperature = 냉 접합(IC 주변).
        얼음물 시험 시 핫은 약 0°C 근처여야 함. 값이 비정상적으로 높으면 열전대 극성/접촉/타입·배선을 먼저 의심.
        """
        try:
            hot = self.sensor.temperature
            if not self._mcp9600_junctions_logged:
                self._mcp9600_junctions_logged = True
                try:
                    amb = self.sensor.ambient_temperature
                    delta = self.sensor.delta_temperature
                    logger.debug(
                        "MCP9600 점검(1회): 핫접합=%.2f°C, 냉접합(주변)=%.2f°C, 델타=%.2f°C — "
                        "얼음 시험 시 핫은 ~0°C대가 정상입니다.",
                        hot,
                        amb,
                        delta,
                    )
                except Exception:
                    logger.debug("MCP9600 핫접합=%.2f°C (냉접합 읽기 생략)", hot)
            return hot
        except Exception as e:
            log_repeat(logger, "temp.mcp9600", logging.ERROR, "MCP9600 읽기 오류: %s", e)
            return None

    def read_ds18b20(self):
        try:
            with open(self.sensor_file, "r") as f:
                lines = f.readlines()
            if lines[0].strip()[-3:] != "YES":
                return None
            temp_pos = lines[1].find("t=")
            if temp_pos != -1:
                return float(lines[1][temp_pos + 2 :]) / 1000.0
        except Exception as e:
            log_repeat(logger, "temp.ds18b20", logging.ERROR, "DS18B20 읽기 오류: %s", e)
        return None

    def read_dht22(self):
        try:
            return self.sensor.temperature
        except RuntimeError as e:
            verbose(logger, "DHT22 재시도: %s", e)
            return None
        except Exception as e:
            log_repeat(logger, "temp.dht22", logging.ERROR, "DHT22 읽기 오류: %s", e)
            return None

    def read(self):
        if self.sensor_type == "MCP9600":
            return self.read_mcp9600()
        if self.sensor_type == "DS18B20":
            return self.read_ds18b20()
        if self.sensor_type == "DHT22":
            return self.read_dht22()
        return None

    def read_with_status(self):
        temperature = self.read()
        return {"temperature": temperature, "status": self.get_temperature_status(temperature)}

    def close(self):
        if self.sensor_type == "DHT22" and self.sensor:
            self.sensor.exit()
        logger.debug("온도 센서 연결 종료")

    def gpio_debug_info(self):
        """I2C(MCP9600)는 bus 점유 중이므로 SDA/SCL을 gpiozero로 읽지 않음."""
        logger.info("=== GPIO 디버깅 ===")
        try:
            if self.sensor_type == "MCP9600":
                logger.info("MCP9600은 I2C(SDA/SCL) 사용 — gpiozero로 해당 핀을 잡지 않습니다.")
            if self.sensor_type == "DHT22":
                p = gpiozero.Button(4)
                logger.info(f"DHT22 GPIO4: {'HIGH' if p.value else 'LOW'}")
                p.close()
            if self.sensor_type == "DS18B20":
                p = gpiozero.Button(4)
                logger.info(f"1-Wire GPIO4: {'HIGH' if p.value else 'LOW'}")
                p.close()
        except Exception as e:
            logger.error(f"GPIO 디버깅 오류: {e}")

    def check_i2c_communication(self):
        logger.info("=== i2cdetect ===")
        try:
            r = subprocess.run(["i2cdetect", "-y", "1"], capture_output=True, text=True)
            if r.returncode == 0:
                logger.info(r.stdout)
            else:
                logger.error(r.stderr or "i2cdetect 실패")
        except FileNotFoundError:
            logger.error("i2cdetect 없음")
        except Exception as e:
            logger.error(f"i2cdetect 오류: {e}")

    def sensor_connection_test(self):
        logger.info(f"=== {self.sensor_type} 연결 테스트 ===")
        try:
            if self.sensor_type == "MCP9600":
                t = self.sensor.temperature
                logger.info(f"MCP9600 온도: {t}°C")
            elif self.sensor_type == "DHT22":
                t = self.sensor.temperature
                logger.info(f"DHT22 온도: {t}°C")
            elif self.sensor_type == "DS18B20":
                import glob

                dev = glob.glob("/sys/bus/w1/devices/28*")
                if dev:
                    logger.info(f"DS18B20: {dev[0]}")
                else:
                    logger.error("DS18B20 장치 없음")
        except Exception as e:
            logger.error(f"연결 테스트 오류: {e}")


def test_temperature_sensor(sensor_type="MCP9600"):
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    try:
        reader = TemperatureReader(sensor_type=sensor_type)
        reader.gpio_debug_info()
        reader.check_i2c_communication()
        reader.sensor_connection_test()
        for i in range(3):
            t = reader.read()
            if t is not None:
                print(f"온도: {t:.2f}°C")
                break
            time.sleep(1)
        reader.close()
        return True
    except Exception as e:
        print(f"실패: {e}")
        return False


if __name__ == "__main__":
    st = sys.argv[1] if len(sys.argv) > 1 else "MCP9600"
    test_temperature_sensor(sensor_type=st)
