# dashboard/stats.py
from flask import Blueprint, jsonify
import psutil
import time

stats_bp = Blueprint("stats", __name__)

@stats_bp.route("/")
def system_stats():
    return jsonify({
        # Setting interval=None makes it non-blocking (instant response)
        "cpu_percent": psutil.cpu_percent(interval=None),
        "memory": dict(psutil.virtual_memory()._asdict()),
        "disk": dict(psutil.disk_usage('/')._asdict()),
        "boot_time": time.time() - psutil.boot_time()
    })