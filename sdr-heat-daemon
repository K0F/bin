#!/usr/bin/env python3
"""
sdr-heat-daemon: Autonomous Wireless Heating Meter Telemetry Collector
Captures Wireless M-Bus Mode C/T packets on 868.95 MHz using RTL-SDR and rtl_433.
Maintains SQLite database, JSONL archive, /dev/shm fast IPC, and SuperCollider OSC relay.

Part of The Observatoř environmental telemetry suite.
"""

import os
import sys
import json
import time
import socket
import struct
import signal
import sqlite3
import subprocess
from datetime import datetime

HOME = os.path.expanduser("~")
DATA_DIR = os.path.join(HOME, "src", "observator", "data")
DB_PATH = os.path.join(DATA_DIR, "heat_meters.db")
JSONL_PATH = os.path.join(DATA_DIR, "heat_meters.jsonl")
SHM_LATEST = "/dev/shm/latest_heat_meter.json"
SHM_SUMMARY = "/dev/shm/heat_fleet_summary.json"

OSC_HOST = "127.0.0.1"
OSC_PORT_SCLANG = 57120

os.makedirs(DATA_DIR, exist_ok=True)

# OSC UDP Socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

def make_osc_message(address, args):
    def pad4(b):
        return b + b"\x00" * ((4 - (len(b) % 4)) % 4)
    msg = pad4(address.encode("utf-8") + b"\x00")
    tags = ","
    payload = bytearray()
    for arg in args:
        if isinstance(arg, int):
            tags += "i"
            payload.extend(struct.pack(">i", arg))
        elif isinstance(arg, float):
            tags += "f"
            payload.extend(struct.pack(">f", arg))
        elif isinstance(arg, str):
            tags += "s"
            payload.extend(pad4(arg.encode("utf-8") + b"\x00"))
    msg += pad4(tags.encode("utf-8") + b"\x00")
    msg += payload
    return bytes(msg)

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meters (
            id INTEGER PRIMARY KEY,
            manufacturer TEXT,
            model TEXT,
            room_label TEXT DEFAULT '',
            first_seen TEXT,
            last_seen TEXT,
            last_hca REAL,
            prev_hca REAL,
            billing_date TEXT,
            total_packets INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS readings (
            id INTEGER,
            timestamp TEXT,
            hca_val REAL,
            hca_prev REAL,
            billing_date TEXT,
            raw_hex TEXT,
            FOREIGN KEY(id) REFERENCES meters(id)
        )
    """)
    cur.execute("CREATE INDEX IF NOT EXISTS idx_readings_id_time ON readings(id, timestamp)")
    conn.commit()
    conn.close()

def update_summary(conn):
    cur = conn.cursor()
    cur.execute("""
        SELECT id, manufacturer, room_label, last_seen, last_hca, prev_hca, billing_date, total_packets 
        FROM meters ORDER BY last_seen DESC
    """)
    rows = cur.fetchall()
    meters_list = []
    total_consumption = 0.0
    for r in rows:
        val = r[4] or 0.0
        total_consumption += val
        meters_list.append({
            "id": r[0],
            "manufacturer": r[1],
            "room_label": r[2] if r[2] else f"Meter #{r[0]}",
            "last_seen": r[3],
            "last_hca": val,
            "prev_hca": r[5] or 0.0,
            "billing_date": r[6],
            "packets": r[7]
        })

    summary = {
        "timestamp": datetime.now().isoformat(),
        "total_meters": len(meters_list),
        "total_units": round(total_consumption, 3),
        "meters": meters_list
    }
    tmp_path = SHM_SUMMARY + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(summary, f, indent=2)
    os.replace(tmp_path, SHM_SUMMARY)

def process_packet(pkt):
    meter_id = pkt.get("id")
    if not meter_id:
        return

    mfg = pkt.get("M", "UNK")
    now_ts = pkt.get("time", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    data_hex = pkt.get("data", "")
    billing_date = pkt.get("inst_date_17", "")
    
    # Try parsing current consumption
    last_hca = 0.0
    try:
        last_hca = float(pkt.get("inst_hca_0", "0.0").strip())
    except (ValueError, TypeError):
        pass

    # Try parsing previous billing period
    prev_hca = 0.0
    try:
        prev_hca = float(pkt.get("inst_hca_17", "0.0").strip())
    except (ValueError, TypeError):
        pass

    # 1. Update SQLite DB
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()
    cur.execute("SELECT id, total_packets FROM meters WHERE id = ?", (meter_id,))
    row = cur.fetchone()
    if row:
        pkts = row[1] + 1
        cur.execute("""
            UPDATE meters 
            SET last_seen = ?, last_hca = ?, prev_hca = ?, billing_date = ?, total_packets = ?
            WHERE id = ?
        """, (now_ts, last_hca, prev_hca, billing_date, pkts, meter_id))
    else:
        cur.execute("""
            INSERT INTO meters (id, manufacturer, model, first_seen, last_seen, last_hca, prev_hca, billing_date, total_packets)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (meter_id, mfg, pkt.get("type_string", "HCA"), now_ts, now_ts, last_hca, prev_hca, billing_date))
    
    cur.execute("""
        INSERT INTO readings (id, timestamp, hca_val, hca_prev, billing_date, raw_hex)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (meter_id, now_ts, last_hca, prev_hca, billing_date, data_hex))
    conn.commit()

    # 2. Update SHM summary and latest
    update_summary(conn)
    conn.close()

    tmp_latest = SHM_LATEST + ".tmp"
    with open(tmp_latest, "w") as f:
        json.dump(pkt, f, indent=2)
    os.replace(tmp_latest, SHM_LATEST)

    # 3. Append to JSONL
    with open(JSONL_PATH, "a") as f:
        f.write(json.dumps(pkt) + "\n")

    # 4. Relay to SuperCollider via OSC
    try:
        osc_data = make_osc_message("/observator/heat", [int(meter_id), float(last_hca), float(prev_hca), str(mfg)])
        sock.sendto(osc_data, (OSC_HOST, OSC_PORT_SCLANG))
    except Exception:
        pass

    print(f"[{now_ts}] Heat Meter #{meter_id} ({mfg}): current={last_hca} prev={prev_hca} (logged)")
    sys.stdout.flush()

def run_collector():
    init_db()
    print("[*] sdr-heat-daemon started. Listening on 868.95 MHz Mode C&T...")
    sys.stdout.flush()

    cmd = [
        "rtl_433",
        "-f", "868.95M",
        "-s", "1200k",
        "-R", "104",
        "-g", "19.7",
        "-F", "json"
    ]

    while True:
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)
            for line in proc.stdout:
                line = line.strip()
                if not line:
                    continue
                try:
                    pkt = json.loads(line)
                    process_packet(pkt)
                except json.JSONDecodeError:
                    pass
            proc.wait()
            print("[-] rtl_433 exited with code", proc.returncode, "- restarting in 3s...")
            time.sleep(3)
        except Exception as e:
            print("[-] Collector exception:", e, "- retrying in 5s...")
            time.sleep(5)

if __name__ == "__main__":
    def sig_handler(sig, frame):
        print("\n[*] Stopping sdr-heat-daemon...")
        sys.exit(0)
    signal.signal(signal.SIGINT, sig_handler)
    signal.signal(signal.SIGTERM, sig_handler)
    run_collector()
