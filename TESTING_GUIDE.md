# IEEE 3394 Exemplar Agent - Multi-Channel Testing Guide

This guide shows how to test the agent through different channel interfaces, demonstrating the P3394 multi-channel architecture.

## Architecture Overview

```
┌─────────────────────────────────────────────────────────┐
│           IEEE 3394 Exemplar Agent (Daemon)              │
│                                                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │   Gateway    │  │    Skills    │  │ KSTAR Memory │  │
│  │  (Router)    │  │   Loader     │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
│         │                                                 │
└─────────┼─────────────────────────────────────────────────┘
          │
  ┌───────┴──────────────────────────────────────────┐
  │                Channel Adapters                   │
  │                                                    │
  │  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
  │  │   CLI    │  │Anthropic │  │  P3394   │       │
  │  │ (Socket) │  │   API    │  │  Server  │       │
  │  │          │  │ (HTTP)   │  │  (HTTP)  │       │
  │  └──────────┘  └──────────┘  └──────────┘       │
  └─────────────────────────────────────────────────┘
          │              │              │
          ▼              ▼              ▼
    [CLI Client]  [HTTP Client]  [P3394 Client]
```

---

## Prerequisites

### 1. Install Dependencies

```bash
# From project root
uv sync

# Or if using pip
pip install -e .
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'

# Or add to .env file
echo "ANTHROPIC_API_KEY=your-api-key-here" > .env
```

### 3. Verify Installation

```bash
uv run python -m ieee3394_agent --help
```

---

## Channel 1: CLI Client (Unix Socket)

The CLI channel provides an interactive REPL interface over Unix sockets.

### Terminal 1: Start the Agent Daemon

```bash
# Start agent in daemon mode
uv run python -m ieee3394_agent --daemon

# With debug logging
uv run python -m ieee3394_agent --daemon --debug

# Custom socket path
uv run python -m ieee3394_agent --daemon --socket /tmp/my-agent.sock
```

**Expected Output:**
```
2024-01-28 21:50:00 - ieee3394_agent.server - INFO - Starting IEEE 3394 Exemplar Agent daemon
2024-01-28 21:50:01 - ieee3394_agent.server - INFO - Unix socket server listening on /tmp/ieee3394-agent.sock
2024-01-28 21:50:01 - ieee3394_agent.server - INFO - Agent ready to accept connections
```

### Terminal 2: Connect with CLI Client

```bash
# Connect to agent
uv run python -m ieee3394_agent

# Connect to custom socket
uv run python -m ieee3394_agent --socket /tmp/my-agent.sock
```

**Expected Output:**
```
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent - CLI                  ║
╠══════════════════════════════════════════════════════════════╣
║  Connected to: /tmp/ieee3394-agent.sock                      ║
║  Type /help for commands, /exit to quit                      ║
╚══════════════════════════════════════════════════════════════╝

>>>
```

### Test Commands

```bash
# Get help
>>> /help

# Ask about the agent
>>> What is the IEEE 3394 standard?

# Test IEEE WG Manager skill
>>> Help me prepare for an IEEE sponsor ballot

# List available skills
>>> /skills

# Get agent status
>>> /status

# Exit
>>> /exit
```

---

## Channel 2: Anthropic API Server (HTTP)

The Anthropic API server makes the agent accessible via HTTP, compatible with Anthropic's API format.

### Terminal 1: Start Agent with API Server

```bash
# Start with Anthropic API adapter enabled
uv run python -m ieee3394_agent --daemon --anthropic-api --api-port 8100

# With custom API keys for authentication
uv run python -m ieee3394_agent --daemon --anthropic-api --api-port 8100 \
  --api-keys "test-key-1,test-key-2"

# Full example with all options
uv run python -m ieee3394_agent --daemon \
  --anthropic-api --api-port 8100 \
  --debug
```

**Expected Output:**
```
2024-01-28 21:50:00 - ieee3394_agent.server - INFO - Starting IEEE 3394 Exemplar Agent daemon
2024-01-28 21:50:01 - ieee3394_agent.channels.anthropic_api_server - INFO - Anthropic API server listening on http://0.0.0.0:8100
2024-01-28 21:50:01 - ieee3394_agent.server - INFO - Agent ready to accept connections
```

### Terminal 2: Test with curl

```bash
# Test basic message
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key-1" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [
      {"role": "user", "content": "What is the IEEE 3394 standard?"}
    ]
  }'

# Test IEEE WG Manager skill
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key-1" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [
      {"role": "user", "content": "Help me calculate ballot approval rates. We got 30 Approve, 5 Disapprove, 10 Abstain out of 50 invitations."}
    ]
  }'

# Test with streaming
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key-1" \
  -N \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "stream": true,
    "messages": [
      {"role": "user", "content": "Explain P3394 message format"}
    ]
  }'
```

### Test with Python

```python
#!/usr/bin/env python3
"""Test Anthropic API channel"""

import anthropic

# Connect to local agent
client = anthropic.Anthropic(
    api_key="test-key-1",
    base_url="http://localhost:8100"
)

# Send message
message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "What is IEEE P3394?"}
    ]
)

print(message.content[0].text)

# Test streaming
with client.messages.stream(
    model="claude-sonnet-4-5-20250929",
    max_tokens=1024,
    messages=[
        {"role": "user", "content": "Help me prepare meeting minutes"}
    ]
) as stream:
    for text in stream.text_stream:
        print(text, end="", flush=True)
```

### Test with Claude Code CLI

```bash
# Configure Claude Code to use local agent
export ANTHROPIC_BASE_URL=http://localhost:8100
export ANTHROPIC_API_KEY=test-key-1

# Use Claude Code normally - it will connect to your local agent!
claude "What skills does this agent have?"
```

---

## Channel 3: P3394 Agent Server (Agent-to-Agent)

The P3394 server enables agent-to-agent communication using the P3394 protocol.

### Terminal 1: Start Agent with P3394 Server

```bash
# P3394 server is enabled by default
uv run python -m ieee3394_agent --daemon --p3394-port 8101

# Or explicitly enable it
uv run python -m ieee3394_agent --daemon --p3394-server --p3394-port 8101

# Start with both API servers
uv run python -m ieee3394_agent --daemon \
  --anthropic-api --api-port 8100 \
  --p3394-server --p3394-port 8101
```

**Expected Output:**
```
2024-01-28 21:50:00 - ieee3394_agent.server - INFO - Starting IEEE 3394 Exemplar Agent daemon
2024-01-28 21:50:01 - ieee3394_agent.channels.p3394_server - INFO - P3394 server listening on http://0.0.0.0:8101
2024-01-28 21:50:01 - ieee3394_agent.server - INFO - Agent ready to accept connections
```

### Terminal 2: Test with P3394 Client

```bash
# Test with built-in P3394 client
uv run python -c "
from ieee3394_agent.channels.p3394_client import P3394Client
import asyncio

async def test():
    client = P3394Client('http://localhost:8101')

    # Send P3394 message
    response = await client.send_message(
        'What is the IEEE 3394 standard?',
        session_id='test-session-123'
    )
    print(response)

    await client.close()

asyncio.run(test())
"
```

### Test with curl (P3394 JSON format)

```bash
# Send P3394 Universal Message Format
curl -X POST http://localhost:8101/message \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "source": {
      "agent_id": "test-client",
      "channel_id": "http"
    },
    "destination": {
      "agent_id": "ieee3394-exemplar"
    },
    "content": [
      {
        "type": "text",
        "data": "What capabilities do you have?"
      }
    ],
    "session_id": "test-session-123"
  }'

# Get agent capabilities
curl http://localhost:8101/capabilities

# Health check
curl http://localhost:8101/health
```

---

## Channel 4: Multiple Channels Simultaneously

Run all channels at once for comprehensive testing.

### Start Fully-Equipped Daemon

```bash
uv run python -m ieee3394_agent --daemon \
  --anthropic-api --api-port 8100 \
  --p3394-server --p3394-port 8101 \
  --debug
```

**This enables:**
- ✅ CLI client access via Unix socket
- ✅ HTTP API access (Anthropic-compatible) on port 8100
- ✅ P3394 agent-to-agent access on port 8101
- ✅ Debug logging for troubleshooting

### Test All Channels

**Terminal 2 - CLI:**
```bash
uv run python -m ieee3394_agent
>>> What is P3394?
```

**Terminal 3 - HTTP API:**
```bash
curl http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{"model": "claude-sonnet-4-5-20250929", "max_tokens": 1024, "messages": [{"role": "user", "content": "Hello"}]}'
```

**Terminal 4 - P3394:**
```bash
curl http://localhost:8101/message \
  -H "Content-Type: application/json" \
  -d '{"type": "request", "content": [{"type": "text", "data": "Status check"}]}'
```

---

## Testing the IEEE WG Manager Skill

Once the agent is running, test the newly added IEEE WG Manager skill:

### Via CLI Channel

```bash
>>> Help me calculate ballot results. We got 30 Approve, 5 Disapprove, 10 Abstain.

>>> Generate an IEEE meeting agenda for our next working group meeting

>>> What are the IEEE ballot types and their approval thresholds?

>>> Explain the standards development lifecycle from PAR to publication

>>> Help me consolidate comments from a ballot
```

### Via HTTP API

```bash
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{
      "role": "user",
      "content": "Help me prepare for an IEEE sponsor ballot. What do I need to know?"
    }]
  }'
```

### Via P3394 Protocol

```bash
curl -X POST http://localhost:8101/message \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "content": [{
      "type": "text",
      "data": "Generate meeting minutes template for IEEE working group"
    }],
    "session_id": "wg-meeting-001"
  }'
```

---

## Troubleshooting

### "ANTHROPIC_API_KEY not set"

```bash
export ANTHROPIC_API_KEY='your-key-here'
# or
echo "ANTHROPIC_API_KEY=your-key" > .env
```

### "Socket already in use"

```bash
# Remove old socket
rm /tmp/ieee3394-agent.sock

# Or use custom socket path
uv run python -m ieee3394_agent --daemon --socket /tmp/my-agent.sock
```

### "Connection refused" (HTTP channels)

```bash
# Check if daemon is running
ps aux | grep ieee3394

# Check if ports are in use
lsof -i :8100
lsof -i :8101

# Restart daemon with debug logging
uv run python -m ieee3394_agent --daemon --debug
```

### Skill Not Loading

```bash
# Check skills directory
ls -la .claude/skills/

# Verify skill YAML frontmatter
head -5 .claude/skills/ieee-wg-manager/SKILL.md

# Start with debug to see skill loading
uv run python -m ieee3394_agent --daemon --debug
```

---

## Testing Checklist

### Basic Functionality
- [ ] Agent starts in daemon mode
- [ ] CLI client connects successfully
- [ ] Can send messages and receive responses
- [ ] `/help` command works
- [ ] `/skills` shows loaded skills
- [ ] `/exit` cleanly disconnects

### HTTP API Channel
- [ ] API server starts on specified port
- [ ] Can send messages via curl
- [ ] Streaming responses work
- [ ] API authentication works (if keys configured)
- [ ] Python client library works

### P3394 Channel
- [ ] P3394 server starts
- [ ] Can send P3394 UMF messages
- [ ] Capabilities endpoint works
- [ ] Health check responds

### Skills
- [ ] IEEE WG Manager skill loads
- [ ] Can invoke skill with relevant queries
- [ ] Skill accesses bundled resources
- [ ] Scripts are executable
- [ ] Templates are accessible

### Multi-Channel
- [ ] All channels work simultaneously
- [ ] Sessions are maintained per channel
- [ ] No cross-channel interference

---

## Performance Testing

### Load Testing CLI

```bash
# Multiple concurrent clients
for i in {1..5}; do
  (echo "Hello from client $i" | uv run python -m ieee3394_agent) &
done
wait
```

### Load Testing HTTP API

```bash
# Using Apache Bench
ab -n 100 -c 10 -p request.json -T application/json \
  -H "x-api-key: test-key" \
  http://localhost:8100/v1/messages

# Using wrk
wrk -t4 -c100 -d30s --latency \
  -s post_message.lua \
  http://localhost:8100/v1/messages
```

---

## Development Tips

### Watch Logs in Real-Time

```bash
# Terminal 1: Run with debug
uv run python -m ieee3394_agent --daemon --debug

# Terminal 2: Filter logs
uv run python -m ieee3394_agent --daemon --debug 2>&1 | grep "ieee3394_agent"

# Terminal 3: Save logs
uv run python -m ieee3394_agent --daemon --debug 2>&1 | tee agent.log
```

### Test Individual Components

```bash
# Test UMF message parsing
uv run python -c "
from ieee3394_agent.core.umf import P3394Message
msg = P3394Message.text('Hello')
print(msg.to_dict())
"

# Test skill loading
uv run python -c "
from ieee3394_agent.core.skill_loader import SkillLoader
loader = SkillLoader('.claude/skills')
skills = loader.load_all_skills()
print(f'Loaded {len(skills)} skills')
"
```

---

## Next Steps

After testing all channels:

1. **Deploy**: Package agent for production deployment
2. **Monitor**: Set up logging and monitoring
3. **Scale**: Add more channel adapters as needed
4. **Extend**: Create additional skills for your domain

## Additional Resources

- **P3394 Standard**: IEEE P3394 documentation
- **Agent Architecture**: See CLAUDE.md
- **Skill Development**: See .claude/skills/README.md
- **API Reference**: See docs/api.md (if available)
