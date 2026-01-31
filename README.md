# P3394 Agent Starter Kit

Build P3394-compliant agents with this template. Clone, customize, and deploy your own agent in minutes.

## Features

- **Universal Message Format (UMF)** - Standard message structure for agent communication
- **Multi-Channel Architecture** - CLI, Web, WhatsApp, and API channels with unified routing
- **Configurable Identity** - Customize agent name, version, and behavior via `agent.yaml`
- **Skills System** - Auto-load capabilities from `.claude/skills/` directory
- **Capability Catalog** - Unified discovery with system↔memory synchronization
- **Authentication & Authorization** - Built-in security with progressive authentication
- **Hook System** - Extensible security, logging, and compliance hooks

## Quick Start

### 1. Install Dependencies

```bash
uv sync
```

### 2. Set API Key

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

### 3. Customize Your Agent

Edit `agent.yaml`:

```yaml
agent:
  id: "my-agent"
  name: "My Custom Agent"
  version: "0.1.0"
  description: "My P3394-compliant assistant"

channels:
  cli:
    enabled: true
  web:
    enabled: true
    port: 8000

llm:
  system_prompt: |
    You are {agent_name}, a helpful assistant.
```

### 4. Run Your Agent

```bash
# Start the daemon
uv run python -m p3394_agent --daemon

# Connect as client (in another terminal)
uv run python -m p3394_agent
```

See **[QUICKSTART.md](./QUICKSTART.md)** for the complete guide.

## Configuration

All configuration is centralized in `agent.yaml`:

| Section | Purpose |
|---------|---------|
| `agent` | Identity: id, name, version, description |
| `channels` | Enable/configure CLI, web, WhatsApp |
| `llm` | Model, system prompt, temperature |
| `skills` | Skills to load on startup |
| `storage` | Database path and type |

### Environment Variables

Use environment variables for secrets:

```yaml
channels:
  whatsapp:
    service_phone: "${WHATSAPP_PHONE}"
    api_key: "${WHATSAPP_API_KEY}"
```

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    P3394 Agent                              │
├─────────────────────────────────────────────────────────────┤
│                 Agent Gateway (Router)                      │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐        │
│  │  Symbolic   │  │    LLM      │  │   Skill     │        │
│  │  Commands   │  │   Handler   │  │  Handler    │        │
│  └─────────────┘  └─────────────┘  └─────────────┘        │
├─────────────────────────────────────────────────────────────┤
│                    Channel Adapters                         │
│  ┌──────┐  ┌──────┐  ┌──────────┐  ┌──────────┐          │
│  │ CLI  │  │ Web  │  │ WhatsApp │  │   API    │          │
│  └──────┘  └──────┘  └──────────┘  └──────────┘          │
└─────────────────────────────────────────────────────────────┘
```

**Message Flow:**
1. User sends message via any channel
2. Channel adapter converts to P3394 UMF
3. Gateway routes to appropriate handler
4. Response converted back and sent

## Skills System

Skills are markdown files in `.claude/skills/` that extend agent capabilities.

### Creating a Skill

```bash
mkdir -p .claude/skills/my-skill
```

Create `.claude/skills/my-skill/SKILL.md`:

```markdown
---
name: my-skill
description: What this skill does
triggers:
  - "trigger phrase"
---

# Skill Instructions

When this skill is triggered:
1. Do this
2. Then this
```

### Included Skills

| Skill | Description |
|-------|-------------|
| echo | Simple echo for testing |
| help | Contextual help |
| site-generator | Generate static HTML |
| p3394-explainer | Explain P3394 concepts |

## Channels

### CLI Channel

Interactive terminal interface:

```bash
uv run python -m p3394_agent
```

### Web Channel

HTTP/WebSocket interface (enable in agent.yaml):

```yaml
channels:
  web:
    enabled: true
    port: 8000
```

### API Channel

Anthropic API-compatible endpoint:

```bash
uv run python -m p3394_agent --daemon --anthropic-api --api-port 8100
```

### WhatsApp Channel

Meta Business API integration (requires setup):

```yaml
channels:
  whatsapp:
    enabled: true
    service_phone: "${WHATSAPP_PHONE}"
```

## Examples

See the `examples/` directory:

| Example | Description |
|---------|-------------|
| simple-chatbot | Minimal chatbot |

## Commands

Built-in symbolic commands (instant, no LLM):

| Command | Description |
|---------|-------------|
| `/help` | Show help |
| `/about` | About this agent |
| `/status` | Agent status |
| `/listSkills` | List skills |
| `/version` | Version info |

## Project Structure

```
p3394-agent-starter/
├── agent.yaml           # Central configuration
├── config/              # Configuration module
│   ├── schema.py        # AgentConfig dataclass
│   └── loader.py        # YAML loader
├── src/p3394_agent/     # Agent source code
│   ├── core/            # Gateway, UMF, session
│   ├── channels/        # Channel adapters
│   ├── plugins/         # Hooks and tools
│   └── memory/          # KSTAR memory
├── .claude/skills/      # Skills directory
├── examples/            # Example projects
├── QUICKSTART.md        # Getting started
└── README.md            # This file
```

## Documentation

- **[QUICKSTART.md](./QUICKSTART.md)** - 5-minute getting started
- **[.claude/skills/README.md](./.claude/skills/README.md)** - Skill development guide
- **[docs/CAPABILITY_CATALOG.md](./docs/CAPABILITY_CATALOG.md)** - Capability discovery and catalog
- **[docs/CAPABILITY_ACL.md](./docs/CAPABILITY_ACL.md)** - Access control system
- **[CLAUDE.md](./CLAUDE.md)** - Complete architecture specification

## Development

```bash
# Install dev dependencies
uv sync --dev

# Run tests
uv run pytest

# Format code
uv run ruff check --fix
```

## P3394 Standard

This starter kit implements the P3394 Universal Message Format for agent interoperability.

**Key Concepts:**
- **UMF Messages** - Standard structure for all agent communication
- **Channel Adapters** - Transform protocols to/from UMF
- **Symbolic Commands** - Instant commands without LLM
- **LLM Integration** - Claude API for natural language

Learn more at [ieee3394.org](https://ieee3394.org).

## License

MIT License - See LICENSE file for details.
