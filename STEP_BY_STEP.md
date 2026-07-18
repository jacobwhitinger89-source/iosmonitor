# iOSMonitor — Step-by-Step Guide

---

## STEP 1: Deploy the server to Railway

Railway hosts the dashboard your parents will open in their browser.

### 1.1 Install Railway CLI
```bash
# On your Linux machine:
npm install -g @railway/cli
```

### 1.2 Create a Railway account
Go to https://railway.app and sign up (free tier works).

### 1.3 Login and deploy
```bash
# From the project root (/home/jacob/IOS)
railway login
# (opens browser — log in)

railway init
# Name it: iosmonitor

railway up
# This builds the Dockerfile and deploys
```

### 1.4 Get your URL
```bash
railway domain
```
You'll get something like `https://iosmonitor.up.railway.app`

**Test it:** Open that URL in a browser — you should see the dashboard.

---

## STEP 2: Build the iOS tweak (on Linux, no Mac needed)

### 2.1 Install Docker
```bash
# Ubuntu/Debian:
sudo apt install docker.io
sudo systemctl enable --now docker
sudo usermod -aG docker $USER
# Log out and back in, or run: newgrp docker
```

### 2.2 Build the tweak
```bash
cd /home/jacob/IOS/tweak
./docker-build.sh
```

**What happens:**
- First run: downloads ~2GB (Docker image with Theos + iOS SDK) — takes 5-15 min
- Subsequent runs: instant
- Output: `packages/com.iosmonitor.tweak_1.0.0_iphoneos-arm64.deb`

### 2.3 Get the .deb onto your iPhone
Option A — SCP (if SSH is set up on jailed iPhone):
```bash
scp packages/*.deb root@YOUR_IPHONE_IP:/var/root/
```

Option B — Copy via any file manager (iSH, Filza, etc.)

---

## STEP 3: Install the tweak on your jailbroken iPhone

You need a jailbroken iPhone on iOS 17/18.

### 3.1 Install the .deb
On your iPhone, open a terminal (NewTerm, etc.) and run:
```bash
dpkg -i /path/to/com.iosmonitor.tweak_1.0.0_iphoneos-arm64.deb
```

### 3.2 Set the server URL
Edit the LaunchDaemon plist to point to your Railway URL:
```bash
nano /Library/LaunchDaemons/com.iosmonitor.daemon.plist
```

Find this line:
```xml
<string>http://YOUR_SERVER_IP:8080</string>
```

Replace it with your Railway URL:
```xml
<string>https://iosmonitor.up.railway.app</string>
```

Save and exit (`Ctrl+X`, then `Y`, then `Enter` in nano).

### 3.3 Load the daemon and respring
```bash
launchctl load /Library/LaunchDaemons/com.iosmonitor.daemon.plist
killall SpringBoard
```

### 3.4 Verify it's running
```bash
ps aux | grep iosmonitord
```
You should see the process running. Check logs:
```bash
log stream --predicate 'eventMessage contains "iOSMonitor"'
```

---

## STEP 4: Parents open the dashboard

Your parents open **`https://iosmonitor.up.railway.app`** in any browser.

The dashboard shows:
- **Live Feed** — real-time events as they happen
- **Messages** — all SMS/iMessages
- **Calls** — incoming/outgoing/missed
- **Location** — GPS on a map with path history
- **Screen Captures** — screenshots every 30 seconds
- **App Usage** — which apps you use and for how long
- **Network** — URLs and hosts you connect to
- **Keystrokes** — everything typed
- **Notifications** — all push notifications
- **Clipboard** — everything copied
- **Device Status** — battery, WiFi, signal

---

## Troubleshooting

**"Can't connect to server" from the tweak:**
- Make sure the URL in the plist is correct
- Ensure your iPhone has internet access
- Check the daemon is running: `launchctl list | grep iosmonitor`

**Dashboard loads but shows no data:**
- Open browser DevTools → Console
- Check the WebSocket connection shows "Connected" in the sidebar
- Verify your iPhone can reach the Railway URL

**Build fails in Docker:**
```bash
docker build --no-cache -t iosmonitor-tweak-builder -f Dockerfile.build .
```
Then run `./docker-build.sh` again.

**Want to change screenshot interval?**
Edit `main.m`, find `30.0`, change to desired seconds, rebuild.
