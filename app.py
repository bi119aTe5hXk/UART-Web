import os
import serial
import threading
from datetime import datetime
from flask import Flask, send_from_directory
from flask_socketio import SocketIO, emit

# Setup 2 UART ports
PORTS = [
    {"name": "device1", "path": "/dev/ttyUSB0", "baud": 115200},
    {"name": "device2", "path": "/dev/ttyUSB1", "baud": 115200},
]

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__, static_url_path="/static", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

serial_objects = {}

# -------------------------------
# Read UART
# -------------------------------
def read_serial(portinfo):
    name = portinfo["name"]
    path = portinfo["path"]
    baud = portinfo["baud"]
    logfile = os.path.join(LOG_DIR, f"{name}.log")

    ser = serial.Serial(path, baud, timeout=0.1)
    serial_objects[name] = ser

    print(f"[INFO] Start reading {name} on {path}")

    with open(logfile, "a") as f:
        while True:
            try:
                line = ser.readline().decode(errors="ignore")
                if line:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    text = f"[{timestamp}] {line}"

                    # log
                    f.write(text)
                    f.flush()

                    # push to web
                    socketio.emit("log", {"device": name, "text": text})
            except Exception as e:
                print(f"[ERROR] serial read error on {name}: {e}")
                break

# -------------------------------
# Web to UART
# -------------------------------
@socketio.on("send")
def send_cmd(data):
    device = data["device"]
    cmd = data["cmd"]

    if device in serial_objects:
        ser = serial_objects[device]
        ser.write((cmd + "\n").encode())

# -------------------------------
# Download log file
# -------------------------------
@app.route("/logs/<path:filename>")
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)

# -------------------------------
# Main page
# -------------------------------
@app.route("/")
def index():
    return app.send_static_file("index.html")

# -------------------------------
# Boot
# -------------------------------
if __name__ == "__main__":
    # Start UART
    for p in PORTS:
        t = threading.Thread(target=read_serial, args=(p,), daemon=True)
        t.start()

    # Start web service
    socketio.run(app, host="0.0.0.0", port=8080)
