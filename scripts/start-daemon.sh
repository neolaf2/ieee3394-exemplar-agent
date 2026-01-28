#!/bin/bash
# Start the IEEE 3394 Agent daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
LOG_DIR="$HOME/.P3394_agent_ieee3394-exemplar/logs"

# Create log directory if needed
mkdir -p "$LOG_DIR"

# Check if already running
if [ -e /tmp/ieee3394-agent.sock ]; then
    echo "⚠️  Agent daemon may already be running"
    echo "   Socket exists at: /tmp/ieee3394-agent.sock"
    echo ""
    read -p "Stop existing daemon and restart? (y/N) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        "$SCRIPT_DIR/stop-daemon.sh"
        sleep 2
    else
        exit 1
    fi
fi

# Check for API key
if [ -z "$ANTHROPIC_API_KEY" ]; then
    if [ -f "$PROJECT_DIR/.env" ]; then
        echo "📝 Loading .env file..."
        export $(grep -v '^#' "$PROJECT_DIR/.env" | xargs)
    fi
fi

if [ -z "$ANTHROPIC_API_KEY" ]; then
    echo "❌ Error: ANTHROPIC_API_KEY not set"
    echo ""
    echo "Please set your API key:"
    echo "  export ANTHROPIC_API_KEY='your-api-key-here'"
    echo ""
    echo "Or add to .env file:"
    echo "  echo 'ANTHROPIC_API_KEY=your-api-key-here' > .env"
    exit 1
fi

echo "🚀 Starting IEEE 3394 Agent daemon..."

cd "$PROJECT_DIR"

# Start in background
nohup uv run ieee3394-agent --daemon \
    > "$LOG_DIR/daemon.log" 2>&1 &

DAEMON_PID=$!

# Save PID
echo $DAEMON_PID > /tmp/ieee3394-agent.pid

echo "✓ Daemon started with PID: $DAEMON_PID"
echo "  Socket: /tmp/ieee3394-agent.sock"
echo "  Logs: $LOG_DIR/daemon.log"
echo ""
echo "To connect:"
echo "  uv run ieee3394-agent"
echo ""
echo "To stop:"
echo "  $SCRIPT_DIR/stop-daemon.sh"

# Wait for socket to be created
for i in {1..10}; do
    if [ -e /tmp/ieee3394-agent.sock ]; then
        echo "✓ Socket ready"
        exit 0
    fi
    sleep 0.5
done

echo "⚠️  Warning: Socket not created within 5 seconds"
echo "   Check logs at: $LOG_DIR/daemon.log"
