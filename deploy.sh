#!/bin/bash
# Run this on the Raspberry Pi to pull and deploy the latest changes.
# Usage: bash deploy.sh

set -e
cd "$(dirname "$0")"

echo "  Pulling latest changes..."
git pull

echo "  Rebuilding and restarting app..."
docker compose up -d --build app

echo "  Done. App is live at http://localhost:8765"
