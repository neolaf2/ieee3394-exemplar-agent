# Agent SDK Configuration Reference

Complete configuration options for the Claude Agent SDK.

## Agent Initialization

### Constructor Parameters

```python
from claude_agent_sdk import Agent

agent = Agent(
    # Required
    model="claude-sonnet-4-20250514",  # Model to use

    # Common options
    system_prompt="...",               # System instructions
    tools=[...],                       # List of tools
    api_key="...",                     # API key (or use env var)

    # Advanced options
    max_tokens=4096,                   # Max response tokens
    temperature=0.7,                   # Sampling temperature
    permissions={...},                 # Permission configuration
    mcp_servers=[...],                 # MCP server configurations
)
```

### Model Options

| Model | Best For | Speed | Cost |
|-------|----------|-------|------|
| `claude-haiku-3-5-20241022` | Simple tasks, high volume | Fastest | Lowest |
| `claude-sonnet-4-20250514` | Balanced performance | Medium | Medium |
| `claude-opus-4-20250514` | Complex reasoning | Slowest | Highest |

## System Prompt Configuration

### Structure Guidelines

```python
SYSTEM_PROMPT = """
# Role Definition
You are a [specific role] that [primary purpose].

## Capabilities
- Capability 1
- Capability 2
- Capability 3

## Guidelines
1. Important guideline
2. Another guideline

## Constraints
- Things to avoid
- Boundaries

## Output Format
[How to structure responses]
"""
```

### Examples by Use Case

**Code Review Agent:**
```python
SYSTEM_PROMPT = """You are a senior code reviewer specializing in Python.

## Focus Areas
- Security vulnerabilities (OWASP Top 10)
- Performance issues
- Code maintainability
- Test coverage gaps

## Review Style
- Be constructive and specific
- Provide code examples for fixes
- Prioritize issues by severity
- Acknowledge good patterns

## Output Format
Start with a summary, then list issues by severity:
1. Critical (security/correctness)
2. Warning (performance/maintainability)
3. Info (style/minor improvements)
"""
```

**Customer Support Agent:**
```python
SYSTEM_PROMPT = """You are a customer support specialist for TechCorp.

## Your Role
Help customers with:
- Product questions
- Troubleshooting
- Account issues
- Billing inquiries

## Tone
- Professional but friendly
- Patient and understanding
- Clear and concise

## Guidelines
- Never share internal information
- Escalate complex issues to humans
- Always verify customer identity for account changes
- Use the customer's name when possible

## When Uncertain
If you cannot help, say: "I'll connect you with a specialist who can better assist."
"""
```

## Permission Configuration

### Permission Options

```python
permissions = {
    # File system
    "allow_file_read": True,      # Read files
    "allow_file_write": False,    # Write/create files
    "allowed_paths": ["/data/*"], # Path restrictions

    # Network
    "allow_network": True,        # Make HTTP requests
    "allowed_domains": [          # Domain whitelist
        "api.example.com",
        "*.internal.corp",
    ],

    # Execution
    "allow_code_execution": False,  # Run code
    "allow_shell": False,           # Shell commands
}

agent = Agent(
    permissions=permissions,
    ...
)
```

### Security Best Practices

1. **Principle of Least Privilege**: Only enable permissions actually needed
2. **Path Restrictions**: Limit file access to specific directories
3. **Domain Whitelisting**: Restrict network access to known APIs
4. **No Shell by Default**: Avoid shell access unless essential

## MCP Server Integration

### Configuration Format

```python
mcp_servers = [
    {
        "name": "database",
        "command": "python",
        "args": ["-m", "mcp_database_server"],
        "env": {
            "DATABASE_URL": "${DATABASE_URL}",
        },
    },
    {
        "name": "api",
        "url": "https://mcp.example.com/api",
        "api_key": "${MCP_API_KEY}",
    },
]

agent = Agent(
    mcp_servers=mcp_servers,
    ...
)
```

### Local MCP Server (stdio)

```python
{
    "name": "local-tools",
    "command": "node",
    "args": ["./mcp-server/index.js"],
    "cwd": "/path/to/server",
    "env": {
        "LOG_LEVEL": "info",
    },
}
```

### Remote MCP Server (SSE)

```python
{
    "name": "remote-service",
    "url": "https://mcp.service.com/sse",
    "headers": {
        "Authorization": "Bearer ${API_TOKEN}",
    },
}
```

## Response Handling

### Single Response Mode

```python
response = agent.run("Your prompt here")

# Access response data
print(response.content)      # Main text content
print(response.tool_calls)   # Tools that were called
print(response.usage)        # Token usage info
```

### Streaming Mode

```python
for chunk in agent.stream("Generate a long report"):
    # Process incremental content
    if chunk.content:
        print(chunk.content, end="", flush=True)

    # Check for tool calls
    if chunk.tool_calls:
        for call in chunk.tool_calls:
            print(f"Called: {call.name}")
```

### Response Object

```python
@dataclass
class AgentResponse:
    content: str                    # Text response
    tool_calls: list[ToolCall]      # Tools invoked
    usage: Usage                    # Token counts
    stop_reason: str                # Why generation stopped
    model: str                      # Model used
```

## Error Handling

### Exception Types

```python
from claude_agent_sdk import (
    AgentError,           # Base exception
    AuthenticationError,  # API key issues
    RateLimitError,       # Rate limit exceeded
    InvalidRequestError,  # Bad request params
    ToolExecutionError,   # Tool failed
)

try:
    response = agent.run("...")
except AuthenticationError:
    print("Check your API key")
except RateLimitError as e:
    print(f"Rate limited. Retry after {e.retry_after}s")
except InvalidRequestError as e:
    print(f"Invalid request: {e.message}")
except ToolExecutionError as e:
    print(f"Tool {e.tool_name} failed: {e.message}")
except AgentError as e:
    print(f"Agent error: {e}")
```

### Retry Configuration

```python
agent = Agent(
    retry_config={
        "max_retries": 3,
        "initial_delay": 1.0,      # seconds
        "max_delay": 60.0,         # seconds
        "exponential_base": 2,     # backoff multiplier
        "retry_on": [              # Error types to retry
            "rate_limit",
            "overloaded",
            "timeout",
        ],
    },
    ...
)
```

## Advanced Configuration

### Timeout Settings

```python
agent = Agent(
    timeout=120,                    # Request timeout (seconds)
    connect_timeout=10,             # Connection timeout
    read_timeout=60,                # Read timeout
    ...
)
```

### Logging

```python
import logging

# Enable SDK logging
logging.getLogger("claude_agent_sdk").setLevel(logging.DEBUG)

# Or configure specific components
logging.getLogger("claude_agent_sdk.tools").setLevel(logging.INFO)
logging.getLogger("claude_agent_sdk.mcp").setLevel(logging.DEBUG)
```

### Custom HTTP Client

```python
import httpx

# Custom client with proxy
custom_client = httpx.Client(
    proxy="http://proxy.corp.com:8080",
    verify="/path/to/ca-bundle.crt",
)

agent = Agent(
    http_client=custom_client,
    ...
)
```

## Environment Variables

### Standard Variables

| Variable | Purpose | Default |
|----------|---------|---------|
| `ANTHROPIC_API_KEY` | API authentication | Required |
| `ANTHROPIC_BASE_URL` | API endpoint | `https://api.anthropic.com` |
| `ANTHROPIC_LOG_LEVEL` | SDK log level | `WARNING` |

### Loading from .env

```python
from dotenv import load_dotenv
import os

# Load .env file
load_dotenv()

# Access variables
api_key = os.getenv("ANTHROPIC_API_KEY")
custom_url = os.getenv("CUSTOM_API_URL")

agent = Agent(
    api_key=api_key,
    base_url=custom_url,
    ...
)
```

## Configuration Patterns

### Development vs Production

```python
import os

ENV = os.getenv("ENVIRONMENT", "development")

if ENV == "production":
    config = {
        "model": "claude-sonnet-4-20250514",
        "max_tokens": 4096,
        "temperature": 0.3,  # More deterministic
        "retry_config": {"max_retries": 5},
    }
else:
    config = {
        "model": "claude-haiku-3-5-20241022",  # Faster for dev
        "max_tokens": 1024,
        "temperature": 0.7,
    }

agent = Agent(**config, system_prompt="...")
```

### Configuration File

```python
# config.yaml
model: claude-sonnet-4-20250514
max_tokens: 4096
permissions:
  allow_file_read: true
  allow_network: true
  allowed_domains:
    - api.example.com

# agent.py
import yaml

with open("config.yaml") as f:
    config = yaml.safe_load(f)

agent = Agent(
    model=config["model"],
    max_tokens=config["max_tokens"],
    permissions=config["permissions"],
    system_prompt="...",
)
```
