# xAPI LRS MCP Server Integration

This guide shows how to integrate the IEEE 3394 Agent with an xAPI Learning Record Store (LRS) via MCP.

## Overview

The P3394 Agent can send xAPI statements to an MCP server for:
- **Centralized storage**: Multiple agents sharing one LRS
- **Real-time analytics**: Query statements as they arrive
- **Advanced queries**: SQL, vector search, graph traversals
- **Federation**: Sync with remote LRS instances

## MCP Server Interface

An xAPI LRS MCP server must implement these tools:

### `xapi_store_statement`

Stores an xAPI statement.

```python
{
    "name": "xapi_store_statement",
    "inputSchema": {
        "type": "object",
        "properties": {
            "statement": {
                "type": "object",
                "description": "xAPI 1.0.3 compliant statement"
            }
        },
        "required": ["statement"]
    }
}
```

### `xapi_query_statements` (Optional)

Queries statements from the LRS.

```python
{
    "name": "xapi_query_statements",
    "inputSchema": {
        "type": "object",
        "properties": {
            "session_id": {"type": "string"},
            "agent": {"type": "string"},
            "verb": {"type": "string"},
            "since": {"type": "string"},
            "limit": {"type": "number", "default": 100}
        }
    }
}
```

## Agent Configuration

### 1. Initialize with MCP Client

```python
from ieee3394_agent.core.storage import AgentStorage

# Create storage with MCP client
storage = AgentStorage(
    agent_name="ieee3394-exemplar",
    enable_xapi=True,
    xapi_mcp_client=your_mcp_client  # Your MCP client instance
)
```

### 2. Statements Automatically Forwarded

All P3394 messages are automatically logged to the MCP LRS:

```python
# In server.py, this happens automatically:
await storage.log_xapi_statement(
    session_id=session_id,
    message=incoming_message
)

# Statement is sent to:
# 1. Local JSONL file (backup)
# 2. MCP server (if configured)
# 3. Remote LRS (if configured)
```

## Multiple Backends

The xAPI integration supports multiple backends simultaneously:

```python
from ieee3394_agent.core.xapi import LRSWriter

# Local + MCP + Remote
lrs = LRSWriter(
    storage_path="./xapi_statements.jsonl",  # Local backup
    mcp_client=mcp_client,                   # MCP server
    remote_endpoint="https://lrs.example.com/xapi"  # Remote LRS
)

# Writes to all three
await lrs.write_statement(statement)
```

## Example MCP Server Tools

Here's how an MCP server would implement the xAPI tools:

```python
# In your MCP server implementation

@mcp_server.tool("xapi_store_statement")
async def store_statement(statement: dict) -> dict:
    """Store xAPI statement in database"""

    # Extract fields for indexing
    stmt_id = statement.get("id", str(uuid4()))
    actor = statement.get("actor", {}).get("name", "unknown")
    verb = statement.get("verb", {}).get("id", "unknown")
    timestamp = statement.get("timestamp", datetime.utcnow().isoformat())

    # Extract session ID from context
    session_id = None
    context = statement.get("context", {})
    parent = context.get("contextActivities", {}).get("parent", [{}])[0]
    if parent.get("id"):
        match = re.search(r"session/([^/]+)", parent["id"])
        if match:
            session_id = match.group(1)

    # Store in database (SQLite, PostgreSQL, MongoDB, etc.)
    await db.insert_statement(
        id=stmt_id,
        statement=statement,
        actor=actor,
        verb=verb,
        timestamp=timestamp,
        session_id=session_id
    )

    return {
        "statement_id": stmt_id,
        "stored": True
    }


@mcp_server.tool("xapi_query_statements")
async def query_statements(
    session_id: str = None,
    agent: str = None,
    verb: str = None,
    since: str = None,
    limit: int = 100
) -> dict:
    """Query xAPI statements"""

    # Build query
    query = {"limit": limit}
    if session_id:
        query["session_id"] = session_id
    if agent:
        query["actor"] = agent
    if verb:
        query["verb"] = verb
    if since:
        query["since"] = since

    # Execute query
    results = await db.query_statements(query)

    return {
        "statements": results,
        "count": len(results)
    }
```

## Testing the Integration

### 1. Start Agent with MCP LRS

```bash
# Terminal 1: Start your xAPI LRS MCP server
./xapi_lrs_server

# Terminal 2: Start agent daemon (uses MCP automatically)
uv run ieee3394-agent --daemon
```

### 2. Send Messages

```python
from ieee3394_agent.client import AgentClient
import asyncio

async def test():
    client = AgentClient()
    await client.connect()

    # Send messages - automatically logged to MCP LRS
    await client.send_message("/help")
    await client.send_message("What is P3394?")

    await client.disconnect()

asyncio.run(test())
```

### 3. Query MCP LRS

```python
import asyncio

async def query_lrs():
    # Query the MCP server directly
    mcp = your_mcp_client
    result = await mcp.call_tool("xapi_query_statements", {
        "limit": 10
    })

    statements = result["statements"]
    print(f"Found {len(statements)} statements")

    for stmt in statements:
        actor = stmt["actor"]["name"]
        verb = stmt["verb"]["display"]["en-US"]
        obj = stmt["object"]["definition"]["name"]["en-US"]
        print(f"  {actor} {verb} {obj}")

asyncio.run(query_lrs())
```

## Benefits

✅ **Centralized Analytics**: All agents log to one LRS
✅ **Standards Compliant**: Full xAPI 1.0.3 compatibility
✅ **Pluggable**: Local file, MCP, or remote LRS
✅ **Real-time**: Stream statements as they happen
✅ **Audit Trail**: Complete interaction history
✅ **Interoperable**: Works with any xAPI tool

## Example MCP Server Projects

Reference implementations:
- **@anthropic/kstar-memory-server**: KSTAR memory with xAPI support
- **learning-locker**: Open-source LRS (can add MCP adapter)
- **Watershed LRS**: Commercial LRS with API

## Advanced: Vector Search

Add semantic search over xAPI statements:

```python
# In your MCP server
import openai

@mcp_server.tool("xapi_semantic_search")
async def semantic_search(query: str, limit: int = 10):
    """Search statements by semantic similarity"""

    # Generate embedding for query
    query_embedding = openai.Embedding.create(
        input=query,
        model="text-embedding-3-small"
    )["data"][0]["embedding"]

    # Vector similarity search
    results = await db.vector_search(
        embedding=query_embedding,
        limit=limit
    )

    return {"statements": results}
```

## Next Steps

- Implement pre-built analytics dashboards
- Add real-time WebSocket streaming
- Create learning path analysis tools
- Integrate with LMS platforms

---

For complete xAPI specification: https://github.com/adlnet/xAPI-Spec
