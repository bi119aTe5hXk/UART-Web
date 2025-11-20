import os
import json
import asyncio
import serial
from datetime import datetime
from flask import Flask, send_from_directory
import websockets

PORTS = [
    {"name": "device1", "path": "/dev/ttyUSB0", "baud": 115200},
    {"name": "device2", "path": "/dev/ttyUSB1", "baud": 115200},
]

LOG_DIR = "logs"
os.makedirs(LOG_DIR, exist_ok=True)

serial_objects = {}
connected_clients = set()

app = Flask(__name__, static_url_path="/static", static_folder="static")

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/logs/<path:filename>")
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)


async def read_serial(portinfo):
    name = portinfo["name"]
    path = portinfo["path"]
    baud = portinfo["baud"]
    logfile = os.path.join(LOG_DIR, f"{name}.log")

    ser = serial.Serial(path, baud, timeout=0.1)
    serial_objects[name] = ser

    def readline():
        return ser.readline().decode(errors="ignore")

    while True:
        line = await asyncio.to_thread(readline)
        if line:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text = f"[{timestamp}] {line}"
            with open(logfile, "a") as f:
                f.write(text)
                f.flush()
            msg = json.dumps({"device": name, "text": text})
            await send_to_all(msg)


async def ws_handler(websocket, path):
    print("WebSocket client connected")
    connected_clients.add(websocket)
    try:
        async for message in websocket:
            print("WS received:", message)
            data = json.loads(message)
            device = data["device"]
            cmd = data["cmd"]
            if device in serial_objects:
                serial_objects[device].write((cmd + "\r\n").encode())
                serial_objects[device].flush()
    finally:
        connected_clients.remove(websocket)
        print("WebSocket client disconnected")


async def send_to_all(msg):
    dead = []
    for ws in connected_clients:
        try:
            await ws.send(msg)
        except:
            dead.append(ws)
    for ws in dead:
        connected_clients.remove(ws)


async def main():
    tasks = [asyncio.create_task(read_serial(p)) for p in PORTS]

    ws_server = websockets.serve(ws_handler, "0.0.0.0", 8765)
    await ws_server

    from threading import Thread
    Thread(target=lambda: app.run(host="0.0.0.0", port=8080), daemon=True).start()

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
