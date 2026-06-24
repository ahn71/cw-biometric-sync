from flask import Blueprint, jsonify
import json
import os
import re
import socket
import threading

devices_bp = Blueprint("devices", __name__)

LOG_FILE = os.path.join("logs", "logs.log")
STATUS_FILE = os.path.join("logs", "status.json")
SUCCESS_LOG_PREFIX = "attendance_success_log_"
FAILED_LOG_PREFIX = "attendance_failed_log_"


def read_status():
    if not os.path.exists(STATUS_FILE):
        return {}

    try:
        with open(STATUS_FILE, "r", encoding="utf-8", errors="replace") as f:
            return json.load(f)
    except Exception:
        return {}


def count_file_lines(path):
    if not os.path.exists(path):
        return 0

    with open(path, "r", encoding="utf-8", errors="replace") as f:
        return sum(1 for line in f if line.strip())


def log_file_for(prefix, device_id):
    return os.path.join("logs", f"{prefix}{device_id}.log")


def latest_fetch_count(ip):
    if not os.path.exists(LOG_FILE):
        return None

    pattern = re.compile(rf"{re.escape(ip)}\s+Attendances Fetched:\s+(\d+)")
    latest = None
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            match = pattern.search(line)
            if match:
                latest = int(match.group(1))
    return latest


def latest_connection_state(ip):
    if can_open_zk_port(ip):
        return "online"

    if not os.path.exists(LOG_FILE):
        return "configured"

    latest_line = ""
    latest_ts = None
    ts_pattern = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")
    with open(LOG_FILE, "r", encoding="utf-8", errors="replace") as f:
        for line in f:
            if ip in line:
                latest_line = line
                m = ts_pattern.match(line)
                if m:
                    from datetime import datetime
                    try:
                        latest_ts = datetime.strptime(m.group(1), "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

    if not latest_line:
        return "configured"
    if any(word in latest_line.upper() for word in ("ERROR", "CRITICAL", "FAILED", "EXCEPTION")):
        return "offline"

    if latest_ts:
        from datetime import datetime, timedelta
        age = datetime.now() - latest_ts
        if age > timedelta(minutes=5):
            return "offline"

    return "online"


def can_open_zk_port(ip):
    if not ip:
        return False

    try:
        with socket.create_connection((ip, 4370), timeout=0.4):
            return True
    except OSError:
        return False


def load_devices():
    try:
        from local_config import devices
    except Exception:
        return []

    status = read_status()

    user_count_per_device = {}
    try:
        from dashboard.users import load_users
        for user in load_users():
            for dev in user.get("devices", []):
                user_count_per_device[dev] = user_count_per_device.get(dev, 0) + 1
    except Exception:
        pass

    return [
        {
            **device,
            "status": device.get("status") or latest_connection_state(device.get("ip", "")),
            "last_pull": status.get(f"{device.get('device_id')}_pull_timestamp"),
            "last_push": status.get(f"{device.get('device_id')}_push_timestamp"),
            "last_attendance_count": latest_fetch_count(device.get("ip", "")),
            "success_log_count": count_file_lines(log_file_for(SUCCESS_LOG_PREFIX, device.get("device_id", ""))),
            "failed_log_count": count_file_lines(log_file_for(FAILED_LOG_PREFIX, device.get("device_id", ""))),
            "user_count": user_count_per_device.get(device.get("device_id", ""), 0),
            "firmware": None,
        }
        for device in devices
    ]


@devices_bp.route("/")
def list_devices():
    return jsonify({
        "devices": load_devices()
    })


@devices_bp.route("/online")
def online_devices():
    devices = load_devices()
    online = [d for d in devices if d.get("status") == "online"]

    return jsonify({
        "online_count": len(online),
        "devices": online
    })


def _run_sync():
    try:
        import importlib.util
        script_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "biometric_sync.py")
        spec = importlib.util.spec_from_file_location("biometric_sync_module", script_path)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.main()
    except Exception:
        pass

@devices_bp.route("/sync/<device_id>", methods=["POST"])
def sync_device(device_id):
    try:
        thread = threading.Thread(target=_run_sync, daemon=True)
        thread.start()
        return jsonify({"status": "triggered", "device": device_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
