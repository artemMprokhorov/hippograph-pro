#!/usr/bin/env bash
# install_hippograph_cli.sh — Install hippograph CLI tool
# Usage: bash install_hippograph_cli.sh [API_URL] [API_KEY]
# Example:
#   bash install_hippograph_cli.sh http://localhost:5001 my-api-key
#   bash install_hippograph_cli.sh http://192.168.0.X:5001 my-api-key
#   bash install_hippograph_cli.sh https://memory.yourdomain.com my-api-key

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/mehen_cli.py"

API_URL="${1:-http://localhost:5001}"
API_KEY="${2:-your-api-key-here}"

if [ ! -f "$CLI_SCRIPT" ]; then
    echo "❌ mehen_cli.py not found at: $CLI_SCRIPT"
    echo "   Run from the HippoGraph Pro repository root."
    exit 1
fi

if ! command -v python3 &>/dev/null; then
    echo "❌ python3 not found. Install Python 3.10+ first."
    exit 1
fi

echo "🧠 Installing hippograph CLI..."
echo "   API URL: $API_URL"
echo "   Script:  $CLI_SCRIPT"

cat > /usr/local/bin/hippograph << WRAPPER
#!/usr/bin/env bash
export HIPPOGRAPH_API_URL="\${HIPPOGRAPH_API_URL:-$API_URL}"
export HIPPOGRAPH_API_KEY="\${HIPPOGRAPH_API_KEY:-$API_KEY}"
exec python3 $CLI_SCRIPT "\$@"
WRAPPER

chmod +x /usr/local/bin/hippograph

echo "✅ Installed: /usr/local/bin/hippograph"
echo ""
echo "🚀 Try it:"
echo "   hippograph search 'temporal retrieval'"
echo "   hippograph stats"
echo "   hippograph pcb"
echo "   hippograph repl"
echo ""
echo "💡 Override URL/key anytime:"
echo "   HIPPOGRAPH_API_URL=http://other-host:5001 hippograph search 'query'"