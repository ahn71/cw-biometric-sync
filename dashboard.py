from flask import Flask, render_template_string
import psutil
import subprocess
import json
import os

app = Flask(__name__)

SERVICE_NAME = "CWBiometricSync"

LOG_DIR = "logs"
STATUS_FILE = os.path.join(LOG_DIR, "status.json")
LOG_FILE = os.path.join(LOG_DIR, "logs.log")
ERROR_FILE = os.path.join(LOG_DIR, "error.log")


def service_status():
    try:
        output = subprocess.check_output(
            ["sc", "query", SERVICE_NAME],
            text=True
        )

        if "RUNNING" in output:
            return "🟢 RUNNING"
        elif "STOPPED" in output:
            return "🔴 STOPPED"
        else:
            return "🟡 UNKNOWN"

    except Exception:
        return "❌ NOT FOUND"


def read_last_lines(file, n=20):

    if not os.path.exists(file):
        return []

    with open(file, encoding="utf8", errors="ignore") as f:
        return f.readlines()[-n:]


def last_sync():

    if not os.path.exists(STATUS_FILE):
        return "N/A"

    try:
        with open(STATUS_FILE) as f:
            data = json.load(f)

        return data.get(
            "mission_accomplished_timestamp",
            "N/A"
        )

    except:
        return "N/A"


HTML = """
<!doctype html>

<html>

<head>

<meta http-equiv="refresh" content="2">

<title>CW Biometric Dashboard</title>

<style>

body{
font-family:Arial;
background:#f5f5f5;
margin:30px;
}

.card{
background:white;
padding:20px;
margin-bottom:20px;
border-radius:8px;
box-shadow:0 0 5px #ccc;
}

pre{
background:black;
color:#00ff00;
padding:10px;
height:300px;
overflow:auto;
}

</style>

</head>

<body>

<h1>CW Biometric Sync Dashboard</h1>

<div class="card">

<h3>Service Status</h3>

{{service}}

</div>

<div class="card">

<h3>Last Sync</h3>

{{sync}}

</div>

<div class="card">

<h3>CPU</h3>

{{cpu}} %

<h3>RAM</h3>

{{ram}} %

</div>

<div class="card">

<h3>Live Logs</h3>

<pre>

{% for line in logs %}

{{line}}

{% endfor %}

</pre>

</div>

<div class="card">

<h3>Error Logs</h3>

<pre>

{% for line in errors %}

{{line}}

{% endfor %}

</pre>

</div>

</body>

</html>

"""


@app.route("/")
def index():

    return render_template_string(

        HTML,

        service=service_status(),

        sync=last_sync(),

        cpu=psutil.cpu_percent(),

        ram=psutil.virtual_memory().percent,

        logs=read_last_lines(LOG_FILE),

        errors=read_last_lines(ERROR_FILE)

    )


app.run(
    host="0.0.0.0",
    port=5000
)