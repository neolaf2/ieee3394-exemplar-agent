# P3394 Agent Starter Kit - Quick Start

Get your P3394-compliant agent running in 5 minutes.

## Prerequisites

- Python 3.10+
- [uv](https://github.com/astral-sh/uv) package manager
- Anthropic API key

## Step 1: Install Dependencies

```bash
uv sync
```

## Step 2: Set Your API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

## Step 3: Customize Your Agent (Optional)

Edit `agent.yaml` to customize your agent:

```yaml
agent:
  id: "my-custom-agent"
  name: "My Custom Agent"
  version: "0.1.0"
  description: "My P3394-compliant assistant"

channels:
  cli:
    enabled: true
  web:
    enabled: true
    port: 8000
```

## Step 4: Run Your Agent

```bash
# Run in daemon mode
uv run python -m p3394_agent --daemon
```

You should see:
```
🚀 P3394 Agent running on /tmp/p3394-agent.sock
   Agent: My Custom Agent v0.1.0
   Press Ctrl+C to stop
```

## Step 5: Connect a Client

In a **new terminal**, start a client session:

```bash
uv run python -m p3394_agent
```

This launches the interactive CLI interface where you can chat with the agent.

## Your First Session

After starting, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║              My Custom Agent                                  ║
║                   CLI Channel                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Version: 0.1.0                                              ║
║  Session: abc123...                                          ║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                      ║
║  Type 'exit' to quit                                          ║
╚══════════════════════════════════════════════════════════════╝

>>>
```

## Try These Commands

### Symbolic Commands (Instant, no LLM)
```
>>> /help
>>> /about
>>> /status
>>> /version
>>> /listSkills
```

### Natural Language (Uses Claude API)
```
>>> Hello! What can you do?
>>> echo Hello World!
>>> How do I configure channels?
```

## Configuration Reference

### agent.yaml Structure

```yaml
# Agent identity
agent:
  id: "my-agent"
  name: "My Agent"
  version: "0.1.0"
  description: "Description here"

# Channel configuration (all HTTP channels on single port)
channels:
  cli:
    enabled: true
    default: true
  web:
    enabled: true
    host: "0.0.0.0"
    port: 8000
    routes:
      chat: "/"              # Web chat at root
      anthropic_api: "/v1"   # Anthropic API
      p3394: "/p3394"        # P3394 protocol
  anthropic_api:
    enabled: true
    api_keys: []             # Empty = no auth for testing
  p3394:
    enabled: true
  whatsapp:
    enabled: false
    service_phone: "${WHATSAPP_PHONE}"

# Skills to load
skills:
  - name: "echo"
    enabled: true
  - name: "help"
    enabled: true

# LLM configuration
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  system_prompt: |
    You are {agent_name}, a helpful assistant.

# Storage configuration
storage:
  type: "sqlite"
  path: "./data/agent.db"
```

### Environment Variables

Use environment variables in `agent.yaml`:

```yaml
channels:
  whatsapp:
    service_phone: "${WHATSAPP_PHONE}"           # Required
    gateway_url: "${GATEWAY_URL:-http://localhost:8000}"  # With default
```

## Creating Custom Skills

Create a skill in `.claude/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: My custom skill
triggers:
  - "do something"
  - "help me with X"
---

# My Skill

When this skill is triggered, do the following:

1. Extract the user's request
2. Process it according to these rules
3. Return a helpful response
```

Skills are automatically loaded on agent startup.

## Multi-Channel Setup

All HTTP channels are served on a single port (8000 by default):

```bash
uv run python -m p3394_agent --daemon
```

This enables:
- **CLI** (Unix socket) - Interactive REPL at `/tmp/p3394-agent-cli.sock`
- **Web Chat** - Browser UI at `http://localhost:8000/chat`
- **Web API** - REST API at `http://localhost:8000/api/`
- **Anthropic API** - Compatible API at `http://localhost:8000/v1/messages`
- **P3394 Protocol** - Native agent protocol at `http://localhost:8000/p3394/`

### Connecting with Cherry Studio or Cursor

Configure your client to use:
- **Base URL**: `http://localhost:8000`
- **API Path**: `/v1/messages`
- **Model**: `ieee-3394-agent`

The Anthropic API is compatible with any client that supports the Claude API format.

## Troubleshooting

### "ANTHROPIC_API_KEY not set" error

```bash
export ANTHROPIC_API_KEY='sk-ant-...'
```

### Dependencies not installed

```bash
uv sync
```

### Port already in use

Change the port in `agent.yaml`:

```yaml
channels:
  web:
    port: 8080  # Use a different port
```

## What's Happening Behind the Scenes

1. **You type** → CLI adapter creates a P3394Message
2. **Gateway routes** → Determines if symbolic command or LLM
3. **Handler executes** → Runs function or calls Claude API
4. **Response returns** → Formatted and displayed

Every message follows the P3394 Universal Message Format standard.

## Next Steps

- **[Full Documentation](./docs/)** - Detailed guides and API reference
- **[Skill Development Guide](./.claude/skills/README.md)** - Create custom skills
- **[P3394 Standard](https://ieee3394.org)** - Learn about the standard
