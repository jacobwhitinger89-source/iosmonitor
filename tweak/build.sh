#!/bin/bash
# Build the iOSMonitor tweak + daemon
# Requires Theos to be installed: https://theos.dev

set -e

echo "=== iOSMonitor Tweak Build ==="
echo ""

# Check for Theos
if [ -z "$THEOS" ]; then
    if [ -d "$HOME/theos" ]; then
        export THEOS="$HOME/theos"
    elif [ -d "/opt/theos" ]; then
        export THEOS="/opt/theos"
    else
        echo "ERROR: Theos not found. Install it first:"
        echo "  bash -c \"\$(curl -fsSL https://raw.github.com/theos/theos/master/bin/install-theos)\""
        exit 1
    fi
fi

echo "Using Theos at: $THEOS"

# Build
make clean
make package

echo ""
echo "=== Build Complete ==="
echo ""
echo "Next steps:"
echo "  1. Copy the .deb from packages/ to your iPhone"
echo "  2. Install: dpkg -i com.iosmonitor.tweak_*.deb"
echo "  3. Edit SERVER_URL in /Library/LaunchDaemons/com.iosmonitor.daemon.plist"
echo "  4. Load daemon: launchctl load /Library/LaunchDaemons/com.iosmonitor.daemon.plist"
echo "  5. Respring to load the tweak hooks"
