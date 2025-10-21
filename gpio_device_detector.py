#!/usr/bin/env python3
"""
GPIO 연결 장치 감지 스크립트
라즈베리파이의 GPIO 핀에 연결된 장치들을 감지합니다.
"""

import subprocess
import re
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class GPIODeviceDetector:
    """GPIO 연결 장치 감지 클래스"""

    def __init__(self):
        self.connected_devices = []

    def check_i2c_devices(self):
        """연결된 I2C 장치 확인"""
        logger.info("=== I2C 장치 스캔 ===")

        try:
            # i2cdetect 명령 실행
            result = subprocess.run(['i2cdetect', '-y', '1'],
                                  capture_output=True, text=True, timeout=10)

            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')
                logger.info("I2C 장치 목록:")
                for line in lines:
                    logger.info(line)

                # I2C 주소에서 장치 찾기
                i2c_devices = []
                for line in lines[1:]:  # 첫 번째 줄은 헤더이므로 제외
                    # 16진수 주소 찾기 (예: 60:, 61:, 등)
                    addresses = re.findall(r'\b[0-9a-f]{2}:\s+([0-9a-f-]+)', line, re.IGNORECASE)
                    for addr in addresses:
                        if addr != '--':
                            i2c_devices.append(f"0x{addr}")

                if i2c_devices:
                    logger.info(f"발견된 I2C 장치들: {', '.join(i2c_devices)}")
                    self.connected_devices.extend([f"I2C 장치 {addr}" for addr in i2c_devices])
                else:
                    logger.warning("연결된 I2C 장치를 찾을 수 없습니다")

                return i2c_devices
            else:
                logger.error(f"I2C 스캔 실패: {result.stderr}")
                return []

        except FileNotFoundError:
            logger.error("i2cdetect 명령어를 찾을 수 없습니다. i2c-tools를 설치해주세요.")
            logger.info("설치 명령: sudo apt-get install i2c-tools")
            return []
        except subprocess.TimeoutExpired:
            logger.error("I2C 스캔 시간 초과")
            return []
        except Exception as e:
            logger.error(f"I2C 스캔 중 오류 발생: {e}")
            return []

    def check_gpio_status(self):
        """GPIO 핀 상태 확인"""
        logger.info("=== GPIO 핀 상태 확인 ===")

        try:
            import gpiozero

            # 주요 GPIO 핀들 확인
            gpio_pins = {
                2: "SDA (I2C 데이터)",
                3: "SCL (I2C 클록)",
                4: "GPIO 4",
                14: "TXD (UART 송신)",
                15: "RXD (UART 수신)",
                17: "GPIO 17",
                18: "GPIO 18",
                27: "GPIO 27",
                22: "GPIO 22",
                23: "GPIO 23",
                24: "GPIO 24",
                10: "MOSI (SPI)",
                9: "MISO (SPI)",
                11: "SCLK (SPI)",
                5: "GPIO 5",
                6: "GPIO 6",
                13: "GPIO 13",
                19: "GPIO 19",
                26: "GPIO 26"
            }

            logger.info("핀 번호 | 상태 | 설명")
            logger.info("-" * 50)

            active_pins = []

            for pin_num, description in gpio_pins.items():
                try:
                    pin = gpiozero.Button(pin_num)
                    state = "HIGH" if pin.value else "LOW"
                    logger.info(f"GPIO {pin_num:2d} | {state:4s} | {description}")

                    if state == "LOW":  # LOW는 장치가 연결되어 있을 가능성
                        active_pins.append(f"GPIO {pin_num} ({description})")

                    pin.close()

                except Exception as e:
                    logger.warning(f"GPIO {pin_num} 확인 실패: {e}")

            if active_pins:
                logger.info(f"활성 상태인 핀들: {', '.join(active_pins)}")
                self.connected_devices.extend(active_pins)
            else:
                logger.info("활성 상태인 GPIO 핀을 찾을 수 없습니다")

            return active_pins

        except ImportError:
            logger.error("gpiozero 라이브러리가 설치되지 않았습니다.")
            logger.info("설치 명령: pip install gpiozero")
            return []

    def check_connected_interfaces(self):
        """연결된 인터페이스 확인"""
        logger.info("=== 연결된 인터페이스 확인 ===")

        interfaces = []

        # I2C 인터페이스 확인
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'i2c_bcm2708' in result.stdout or 'i2c_bcm2835' in result.stdout:
                interfaces.append("I2C 인터페이스 활성화됨")
            else:
                interfaces.append("I2C 인터페이스 비활성화됨")
        except:
            interfaces.append("I2C 인터페이스 상태 확인 불가")

        # SPI 인터페이스 확인
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'spi_bcm2835' in result.stdout:
                interfaces.append("SPI 인터페이스 활성화됨")
            else:
                interfaces.append("SPI 인터페이스 비활성화됨")
        except:
            interfaces.append("SPI 인터페이스 상태 확인 불가")

        # UART 인터페이스 확인
        try:
            result = subprocess.run(['lsmod'], capture_output=True, text=True)
            if 'uart_bcm2835' in result.stdout:
                interfaces.append("UART 인터페이스 활성화됨")
            else:
                interfaces.append("UART 인터페이스 비활성화됨")
        except:
            interfaces.append("UART 인터페이스 상태 확인 불가")

        for interface in interfaces:
            logger.info(f"- {interface}")

        return interfaces

    def generate_report(self):
        """연결 상태 보고서 생성"""
        logger.info("=== 연결 장치 보고서 ===")

        if not self.connected_devices:
            logger.warning("연결된 장치를 찾을 수 없습니다")
            return

        logger.info(f"총 {len(self.connected_devices)}개의 장치/핀을 발견했습니다:")
        logger.info("-" * 50)

        for i, device in enumerate(self.connected_devices, 1):
            logger.info(f"{i}. {device}")

        logger.info("-" * 50)
        logger.info("문제 해결 팁:")
        logger.info("- I2C 장치가 감지되지 않으면 풀업 저항을 확인하세요")
        logger.info("- GPIO 핀이 LOW 상태면 장치가 연결되어 있을 수 있습니다")
        logger.info("- 추가 도움이 필요하면 배선 연결을 다시 확인하세요")

def main():
    """메인 실행 함수"""
    print("🔍 GPIO 연결 장치 감지 시작...")
    print("=" * 60)

    detector = GPIODeviceDetector()

    # I2C 장치 확인
    i2c_devices = detector.check_i2c_devices()
    print()

    # GPIO 핀 상태 확인
    active_pins = detector.check_gpio_status()
    print()

    # 연결된 인터페이스 확인
    interfaces = detector.check_connected_interfaces()
    print()

    # 보고서 생성
    detector.generate_report()

    print("=" * 60)
    print("✅ 장치 감지 완료!")

    if not detector.connected_devices:
        print("\n💡 문제 해결 제안:")
        print("1. 모든 장치가 제대로 연결되어 있는지 확인하세요")
        print("2. 전원이 올바르게 공급되고 있는지 확인하세요")
        print("3. I2C 장치의 경우 풀업 저항이 필요할 수 있습니다")
        print("4. 배선이 정확한 핀에 연결되어 있는지 다시 확인하세요")

if __name__ == "__main__":
    main()
