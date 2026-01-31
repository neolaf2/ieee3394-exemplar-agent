# MCP Channel Adapter

The MCP (Model Context Protocol) Channel Adapter provides bidirectional integration between P3394 agents and the MCP ecosystem.

## Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                     MCP Channel Architecture                             │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  INBOUND (MCPServerAdapter)              OUTBOUND (MCPClientAdapter)    │
│  ┌─────────────────────────┐            ┌─────────────────────────┐    │
│  │ MCP Client (Claude Code)│            │   MCP Subagent          │    │
│  │ calls P3394 tools       │            │   (KSTAR Memory, etc.)  │    │
│  └───────────┬─────────────┘            └───────────▲─────────────┘    │
│              │                                      │                   │
│              ▼                                      │                   │
│  ┌─────────────────────────┐            ┌─────────────────────────┐    │
│  │ MCP Tool Call           │            │ MCP Tool Call           │    │
│  │ {"name": "p3394_...",   │            │ {"name": "kstar_...",   │    │
│  │  "arguments": {...}}    │            │  "arguments": {...}}    │    │
│  └───────────┬─────────────┘            └───────────▲─────────────┘    │
│              │                                      │                   │
│              ▼                                      │                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      P3394 UMF Layer                             │   │
│  │              (Semantic meaning preserved)                        │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│              │                                      ▲                   │
│              ▼                                      │                   │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │                      Agent Gateway                               │   │
│  │              (Routes to handlers)                                │   │
│  └─────────────────────────────────────────────────────────────────┘   │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Components

### 1. MCPServerAdapter (Inbound)

Exposes the P3394 agent as an MCP server. MCP clients can call P3394 capabilities as MCP tools.

**Use Cases:**
- Claude Code calling your P3394 agent
- Other LLM tools integrating with your agent
- Automated pipelines invoking agent capabilities

**Transports:**
- `stdio` - Standard input/output (default for CLI tools)
- `sse` - Server-Sent Events over HTTP

### 2. MCPClientAdapter (Outbound)

Connects to MCP subagents from the P3394 gateway.

**Use Cases:**
- Calling KSTAR memory server
- Integrating with external MCP services
- Agent-to-agent communication via MCP

**Transports:**
- `stdio` - Subprocess with pipe communication
- `http` - HTTP POST to MCP server

### 3. OutboundChannelRouter

Unified router that selects the appropriate transport for outbound messages.

**Supported Transports:**
| Transport | Use Case | Latency |
|-----------|----------|---------|
| `direct` | Same-process (KSTAR memory) | ~1ms |
| `mcp_stdio` | MCP subagent subprocess | ~10ms |
| `mcp_http` | MCP subagent over HTTP | ~50ms |
| `http` | Generic HTTP endpoint | ~50ms |

## Usage

### Starting the MCP Server

```python
from p3394_agent.channels import MCPServerAdapter

# Create adapter
mcp_server = MCPServerAdapter(
    gateway=gateway,
    transport="stdio"  # or "sse"
)

# Start server (blocks)
await mcp_server.start()
```

### Command Line

```bash
# Start agent with MCP server on stdio
uv run python -m p3394_agent --mcp-server

# Start agent with MCP server on SSE (HTTP)
uv run python -m p3394_agent --mcp-server --mcp-transport sse --mcp-port 8002
```

### Connecting to MCP Subagents

```python
from p3394_agent.channels import MCPClientAdapter

# Create client
mcp_client = MCPClientAdapter(gateway)

# Connect via stdio (starts subprocess)
await mcp_client.connect_stdio(
    agent_id="kstar-memory",
    command="p3394-memory-server",
    args=["--mode", "stdio"]
)

# Connect via HTTP
await mcp_client.connect_http(
    agent_id="remote-agent",
    endpoint="http://localhost:8002"
)

# Send P3394 message
response = await mcp_client.send("kstar-memory", message)
```

## Auto-Generated MCP Tools

The MCPServerAdapter automatically generates MCP tools from:

### 1. P3394 Capabilities

Each registered capability becomes an MCP tool:

```
Capability: kstar:store_trace
    → MCP Tool: p3394_kstar_store_trace
```

### 2. Symbolic Commands

Each symbolic command becomes an MCP tool:

```
Command: /help
    → MCP Tool: p3394_cmd_help
```

### 3. Built-in Tools

| Tool | Description |
|------|-------------|
| `p3394_send_message` | Send a text message to the agent |
| `p3394_umf` | Send a raw P3394 UMF message |

## Authentication

MCP clients are authenticated based on transport:

| Transport | Method | Assurance Level |
|-----------|--------|-----------------|
| stdio | OS user + PID | MEDIUM |
| SSE + Bearer token | Token validation | MEDIUM |
| SSE anonymous | Client IP | LOW |

Authentication context is embedded in the P3394 message metadata:

```python
{
    "security": {
        "client_assertion": {
            "channel_id": "mcp",
            "channel_identity": "mcp:stdio:username:12345",
            "assurance_level": "medium",
            "authentication_method": "mcp_stdio"
        }
    }
}
```

## Message Transformation

### Inbound: MCP → P3394

```
MCP Tool Call:
{
    "name": "p3394_kstar_store_trace",
    "arguments": {
        "situation": {"domain": "test"},
        "task": {"goal": "example"},
        "action": {"type": "demo"}
    }
}

    ↓ Transform ↓

P3394 UMF Message:
{
    "type": "request",
    "content": [{
        "type": "tool_call",
        "data": {
            "capability_id": "kstar:store_trace",
            "arguments": {...}
        }
    }],
    "metadata": {
        "security": {...},
        "channel": {"channel_id": "mcp", "mcp_tool": "p3394_kstar_store_trace"}
    }
}
```

### Outbound: P3394 → MCP

```
P3394 UMF Message:
{
    "type": "request",
    "destination": {"agent_id": "kstar-memory"},
    "content": [{
        "type": "tool_call",
        "data": {
            "capability_id": "kstar:store_trace",
            "arguments": {...}
        }
    }]
}

    ↓ Transform ↓

MCP Tool Call:
{
    "jsonrpc": "2.0",
    "method": "tools/call",
    "params": {
        "name": "kstar_store_trace",
        "arguments": {...}
    }
}
```

## Configuration

### agent.yaml

```yaml
channels:
  mcp:
    enabled: true
    transport: stdio  # or "sse"
    sse_port: 8002    # if using SSE transport

# MCP subagents to auto-connect
subagents:
  kstar-memory:
    transport: direct  # Same process
  external-service:
    transport: mcp_http
    endpoint: http://localhost:8003
```

## Example: Claude Code Integration

To use your P3394 agent from Claude Code, add to your MCP config:

```json
{
  "mcpServers": {
    "p3394-agent": {
      "command": "uv",
      "args": ["run", "python", "-m", "p3394_agent", "--mcp-server"],
      "cwd": "/path/to/your/agent"
    }
  }
}
```

Then in Claude Code, you can call:

```
Use the p3394_send_message tool to ask the agent about P3394
```

## Semantic Transparency

The key architectural principle: **P3394 UMF provides semantic transparency**.

Whether invoked via:
- MCP tool call
- HTTP API
- CLI command
- Direct Python call

The same P3394 UMF message is created, carrying identical semantic meaning. The transport is abstracted away.

## See Also

- [P3394-LONG-TERM-MEMORY-SPEC.md](./P3394-LONG-TERM-MEMORY-SPEC.md) - KSTAR Memory as P3394 Subagent
- [CHANNEL_BINDING.md](./CHANNEL_BINDING.md) - Channel authentication
- [CAPABILITY_CATALOG.md](./CAPABILITY_CATALOG.md) - Capability discovery
