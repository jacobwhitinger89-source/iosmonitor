#!/bin/bash
# iOSMonitor — One-click Deploy Script
# Run this on YOUR Linux/Mac machine (not on the server)

set -e

echo "=== iOSMonitor Deploy ==="

# Check prerequisites
for cmd in git python3; do
  if ! which $cmd &>/dev/null; then
    echo "Missing: $cmd. Install it first."
    exit 1
  fi
done

# 1. Get code
echo "[1/4] Getting code..."
cd /tmp
git clone https://github.com/jacobwhitinger89-source/iosmonitor.git 2>/dev/null || {
  echo "Creating fresh copy..."
  mkdir -p iosmonitor
  cd iosmonitor
  curl -sL https://github.com/jacobwhitinger89-source/iosmonitor/archive/refs/heads/master.tar.gz | tar xz --strip=1
  cd /tmp
}
cd iosmonitor

# 2. Deploy to Railway
echo "[2/4] Deploying to Railway..."
echo ""
echo "Go to: https://railway.app/new"
echo "Click 'Deploy from GitHub repo'"
echo "Select: jacobwhitinger89-source/iosmonitor"
echo ""
echo "Or if you want the CLI:"
echo "  npm i -g @railway/cli"
echo "  railway login"
echo "  railway init --yes"
echo "  railway up"
echo ""
echo "Your URL will be: https://iosmonitor.up.railway.app"
echo ""

# 3. Build tweak with Docker
echo "[3/4] Would you like to build the iOS tweak? [y/N]"
read -r BUILD_TWEAK
if [[ "$BUILD_TWEAK" =~ ^[Yy]$ ]]; then
  if which docker &>/dev/null; then
    cd tweak
    chmod +x docker-build.sh
    ./docker-build.sh
    cd ..
    echo "Tweak built: tweak/packages/*.deb"
  else
    echo "Docker not found. Install it first:"
    echo "  curl -fsSL https://get.docker.com | sh"
  fi
fi

# 4. Summary
echo ""
echo "=== Deploy Complete ==="
echo ""
echo "Server: https://iosmonitor.up.railway.app"
echo ""
echo "On your jailbroken iPhone, run:"
echo "  wget https://github.com/jacobwhitinger89-source/iosmonitor/releases/download/v1/tweak.deb"
echo "  dpkg -i tweak.deb"
echo "  nano /Library/LaunchDaemons/com.iosmonitor.daemon.plist"
echo "  # Set SERVER_URL=https://iosmonitor.up.railway.app"
echo "  launchctl load /Library/LaunchDaemons/com.iosmonitor.daemon.plist"
echo "  killall SpringBoard"
