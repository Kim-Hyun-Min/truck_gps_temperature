#!/usr/bin/env python3
import sqlite3
from datetime import datetime
from flask import Flask, render_template, jsonify
from config import (
    DB_PATH,
    DASHBOARD_TEMP_CHART_SECONDS,
    DASHBOARD_HOST,
    DASHBOARD_PORT,
    REVERSE_GEOCODE_API_URL,
    REVERSE_GEOCODE_API_LANGUAGE,
)
import urllib.request
import urllib.parse
import json as jsonlib
import socket

NETWORK_IFACES = ("wlan0", "eth0")


def _iface_is_up(ifname):
    path = f"/sys/class/net/{ifname}/operstate"
    try:
        with open(path, encoding="utf-8") as f:
            return f.read().strip() == "up"
    except OSError:
        return False


def _iface_has_ipv4(ifname):
    try:
        import fcntl
        import struct
    except ImportError:
        return False
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        fcntl.ioctl(
            sock.fileno(),
            0x8915,  # SIOCGIFADDR
            struct.pack("256s", ifname.encode("utf-8")[:15]),
        )
        return True
    except OSError:
        return False
    finally:
        sock.close()


def local_network_status():
    """Return (connected, interface) for Wi-Fi or Ethernet with an IPv4 address."""
    for ifname in NETWORK_IFACES:
        if _iface_is_up(ifname) and _iface_has_ipv4(ifname):
            return True, ifname
    return False, None


def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


app = Flask(__name__)


@app.route('/')
def index():
    return render_template('index.html', chart_window_seconds=DASHBOARD_TEMP_CHART_SECONDS)


@app.route('/api/latest')
def api_latest():
    """가장 최신 GPS+온도 1건 반환"""
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT id, vehicle_id, timestamp, datetime, latitude, longitude, altitude, speed, heading, temperature, status
        FROM gps_temperature_data
        ORDER BY timestamp DESC
        LIMIT 1
        """
    )
    row = cur.fetchone()
    conn.close()

    if not row:
        return jsonify({}), 200

    return jsonify({k: row[k] for k in row.keys()})


@app.route('/api/temperature-series')
def api_temperature_series():
    """최근 DASHBOARD_TEMP_CHART_SECONDS 구간의 온도 시리즈 (차트용, DB 보관과 별도)"""
    since_ts = datetime.now().timestamp() - DASHBOARD_TEMP_CHART_SECONDS

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT timestamp, datetime, temperature
        FROM gps_temperature_data
        WHERE temperature IS NOT NULL AND timestamp >= ?
        ORDER BY timestamp ASC
        """,
        (since_ts,)
    )
    rows = cur.fetchall()
    conn.close()

    series = [
        {
            't': r['datetime'],
            'x': r['timestamp'],
            'y': r['temperature'],
        }
        for r in rows
    ]
    return jsonify(series)


@app.route('/api/reverse-geocode')
def api_reverse_geocode():
    """간단한 리버스 지오코딩 (BigDataCloud API 사용)"""
    try:
        from flask import request
        lat = request.args.get('lat', type=float)
        lon = request.args.get('lon', type=float)
        if lat is None or lon is None:
            return jsonify({}), 400

        # BigDataCloud Reverse Geocoding API 사용 (config.py에서 설정)
        url = f"{REVERSE_GEOCODE_API_URL}?latitude={lat}&longitude={lon}&localityLanguage={REVERSE_GEOCODE_API_LANGUAGE}"
        req = urllib.request.Request(url, headers={'User-Agent': 'TruckGPS/1.0'})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = jsonlib.loads(resp.read().decode('utf-8'))
        
        # 한국 주소 우선 조합 (시/도 + 시/군/구)
        city = data.get('city', '') or data.get('principalSubdivision', '')
        locality = data.get('locality', '')
        display = ' '.join([p for p in [city, locality] if p])
        return jsonify({ 'display': display })
    except Exception as e:
        # 에러 발생 시 빈 문자열 반환
        return jsonify({ 'display': '' })


@app.route('/api/health/internet')
def api_health_internet():
    """로컬 네트워크(와이파이 wlan0 또는 유선 eth0) 연결 여부"""
    connected, ifname = local_network_status()
    return jsonify({
        'connected': connected,
        'interface': ifname,
    })


@app.route('/api/health/temperature')
def api_health_temperature():
    """최근 온도 데이터 수집 여부로 센서 연결 상태 추정"""
    try:
        from datetime import datetime
        import time
        conn = sqlite3.connect(DB_PATH)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT timestamp, temperature
            FROM gps_temperature_data
            WHERE temperature IS NOT NULL
            ORDER BY timestamp DESC
            LIMIT 1
            """
        )
        row = cur.fetchone()
        conn.close()
        if not row:
            return jsonify({ 'connected': False, 'age_s': None })
        last_ts, last_temp = row
        age = max(0.0, time.time() - float(last_ts))
        # 15초 이내 업데이트면 연결 OK로 판단
        return jsonify({ 'connected': age <= 5.0, 'age_s': age })
    except Exception:
        return jsonify({ 'connected': False, 'age_s': None })


if __name__ == '__main__':
    import os
    import argparse
    parser = argparse.ArgumentParser()
    # 명령줄 인자 우선, 그 다음 환경변수, 마지막으로 config.py 기본값
    parser.add_argument('--port', type=int, default=int(os.getenv('DASHBOARD_PORT', DASHBOARD_PORT)))
    parser.add_argument('--host', type=str, default=os.getenv('DASHBOARD_HOST', DASHBOARD_HOST))
    args = parser.parse_args()
    # 라즈베리파이 로컬 모니터 표시용으로 설정된 호스트/포트 사용
    app.run(host=args.host, port=args.port, debug=False)


