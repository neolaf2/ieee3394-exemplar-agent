#!/bin/bash
# Stop the IEEE 3394 Agent daemon

set -e

echo "🛑 Stopping IEEE 3394 Agent daemon..."

# Check if PID file exists
if [ -f /tmp/ieee3394-agent.pid ]; then
    PID=$(cat /tmp/ieee3394-agent.pid)

    if ps -p $PID > /dev/null 2>&1; then
        echo "  Sending SIGTERM to PID $PID..."
        kill $PID

        # Wait for process to exit
        for i in {1..10}; do
            if ! ps -p $PID > /dev/null 2>&1; then
                echo "✓ Daemon stopped"
                rm -f /tmp/ieee3394-agent.pid
                rm -f /tmp/ieee3394-agent.sock
                exit 0
            fi
            sleep 1
        done

        # Force kill if still running
        echo "  Process still running, sending SIGKILL..."
        kill -9 $PID
        rm -f /tmp/ieee3394-agent.pid
        rm -f /tmp/ieee3394-agent.sock
        echo "✓ Daemon force stopped"
    else
        echo "  PID $PID not running"
        rm -f /tmp/ieee3394-agent.pid
        rm -f /tmp/ieee3394-agent.sock
    fi
else
    # Try to find by process name
    PIDS=$(pgrep -f "ieee3394-agent --daemon" || true)

    if [ -n "$PIDS" ]; then
        echo "  Found daemon process(es): $PIDS"
        echo $PIDS | xargs kill
        sleep 2
        rm -f /tmp/ieee3394-agent.sock
        echo "✓ Daemon stopped"
    else
        echo "  No daemon process found"
    fi
fi

# Clean up socket if it still exists
if [ -e /tmp/ieee3394-agent.sock ]; then
    rm -f /tmp/ieee3394-agent.sock
    echo "  Cleaned up socket file"
fi
