# IEEE 3394 Agent Daemon Management

Quick guide for starting, stopping, and managing the agent daemon.

## Quick Start

### 1. Set API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or add to `.env` file:
```bash
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### 2. Start Daemon

```bash
# Using uv (recommended)
uv run ieee3394-agent --daemon

# Or using Python directly
python -m ieee3394_agent --daemon

# With debug logging
uv run ieee3394-agent --daemon --debug
```

The daemon will start and display:
```
🚀 IEEE 3394 Agent Host running on /tmp/ieee3394-agent.sock
   Agent: IEEE 3394 Exemplar Agent v0.1.0
   Press Ctrl+C to stop
```

### 3. Connect Client

In another terminal:

```bash
# Connect to daemon
uv run ieee3394-agent

# Or
python -m ieee3394_agent
```

### 4. Stop Daemon

Press `Ctrl+C` in the daemon terminal, or:

```bash
# Find and kill the process
pkill -f "ieee3394-agent --daemon"

# Or more gracefully
pgrep -f "ieee3394-agent --daemon" | xargs kill -SIGTERM
```

## Management Scripts

### Start Script (`scripts/start-daemon.sh`)

```bash
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
```

### Stop Script (`scripts/stop-daemon.sh`)

```bash
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
```

### Restart Script (`scripts/restart-daemon.sh`)

```bash
#!/bin/bash
# Restart the IEEE 3394 Agent daemon

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "🔄 Restarting IEEE 3394 Agent daemon..."
echo ""

"$SCRIPT_DIR/stop-daemon.sh"
sleep 2
"$SCRIPT_DIR/start-daemon.sh"
```

### Status Script (`scripts/status-daemon.sh`)

```bash
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
```

## System Service Setup

### macOS (launchd)

Create `~/Library/LaunchAgents/com.ieee3394.agent.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.ieee3394.agent</string>

    <key>ProgramArguments</key>
    <array>
        <string>/usr/local/bin/uv</string>
        <string>run</string>
        <string>ieee3394-agent</string>
        <string>--daemon</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>ANTHROPIC_API_KEY</key>
        <string>your-api-key-here</string>
    </dict>

    <key>WorkingDirectory</key>
    <string>/path/to/ieee3394Agent</string>

    <key>StandardOutPath</key>
    <string>/tmp/ieee3394-agent.log</string>

    <key>StandardErrorPath</key>
    <string>/tmp/ieee3394-agent.error.log</string>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>
</dict>
</plist>
```

Then:

```bash
# Load the service
launchctl load ~/Library/LaunchAgents/com.ieee3394.agent.plist

# Start the service
launchctl start com.ieee3394.agent

# Stop the service
launchctl stop com.ieee3394.agent

# Unload the service
launchctl unload ~/Library/LaunchAgents/com.ieee3394.agent.plist

# Check status
launchctl list | grep ieee3394
```

### Linux (systemd)

Create `/etc/systemd/system/ieee3394-agent.service`:

```ini
[Unit]
Description=IEEE 3394 Exemplar Agent
After=network.target

[Service]
Type=simple
User=your-username
WorkingDirectory=/path/to/ieee3394Agent
Environment="ANTHROPIC_API_KEY=your-api-key-here"
ExecStart=/usr/local/bin/uv run ieee3394-agent --daemon
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Then:

```bash
# Reload systemd
sudo systemctl daemon-reload

# Enable service (start on boot)
sudo systemctl enable ieee3394-agent

# Start service
sudo systemctl start ieee3394-agent

# Stop service
sudo systemctl stop ieee3394-agent

# Restart service
sudo systemctl restart ieee3394-agent

# Check status
sudo systemctl status ieee3394-agent

# View logs
sudo journalctl -u ieee3394-agent -f
```

## Troubleshooting

### Socket Already Exists

```bash
# Remove stale socket
rm /tmp/ieee3394-agent.sock

# Restart daemon
./scripts/restart-daemon.sh
```

### Port/Socket in Use

```bash
# Find process using the socket
lsof /tmp/ieee3394-agent.sock

# Kill the process
kill $(lsof -t /tmp/ieee3394-agent.sock)
```

### Check Logs

```bash
# Daemon log
tail -f ~/.P3394_agent_ieee3394-exemplar/logs/server.log

# Background daemon log (if using start script)
tail -f ~/.P3394_agent_ieee3394-exemplar/logs/daemon.log
```

### Verify API Key

```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Test with client
uv run ieee3394-agent

# If error, set it:
export ANTHROPIC_API_KEY='your-key-here'
```

### Clean Restart

```bash
# Stop daemon
./scripts/stop-daemon.sh

# Clean up all temporary files
rm -f /tmp/ieee3394-agent.sock
rm -f /tmp/ieee3394-agent.pid

# Restart
./scripts/start-daemon.sh
```

## Command Reference

| Command | Description |
|---------|-------------|
| `uv run ieee3394-agent --daemon` | Start daemon (foreground) |
| `./scripts/start-daemon.sh` | Start daemon (background) |
| `./scripts/stop-daemon.sh` | Stop daemon |
| `./scripts/restart-daemon.sh` | Restart daemon |
| `./scripts/status-daemon.sh` | Check daemon status |
| `uv run ieee3394-agent` | Connect as client |
| `pkill -f "ieee3394-agent --daemon"` | Force kill daemon |

## Next Steps

1. **Make scripts executable:**
   ```bash
   chmod +x scripts/*.sh
   ```

2. **Test the scripts:**
   ```bash
   ./scripts/start-daemon.sh
   ./scripts/status-daemon.sh
   ./scripts/stop-daemon.sh
   ```

3. **Set up system service** (optional but recommended for production)

4. **Monitor logs** to ensure everything works:
   ```bash
   tail -f ~/.P3394_agent_ieee3394-exemplar/logs/*.log
   ```
