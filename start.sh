#!/bin/bash
# DayForge Life Planner — Start Script
# Usage: bash start.sh   (from the dayforge/ folder)

set -e
cd "$(dirname "$0")"

if command -v uv &>/dev/null; then
    uv run python server.py
else
    python3 server.py
fi
