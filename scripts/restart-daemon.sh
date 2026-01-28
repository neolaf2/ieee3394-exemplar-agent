#!/bin/bash
# Restart the IEEE 3394 Agent daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Restarting IEEE 3394 Agent daemon..."
echo ""

"$SCRIPT_DIR/stop-daemon.sh"
sleep 2
"$SCRIPT_DIR/start-daemon.sh"
