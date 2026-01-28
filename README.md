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

#### Option 1: Daemon + Client (Recommended)

```bash
# Terminal 1: Start daemon (agent host)
uv run ieee3394-agent --daemon

# Terminal 2: Connect client
uv run ieee3394-agent
```

#### Option 2: Using Management Scripts

```bash
# Start daemon in background
./scripts/start-daemon.sh

# Check status
./scripts/status-daemon.sh

# Connect client
uv run ieee3394-agent

# Stop daemon
./scripts/stop-daemon.sh

# Restart daemon
./scripts/restart-daemon.sh
```

#### Option 3: Direct CLI (Single Process)

```bash
# Run directly without daemon
python -m ieee3394_agent.cli
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
