# P3394 Agent SDK Usage Guide

Quick reference for using the `p3394_agent` SDK. For architecture patterns and deployment, see [SDK_DEVELOPER_GUIDE.md](./SDK_DEVELOPER_GUIDE.md).

## Installation

```bash
pip install git+https://github.com/ieee3394/p3394-agent-starter.git
```

Or add to `pyproject.toml`:

```toml
dependencies = [
    "p3394-agent-starter @ git+https://github.com/ieee3394/p3394-agent-starter.git",
]
```

## Quick Examples

### 1. Working with Messages (UMF)

The Universal Message Format is the core of P3394. All agent communication uses these types.

```python
from p3394_agent import (
    P3394Message,
    P3394Content,
    P3394Address,
    MessageType,
    ContentType,
)

# Create a simple text message
msg = P3394Message.text("Hello, agent!")

# Create a message with metadata
msg = P3394Message(
    type=MessageType.REQUEST,
    session_id="session-123",
    content=[
        P3394Content(type=ContentType.TEXT, data="What is P3394?"),
        P3394Content(
            type=ContentType.JSON,
            data={"context": "developer-docs"},
            metadata={"priority": "high"}
        ),
    ],
)

# Serialize to dict (for JSON APIs)
data = msg.to_dict()

# Deserialize from dict
msg2 = P3394Message.from_dict(data)

# Extract text content
text = msg.extract_text()  # "What is P3394?"

# Work with addresses
addr = P3394Address(
    agent_id="my-agent",
    channel_id="cli",
    session_id="abc123"
)
uri = addr.to_uri()  # "p3394://my-agent/cli?session=abc123"
addr2 = P3394Address.from_uri(uri)
```

### 2. Connecting as a Client

```python
import asyncio
from p3394_agent import AgentClient

async def main():
    # Connect to a running agent daemon
    client = AgentClient(socket_path="/tmp/ieee3394-agent.sock")

    if await client.connect():
        # Send a message and get response
        response = await client.send_message("/help")
        print(response.extract_text())

        # Send another message
        response = await client.send_message("Explain P3394 UMF")
        print(response.extract_text())

        await client.disconnect()

asyncio.run(main())
```

### 3. Defining Capabilities

Capabilities are the unified abstraction for all agent functionality.

```python
from p3394_agent import (
    AgentCapabilityDescriptor,
    CapabilityKind,
    ExecutionSubstrate,
    CapabilityExecution,
    CapabilityInvocation,
    CapabilityExposure,
    CapabilityPermissions,
    InvocationMode,
    ExposureScope,
)

# Define a symbolic command capability
help_capability = AgentCapabilityDescriptor(
    capability_id="cmd:help",
    name="Help Command",
    version="1.0.0",
    description="Display available commands and usage",
    kind=CapabilityKind.ATOMIC,
    execution=CapabilityExecution(
        substrate=ExecutionSubstrate.SYMBOLIC,
        entrypoint="gateway._cmd_help"
    ),
    invocation=CapabilityInvocation(
        modes=[InvocationMode.COMMAND],
        command_aliases=["/help", "/?", "/commands"]
    ),
    exposure=CapabilityExposure(
        scope=ExposureScope.PUBLIC,
        channels=["cli", "web", "api"]
    ),
    permissions=CapabilityPermissions(
        danger_level="low"
    )
)

# Define an LLM-powered capability
explain_capability = AgentCapabilityDescriptor(
    capability_id="skill:explain-p3394",
    name="Explain P3394",
    version="1.0.0",
    description="Explain P3394 concepts with examples",
    kind=CapabilityKind.ATOMIC,
    execution=CapabilityExecution(
        substrate=ExecutionSubstrate.LLM,
        runtime="claude-sonnet-4"
    ),
    invocation=CapabilityInvocation(
        modes=[InvocationMode.MESSAGE],
        message_triggers=["explain p3394", "what is umf", "how do channels work"]
    ),
    exposure=CapabilityExposure(scope=ExposureScope.PUBLIC),
    permissions=CapabilityPermissions()
)

# Serialize to JSON
json_str = help_capability.to_json()

# Deserialize from dict
cap = AgentCapabilityDescriptor.from_dict({
    "capability_id": "cmd:status",
    "name": "Status",
    "version": "1.0.0",
    "description": "Show agent status",
    "kind": "atomic",
    "execution": {"substrate": "symbolic"},
    "invocation": {"modes": ["command"]},
    "exposure": {"scope": "public"},
    "permissions": {}
})
```

### 4. Working with Sessions

```python
from p3394_agent import Session, SessionManager, ChannelRole
from datetime import timedelta

# Create a session manager
manager = SessionManager(default_ttl=timedelta(hours=24))

# Create a session
session = await manager.create_session(
    client_id="user-123",
    channel_id="cli"
)

# Access session properties
print(f"Session ID: {session.id}")
print(f"Authenticated: {session.is_authenticated}")
print(f"Role: {session.client_role}")

# Check permissions
if session.can_execute_capability("cmd:admin"):
    # Allowed
    pass

# Get session later
session = manager.get_session(session.id)

# Validate channel access (for multi-channel sessions)
result = manager.validate_channel_access(
    session_id=session.id,
    channel_id="web",
    channel_type="http",
    is_write_operation=True
)

if result.allowed:
    print(f"Access granted with role: {result.role}")
else:
    print(f"Access denied: {result.error_message}")
```

### 5. Using KSTAR Memory

```python
from p3394_agent import KStarMemory

# Initialize memory
memory = KStarMemory()

# Store a trace (episodic memory)
trace_id = await memory.store_trace({
    "situation": {
        "domain": "customer_support",
        "actor": "user-123",
        "now": "2026-02-05T10:00:00Z"
    },
    "task": {
        "goal": "Answer product question"
    },
    "action": {
        "type": "respond",
        "parameters": {"topic": "pricing"}
    },
    "result": {
        "success": True,
        "outcome": "Question answered"
    },
    "session_id": "session-abc"
})

# Store a perception (declarative memory)
perception_id = await memory.store_perception({
    "content": "User prefers concise responses",
    "context": {"domain": "preferences"},
    "tags": ["user-pref", "communication-style"],
    "importance": 0.8
})

# Store a skill (procedural memory)
skill_id = await memory.store_skill({
    "name": "product-lookup",
    "description": "Look up product information",
    "domain": "catalog"
})

# Query memory
result = await memory.query(domain="customer_support", goal="pricing")
skills = await memory.find_skills(domain="catalog", goal="lookup")

# Get stats
stats = await memory.get_stats()
print(f"Traces: {stats['trace_count']}")
print(f"Skills: {stats['skill_count']}")
```

### 6. Creating a Channel Adapter

```python
from p3394_agent import (
    ChannelAdapter,
    ChannelCapabilities,
    P3394Message,
    ContentType,
)
from typing import Dict, Any

class MyChannelAdapter(ChannelAdapter):
    """Custom channel adapter example."""

    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.MARKDOWN],
            supports_markdown=True,
            max_message_size=4000,
            supports_slash_commands=True
        )

    def authenticate_client(self, context: Dict[str, Any]):
        # Extract identity from your channel
        user_id = context.get("user_id")
        return self.create_client_assertion(
            channel_identity=f"mychannel:{user_id}",
            assurance_level="medium",
            authentication_method="oauth"
        )

    async def start(self):
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)
        # Start your channel's event loop

    async def stop(self):
        self.is_active = False

    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        # Adapt content to your channel's capabilities
        adapted = self.adapt_content(message)

        # Send via your channel's API
        text = adapted.extract_text()
        # your_api.send(reply_to["client_id"], text)
```

## Type Reference

### Core Message Types

| Type | Description |
|------|-------------|
| `P3394Message` | Main message container with content blocks |
| `P3394Content` | Individual content block (text, JSON, etc.) |
| `P3394Address` | Agent addressing: `p3394://agent/channel?session=id` |
| `MessageType` | Enum: REQUEST, RESPONSE, NOTIFICATION, ERROR |
| `ContentType` | Enum: TEXT, JSON, MARKDOWN, HTML, IMAGE, etc. |

### Capability Types

| Type | Description |
|------|-------------|
| `AgentCapabilityDescriptor` | Full capability definition |
| `CapabilityKind` | Enum: ATOMIC, COMPOSITE, PROXY, TEMPLATE |
| `ExecutionSubstrate` | Enum: SYMBOLIC, LLM, SHELL, AGENT |
| `InvocationMode` | Enum: DIRECT, COMMAND, MESSAGE, EVENT |
| `ExposureScope` | Enum: INTERNAL, AGENT, CHANNEL, HUMAN, PUBLIC |

### Session Types

| Type | Description |
|------|-------------|
| `Session` | Client session with auth state and permissions |
| `SessionManager` | Manages session lifecycle |
| `ChannelRole` | Enum: PRIMARY, OBSERVER, COLLABORATIVE |
| `ChannelBinding` | Connects a channel to a session |

### Memory Types

| Type | Description |
|------|-------------|
| `KStarMemory` | Main memory store for traces, perceptions, skills |
| `ControlToken` | Authority token for actions |
| `TokenType` | Enum: API_KEY, CREDENTIAL, PERMISSION, etc. |

## Best Practices

1. **Always use `P3394Message.text()` for simple messages** - it handles content wrapping
2. **Serialize with `to_dict()` for JSON APIs** - don't access internal fields directly
3. **Check session permissions before capability execution** - use `session.can_execute_capability()`
4. **Adapt content for channels** - call `self.adapt_content(message)` before sending
5. **Use type hints** - the SDK is fully typed for mypy compatibility

## See Also

- [SDK Developer Guide](./SDK_DEVELOPER_GUIDE.md) - Architecture patterns, deployment
- [Capability ACL](./CAPABILITY_ACL.md) - Access control configuration
- [MCP Channel](./MCP_CHANNEL.md) - Agent-to-agent communication
- [Memory Spec](./P3394-LONG-TERM-MEMORY-SPEC.md) - KSTAR memory architecture
