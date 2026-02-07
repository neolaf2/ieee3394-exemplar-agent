# IEEE 3394 Agent Architecture

## Overview

The IEEE 3394 Exemplar Agent demonstrates proper channel adapter architecture as specified in the P3394 standard.

## Architecture Layers

```
┌─────────────────────────────────────────────────────────────┐
│                     USER INTERFACES                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐         │
│  │ CLI Client  │  │ Web Browser │  │ MCP Client  │         │
│  │ (Terminal)  │  │ (HTTP/WS)   │  │ (Protocol)  │         │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘         │
└─────────┼─────────────────┼─────────────────┼───────────────┘
          │                 │                 │
          │ Simple format   │ HTTP/WS         │ MCP protocol
          │ {"text":"..."}  │ requests        │ messages
          │                 │                 │
┌─────────┼─────────────────┼─────────────────┼───────────────┐
│         ↓                 ↓                 ↓               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │ CLI Channel  │  │ Web Channel  │  │ MCP Channel  │     │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │     │
│  │              │  │              │  │              │     │
│  │ Transforms:  │  │ Transforms:  │  │ Transforms:  │     │
│  │ CLI → UMF    │  │ HTTP → UMF   │  │ MCP → UMF    │     │
│  │ UMF → CLI    │  │ UMF → HTTP   │  │ UMF → MCP    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                  │                  │             │
│         └──────────────────┴──────────────────┘             │
│                            │                                │
│                    P3394 UMF Messages                       │
│                            ↓                                │
│                 ┌──────────────────┐                        │
│                 │  Agent Gateway   │                        │
│                 │                  │                        │
│                 │  - Routes UMF    │                        │
│                 │  - KSTAR Memory  │                        │
│                 │  - xAPI Logging  │                        │
│                 │  - Skills        │                        │
│                 │  - SubAgents     │                        │
│                 └──────────────────┘                        │
│                    AGENT CORE                               │
└─────────────────────────────────────────────────────────────┘
```

## Components

### 1. User Interfaces (Clients)

**Responsibility:** Present interface to humans or programs

**Examples:**
- **CLI Client** (`cli_client.py`) - Terminal REPL interface
- **Web Browser** - HTML/JavaScript interface
- **MCP Client** - Agent-to-agent protocol

**Protocol:** Each uses its native format (plain text, HTTP, MCP)

### 2. Channel Adapters

**Responsibility:** Transform native protocols ↔ P3394 UMF

**Examples:**
- **CLI Channel Adapter** (`channels/cli.py`)
  - Listens on Unix socket: `/tmp/ieee3394-agent-cli.sock`
  - Receives: `{"text": "user message"}`
  - Transforms to: `P3394Message(type=REQUEST, content=[...])`
  - Returns: `{"type": "response", "text": "agent reply"}`

- **Web Channel Adapter** (`channels/web.py`) - *Pending*
  - Listens on HTTP port
  - Receives: HTTP POST/WebSocket
  - Transforms to/from UMF

- **MCP Channel Adapter** (`channels/mcp.py`) - *Pending*
  - MCP protocol compliance
  - Transforms to/from UMF

**Key Insight:** Channel adapters are **protocol translators**. They don't contain business logic - they only transform messages.

### 3. Agent Gateway

**Responsibility:** Route UMF messages, orchestrate services

**Functions:**
- Message routing (symbolic commands vs LLM)
- Session management
- KSTAR memory integration
- xAPI statement logging
- Skill invocation
- SubAgent delegation

**Protocol:** P3394 UMF (Universal Message Format) only

## Current Implementation

### Daemon Mode (All Channels)

```bash
# Start daemon with all channels
uv run ieee3394-agent --daemon
```

This starts:
1. **Agent Gateway** - Core message router
2. **UMF Server** - Direct UMF protocol (port: `/tmp/ieee3394-agent.sock`)
3. **CLI Channel Adapter** - CLI protocol (port: `/tmp/ieee3394-agent-cli.sock`)

### CLI Client

```bash
# Connect CLI client to CLI channel
uv run ieee3394-cli

# Or directly
python -m ieee3394_agent.cli_client
```

**Flow:**
```
User types: "Hello"
    ↓
CLI Client sends: {"text": "Hello"}
    ↓
CLI Channel Adapter receives JSON
    ↓
Adapter transforms to: P3394Message(type=REQUEST, content=[P3394Content(TEXT, "Hello")])
    ↓
Gateway routes UMF message
    ↓
Gateway returns: P3394Message(type=RESPONSE, content=[P3394Content(TEXT, "Hi there!")])
    ↓
Adapter transforms to: {"type": "response", "text": "Hi there!"}
    ↓
CLI Client displays: "Hi there!"
```

### Legacy UMF Client

```bash
# Direct UMF protocol client (bypasses channel adapters)
uv run ieee3394-agent

# Or
python -m ieee3394_agent
```

This connects directly to the UMF server and sends P3394Message objects. It's useful for testing but not recommended for end users.

## Message Formats

### CLI Client Protocol

**Request:**
```json
{
  "text": "What is P3394?"
}
```

**Response:**
```json
{
  "type": "response",
  "message_id": "uuid-here",
  "session_id": "session-uuid",
  "text": "P3394 is the IEEE standard for..."
}
```

**Error:**
```json
{
  "type": "error",
  "message_id": "uuid-here",
  "session_id": "session-uuid",
  "text": "Error message here"
}
```

### P3394 UMF (Internal)

**Request:**
```python
P3394Message(
    id="msg-uuid",
    type=MessageType.REQUEST,
    timestamp="2026-01-28T20:00:00Z",
    content=[
        P3394Content(type=ContentType.TEXT, data="What is P3394?")
    ],
    session_id="session-uuid"
)
```

**Response:**
```python
P3394Message(
    id="response-uuid",
    type=MessageType.RESPONSE,
    timestamp="2026-01-28T20:00:01Z",
    content=[
        P3394Content(type=ContentType.TEXT, data="P3394 is...")
    ],
    session_id="session-uuid",
    reply_to="msg-uuid"
)
```

## Benefits of Channel Adapter Pattern

### ✅ Separation of Concerns
- **Clients** focus on UI/UX
- **Adapters** focus on protocol transformation
- **Gateway** focuses on business logic

### ✅ Multiple Interfaces
- Same agent, multiple entry points
- CLI, Web, MCP all work simultaneously
- Each optimized for its use case

### ✅ Protocol Independence
- Gateway doesn't know about CLI, HTTP, etc.
- Easy to add new channels without modifying gateway
- Clients can use any protocol

### ✅ Standards Compliance
- All internal communication uses P3394 UMF
- Adapters ensure UMF compliance
- Interoperability with other P3394 agents

### ✅ Testability
- Test adapters independently
- Test gateway with pure UMF
- Mock adapters for unit tests

## Adding New Channels

To add a new channel (e.g., Slack, Discord, SMS):

1. **Create Channel Adapter** (`channels/slack.py`):
   ```python
   class SlackChannelAdapter:
       def __init__(self, gateway: AgentGateway):
           self.gateway = gateway

       async def handle_slack_message(self, slack_event):
           # Transform Slack event → UMF
           umf_msg = self._slack_to_umf(slack_event)

           # Send to gateway
           response = await self.gateway.handle(umf_msg)

           # Transform UMF → Slack format
           slack_reply = self._umf_to_slack(response)

           # Send to Slack API
           await self.slack_client.send_message(slack_reply)
   ```

2. **Register with Gateway** (in `server.py`):
   ```python
   slack_channel = SlackChannelAdapter(gateway)
   await slack_channel.start()
   ```

3. **No Gateway Changes Needed** - Gateway only sees UMF!

## File Structure

```
src/ieee3394_agent/
├── core/
│   ├── gateway.py           # Agent Gateway (routes UMF)
│   ├── umf.py              # P3394 UMF definitions
│   ├── session.py          # Session management
│   └── storage.py          # STM/LTM storage
├── channels/
│   ├── cli.py              # CLI Channel Adapter
│   ├── web.py              # Web Channel Adapter (pending)
│   └── mcp.py              # MCP Channel Adapter (pending)
├── memory/
│   └── kstar.py            # KSTAR memory
├── plugins/
│   └── hooks.py            # P3394 hooks
├── cli_client.py           # CLI Client (user interface)
├── client.py               # Generic UMF client
└── server.py               # Daemon (starts gateway + channels)
```

## Best Practices

### DO:
- ✅ Keep channel adapters thin - only transform messages
- ✅ Put business logic in the gateway
- ✅ Use P3394 UMF for all internal communication
- ✅ Log all UMF messages as xAPI statements
- ✅ Create session per client connection

### DON'T:
- ❌ Put business logic in channel adapters
- ❌ Let clients send UMF directly (use adapters)
- ❌ Mix channel-specific code in the gateway
- ❌ Bypass adapters for "quick hacks"

## Testing

### Test Channel Adapter
```python
# Test CLI adapter transforms messages correctly
cli_msg = {"text": "/help"}
umf_msg = adapter._cli_to_umf(cli_msg, session_id)
assert umf_msg.type == MessageType.REQUEST
assert umf_msg.content[0].data == "/help"
```

### Test Gateway
```python
# Test gateway with pure UMF (no adapter needed)
umf_request = P3394Message.text("/help")
umf_response = await gateway.handle(umf_request)
assert umf_response.type == MessageType.RESPONSE
```

### Integration Test
```python
# Test full flow
client = CLIClient()
await client.connect()
response = await client.send_message("/help")
assert "Available Commands" in response["text"]
```

---

This architecture ensures proper separation of concerns and makes the agent truly multi-channel while maintaining P3394 compliance.
