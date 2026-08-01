#!/bin/bash
# Demo Script for DataHub Health Guardian Agent

echo "=================================================="
echo "🏥 Starting DataHub Health Guardian Agent Demo..."
echo "=================================================="

# Check if server is running
if ! curl -s http://localhost:8000/api/health > /dev/null; then
    echo "❌ Server is not running. Please start it using:"
    echo "   python -m uvicorn guardian.server:app --reload"
    exit 1
fi

echo "✅ Server is running."
echo ""
echo "🚀 Triggering Health Scan..."
curl -s -X POST "http://localhost:8000/api/scan?demo=true" | jq . > /dev/null

echo "✅ Scan completed!"
echo ""
echo "📊 Opening Dashboard..."
# Fallback mechanism to open index.html
if which xdg-open > /dev/null; then
  xdg-open dashboard/index.html
elif which open > /dev/null; then
  open dashboard/index.html
else
  echo "Please open dashboard/index.html in your browser manually."
fi
echo "🎉 Demo complete!"
