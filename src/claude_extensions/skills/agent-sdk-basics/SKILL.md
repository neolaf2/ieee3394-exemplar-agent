---
name: Agent SDK Basics
description: This skill should be used when the user asks to "build an agent", "create an agent with Claude", "set up an agent project", "define agent tools", "agent SDK", "claude-agent-sdk", or needs guidance on getting started with the Claude Agent SDK for Python. Provides project setup with uv, tool definitions, and basic agent patterns.
version: 0.1.0
---

# Claude Agent SDK Basics (Python)

Comprehensive guidance for building agents with the Claude Agent SDK using Python and `uv` package management.

## Overview

The Claude Agent SDK enables building autonomous AI agents that can execute multi-step tasks, use tools, and maintain context across interactions. This skill covers project setup, basic patterns, tool definitions, and common configurations.

## Project Setup with UV

### Initialize a New Agent Project

```bash
# Create and enter project directory
mkdir my-agent && cd my-agent

# Initialize with uv
uv init

# Add the Agent SDK
uv add claude-agent-sdk

# Add common dependencies
uv add python-dotenv
```

### Standard Project Structure (Flat/Simple)

```
my-agent/
├── pyproject.toml
├── uv.lock
├── .env.example
├── .gitignore
├── README.md
└── src/
    └── my_agent/
        ├── __init__.py
        └── main.py
```

### pyproject.toml Example

```toml
[project]
name = "my-agent"
version = "0.1.0"
description = "My Claude Agent"
requires-python = ">=3.11"
dependencies = [
    "claude-agent-sdk>=0.1.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "ruff>=0.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"
```

## Basic Agent Implementation

### Minimal Agent

```python
# src/my_agent/main.py
import os
from dotenv import load_dotenv
from claude_agent_sdk import Agent

load_dotenv()

def main():
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a helpful assistant.",
    )

    response = agent.run("Hello, what can you help me with?")
    print(response.content)

if __name__ == "__main__":
    main()
```

### Agent with Custom Tools

```python
from claude_agent_sdk import Agent, Tool
from typing import Any

# Define a tool
@Tool
def get_weather(location: str) -> dict[str, Any]:
    """Get the current weather for a location.

    Args:
        location: City name or coordinates

    Returns:
        Weather information including temperature and conditions
    """
    # Implementation here
    return {"temperature": 72, "conditions": "sunny", "location": location}

def main():
    agent = Agent(
        model="claude-sonnet-4-20250514",
        system_prompt="You are a weather assistant.",
        tools=[get_weather],
    )

    response = agent.run("What's the weather in San Francisco?")
    print(response.content)
```

## Tool Definition Patterns

### Using the @Tool Decorator

The `@Tool` decorator transforms Python functions into agent tools. Requirements:

1. **Type hints** - All parameters must have type annotations
2. **Docstring** - Must include description, Args section, and Returns section
3. **Return type** - Should return JSON-serializable data

```python
@Tool
def search_database(
    query: str,
    limit: int = 10,
    include_archived: bool = False
) -> list[dict[str, Any]]:
    """Search the database for matching records.

    Args:
        query: Search query string
        limit: Maximum number of results to return
        include_archived: Whether to include archived records

    Returns:
        List of matching records with id, title, and content fields
    """
    # Implementation
    return [{"id": 1, "title": "Result", "content": "..."}]
```

### Tool Categories

**Data Tools** - Read/write data from external sources:
```python
@Tool
def read_file(path: str) -> str:
    """Read contents of a file."""
    with open(path) as f:
        return f.read()
```

**Action Tools** - Perform actions with side effects:
```python
@Tool
def send_email(to: str, subject: str, body: str) -> dict[str, Any]:
    """Send an email message."""
    # Send email
    return {"status": "sent", "message_id": "..."}
```

**Computation Tools** - Perform calculations:
```python
@Tool
def calculate_metrics(data: list[float]) -> dict[str, float]:
    """Calculate statistical metrics for data."""
    return {
        "mean": sum(data) / len(data),
        "min": min(data),
        "max": max(data),
    }
```

## Agent Configuration Options

### Model Selection

```python
# Fast, cost-effective
agent = Agent(model="claude-haiku-3-5-20241022", ...)

# Balanced performance
agent = Agent(model="claude-sonnet-4-20250514", ...)

# Maximum capability
agent = Agent(model="claude-opus-4-20250514", ...)
```

### System Prompt Best Practices

Write clear, structured system prompts:

```python
SYSTEM_PROMPT = """You are a code review assistant specializing in Python.

## Your Role
- Review code for bugs, security issues, and style problems
- Suggest improvements with explanations
- Be constructive and educational

## Guidelines
- Focus on significant issues, not minor style preferences
- Provide code examples for suggested changes
- Explain the reasoning behind recommendations

## Output Format
- Start with a summary
- List issues by severity (critical, warning, info)
- End with positive observations
"""

agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt=SYSTEM_PROMPT,
)
```

### Streaming vs Single Mode

**Single mode** - Wait for complete response:
```python
response = agent.run("Analyze this code...")
print(response.content)
```

**Streaming mode** - Process response incrementally:
```python
for chunk in agent.stream("Write a long document..."):
    print(chunk.content, end="", flush=True)
```

## Environment Setup

### Required Environment Variables

Create `.env.example`:
```
ANTHROPIC_API_KEY=your_api_key_here
```

Create `.gitignore`:
```
.env
.venv/
__pycache__/
*.pyc
.ruff_cache/
```

### Loading Environment Variables

```python
from dotenv import load_dotenv
import os

load_dotenv()

# SDK automatically uses ANTHROPIC_API_KEY
# Or explicitly pass it:
agent = Agent(
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    ...
)
```

## Running the Agent

```bash
# Run with uv
uv run python -m my_agent.main

# Or activate virtual environment
source .venv/bin/activate
python -m my_agent.main
```

## Common Patterns

### Error Handling

```python
from claude_agent_sdk import Agent, AgentError

try:
    response = agent.run("...")
except AgentError as e:
    print(f"Agent error: {e}")
except Exception as e:
    print(f"Unexpected error: {e}")
```

### Context Management

```python
# Create agent with conversation history
agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt="You are a helpful assistant.",
)

# First interaction
response1 = agent.run("My name is Alice.")

# Agent maintains context
response2 = agent.run("What's my name?")  # Knows it's Alice
```

### Permissions Configuration

```python
agent = Agent(
    model="claude-sonnet-4-20250514",
    system_prompt="...",
    permissions={
        "allow_file_read": True,
        "allow_file_write": False,
        "allow_network": True,
    },
)
```

## Quick Reference

| Task | Command/Code |
|------|-------------|
| Create project | `uv init && uv add claude-agent-sdk` |
| Run agent | `uv run python -m my_agent.main` |
| Add dependency | `uv add package-name` |
| Check types | `uv run mypy src/` |
| Run tests | `uv run pytest` |

## Additional Resources

### Reference Files

For detailed patterns and advanced configurations:
- **`references/tool-patterns.md`** - Comprehensive tool definition patterns
- **`references/configuration.md`** - Full configuration options reference

### Example Files

Working examples in `examples/`:
- **`minimal-agent.py`** - Simplest possible agent
- **`agent-with-tools.py`** - Agent with custom tools
- **`streaming-agent.py`** - Streaming response example

## Next Steps

After mastering basics, explore the **agent-sdk-advanced** skill for:
- Multi-agent systems and orchestration
- Domain-driven design with layered architecture
- Property graph integration for agent memory
- MCP server integration
