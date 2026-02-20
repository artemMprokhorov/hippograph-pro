#!/bin/bash
set -e

echo "🚀 Starting HippoGraph..."

# Start nginx for web viewer
echo "🌐 Starting nginx for graph viewer..."
service nginx start

# Configure ngrok with authtoken (from environment)
if [ -n "$NGROK_AUTHTOKEN" ] && [ -n "$NGROK_DOMAIN" ]; then
    echo "🔑 Configuring ngrok authtoken..."
    ngrok config add-authtoken $NGROK_AUTHTOKEN
    echo "🔗 Starting ngrok tunnel..."
    ngrok http --url=$NGROK_DOMAIN 5000 > /dev/null 2>&1 &
    sleep 3
    echo "   - Internet: https://$NGROK_DOMAIN"
fi

echo "📊 Graph viewer available at:"
echo "   - Local: http://localhost:5002"
echo "🧠 API server:"
echo "   - Local: http://localhost:5001"

# Start Flask server
echo "▶️  Starting Flask MCP server..."
exec python src/server.py
