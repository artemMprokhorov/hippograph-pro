#!/usr/bin/env bash
# install_mehen_cli.sh — Install mehen CLI tool
# Usage: bash install_mehen_cli.sh [API_URL] [API_KEY]
# Example:
#   bash install_mehen_cli.sh http://localhost:5020 my-api-key
#   bash install_mehen_cli.sh http://192.168.0.212:5020 my-api-key
#   bash install_mehen_cli.sh https://memory.yourdomain.com my-api-key

set -e

# Resolve script directory (works regardless of where you run from)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CLI_SCRIPT="$SCRIPT_DIR/mehen_cli.py"

# Args or defaults
API_URL="${1:-http://localhost:5000}"
API_KEY="${2:-your-api-key-here}"

# Validate CLI script exists
if [ ! -f "$CLI_SCRIPT" ]; then
    echo "❌ mehen_cli.py not found at: $CLI_SCRIPT"
    echo "   Run this script from the Mehen-Graph repository root."
    exit 1
fi

# Check python3
if ! command -v python3 &>/dev/null; then
    echo "❌ python3 not found. Install Python 3.10+ first."
    exit 1
fi

echo "🌀 Installing mehen CLI..."
echo "   API URL: $API_URL"
echo "   Script:  $CLI_SCRIPT"

# Create wrapper in /usr/local/bin
cat > /usr/local/bin/mehen << WRAPPER
#!/usr/bin/env bash
export MEHEN_API_URL="\${MEHEN_API_URL:-$API_URL}"
export MEHEN_API_KEY="\${MEHEN_API_KEY:-$API_KEY}"
exec python3 $CLI_SCRIPT "\$@"
WRAPPER

chmod +x /usr/local/bin/mehen

echo "✅ Installed: /usr/local/bin/mehen"
echo ""
echo "🚀 Try it:"
echo "   mehen search 'what did we work on last week'"
echo "   mehen stats"
echo "   mehen pcb"
echo "   mehen repl"
echo ""
echo "💡 Override URL/key anytime:"
echo "   MEHEN_API_URL=http://other-host:5020 mehen search 'query'"