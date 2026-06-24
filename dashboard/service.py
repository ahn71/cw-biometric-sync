from flask import Blueprint, jsonify
import psutil
import os
import subprocess
import sys

service_bp = Blueprint("service", __name__)

SERVICE_NAME = "CWBiometricSync"
SCRIPT_NAME = "biometric_sync.py"


def is_service_running():
    """Check if process is running"""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(cmdline)
            if SERVICE_NAME in joined or SCRIPT_NAME in joined:
                return True
        except Exception:
            pass
    return False


def service_processes():
    processes = []
    current_pid = os.getpid()
    for proc in psutil.process_iter(["pid", "name", "cmdline"]):
        try:
            cmdline = proc.info.get("cmdline") or []
            joined = " ".join(cmdline)
            if proc.info["pid"] != current_pid and (SERVICE_NAME in joined or SCRIPT_NAME in joined):
                processes.append(proc)
        except Exception:
            pass
    return processes


def start_service():
    if is_service_running():
        return "already_running"

    subprocess.Popen(
        [sys.executable, SCRIPT_NAME],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
    return "started"


def stop_service():
    processes = service_processes()
    for proc in processes:
        proc.terminate()

    gone, alive = psutil.wait_procs(processes, timeout=5)
    for proc in alive:
        proc.kill()

    return len(gone) + len(alive)


@service_bp.route("/status")
def status():
    return jsonify({
        "service": SERVICE_NAME,
        "running": is_service_running()
    })


@service_bp.route("/start")
def start():
    try:
        return jsonify({"status": start_service(), "running": is_service_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@service_bp.route("/stop")
def stop():
    try:
        stopped = stop_service()
        return jsonify({"status": "stopped", "stopped_processes": stopped, "running": is_service_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@service_bp.route("/restart")
def restart():
    try:
        stop_service()
        start_service()
        return jsonify({"status": "restarted", "running": is_service_running()})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
