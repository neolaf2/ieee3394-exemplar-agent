# xAPI Integration for P3394 Agent

## Overview

The IEEE 3394 Exemplar Agent logs all interactions as **xAPI (Experience API)** statements, creating a standardized learning record that can be:

- Stored locally (JSONL files)
- Sent to an MCP agent (xAPI LRS)
- Forwarded to a remote LRS endpoint

## What is xAPI?

xAPI (formerly Tin Can API) is a standard for tracking learning experiences and activities. Each experience is recorded as a "statement" in the format:

**"Actor performed Verb on Object"**

Example: "Alice asked a question about P3394"

## xAPI Statement Structure

```json
{
  "id": "uuid-here",
  "actor": {
    "objectType": "Agent",
    "name": "alice",
    "account": {
      "homePage": "p3394://ieee3394-exemplar",
      "name": "alice"
    }
  },
  "verb": {
    "id": "http://adlnet.gov/expapi/verbs/asked",
    "display": {"en-US": "asked"}
  },
  "object": {
    "objectType": "Activity",
    "id": "p3394://message/msg-123",
    "definition": {
      "type": "http://activitystrea.ms/schema/1.0/message",
      "name": {"en-US": "User Message"},
      "description": {"en-US": "What is P3394?"}
    }
  },
  "timestamp": "2026-01-28T19:30:00Z",
  "context": {
    "contextActivities": {
      "parent": [{
        "objectType": "Activity",
        "id": "p3394://session/abc-123",
        "definition": {
          "type": "http://activitystrea.ms/schema/1.0/conversation",
          "name": {"en-US": "Session abc-123"}
        }
      }]
    },
    "extensions": {
      "http://id.tincanapi.com/extension/p3394-message-id": "msg-123",
      "http://id.tincanapi.com/extension/p3394-message-type": "request"
    }
  }
}
```

## Verbs Used

| Verb | Description | Usage |
|------|-------------|-------|
| `asked` | User asks a question or makes a request | User messages |
| `responded` | Agent provides a response | Agent replies |
| `executed` | Command or action was executed | /help, /status commands |
| `completed` | Activity completed (with or without error) | Session end, error responses |
| `interacted` | General interaction | Default fallback |
| `viewed` | Content was viewed | Future: documentation views |

## Activity Types

| Type | Description |
|------|-------------|
| `message` | General message exchange |
| `command` | Symbolic command (starts with /) |
| `conversation` | Full session/conversation context |
| `agent` | External agent/service interaction |

## Storage Locations

### Local JSONL File (Default)

Each session gets its own xAPI statements file:

```
~/.P3394_agent_ieee3394-exemplar/STM/server/[session_id]/xapi_statements.jsonl
```

Format: One JSON statement per line (JSONL)

### MCP Agent (Optional)

Configure an xAPI LRS MCP server:

```python
storage = AgentStorage(
    agent_name="ieee3394-exemplar",
    enable_xapi=True,
    xapi_mcp_client=mcp_client
)
```

The MCP agent should implement:
- `xapi_store_statement` tool

### Remote LRS (Optional)

Point to a remote Learning Record Store:

```python
lrs_writer = LRSWriter(
    remote_endpoint="https://lrs.example.com/xapi"
)
```

## Usage Examples

### Reading Session History

```python
from ieee3394_agent.core.storage import AgentStorage

storage = AgentStorage()

# Read all xAPI statements for a session
statements = await storage.read_xapi_statements(
    session_id="abc-123",
    limit=100
)

for stmt in statements:
    actor = stmt["actor"]["name"]
    verb = stmt["verb"]["display"]["en-US"]
    obj_name = stmt["object"]["definition"]["name"]["en-US"]
    print(f"{actor} {verb} {obj_name}")
```

Output:
```
alice asked User Message
agent responded Agent Response
alice executed /status
agent responded Agent Response
```

### Analyzing Conversations

```python
# Get all "asked" statements
questions = [
    s for s in statements
    if s["verb"]["id"] == "http://adlnet.gov/expapi/verbs/asked"
]

# Count interactions by type
from collections import Counter
verb_counts = Counter(
    s["verb"]["display"]["en-US"]
    for s in statements
)
print(verb_counts)
# {'asked': 5, 'responded': 5, 'executed': 2}
```

### Querying with JMESPath

```python
import jmespath

# Find all commands executed
commands = jmespath.search(
    "[?object.definition.type=='http://activitystrea.ms/schema/1.0/command'].object.definition.name.\"en-US\"",
    statements
)
print(commands)  # ['/help', '/status', '/about']
```

## Benefits

✅ **Standardized Format**: xAPI is an industry standard (ADL/IEEE)
✅ **Replay Capability**: Reconstruct full conversation from statements
✅ **Analytics Ready**: Query, filter, aggregate interactions
✅ **Learning Analytics**: Track user learning patterns
✅ **Compliance**: Audit trail for regulated environments
✅ **Interoperable**: Export to any xAPI-compliant LRS
✅ **Pluggable Backend**: File, MCP agent, or remote LRS

## P3394 Extensions

We extend xAPI with P3394-specific fields in the `context.extensions`:

```json
"extensions": {
  "http://id.tincanapi.com/extension/p3394-message-id": "msg-123",
  "http://id.tincanapi.com/extension/p3394-message-type": "request",
  "http://id.tincanapi.com/extension/reply-to": "msg-122"
}
```

This preserves P3394 message threading while maintaining xAPI compliance.

## MCP Agent Integration

To use an xAPI LRS as an MCP agent:

### 1. Define MCP Server

```json
{
  "mcpServers": {
    "xapi-lrs": {
      "command": "node",
      "args": ["path/to/xapi-lrs-mcp-server.js"],
      "env": {
        "LRS_ENDPOINT": "https://lrs.example.com",
        "LRS_USERNAME": "username",
        "LRS_PASSWORD": "password"
      }
    }
  }
}
```

### 2. MCP Server Implementation

The MCP server should expose:

**Tool: `xapi_store_statement`**
```json
{
  "name": "xapi_store_statement",
  "description": "Store an xAPI statement in the LRS",
  "inputSchema": {
    "type": "object",
    "properties": {
      "statement": {
        "type": "object",
        "description": "xAPI statement object"
      }
    },
    "required": ["statement"]
  }
}
```

**Tool: `xapi_query_statements`** (optional)
```json
{
  "name": "xapi_query_statements",
  "description": "Query xAPI statements from the LRS",
  "inputSchema": {
    "type": "object",
    "properties": {
      "session_id": {"type": "string"},
      "verb": {"type": "string"},
      "since": {"type": "string"},
      "limit": {"type": "number"}
    }
  }
}
```

### 3. Connect Agent to MCP

```python
# In server.py
from mcp_client import MCPClient

# Connect to xAPI LRS MCP server
xapi_mcp = MCPClient("xapi-lrs")
await xapi_mcp.connect()

# Initialize storage with MCP client
storage = AgentStorage(
    agent_name="ieee3394-exemplar",
    enable_xapi=True,
    xapi_mcp_client=xapi_mcp
)
```

## Session Replay

Reconstruct a full conversation from xAPI statements:

```python
statements = await storage.read_xapi_statements("session-123")

print("=== Session Replay ===")
for stmt in statements:
    timestamp = stmt["timestamp"]
    actor = stmt["actor"]["name"]
    verb = stmt["verb"]["display"]["en-US"]

    if verb == "asked":
        question = stmt["object"]["definition"]["description"]["en-US"]
        print(f"[{timestamp}] {actor}: {question}")
    elif verb == "responded":
        # Would need to store response content in result
        print(f"[{timestamp}] agent: [response]")
```

## Future Enhancements

- **Semantic tagging**: Add topics, entities extracted from messages
- **Sentiment analysis**: Track user satisfaction over time
- **Learning paths**: Identify common question sequences
- **Competency mapping**: Link to skills/knowledge areas
- **Dashboards**: Visual analytics of agent usage
- **A/B testing**: Compare response strategies

## Specification Compliance

- **xAPI Version**: 1.0.3
- **Profile**: Custom P3394 Agent Profile
- **Specification**: https://github.com/adlnet/xAPI-Spec

## Related Standards

- **KSTAR**: Episodic memory (K→S→T→A→R cycle)
- **xAPI**: Experience tracking (Actor-Verb-Object statements)
- **P3394**: Agent communication (UMF messages)

All three work together to create a complete audit trail of agent interactions!
