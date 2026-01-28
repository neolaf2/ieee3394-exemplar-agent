# Agent Storage Architecture

## Overview

The IEEE 3394 Exemplar Agent uses a structured directory hierarchy that separates Short-Term Memory (STM) for transient sessions from Long-Term Memory (LTM) for persistent capabilities.

## Directory Structure

```
~/.P3394_agent_ieee3394-exemplar/
├── STM/                          # Short-Term Memory (sessions)
│   ├── server/                   # Server sessions (inbound)
│   │   └── [session_id]/
│   │       ├── trace.jsonl      # Session traces (KSTAR)
│   │       ├── context.json     # Session context
│   │       └── files/           # Session files
│   └── client/                   # Client sessions (outbound)
│       └── [session_id]/
│           ├── requests.jsonl   # Outbound requests
│           └── responses.jsonl  # Received responses
├── LTM/                          # Long-Term Memory (persistent)
│   ├── server/                   # Server capabilities
│   │   ├── plugins/             # Server plugins
│   │   ├── skills/              # Server skills (.md)
│   │   ├── agents/              # SubAgents (.md)
│   │   ├── channels/            # Channel adapter templates
│   │   ├── manifest.json        # Agent manifest (P3394)
│   │   ├── config.json          # Server configuration
│   │   └── allowlist.json       # Allowed operations/tools
│   └── client/                   # Client capabilities
│       ├── credentials/         # API keys, tokens (mode 700)
│       │   ├── anthropic.key
│       │   └── mcp_servers.json
│       ├── tools/               # Tool configurations
│       ├── agents/              # Known external agents
│       │   └── registry.json    # Agent registry
│       └── config.json          # Client configuration
└── logs/                         # Application logs
    ├── server.log               # Server logs
    ├── client.log               # Client logs
    └── audit.log                # Security audit log
```

## Short-Term Memory (STM)

### Server Sessions (Inbound)

When a client connects, the server creates a session directory under `STM/server/[session_id]/`:

- **trace.jsonl**: KSTAR traces for the session (JSONL format, one trace per line)
- **context.json**: Session metadata (client_id, created_at, etc.)
- **files/**: Any files uploaded or generated during the session

### Client Sessions (Outbound)

When the agent connects to external agents (like LLM providers or MCP servers), it creates a client session:

- **requests.jsonl**: Log of all outbound requests
- **responses.jsonl**: Log of all received responses
- **context.json**: Target agent info, created_at, etc.

### Cleanup

Old STM sessions are automatically cleaned up after 7 days (configurable).

## Long-Term Memory (LTM)

### Server LTM

Persistent server capabilities:

- **plugins/**: Server plugins (Python modules)
- **skills/**: Agent skills (Markdown format, compatible with Claude Code)
- **agents/**: SubAgent definitions (Markdown format)
- **channels/**: Channel adapter templates
- **manifest.json**: P3394 agent manifest
  ```json
  {
    "agent_id": "ieee3394-exemplar",
    "version": "0.1.0",
    "standard": "IEEE P3394",
    "capabilities": {
      "channels": ["cli", "unix-socket"],
      "message_formats": ["P3394-UMF"]
    }
  }
  ```
- **config.json**: Server configuration
  ```json
  {
    "session_ttl_hours": 24,
    "max_concurrent_sessions": 100,
    "kstar_enabled": true
  }
  ```
- **allowlist.json**: Security allowlist
  ```json
  {
    "allowed_tools": ["Read", "Write", "Edit"],
    "blocked_operations": ["rm -rf /"]
  }
  ```

### Client LTM

Persistent client capabilities:

- **credentials/**: API keys and tokens (mode 600, encrypted in production)
- **tools/**: Tool configurations and settings
- **agents/registry.json**: Known external agents
  ```json
  {
    "known_agents": [
      {
        "agent_id": "claude-api",
        "uri": "https://api.anthropic.com",
        "last_seen": "2026-01-28T19:30:00Z"
      }
    ]
  }
  ```
- **config.json**: Client configuration

## Usage

### Initialization

The storage system is automatically initialized when the agent starts:

```python
from ieee3394_agent.core.storage import AgentStorage

storage = AgentStorage(agent_name="ieee3394-exemplar")
# Creates directory structure at ~/.P3394_agent_ieee3394-exemplar/
```

### Server Session Management

```python
# Create session directory
session_dir = storage.create_server_session(session_id)

# Append trace
storage.append_trace(session_id, trace_data)

# Read session traces
traces = storage.read_session_traces(session_id)

# Cleanup old sessions
storage.cleanup_old_sessions(days=7)
```

### Client Session Management

```python
# Create client session for outbound requests
session_dir = storage.create_client_session(session_id, "claude-api")

# Log request
storage.append_client_request(session_id, request_data)

# Log response
storage.append_client_response(session_id, response_data)
```

### Configuration Management

```python
# Server config
config = storage.get_server_config()
storage.update_server_config({"session_ttl_hours": 48})

# Manifest
manifest = storage.get_manifest()

# Skills and subagents
skills = storage.list_skills()
agents = storage.list_subagents()
```

### Credential Management

```python
# Store credential (encrypted, mode 600)
storage.store_credential("anthropic", api_key)

# Retrieve credential
api_key = storage.get_credential("anthropic")
```

### Agent Registry

```python
# Register external agent
storage.register_external_agent({
    "agent_id": "claude-api",
    "uri": "https://api.anthropic.com",
    "capabilities": ["chat", "streaming"]
})
```

## Security Considerations

1. **Credentials Directory**: Mode 700 (only owner can access)
2. **Individual Credentials**: Mode 600 (only owner can read/write)
3. **In Production**: Credentials should be encrypted at rest
4. **Audit Log**: All security-sensitive operations logged to `audit.log`

## Benefits

✅ **Organized**: Clear separation of STM vs LTM
✅ **P3394 Compliant**: Follows agent architecture best practices
✅ **Debuggable**: All traces persisted to disk
✅ **Secure**: Proper file permissions on sensitive data
✅ **Extensible**: Easy to add new LTM capabilities
✅ **Multi-Agent**: Client sessions track outbound interactions

## Future Enhancements

- Encrypted credentials at rest
- Compression for old STM sessions
- Database backend option (SQLite)
- Replication for distributed agents
- Vector embeddings for semantic search
