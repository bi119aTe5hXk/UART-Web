import os
import glob
import json
import serial
import threading
from datetime import datetime
from flask import Flask, send_from_directory, request, jsonify
from flask_socketio import SocketIO
import logging
from logging.handlers import RotatingFileHandler

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

app = Flask(__name__, static_url_path="/static", static_folder="static")
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

serial_objects = {}   # device_name -> serial instance
loggers = {}          # device_name -> logger instance
PORTS = []            # device descriptors {"name":.., "path":..}


# ---------------------------------------------------
# AUTO-DETECT ALL /dev/ttyUSB*
# ---------------------------------------------------
def detect_ports():
    ports = sorted(glob.glob("/dev/ttyUSB*"))
    result = []
    for idx, p in enumerate(ports):
        result.append({"name": f"device{idx}", "path": p, "baud": 115200})
    return result


PORTS = detect_ports()
print("Detected serial devices:", PORTS)


# ---------------------------------------------------
# LOGGER (with rotating file)
# ---------------------------------------------------
def get_logger(device_name):
    logfile = os.path.join(LOG_DIR, f"{device_name}.log")
    handler = RotatingFileHandler(
        logfile, maxBytes=100 * 1024 * 1024, backupCount=3
    )

    formatter = logging.Formatter(
        "[%(asctime)s] %(message)s", "%Y-%m-%d %H:%M:%S"
    )
    handler.setFormatter(formatter)

    logger = logging.getLogger(device_name)
    logger.setLevel(logging.INFO)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


# Pre-create loggers
for p in PORTS:
    loggers[p["name"]] = get_logger(p["name"])


# ---------------------------------------------------
# SERIAL READER THREAD
# ---------------------------------------------------
def read_serial(portinfo):
    name = portinfo["name"]
    path = portinfo["path"]
    baud = portinfo["baud"]

    try:
        ser = serial.Serial(path, baud, timeout=0.1)
    except Exception as e:
        print(f"Failed to open {path}: {e}")
        return

    serial_objects[name] = ser
    logger = loggers[name]

    while True:
        line = ser.readline().decode(errors="ignore")
        if line:
            text = line.strip()
            logger.info(text)

            socketio.emit(
                "log",
                {
                    "device": name,
                    "text": f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {text}\n"
                }
            )


# ---------------------------------------------------
# ROUTES
# ---------------------------------------------------
@app.route("/")
def index():
    return app.send_static_file("index.html")


@app.route("/api/devices")
def api_devices():
    """Return ONLY the device names for frontend"""
    return jsonify([p["name"] for p in PORTS])


@app.route("/logs/<path:filename>")
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)


# ---------------------------------------------------
# COMMAND (HTTP)
# ---------------------------------------------------
@app.route("/send", methods=["POST"])
def send_cmd_http():
    data = request.json
    device = data.get("device")
    cmd = data.get("cmd")

    if device in serial_objects and cmd:
        serial_objects[device].write((cmd + "\r\n").encode())
        serial_objects[device].flush()
        return {"status": "ok"}

    return {"status": "error", "msg": "invalid device or cmd"}, 400


# ---------------------------------------------------
# COMMAND (SOCKET.IO)
# ---------------------------------------------------
@socketio.on("send")
def socket_send(data):
    device = data.get("device")
    cmd = data.get("cmd")

    if device in serial_objects and cmd:
        serial_objects[device].write((cmd + "\r\n").encode())
        serial_objects[device].flush()


# ---------------------------------------------------
# MAIN
# ---------------------------------------------------
if __name__ == "__main__":
    for p in PORTS:
        threading.Thread(target=read_serial, args=(p,), daemon=True).start()

    socketio.run(app, host="0.0.0.0", port=8080, allow_unsafe_werkzeug=True)
