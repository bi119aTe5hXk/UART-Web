import os
import serial
import threading
from datetime import datetime
from flask import Flask, send_from_directory
from flask_socketio import SocketIO

PORTS = [
    {"name": "device1", "path": "/dev/ttyUSB0", "baud": 115200},
    {"name": "device2", "path": "/dev/ttyUSB1", "baud": 115200},
]

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__, static_url_path="/static", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

serial_objects = {}

def read_serial(portinfo):
    name = portinfo["name"]
    path = portinfo["path"]
    baud = portinfo["baud"]
    logfile = os.path.join(LOG_DIR, f"{name}.log")

    ser = serial.Serial(path, baud, timeout=0.1)
    serial_objects[name] = ser

    with open(logfile, "a") as f:
        while True:
            line = ser.readline().decode(errors="ignore")
            if line:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                text = f"[{timestamp}] {line}"

                f.write(text)
                f.flush()

                socketio.emit("log", {"device": name, "text": text})

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/logs/<path:filename>")
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)

if __name__ == "__main__":
    for p in PORTS:
        threading.Thread(target=read_serial, args=(p,), daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=8080)
