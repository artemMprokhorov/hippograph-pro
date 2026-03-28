#!/bin/bash
# Restart hippograph container and reconnect to network.
# Use instead of 'docker restart hippograph' to avoid MCP 403.
set -e

echo "Restarting hippograph..."
docker restart hippograph

echo "Reconnecting to network..."
docker network connect hippograph-pro_default hippograph 2>/dev/null || true

echo "Waiting for reranker (~30s)..."
sleep 35

# Check ready
RESPONSE=$(docker logs hippograph 2>&1 | grep 'Reranker loaded' | tail -1)
if [ -n "$RESPONSE" ]; then
    echo "Ready: $RESPONSE"
else
    echo "Reranker still loading, check: docker logs hippograph 2>&1 | grep Reranker"
fi