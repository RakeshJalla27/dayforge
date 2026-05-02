#!/bin/bash
# Run this on the Raspberry Pi to pull and deploy the latest changes.
# Usage: bash deploy.sh

set -e
cd "$(dirname "$0")"

echo "  Pulling latest changes..."
git pull

echo "  Rebuilding and restarting app..."
docker compose up -d --build app

echo "  Restarting kiosk browser..."
DISPLAY=:0 pkill -f chromium-browser 2>/dev/null || true
sleep 2
DISPLAY=:0 chromium-browser \
  --kiosk \
  --noerrdialogs \
  --disable-infobars \
  --autoplay-policy=no-user-gesture-required \
  --disable-web-security \
  --user-data-dir=/tmp/chrome-kiosk \
  --force-dark-mode \
  http://localhost:8765 &

echo "  Done. App is live at http://localhost:8765"
