from flask import Blueprint, jsonify
from datetime import datetime
import glob
import json
import os

logs_bp = Blueprint("logs", __name__)

LOG_FILE = "logs/logs.log"
ERROR_FILE = "logs/error.log"
SUCCESS_PATTERN = "logs/attendance_success_log_*.log"
FAILED_PATTERN = "logs/attendance_failed_log_*.log"


def read_last_lines(file_path, n=50):
    if not os.path.exists(file_path):
        return []

    with open(file_path, "r", encoding="utf-8", errors="replace") as f:
        lines = f.readlines()
        return lines[-n:]


def read_matching_logs(pattern, n=80):
    lines = []
    for file_path in glob.glob(pattern):
        device_name = os.path.basename(file_path)
        device_name = device_name.replace("attendance_success_log_", "")
        device_name = device_name.replace("attendance_failed_log_", "")
        device_name = device_name.replace(".log", "")
        for line in read_last_lines(file_path, n):
            lines.append({
                "device": device_name,
                "line": line.strip(),
                "source": os.path.basename(file_path),
            })
    return lines[-n:]


def parse_punch_line(entry, status):
    line = entry["line"]
    timestamp = ""
    employee = ""
    uid = ""
    punch_code = None
    direction = ""

    try:
        payload_start = line.index("{")
        payload = json.loads(line[payload_start:])
        timestamp = payload.get("timestamp") or timestamp
        employee = str(payload.get("user_id") or "")
        uid = str(payload.get("uid") or "")
        punch_code = payload.get("punch")
    except Exception:
        payload = {}

    if not timestamp:
        for fmt_len, fmt in ((19, "%Y-%m-%d %H:%M:%S"), (16, "%Y-%m-%d %H:%M")):
            possible = line[:fmt_len]
            try:
                datetime.strptime(possible, fmt)
                timestamp = possible
                break
            except ValueError:
                pass

    lowered = line.lower()
    if punch_code in (0, 3) or " in " in lowered or "checkin" in lowered:
        direction = "IN"
    elif punch_code in (1, 2, 4, 5) or " out " in lowered or "checkout" in lowered:
        direction = "OUT"

    if not employee:
        parts = line.split("\t")
        if len(parts) >= 5:
            employee = parts[4].strip()

    return {
        "time": timestamp or "Recent",
        "device": entry["device"],
        "employee": employee,
        "employee_id": employee,
        "uid": uid,
        "direction": direction or "AUTO",
        "punch_code": punch_code,
        "status": status,
        "raw": line,
    }


@logs_bp.route("/")
def logs():
    log_lines = read_last_lines(LOG_FILE, 100)
    if not log_lines:
        log_lines = read_last_lines(ERROR_FILE, 100)

    return jsonify({
        "logs": log_lines
    })


@logs_bp.route("/errors")
def errors():
    lines = read_last_lines(LOG_FILE, 200) + read_last_lines(ERROR_FILE, 200)
    errors = [l for l in lines if "ERROR" in l]

    return jsonify({
        "error_count": len(errors),
        "errors": errors
    })


@logs_bp.route("/punches")
def punches():
    success = [parse_punch_line(entry, "success") for entry in read_matching_logs(SUCCESS_PATTERN, 120)]
    failed = [parse_punch_line(entry, "failed") for entry in read_matching_logs(FAILED_PATTERN, 80)]
    punches = sorted(success + failed, key=lambda punch: punch.get("time") or "")[-120:]

    return jsonify({
        "count": len(punches),
        "punches": punches
    })
