# P3394 Agent SDK Developer Guide

Build your own P3394-compliant agents using the SDK. This guide covers packaging, architecture patterns, and implementation strategies for different agent types.

## Table of Contents

1. [SDK Overview](#sdk-overview)
2. [Installation & Packaging](#installation--packaging)
3. [Agent Architecture Patterns](#agent-architecture-patterns)
4. [Companion Agent (Single User)](#companion-agent-single-user)
5. [Task Agent (Multi-User Service)](#task-agent-multi-user-service)
6. [Configuration](#configuration)
7. [Extending the SDK](#extending-the-sdk)
8. [Deployment](#deployment)

---

## SDK Overview

The P3394 Agent SDK provides:

| Component | Description |
|-----------|-------------|
| **Core Gateway** | Message routing, session management, capability dispatch |
| **Channel Adapters** | CLI, Web, MCP, WhatsApp, API channels |
| **KSTAR Memory** | Long-term memory with traces, perceptions, skills, tokens |
| **Authentication** | Principal-based identity, credential binding, ACLs |
| **Skills System** | Markdown-based capability definitions |
| **Hooks** | Pre/post processing for security, logging, compliance |

### Core Principles

1. **P3394 UMF** - All communication uses Universal Message Format
2. **Channel Abstraction** - Same logic, multiple interfaces
3. **Principal Identity** - Semantic identity (Org-Role-Person)
4. **Capability-Based Access** - Fine-grained permissions
5. **Local-First Memory** - User-owned, exportable

---

## Installation & Packaging

### Using as a Dependency

Add to your `pyproject.toml`:

```toml
[project]
dependencies = [
    "p3394-agent-sdk @ git+https://github.com/ieee3394/p3394-agent-starter.git",
]
```

Or install directly:

```bash
pip install git+https://github.com/ieee3394/p3394-agent-starter.git
```

### Publishing Your Own Package

1. **Clone the starter kit:**

```bash
git clone https://github.com/ieee3394/p3394-agent-starter.git my-agent
cd my-agent
```

2. **Customize `pyproject.toml`:**

```toml
[project]
name = "my-custom-agent"
version = "1.0.0"
description = "My P3394-compliant agent"

dependencies = [
    "p3394-agent-sdk>=0.2.0",  # Or include inline
    # Your additional dependencies
]

[project.scripts]
my-agent = "my_agent.__main__:run"
```

3. **Build and publish:**

```bash
# Build wheel
uv build

# Publish to PyPI (or private registry)
uv publish
```

### Package Structure

```
my-agent/
├── pyproject.toml
├── agent.yaml              # Agent configuration
├── src/
│   └── my_agent/
│       ├── __init__.py
│       ├── __main__.py     # Entry point
│       ├── capabilities/   # Custom capabilities
│       └── hooks/          # Custom hooks
├── .claude/
│   └── skills/             # Agent skills
└── tests/
```

---

## Agent Architecture Patterns

### Pattern 1: Companion Agent (Single User)

A personal assistant serving one primary user with deep context.

```
┌─────────────────────────────────────────────────────────────┐
│                   Companion Agent                            │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  User (Owner)                                                │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Principal: urn:principal:org:personal:role:owner:   │   │
│  │            person:user-uuid                          │   │
│  │ Assurance: HIGH (local machine)                     │   │
│  │ Capabilities: ALL (*)                               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                              │
│  Channels: CLI, Web (localhost), MCP                        │
│  Memory: Local SQLite, full access                          │
│  LLM Context: Deep personalization, long history            │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Single owner principal with full access
- Deep personalization and context
- Local-first storage
- All channels enabled
- Rich memory and learning

### Pattern 2: Task Agent (Multi-User Service)

A specialized service handling specific tasks for multiple users.

```
┌─────────────────────────────────────────────────────────────┐
│                     Task Agent                               │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  Multiple Client Principals                                  │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │ Client A         │  │ Client B         │                │
│  │ Role: customer   │  │ Role: customer   │                │
│  │ Caps: query,     │  │ Caps: query,     │                │
│  │       submit     │  │       submit     │                │
│  └──────────────────┘  └──────────────────┘                │
│                                                              │
│  ┌──────────────────┐                                       │
│  │ Admin            │  ← Limited admin access               │
│  │ Role: admin      │                                       │
│  │ Caps: manage,    │                                       │
│  │       configure  │                                       │
│  └──────────────────┘                                       │
│                                                              │
│  Channels: API, Web, WhatsApp (limited)                     │
│  Memory: Per-user isolation, shared knowledge base          │
│  LLM Context: Task-focused, stateless or short sessions     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

**Characteristics:**
- Multiple client principals with limited capabilities
- Per-user memory isolation
- Stateless or session-based
- API-first design
- Strict capability ACLs

---

## Companion Agent (Single User)

### Implementation

```python
# src/my_companion/__main__.py

from p3394_agent.core.gateway_sdk import AgentGateway
from p3394_agent.memory.kstar import KStarMemory
from p3394_agent.channels import CLIChannelAdapter, UnifiedWebServer
from pathlib import Path

async def main():
    # Initialize memory (local SQLite)
    memory = KStarMemory(
        storage_dir=Path.home() / ".my-companion" / "memory"
    )

    # Create gateway
    gateway = AgentGateway(
        memory=memory,
        working_dir=Path.cwd()
    )

    # Register owner principal (implicit for CLI)
    # CLI channel auto-detects local user as owner

    # Start CLI channel
    cli = CLIChannelAdapter(gateway)
    await cli.start()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Configuration (`agent.yaml`)

```yaml
agent:
  id: "my-companion"
  name: "Personal Assistant"
  version: "1.0.0"
  type: "companion"  # Enables single-user optimizations
  description: "Your personal AI companion"

# Single owner - all permissions
principals:
  owner:
    auto_detect: true  # Detect from local user
    capabilities: ["*"]  # Full access

channels:
  cli:
    enabled: true
    socket_path: "/tmp/my-companion.sock"
  web:
    enabled: true
    port: 8000
    host: "127.0.0.1"  # Localhost only for security
  mcp:
    enabled: true
    transport: stdio

llm:
  model: "claude-sonnet-4-20250514"
  system_prompt: |
    You are {agent_name}, a personal AI companion for {owner_name}.

    You have access to the user's:
    - Personal preferences and history
    - Long-term memory of past conversations
    - Learned skills and patterns

    Be helpful, remember context, and learn from interactions.

memory:
  storage: sqlite
  path: "~/.my-companion/memory.db"
  retention_days: 365  # Long retention for companions

skills:
  auto_load: true
  directory: ".claude/skills"
```

### Key Features for Companions

1. **Deep Context**
   ```python
   # Store personal context
   await memory.store_perception({
       "type": "preference",
       "subject": "owner",
       "content": "Prefers concise responses in morning",
       "confidence": 0.9
   })
   ```

2. **Learning from Interactions**
   ```python
   # After successful interaction
   await memory.update_skill_maturity("scheduling", outcome=True)
   ```

3. **Rich Memory Access**
   ```python
   # Query past interactions
   relevant = await memory.query_traces(
       filters={"situation.domain": "calendar"},
       limit=10
   )
   ```

---

## Task Agent (Multi-User Service)

### Implementation

```python
# src/my_task_agent/__main__.py

from p3394_agent.core.gateway_sdk import AgentGateway
from p3394_agent.memory.kstar import KStarMemory
from p3394_agent.channels import UnifiedWebServer
from p3394_agent.core.capability_acl import CapabilityACLRegistry
from pathlib import Path

async def main():
    # Initialize shared memory
    memory = KStarMemory(
        storage_dir=Path("/var/lib/my-task-agent/memory")
    )

    # Create gateway
    gateway = AgentGateway(
        memory=memory,
        working_dir=Path.cwd()
    )

    # Configure strict ACLs
    configure_task_agent_acls(gateway)

    # Start web server (API-focused)
    web = UnifiedWebServer(
        gateway=gateway,
        port=8000,
        host="0.0.0.0"  # Accept external connections
    )
    await web.start()

def configure_task_agent_acls(gateway):
    """Configure limited capabilities for task agent."""

    acl = gateway.acl_registry

    # Default: deny all
    acl.set_default_policy("deny")

    # Customer role: limited capabilities
    acl.set_acl("query_status", {
        "visibility": "public",
        "allowed_roles": ["customer", "admin"]
    })

    acl.set_acl("submit_request", {
        "visibility": "public",
        "allowed_roles": ["customer", "admin"],
        "rate_limit": 10  # Per minute
    })

    # Admin only
    acl.set_acl("manage_users", {
        "visibility": "protected",
        "allowed_roles": ["admin"]
    })

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

### Configuration (`agent.yaml`)

```yaml
agent:
  id: "order-status-agent"
  name: "Order Status Service"
  version: "1.0.0"
  type: "task"  # Enables multi-user optimizations
  description: "Check order status and submit requests"

# Multiple principal roles
principals:
  roles:
    customer:
      capabilities:
        - "query_status"
        - "submit_request"
      rate_limit: 60  # Requests per hour

    admin:
      capabilities:
        - "query_status"
        - "submit_request"
        - "manage_users"
        - "view_analytics"

# Authentication required
authentication:
  required: true
  methods:
    - api_key
    - oauth2

channels:
  web:
    enabled: true
    port: 8000
    host: "0.0.0.0"
    cors_origins: ["https://myapp.com"]
  api:
    enabled: true
    port: 8100
    auth_required: true
  cli:
    enabled: false  # No CLI for task agents
  mcp:
    enabled: false  # Usually not needed

llm:
  model: "claude-haiku-4-20250514"  # Fast, cost-effective
  system_prompt: |
    You are {agent_name}, a specialized service for order status inquiries.

    You can ONLY:
    1. Check order status by order ID
    2. Submit new support requests

    You CANNOT:
    - Access personal information beyond order details
    - Make changes to orders
    - Discuss topics outside order management

    Be concise and professional.

memory:
  storage: sqlite
  path: "/var/lib/order-agent/memory.db"
  retention_days: 30  # Shorter retention
  per_user_isolation: true  # Isolate user data

# Limited capabilities
capabilities:
  - id: "query_status"
    description: "Check order status"
    handler: "handlers.query_status"

  - id: "submit_request"
    description: "Submit support request"
    handler: "handlers.submit_request"
```

### Key Features for Task Agents

1. **Strict Capability Control**
   ```python
   # In capability handler, verify authorization
   async def query_status(message, session):
       principal = session.client_principal

       if not gateway.access_manager.can_access(
           principal.principal_id,
           "query_status"
       ):
           raise UnauthorizedError("Access denied")

       # Proceed with limited scope
       order_id = extract_order_id(message)
       return await lookup_order(order_id)
   ```

2. **User Isolation**
   ```python
   # Queries are scoped to user
   traces = await memory.query_traces(
       filters={
           "metadata.principal_id": session.client_principal_id
       }
   )
   ```

3. **Rate Limiting**
   ```python
   # Built-in rate limiting via ACLs
   acl.set_acl("submit_request", {
       "rate_limit": 10,  # Per minute
       "rate_limit_window": 60
   })
   ```

---

## Configuration

### Environment Variables

```bash
# Required
export ANTHROPIC_API_KEY='your-key'

# Optional
export P3394_AGENT_ID='my-agent'
export P3394_LOG_LEVEL='INFO'
export P3394_STORAGE_PATH='/var/lib/my-agent'

# Channel-specific
export WHATSAPP_PHONE='+1234567890'
export WHATSAPP_API_KEY='wa-key'
```

### Configuration Precedence

1. Environment variables (highest)
2. `agent.yaml` in working directory
3. `~/.p3394/config.yaml` (user defaults)
4. Built-in defaults (lowest)

---

## Extending the SDK

### Custom Capabilities

```python
# src/my_agent/capabilities/weather.py

from p3394_agent.core.capability_registry import Capability

weather_capability = Capability(
    id="weather:current",
    name="Get Current Weather",
    description="Get current weather for a location",
    handler=get_weather,
    input_schema={
        "type": "object",
        "properties": {
            "location": {"type": "string"}
        },
        "required": ["location"]
    }
)

async def get_weather(args, context):
    location = args["location"]
    # Your implementation
    return {"temperature": 72, "condition": "sunny"}
```

Register in gateway:

```python
gateway.capability_registry.register(weather_capability)
```

### Custom Hooks

```python
# src/my_agent/hooks/audit.py

async def audit_hook(input_data, tool_use_id, context):
    """Log all tool usage for compliance."""

    tool_name = input_data.get("tool_name")
    principal = context.get("principal_id")

    logger.info(f"AUDIT: {principal} called {tool_name}")

    return {}  # No modification
```

Register in gateway:

```python
from claude_agent_sdk import HookMatcher

gateway.hooks["PreToolUse"].append(
    HookMatcher(hooks=[audit_hook])
)
```

### Custom Channel Adapter

```python
# src/my_agent/channels/slack.py

from p3394_agent.channels.base import ChannelAdapter

class SlackChannelAdapter(ChannelAdapter):
    def __init__(self, gateway, slack_token):
        super().__init__(gateway, "slack")
        self.slack_token = slack_token

    @property
    def capabilities(self):
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.MARKDOWN],
            supports_markdown=True,
            max_message_size=4000
        )

    def authenticate_client(self, context):
        # Extract Slack user ID
        slack_user = context.get("user_id")
        return self.create_client_assertion(
            channel_identity=f"slack:{slack_user}",
            assurance_level=AssuranceLevel.MEDIUM,
            authentication_method="slack_oauth"
        )

    async def start(self):
        # Connect to Slack RTM or Events API
        pass

    async def send_to_client(self, reply_to, message):
        # Send via Slack API
        pass
```

---

## Deployment

### Docker

```dockerfile
# Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install uv
RUN pip install uv

# Copy project
COPY pyproject.toml .
COPY src/ src/
COPY agent.yaml .
COPY .claude/ .claude/

# Install dependencies
RUN uv sync --frozen

# Run agent
CMD ["uv", "run", "python", "-m", "p3394_agent", "--daemon"]
```

```yaml
# docker-compose.yml
version: '3.8'

services:
  agent:
    build: .
    ports:
      - "8000:8000"
    environment:
      - ANTHROPIC_API_KEY=${ANTHROPIC_API_KEY}
    volumes:
      - agent-memory:/app/memory
    restart: unless-stopped

volumes:
  agent-memory:
```

### Kubernetes

```yaml
# k8s/deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: p3394-agent
spec:
  replicas: 3
  selector:
    matchLabels:
      app: p3394-agent
  template:
    spec:
      containers:
      - name: agent
        image: my-agent:1.0.0
        ports:
        - containerPort: 8000
        env:
        - name: ANTHROPIC_API_KEY
          valueFrom:
            secretKeyRef:
              name: api-keys
              key: anthropic
        volumeMounts:
        - name: memory
          mountPath: /app/memory
      volumes:
      - name: memory
        persistentVolumeClaim:
          claimName: agent-memory
```

### Systemd (Linux)

```ini
# /etc/systemd/system/p3394-agent.service
[Unit]
Description=P3394 Agent
After=network.target

[Service]
Type=simple
User=agent
WorkingDirectory=/opt/my-agent
Environment=ANTHROPIC_API_KEY=xxx
ExecStart=/opt/my-agent/.venv/bin/python -m p3394_agent --daemon
Restart=always

[Install]
WantedBy=multi-user.target
```

---

## Quick Reference

### Companion vs Task Agent

| Aspect | Companion | Task Agent |
|--------|-----------|------------|
| Users | Single owner | Multiple clients |
| Capabilities | All (*) | Limited, role-based |
| Memory | Full access, deep context | Isolated, short retention |
| Channels | CLI, Web, MCP | API, Web |
| LLM Model | Sonnet (smart) | Haiku (fast) |
| Authentication | Implicit (local) | Required (API key/OAuth) |
| Deployment | Local machine | Cloud/server |

### Common Commands

```bash
# Start daemon
uv run python -m p3394_agent --daemon

# Connect as client
uv run python -m p3394_agent

# Start with specific channels
uv run python -m p3394_agent --daemon --web --api

# Export memory
uv run python -m p3394_agent export-memory --output backup.kstar

# Import memory
uv run python -m p3394_agent import-memory --from backup.kstar
```

---

## See Also

- [README.md](../README.md) - Quick start guide
- [CLAUDE.md](../CLAUDE.md) - Full architecture specification
- [MCP_CHANNEL.md](./MCP_CHANNEL.md) - MCP integration
- [CAPABILITY_ACL.md](./CAPABILITY_ACL.md) - Access control
- [P3394-LONG-TERM-MEMORY-SPEC.md](./P3394-LONG-TERM-MEMORY-SPEC.md) - Memory architecture
