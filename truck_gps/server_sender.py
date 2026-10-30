#!/usr/bin/env python3
"""
Send GPS + temperature rows to the configured MQTT broker.
"""

import json
import logging
import os
import subprocess
import threading
import time
from datetime import datetime

from config import (
    BATCH_SIZE,
    MQTT_BROKER_HOST,
    MQTT_BROKER_PORT,
    MQTT_CA_CERT,
    MQTT_CLIENT_ID,
    MQTT_DEVICE_CERT,
    MQTT_PRIVATE_KEY,
    MQTT_QOS,
    MQTT_RETAIN,
    MQTT_TOPIC,
    MQTT_USE_TLS,
    SEND_INTERVAL,
    TEMP_RANGES,
    VEHICLE_ID,
)
from database import GPSDatabase
from log_utils import log_repeat

logger = logging.getLogger(__name__)


class ServerSender:
    """Background sender that publishes unsent rows to MQTT."""

    def __init__(self, db_path):
        self.db_path = db_path
        self.vehicle_id = VEHICLE_ID
        self.send_interval = SEND_INTERVAL
        self.batch_size = BATCH_SIZE

        self.mqtt_broker_host = MQTT_BROKER_HOST
        self.mqtt_broker_port = MQTT_BROKER_PORT
        self.mqtt_topic = MQTT_TOPIC
        self.mqtt_client_id = MQTT_CLIENT_ID
        self.mqtt_qos = MQTT_QOS
        self.mqtt_retain = MQTT_RETAIN
        self.mqtt_use_tls = MQTT_USE_TLS
        self.mqtt_ca_cert = MQTT_CA_CERT
        self.mqtt_device_cert = MQTT_DEVICE_CERT
        self.mqtt_private_key = MQTT_PRIVATE_KEY

        self.mqtt_client = None
        self._mqtt_connected_event = threading.Event()

        self.db = None
        self.running = False
        self.last_send_time = None
        self.send_thread = None

        self.stats = {
            "total_sent": 0,
            "send_failures": 0,
            "last_success": None,
        }
        self.temp_ranges = TEMP_RANGES

    def start(self):
        """Start the background sender thread."""
        if self.running:
            logger.warning("Server sender is already running")
            return

        self.running = True
        self.send_thread = threading.Thread(target=self._send_loop, daemon=True)
        self.send_thread.start()

        mode = "TLS" if self.mqtt_use_tls else "plain"
        logger.debug(
            f"서버 전송 시작 (인터벌: {self.send_interval}초, "
            f"MQTT [{mode}]: {self.mqtt_broker_host}:{self.mqtt_broker_port}, "
            f"토픽: {self.mqtt_topic})"
        )

    def stop(self):
        """Stop the background sender thread."""
        if not self.running:
            return

        self.running = False
        if self.send_thread:
            self.send_thread.join(timeout=5)
        logger.info("Server sender stopped")

    def _send_loop(self):
        """Run the send loop with one DB connection owned by this thread."""
        try:
            self._ensure_db_connected()

            while self.running:
                try:
                    current_time = time.time()
                    if (
                        self.last_send_time is None
                        or current_time - self.last_send_time >= self.send_interval
                    ):
                        self._send_batch()
                        self.last_send_time = current_time

                    remaining = self.send_interval - (time.time() - (self.last_send_time or 0))
                    sleep_for = max(0.01, min(0.2, remaining))
                    time.sleep(sleep_for)

                except Exception as e:
                    log_repeat(logger, "sender.loop", logging.ERROR, "Send loop error: %s", e)
                    time.sleep(1)
        finally:
            self._close_db()

    def _ensure_db_connected(self):
        """Keep one SQLite connection for the sender thread."""
        if self.db is None:
            self.db = GPSDatabase(self.db_path)
            self.db.connect()

    def _close_db(self):
        """Close the sender thread's SQLite connection."""
        if self.db:
            try:
                self.db.close()
            finally:
                self.db = None

    def _send_batch(self):
        """Send one batch of unsent rows."""
        try:
            data_to_send = self._get_unsent_data()
            if not data_to_send:
                logger.debug("No data to send")
                return

            logger.debug(f"Sending {len(data_to_send)} rows via MQTT")
            success = self._send_to_mqtt(data_to_send)

            if success:
                self.stats["total_sent"] += len(data_to_send)
                self.stats["last_success"] = datetime.now()
                logger.debug(f"Sent {len(data_to_send)} rows")
            else:
                self.stats["send_failures"] += 1
                log_repeat(logger, "sender.send_failed", logging.ERROR, "Data send failed")

        except Exception as e:
            log_repeat(logger, "sender.batch", logging.ERROR, "Batch send error: %s", e)
            self.stats["send_failures"] += 1

    def _verify_tls_cert_files(self):
        missing = [
            path
            for path in (self.mqtt_ca_cert, self.mqtt_device_cert, self.mqtt_private_key)
            if not os.path.isfile(path)
        ]
        if missing:
            raise FileNotFoundError(
                "TLS certificate files are missing. Run python3 provision_iot_cert.py on the Pi: "
                + ", ".join(missing)
            )

    def _init_mqtt_client(self):
        """Initialize the MQTT client."""
        try:
            import paho.mqtt.client as mqtt

            self._reset_mqtt_client()
            self.mqtt_client = mqtt.Client(client_id=self.mqtt_client_id, clean_session=True)

            def on_connect(client, userdata, flags, rc):
                if rc == 0:
                    logger.debug(
                        f"MQTT broker connected: {self.mqtt_broker_host}:{self.mqtt_broker_port}"
                    )
                    self._mqtt_connected_event.set()
                else:
                    log_repeat(
                        logger,
                        "sender.mqtt_connect",
                        logging.ERROR,
                        "MQTT broker connection failed: %s",
                        rc,
                    )

            def on_disconnect(client, userdata, rc):
                if rc != 0:
                    log_repeat(
                        logger,
                        "sender.mqtt_disconnect",
                        logging.WARNING,
                        "MQTT broker disconnected: %s",
                        rc,
                    )
                self._mqtt_connected_event.clear()

            self.mqtt_client.on_connect = on_connect
            self.mqtt_client.on_disconnect = on_disconnect

            if self.mqtt_use_tls:
                self._verify_tls_cert_files()
                self.mqtt_client.tls_set(
                    ca_certs=self.mqtt_ca_cert,
                    certfile=self.mqtt_device_cert,
                    keyfile=self.mqtt_private_key,
                )

            self._mqtt_connected_event.clear()
            self.mqtt_client.connect(self.mqtt_broker_host, self.mqtt_broker_port, 60)
            self.mqtt_client.loop_start()
            self._mqtt_connected_event.wait(timeout=5)

        except Exception as e:
            log_repeat(logger, "sender.mqtt_init", logging.ERROR, "MQTT client init failed: %s", e)
            self._reset_mqtt_client()

    def _reset_mqtt_client(self):
        """Stop and discard the current MQTT client so the next send can reconnect."""
        self._mqtt_connected_event.clear()
        if self.mqtt_client is None:
            return

        try:
            self.mqtt_client.loop_stop()
        except Exception:
            pass

        try:
            self.mqtt_client.disconnect()
        except Exception:
            pass

        self.mqtt_client = None

    def _ensure_mqtt_connected(self):
        """Ensure there is an active MQTT connection before publishing."""
        if self.mqtt_client is None:
            self._init_mqtt_client()
        elif not self._mqtt_connected_event.is_set():
            log_repeat(
                logger,
                "sender.mqtt_reinit",
                logging.WARNING,
                "MQTT is disconnected; reinitializing client",
            )
            self._init_mqtt_client()

        return self._mqtt_connected_event.wait(timeout=5)

    def _send_to_mqtt(self, data):
        """Publish data to MQTT."""
        try:
            if not self._ensure_mqtt_connected() or self.mqtt_client is None:
                return False

            for payload in data:
                json_payload = json.dumps(payload, default=str)
                result = self.mqtt_client.publish(
                    self.mqtt_topic,
                    json_payload,
                    qos=self.mqtt_qos,
                    retain=self.mqtt_retain,
                )

                if result.rc != 0:
                    log_repeat(
                        logger,
                        "sender.mqtt_publish",
                        logging.ERROR,
                        "MQTT publish failed: %s",
                        result.rc,
                    )
                    self._reset_mqtt_client()
                    return self._send_to_mqtt_with_mosquitto(json_payload, 1)

            logger.debug(f"Published {len(data)} rows to MQTT")
            return True

        except Exception as e:
            log_repeat(logger, "sender.mqtt_send", logging.ERROR, "MQTT send failed: %s", e)
            self._reset_mqtt_client()
            return False

    def _send_to_mqtt_with_mosquitto(self, json_payload, row_count):
        """Fallback publisher using mosquitto_pub."""
        try:
            cmd = [
                "mosquitto_pub",
                "-h",
                self.mqtt_broker_host,
                "-p",
                str(self.mqtt_broker_port),
                "-t",
                self.mqtt_topic,
                "-m",
                json_payload,
                "-q",
                str(self.mqtt_qos),
            ]
            if self.mqtt_use_tls:
                cmd.extend(
                    [
                        "--cafile",
                        self.mqtt_ca_cert,
                        "--cert",
                        self.mqtt_device_cert,
                        "--key",
                        self.mqtt_private_key,
                    ]
                )

            subprocess.run(cmd, check=True)
            logger.debug(f"Published {row_count} rows with mosquitto_pub fallback")
            return True
        except Exception as e:
            log_repeat(
                logger, "sender.mosquitto", logging.ERROR, "mosquitto_pub fallback failed: %s", e
            )
            return False

    def _get_unsent_data(self):
        """Load unsent rows using the sender thread's persistent DB connection."""
        try:
            self._ensure_db_connected()
            unsent_data = self.db.get_unsent_gps_temperature_data(limit=self.batch_size)
            return [self._format_gps_temperature_data_for_server(row) for row in unsent_data]
        except Exception as e:
            log_repeat(
                logger, "sender.query", logging.ERROR, "GPS+temperature data query error: %s", e
            )
            return []

    def _format_gps_temperature_data_for_server(self, row):
        """Convert a DB row to the MQTT payload row format."""
        return {
            "cmd": "LTE",
            "serial": str(self.vehicle_id),
            "eventDT": datetime.fromtimestamp(row[2]).strftime("%Y-%m-%d %H:%M:%S"),
            "temperature": float(row[9]) if row[9] is not None else None,
            "lat": float(row[4]) if row[4] is not None else None,
            "lng": float(row[5]) if row[5] is not None else None,
            "battery": 100,
        }

    def _get_temperature_status(self, temperature):
        """Classify temperature using configured ranges."""
        if temperature is None:
            return "unknown"

        for status, (min_temp, max_temp) in self.temp_ranges.items():
            if min_temp <= temperature < max_temp:
                return status
        return "normal"

    def _mark_data_as_sent(self, data_ids):
        """Mark rows as sent using the sender thread's persistent DB connection."""
        try:
            self._ensure_db_connected()
            self.db.mark_gps_temperature_data_as_sent(data_ids)
        except Exception as e:
            logger.error(f"GPS+temperature sent mark failed: {e}")

    def get_stats(self):
        """Return sender stats."""
        return {
            **self.stats,
            "is_running": self.running,
            "next_send_in": max(
                0,
                self.send_interval - (time.time() - (self.last_send_time or 0)),
            ),
        }

    def force_send_now(self):
        """Send data immediately."""
        logger.info("Manual send requested")
        self._send_batch()


if __name__ == "__main__":
    print("ServerSender is started by gps_tracker.py")
