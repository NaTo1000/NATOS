#!/bin/bash

SAFE_MODE="${SAFE_MODE:-false}"
CONFIG_FILE="natos_config.json"

# Parse command-line arguments
for arg in "$@"; do
    case "$arg" in
        --safe-mode)
            SAFE_MODE="true"
            ;;
    esac
done

echo "=========================================="
echo "🏎️  NATOS Installation Script"
echo "=========================================="

if [ "$SAFE_MODE" = "true" ]; then
    echo "🛡️  Safe Mode: ENABLED"
fi

echo ""

# Persist safe mode choice to config
echo "{\"safeMode\": $SAFE_MODE}" > "$CONFIG_FILE"

# Install Python dependencies
if [ "$SAFE_MODE" = "true" ]; then
    echo "📦 Installing core dependencies (safe mode)..."
    pip install -q flask==3.0.0 flask-socketio==5.3.5 python-socketio==5.10.0 python-engineio==4.8.0
    echo "⏭️  Skipping optional dependencies in safe mode"
else
    echo "📦 Installing Python dependencies..."
    pip install -q -r requirements.txt
fi

echo ""
echo "✅ Installation complete!"
echo ""
echo "=========================================="
echo "🚀 Starting NATOS..."
echo "=========================================="
echo ""

# Run the application, forwarding safe mode flag
if [ "$SAFE_MODE" = "true" ]; then
    python app.py --safe-mode
else
    python app.py
fi
