from flask import Blueprint, jsonify
import glob
import json
import os

users_bp = Blueprint("users", __name__)

SUCCESS_PATTERN = "logs/attendance_success_log_*.log"
FAILED_PATTERN = "logs/attendance_failed_log_*.log"


def device_name_from_path(file_path, prefix):
    name = os.path.basename(file_path)
    return name.replace(prefix, "").replace(".log", "")


def iter_attendance_lines(pattern, prefix, status):
    for file_path in glob.glob(pattern):
        device = device_name_from_path(file_path, prefix)
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            for line in f:
                try:
                    payload = json.loads(line[line.index("{"):])
                except Exception:
                    continue

                yield {
                    "device": device,
                    "status": status,
                    "uid": str(payload.get("uid") or ""),
                    "user_id": str(payload.get("user_id") or ""),
                    "timestamp": payload.get("timestamp") or "",
                    "punch": payload.get("punch"),
                }


def load_users():
    users = {}
    records = list(iter_attendance_lines(SUCCESS_PATTERN, "attendance_success_log_", "success"))
    records.extend(iter_attendance_lines(FAILED_PATTERN, "attendance_failed_log_", "failed"))

    for record in records:
        user_id = record["user_id"]
        if not user_id:
            continue

        existing = users.setdefault(user_id, {
            "employee_id": user_id,
            "enroll_id": user_id,
            "name": "",
            "department": "",
            "designation": "",
            "mobile": "",
            "status": "seen",
            "uid": record["uid"],
            "devices": set(),
            "punch_count": 0,
            "last_punch": "",
            "last_device": "",
        })

        existing["punch_count"] += 1
        existing["devices"].add(record["device"])
        if record["timestamp"] and record["timestamp"] >= existing["last_punch"]:
            existing["last_punch"] = record["timestamp"]
            existing["last_device"] = record["device"]
            existing["uid"] = record["uid"] or existing["uid"]

    return [
        {
            **user,
            "devices": sorted(user["devices"]),
        }
        for user in sorted(users.values(), key=lambda item: item["last_punch"], reverse=True)
    ]


@users_bp.route("/")
def users():
    loaded_users = load_users()
    return jsonify({
        "count": len(loaded_users),
        "users": loaded_users,
    })
