# Anthropic API Channel Adapters

The IEEE 3394 Agent includes **two Anthropic API channel adapters** that enable bidirectional compatibility with the Anthropic API format:

1. **Server Adapter**: Makes the agent look like an Anthropic API endpoint
2. **Client Adapter**: Allows the agent to call external Anthropic API

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  External Clients/Services                   │
│                                                              │
│  ┌──────────────┐              ┌──────────────┐            │
│  │ Anthropic    │              │  External    │            │
│  │ SDK Client   │              │  Anthropic   │            │
│  │              │              │  API         │            │
│  └──────┬───────┘              └──────┬───────┘            │
│         │                              ↑                    │
└─────────┼──────────────────────────────┼────────────────────┘
          │                              │
          │ HTTP POST                    │ HTTP POST
          │ /v1/messages                 │ /v1/messages
          ↓                              │
┌─────────┼──────────────────────────────┼────────────────────┐
│         ↓                              │                    │
│  ┌──────────────────┐          ┌──────────────────┐        │
│  │  Server Adapter  │          │  Client Adapter  │        │
│  │  (Receives API   │          │  (Sends API      │        │
│  │   calls)         │          │   calls)         │        │
│  └─────────┬────────┘          └──────────────────┘        │
│            │                                                │
│            │ Transforms to/from P3394 UMF                   │
│            ↓                                                │
│     ┌─────────────┐                                         │
│     │   Gateway   │                                         │
│     └─────────────┘                                         │
│                                                             │
│            IEEE 3394 Agent                                  │
└─────────────────────────────────────────────────────────────┘
```

## Server Adapter

### Purpose

The **Server Adapter** makes the IEEE 3394 agent accessible to any client that uses the Anthropic API, including:

- Anthropic SDK (Python, TypeScript, etc.)
- Claude Code
- Other agents that use Anthropic API format
- Custom applications built with Anthropic SDK

### How It Works

1. **Listens** on HTTP port (default: 8100)
2. **Receives** Anthropic API requests at `/v1/messages`
3. **Transforms** Anthropic API format → P3394 UMF
4. **Routes** UMF message to Agent Gateway
5. **Receives** UMF response from Gateway
6. **Transforms** P3394 UMF → Anthropic API format
7. **Returns** Anthropic API response to client

### Starting the Server Adapter

```bash
# Start daemon with Anthropic API server adapter
uv run ieee3394-agent --daemon --anthropic-api

# Custom port
uv run ieee3394-agent --daemon --anthropic-api --api-port 8100

# With API key authentication
uv run ieee3394-agent --daemon --anthropic-api --api-keys "key1,key2,key3"

# No API keys (open for testing)
uv run ieee3394-agent --daemon --anthropic-api
```

When started, you'll see:

```
🚀 IEEE 3394 Agent Host starting...
   Agent: IEEE 3394 Exemplar Agent v0.1.0
   UMF Socket: /tmp/ieee3394-agent.sock
   CLI Channel: /tmp/ieee3394-agent-cli.sock
   Anthropic API: http://0.0.0.0:8100
   API Keys: None (open for testing)
   Press Ctrl+C to stop
```

### Using the Server Adapter

#### From Python (Anthropic SDK)

```python
from anthropic import Anthropic

# Point to your agent instead of Anthropic API
client = Anthropic(
    api_key="your-agent-issued-key",  # Or blank for testing
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

#### From curl

```bash
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{
    "model": "ieee-3394-agent",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "Hello, what is P3394?"}
    ]
  }'
```

#### From Claude Code

```python
# In Claude Code configuration
{
  "anthropic": {
    "api_url": "http://localhost:8100",
    "api_key": "your-agent-issued-key"
  }
}
```

### API Endpoints

#### POST /v1/messages

Create a message (main Anthropic API endpoint).

**Request:**

```json
{
  "model": "ieee-3394-agent",
  "max_tokens": 1024,
  "messages": [
    {"role": "user", "content": "Hello"}
  ],
  "system": "You are a helpful assistant",
  "temperature": 1.0,
  "stream": false
}
```

**Response (non-streaming):**

```json
{
  "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "Response text here"}
  ],
  "model": "ieee-3394-agent",
  "stop_reason": "end_turn",
  "usage": {
    "input_tokens": 10,
    "output_tokens": 20
  }
}
```

**Response (streaming):**

Server-sent events (SSE) format:

```
event: message_start
data: {"type": "message_start", "message": {...}}

event: content_block_start
data: {"type": "content_block_start", ...}

event: content_block_delta
data: {"type": "content_block_delta", "delta": {"text": "chunk"}}

event: message_stop
data: {"type": "message_stop"}
```

#### GET /v1/models

List available models.

**Response:**

```json
{
  "object": "list",
  "data": [
    {
      "id": "ieee-3394-agent",
      "object": "model",
      "created": 1706745600,
      "owned_by": "ieee-3394"
    }
  ]
}
```

#### GET /health

Health check endpoint.

**Response:**

```json
{
  "status": "healthy",
  "agent": "IEEE 3394 Exemplar Agent",
  "version": "0.1.0"
}
```

### API Key Authentication

The server adapter supports **agent-issued API keys** (not Anthropic keys):

**With API keys:**

```bash
# Start with API keys
uv run ieee3394-agent --daemon --anthropic-api --api-keys "sk-agent-key1,sk-agent-key2"

# Client must provide valid key
curl -H "x-api-key: sk-agent-key1" http://localhost:8100/v1/messages ...
```

**Without API keys (testing):**

```bash
# Start without API keys
uv run ieee3394-agent --daemon --anthropic-api

# Any key (or no key) will work
curl -H "x-api-key: anything" http://localhost:8100/v1/messages ...
```

### Message Transformation

**Anthropic API Request → P3394 UMF:**

```python
# Anthropic format
{
  "model": "claude-3-5-sonnet-20241022",
  "messages": [
    {"role": "user", "content": "Hello"},
    {"role": "assistant", "content": "Hi!"},
    {"role": "user", "content": "How are you?"}
  ],
  "system": "You are helpful",
  "max_tokens": 1024
}

# Transformed to UMF
P3394Message(
  type=MessageType.REQUEST,
  content=[
    P3394Content(
      type=ContentType.TEXT,
      data="How are you?",  # Last user message
      metadata={
        "conversation_history": "System: You are helpful\nUser: Hello\nAssistant: Hi!\nUser: How are you?",
        "anthropic_format": True
      }
    )
  ],
  metadata={
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "source_api": "anthropic"
  }
)
```

**P3394 UMF Response → Anthropic API:**

```python
# UMF response
P3394Message(
  type=MessageType.RESPONSE,
  content=[
    P3394Content(type=ContentType.TEXT, data="I'm doing well!")
  ]
)

# Transformed to Anthropic format
{
  "id": "msg_01XFD...",
  "type": "message",
  "role": "assistant",
  "content": [
    {"type": "text", "text": "I'm doing well!"}
  ],
  "model": "claude-3-5-sonnet-20241022",
  "stop_reason": "end_turn",
  "usage": {"input_tokens": 15, "output_tokens": 5}
}
```

---

## Client Adapter

### Purpose

The **Client Adapter** allows the IEEE 3394 agent to make outbound calls to the **real Anthropic API** when needed.

### How It Works

1. Agent creates a **P3394 UMF message**
2. Client adapter **transforms** UMF → Anthropic API format
3. Client adapter **sends** to `https://api.anthropic.com`
4. Anthropic API **responds** with Anthropic format
5. Client adapter **transforms** Anthropic API → UMF
6. Agent receives **UMF response**

### Usage

```python
from ieee3394_agent.channels.anthropic_api_client import AnthropicAPIClientAdapter
from ieee3394_agent.core.umf import P3394Message, P3394Content, ContentType

# Create client adapter with your Anthropic API key
client = AnthropicAPIClientAdapter(
    api_key="sk-ant-your-real-key",  # Real Anthropic API key
    default_model="claude-3-5-sonnet-20241022"
)

# Create UMF message
umf_request = P3394Message(
    type=MessageType.REQUEST,
    content=[
        P3394Content(type=ContentType.TEXT, data="What is machine learning?")
    ],
    metadata={
        "model": "claude-3-5-sonnet-20241022",
        "max_tokens": 1024
    }
)

# Send to Anthropic API
umf_response = await client.send(umf_request)

# Response is in UMF format
print(umf_response.content[0].data)
```

### When to Use

Use the **Client Adapter** when your agent needs to:

- Delegate to the real Claude for specific tasks
- Validate responses against Claude
- Compare outputs
- Use Claude for specialized skills

---

## Testing

### Test the Server Adapter

```bash
# Terminal 1: Start daemon with Anthropic API
uv run ieee3394-agent --daemon --anthropic-api

# Terminal 2: Run test
uv run python test_anthropic_api.py
```

The test script (`test_anthropic_api.py`) tests:

1. **Non-streaming messages**: Regular API call
2. **Streaming messages**: Server-sent events
3. **Conversation context**: Multi-turn messages
4. **System prompts**: Custom instructions

### Expected Output

```
============================================================
Testing Anthropic API Server Adapter
============================================================

1. Testing non-streaming message...
   ✓ Response received
   Message ID: msg_01XFDUDYJgAACzvnptvVoYEL
   Model: ieee-3394-agent
   Stop Reason: end_turn
   Usage: 15 in, 50 out

   Response:
   Hello! I'm glad you asked. IEEE P3394 is...

2. Testing streaming message...
   ✓ Streaming response:
   P3394 defines...

3. Testing multiple messages (conversation)...
   ✓ Response received
   Response:
   The main components of UMF are...

4. Testing system prompt...
   ✓ Response received
   Response:
   P3394 is important because...

============================================================
✓ All tests passed!
============================================================
```

---

## Benefits

### Server Adapter Benefits

✅ **Universal Compatibility**: Any Anthropic SDK client can talk to your agent
✅ **Drop-in Replacement**: Point `base_url` to your agent instead of Anthropic
✅ **Multi-Client Support**: Multiple clients can connect simultaneously
✅ **Streaming Support**: Server-sent events for real-time responses
✅ **API Key Authentication**: Control access with agent-issued keys

### Client Adapter Benefits

✅ **Outbound API Calls**: Agent can call real Anthropic API when needed
✅ **UMF Integration**: All communication stays in P3394 format internally
✅ **Delegation**: Use Claude for specific tasks
✅ **Hybrid Architecture**: Local agent + remote Claude capabilities

---

## Use Cases

### Use Case 1: Multi-Agent System

```
┌─────────────┐     Anthropic API      ┌─────────────┐
│   Agent A   │ ──────────────────────> │ IEEE 3394   │
│             │   (via server adapter)  │   Agent     │
└─────────────┘                         └─────────────┘
                                               │
                                               │ Anthropic API
                                               │ (via client adapter)
                                               ↓
                                        ┌─────────────┐
                                        │ Anthropic   │
                                        │    API      │
                                        └─────────────┘
```

Agent A talks to IEEE 3394 agent using Anthropic API format. IEEE 3394 agent can delegate to real Claude when needed.

### Use Case 2: Testing & Development

Use the server adapter to test your application without making real API calls:

```python
# Development: Point to your local agent
client = Anthropic(
    base_url="http://localhost:8100",
    api_key="test"
)

# Production: Point to real Anthropic API
client = Anthropic(
    base_url="https://api.anthropic.com",
    api_key="sk-ant-real-key"
)
```

### Use Case 3: Claude Code Extension

Run IEEE 3394 agent as a local Claude Code backend:

```json
{
  "anthropic": {
    "api_url": "http://localhost:8100",
    "api_key": "local-agent-key"
  }
}
```

Claude Code thinks it's talking to Anthropic API, but it's actually talking to your custom agent.

---

## File Locations

```
src/ieee3394_agent/
├── channels/
│   ├── anthropic_api_server.py    # Server adapter
│   └── anthropic_api_client.py    # Client adapter
├── server.py                       # Daemon (starts server adapter)
└── __main__.py                     # CLI (--anthropic-api flag)

test_anthropic_api.py               # Test script
ANTHROPIC_API.md                    # This file
```

---

## Troubleshooting

### Server adapter not starting

```bash
# Check if port is in use
lsof -i :8100

# Use different port
uv run ieee3394-agent --daemon --anthropic-api --api-port 8101
```

### Client can't connect

```bash
# Check server is running
curl http://localhost:8100/health

# Check API key
curl -H "x-api-key: test" http://localhost:8100/v1/messages ...
```

### Client adapter errors

```bash
# Set real Anthropic API key
export ANTHROPIC_API_KEY='sk-ant-your-key'

# Or pass to constructor
client = AnthropicAPIClientAdapter(api_key="sk-ant-your-key")
```

---

## Next Steps

1. ✅ Server adapter implemented
2. ✅ Client adapter implemented
3. ✅ Test script created
4. ⏳ Add to daemon startup (optional flag)
5. ⏳ Create integration tests
6. ⏳ Add to ARCHITECTURE.md
7. ⏳ Update README.md

The Anthropic API adapters enable true interoperability between P3394-compliant agents and the broader Anthropic ecosystem!
