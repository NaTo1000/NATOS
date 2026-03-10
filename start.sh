#!/bin/bash

echo "=========================================="
echo "🏎️  NATOS Installation Script"
echo "=========================================="
echo ""

# Install Python dependencies
echo "📦 Installing Python dependencies..."
pip install -q -r requirements.txt

echo ""
echo "✅ Installation complete!"
echo ""
echo "=========================================="
echo "🚀 Starting NATOS..."
echo "=========================================="
echo ""

# Run the application
python app.py
