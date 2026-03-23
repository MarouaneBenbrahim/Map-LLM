#!/bin/bash
# Quick start script for running SumoXPypsa in distrobox
# Usage: ./run.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "🚀 Starting SumoXPypsa Co-Simulation..."
echo ""

# Check if we're in distrobox
if [ ! -f "/run/.containerenv" ]; then
    echo "❌ This script must be run inside the distrobox container!"
    echo "Run: distrobox enter sumoxpypsa"
    echo "Then: ./run.sh"
    exit 1
fi

# SUMO binaries / data (sumo, netconvert, etc.)
export SUMO_HOME=/usr/share/sumo
# Append SUMO tools — do *not* prepend. Prepending puts distro traci/sumolib
# before site-packages and breaks pip/uv-installed libsumo.  traci_compat.py
# also moves these paths to the end of sys.path as a safeguard.
export PYTHONPATH="${PYTHONPATH:+$PYTHONPATH:}${SUMO_HOME}/tools"

# Activate virtual environment
if [ -d "venv" ]; then
    source venv/bin/activate
else
    echo "❌ Virtual environment not found!"
    echo "Run: python3 -m venv venv && source venv/bin/activate"
    echo "     uv pip install -r requirements.txt   # or: pip install -r requirements.txt"
    exit 1
fi

# Check if .env exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Run: cp .env.example .env"
    exit 1
fi

echo "✅ Environment configured"
echo "✅ SUMO_HOME: $SUMO_HOME"
echo "✅ PYTHONPATH includes SUMO tools"
echo "✅ Virtual environment activated"
echo ""
echo "🌐 Starting web server on http://localhost:5000"
echo "Press Ctrl+C to stop"
echo ""

# Use venv's Python explicitly so packages installed with pip/uv into this venv are used.
exec "${SCRIPT_DIR}/venv/bin/python" main_complete_integration.py
