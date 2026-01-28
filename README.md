# IEEE 3394 Exemplar Agent

A reference implementation of the IEEE P3394 Standard for Agent Interfaces, demonstrating:

- **Universal Message Format (UMF)** - Standard message structure for agent communication
- **Multi-Channel Architecture** - Web, CLI, and MCP channels with unified routing
- **KSTAR Memory Integration** - Episodic memory and skill learning
- **Self-Documenting Agent** - The agent IS the documentation

## Architecture

This agent serves dual purposes:
1. **Reference Implementation** - Demonstrates P3394 compliance patterns
2. **Public Agent** - Powers ieee3394.org for standard education and adoption

Built on the Claude Agent SDK with:
- Two-tier message routing (symbolic commands + LLM intelligence)
- Channel adapters transforming protocols to/from P3394 UMF
  - **CLI Channel**: Terminal interface
  - **Anthropic API Channel**: Compatible with Anthropic SDK clients
  - **Web Channel** (coming soon): HTTP/WebSocket interface
- Hook-based extensibility for compliance and logging
- Agent skills and subagents for specialized capabilities

## Quick Start

### Installation

```bash
# Clone the repository
git clone https://github.com/neolaf2/ieee3394-exemplar-agent.git
cd ieee3394-exemplar-agent

# Install dependencies
uv sync

# Set API key
export ANTHROPIC_API_KEY='your-api-key-here'
```

### Running the Agent

#### Start the Daemon

```bash
# Terminal 1: Start daemon with all channels
uv run ieee3394-agent --daemon

# With Anthropic API channel (makes agent accessible via Anthropic API)
uv run ieee3394-agent --daemon --anthropic-api --api-port 8100
```

This starts:
- Agent Gateway (core routing engine)
- CLI Channel Adapter (for CLI clients)
- UMF Server (for direct UMF protocol)
- Anthropic API Server Adapter (optional, if --anthropic-api flag used)

You'll see:
```
🚀 IEEE 3394 Agent Host starting...
   Agent: IEEE 3394 Exemplar Agent v0.1.0
   UMF Socket: /tmp/ieee3394-agent.sock
   CLI Channel: /tmp/ieee3394-agent-cli.sock
   Anthropic API: http://0.0.0.0:8100 (if enabled)
   Press Ctrl+C to stop
```

#### Connect a CLI Client

```bash
# Terminal 2: Connect CLI client
uv run ieee3394-cli

# Or using Python directly
python -m ieee3394_agent.cli_client
```

The CLI client presents a REPL interface:
```
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent                        ║
║                   CLI Client                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                     ║
║  Type 'exit' to quit                                         ║
╚══════════════════════════════════════════════════════════════╝

>>> /help
>>> What is P3394?
>>> exit
```

#### Connect via Anthropic API

```python
# Python: Use Anthropic SDK
from anthropic import Anthropic

client = Anthropic(
    api_key="test-key",  # Agent-issued key (or blank for testing)
    base_url="http://localhost:8100"  # Your agent's endpoint
)

message = client.messages.create(
    model="ieee-3394-agent",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What is P3394?"}
    ]
)

print(message.content[0].text)
```

```bash
# curl: Direct API call
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{
    "model": "ieee-3394-agent",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello!"}
    ]
  }'
```

See **[ANTHROPIC_API.md](./ANTHROPIC_API.md)** for complete Anthropic API adapter documentation.

#### Using Management Scripts

```bash
# Start daemon in background
./scripts/start-daemon.sh

# Check status
./scripts/status-daemon.sh

# Connect CLI client
uv run ieee3394-cli

# Stop daemon
./scripts/stop-daemon.sh

# Restart daemon
./scripts/restart-daemon.sh
```

## Project Status

✅ **MVP Complete** (85% overall progress)

**Implemented:**
- ✅ P3394 Universal Message Format (UMF)
- ✅ Agent Gateway with two-tier routing
- ✅ KSTAR memory integration
- ✅ Daemon/client architecture
- ✅ STM/LTM storage system
- ✅ xAPI (Experience API) logging
- ✅ CLI channel
- ✅ Session management
- ✅ Multi-client support

**Pending:**
- ⏳ Web channel (FastAPI + WebSocket)
- ⏳ Full Claude Agent SDK integration
- ⏳ MCP server connections

## Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - Getting started guide
- **[DAEMON.md](./DAEMON.md)** - Daemon management (start/stop/restart)
- **[ANTHROPIC_API.md](./ANTHROPIC_API.md)** - Anthropic API channel adapters
- **[ARCHITECTURE.md](./ARCHITECTURE.md)** - Channel adapter architecture
- **[STORAGE.md](./STORAGE.md)** - Storage architecture (STM/LTM)
- **[XAPI.md](./XAPI.md)** - xAPI integration guide
- **[CLAUDE.md](./CLAUDE.md)** - Complete architecture specification
- **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** - Current status

## License

MIT License - See LICENSE file for details

## IEEE P3394 Standard

Learn more about the IEEE P3394 Agent Interface Standard:
- **Website:** ieee3394.org (powered by this agent)
- **Working Group:** IEEE Standards Association
- **Purpose:** Enable agent interoperability across vendors and platforms
