#!/bin/bash
# Check IEEE 3394 Agent daemon status

echo "IEEE 3394 Agent Daemon Status"
echo "=============================="
echo ""

# Check if PID file exists
if [ -f /tmp/ieee3394-agent.pid ]; then
    PID=$(cat /tmp/ieee3394-agent.pid)
    echo "PID file: /tmp/ieee3394-agent.pid"
    echo "PID: $PID"

    if ps -p $PID > /dev/null 2>&1; then
        echo "Status: ✓ Running"

        # Show process details
        echo ""
        echo "Process details:"
        ps -p $PID -o pid,ppid,user,%cpu,%mem,etime,command
    else
        echo "Status: ❌ Not running (stale PID file)"
    fi
else
    echo "PID file: Not found"

    # Try to find by process name
    PIDS=$(pgrep -f "ieee3394-agent --daemon" || true)

    if [ -n "$PIDS" ]; then
        echo "Status: ⚠️  Running (no PID file)"
        echo "PIDs: $PIDS"
        echo ""
        echo "Process details:"
        ps -p $PIDS -o pid,ppid,user,%cpu,%mem,etime,command
    else
        echo "Status: ❌ Not running"
    fi
fi

echo ""
echo "Socket:"
if [ -e /tmp/ieee3394-agent.sock ]; then
    echo "  ✓ /tmp/ieee3394-agent.sock exists"
    ls -lh /tmp/ieee3394-agent.sock
else
    echo "  ❌ Socket not found"
fi

echo ""
echo "Storage:"
STORAGE_DIR="$HOME/.P3394_agent_ieee3394-exemplar"
if [ -d "$STORAGE_DIR" ]; then
    echo "  ✓ $STORAGE_DIR"
    echo "  Size: $(du -sh "$STORAGE_DIR" | cut -f1)"

    # Count sessions
    SESSION_COUNT=$(find "$STORAGE_DIR/STM/server" -maxdepth 1 -type d 2>/dev/null | wc -l)
    echo "  Sessions: $((SESSION_COUNT - 1))"  # Subtract 1 for the parent dir
else
    echo "  ❌ Storage directory not found"
fi

echo ""
echo "Logs:"
LOG_DIR="$HOME/.P3394_agent_ieee3394-exemplar/logs"
if [ -d "$LOG_DIR" ]; then
    echo "  ✓ $LOG_DIR"
    ls -lht "$LOG_DIR" 2>/dev/null | head -n 5
else
    echo "  ❌ Log directory not found"
fi
