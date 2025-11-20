import os
import json
import asyncio
import serial
import threading
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

ws_loop = None

@app.route("/")
def index():
    return app.send_static_file("index.html")

@app.route("/logs/<path:filename>")
def download_log(filename):
    return send_from_directory(LOG_DIR, filename, as_attachment=True)

def read_serial(portinfo):
    name = portinfo["name"]
    path = portinfo["path"]
    baud = portinfo["baud"]

    logfile = os.path.join(LOG_DIR, f"{name}.log")

    ser = serial.Serial(path, baud, timeout=0.1)
    serial_objects[name] = ser

    while True:
        line = ser.readline().decode(errors="ignore")
        if line:
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            text = f"[{timestamp}] {line}"

            with open(logfile, "a") as f:
                f.write(text)
                f.flush()

            msg = json.dumps({"device": name, "text": text})

            if ws_loop is not None:
                ws_loop.call_soon_threadsafe(asyncio.create_task, send_to_all(msg))


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


def start_websocket():
    async def ws_main():
        async with websockets.serve(ws_handler, "0.0.0.0", 8765):
            print("WebSocket server running on ws://0.0.0.0:8765")
            await asyncio.Future()  # run forever

    global ws_loop
    loop = asyncio.new_event_loop()
    ws_loop = loop 
    asyncio.set_event_loop(loop)
    loop.run_until_complete(ws_main())
    loop.run_forever()


if __name__ == "__main__":
    for p in PORTS:
        threading.Thread(target=read_serial, args=(p,), daemon=True).start()

    threading.Thread(target=start_websocket, daemon=True).start()

    app.run(host="0.0.0.0", port=8080)
