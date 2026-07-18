#!/bin/bash
# Build the iOSMonitor tweak using Docker (no Mac needed!)
# This creates a .deb file in the tweak/packages/ directory

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
IMAGE_NAME="iosmonitor-tweak-builder"

echo "=== Building iOSMonitor Tweak with Docker ==="
echo ""

# Build the Docker image if not present
if ! docker image inspect "$IMAGE_NAME" &>/dev/null; then
    echo "[1/3] Building Docker build image (this takes a while the first time)..."
    docker build -t "$IMAGE_NAME" -f "$SCRIPT_DIR/Dockerfile.build" "$SCRIPT_DIR"
else
    echo "[1/3] Build image already exists"
fi

echo "[2/3] Compiling tweak..."
mkdir -p "$SCRIPT_DIR/packages"
docker run --rm \
    -v "$SCRIPT_DIR:/build" \
    -v "$SCRIPT_DIR/packages:/build/packages" \
    "$IMAGE_NAME" \
    sh -c "make clean package FINALPACKAGE=1 && cp packages/*.deb /build/packages/"

echo "[3/3] Done!"
echo ""
echo "Built package:"
ls -lh "$SCRIPT_DIR/packages/"*.deb 2>/dev/null || echo "No .deb found"
echo ""
echo "Copy to your iPhone and install with:"
echo "  dpkg -i packages/com.iosmonitor.tweak_*.deb"
echo "Then edit SERVER_URL and load the daemon."
