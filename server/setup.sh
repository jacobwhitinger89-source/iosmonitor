#!/bin/bash
# Server setup for iOSMonitor
# Run this on your server (Raspberry Pi, VPS, or any Linux/Mac machine)

set -e

echo "=== iOSMonitor Server Setup ==="

# Install Python dependencies
echo "[1/3] Installing Python dependencies..."
pip3 install -r requirements.txt

# Create captures directory
mkdir -p captures

# Initialize database
echo "[2/3] Initializing database..."
python3 -c "
from database import init_db
init_db()
print('Database initialized.')
"

echo "[3/3] Setup complete!"
echo ""
echo "To start the server, run:"
echo "  python3 server.py"
echo ""
echo "Then:"
echo "  1. Open http://YOUR_SERVER_IP:8080 in a browser"
echo "  2. Update SERVER_URL in the tweak configuration on your iPhone"
echo "  3. Build and install the tweak via Theos"
