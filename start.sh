#!/bin/bash
set -e

echo "🚀 Starting HippoGraph..."

# Start nginx for web viewer
echo "🌐 Starting nginx for graph viewer..."
service nginx start

# NOTE: ngrok is handled by nginx-proxy container, not here.

echo "📊 Graph viewer available at:"
echo "   - Local: http://localhost:5002"
echo "🧠 API server:"
echo "   - Local: http://localhost:5001"

# Start Flask server
echo "▶️  Starting Flask MCP server..."
exec python src/server.py