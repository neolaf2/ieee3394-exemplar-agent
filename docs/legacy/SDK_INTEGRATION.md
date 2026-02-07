

# Claude Agent SDK Integration

**Branch:** `feature/agent-sdk-refactor`
**Status:** 🚧 In Progress
**Date:** 2026-01-28

## Overview

This branch refactors the IEEE 3394 Exemplar Agent to use the **Claude Agent SDK** instead of direct Anthropic API calls. This provides:

- ✅ Native skill support via `.claude/skills/`
- ✅ Hook system for deterministic processing
- ✅ Custom tools as in-process MCP servers
- ✅ Better integration with Claude Code CLI
- ✅ Improved performance (no subprocess overhead for custom tools)

## Architecture Changes

### Before (master branch)

```
┌─────────────────────────────────────┐
│  Channel Adapters                   │
│  (CLI, Web, P3394, Anthropic API)   │
└───────────┬─────────────────────────┘
            │ UMF Messages
            ↓
┌─────────────────────────────────────┐
│  Gateway                            │
│  • Symbolic command routing         │
│  • Direct Anthropic API calls  ←────┼── Uses anthropic SDK directly
│  • Session management               │
└───────────┬─────────────────────────┘
            │
            ↓
┌─────────────────────────────────────┐
│  KSTAR Memory                       │
└─────────────────────────────────────┘
```

### After (SDK branch)

```
┌─────────────────────────────────────┐
│  Channel Adapters                   │
│  (CLI, Web, P3394, Anthropic API)   │
└───────────┬─────────────────────────┘
            │ UMF Messages
            ↓
┌─────────────────────────────────────┐
│  Gateway (SDK Version)              │
│  • Symbolic command routing         │
│  • ClaudeSDKClient wrapper   ───────┼── Uses Claude Agent SDK
│  • Skill loader                     │
│  • Session management               │
└───────────┬─────────────────────────┘
            │
            ↓
    ┌───────┴────────┐
    │                │
    ↓                ↓
┌─────────┐    ┌────────────┐
│ Hooks   │    │ Custom     │
│ System  │    │ Tools      │
│         │    │ (SDK MCP)  │
│ • KSTAR │    │            │
│ • P3394 │    │ • query_   │
│ • Security│  │   memory   │
│         │    │ • store_   │
│         │    │   trace    │
│         │    │ • list_    │
│         │    │   skills   │
└─────────┘    └────────────┘
            │
            ↓
┌─────────────────────────────────────┐
│  KSTAR Memory                       │
└─────────────────────────────────────┘
            │
            ↓
┌─────────────────────────────────────┐
│  .claude/skills/                    │
│  • p3394-explainer                  │
│  • site-generator                   │
└─────────────────────────────────────┘
```

## Key Components

### 1. Gateway SDK (`core/gateway_sdk.py`)

The refactored gateway wraps `ClaudeSDKClient`:

```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions

class AgentGateway:
    def __init__(self, memory: KStarMemory, working_dir: Path):
        self.memory = memory
        self._sdk_client: Optional[ClaudeSDKClient] = None

        # Load skills from .claude/skills/
        self.skill_loader = SkillLoader(working_dir / ".claude/skills")
        await self.skill_loader.load_all_skills()

    async def _handle_llm(self, message: P3394Message, session: Session):
        """Route to Claude via SDK"""
        if not self._sdk_client:
            options = self.get_sdk_options()
            self._sdk_client = ClaudeSDKClient(options=options)
            await self._sdk_client.connect()

        await self._sdk_client.query(text)

        response_text = ""
        async for msg in self._sdk_client.receive_response():
            for block in msg.content:
                if hasattr(block, 'text'):
                    response_text += block.text

        return P3394Message.text(response_text, ...)
```

**Key Changes:**
- Uses `ClaudeSDKClient` instead of direct `AsyncAnthropic`
- Integrates skill loader for `.claude/skills/` support
- Maintains P3394 message routing architecture
- Preserves symbolic command handling

### 2. SDK Hooks (`plugins/hooks_sdk.py`)

Implements hooks using SDK's `HookMatcher` system:

```python
from claude_agent_sdk import HookMatcher

def create_sdk_hooks(gateway) -> Dict[str, list]:
    async def kstar_pre_tool_hook(input_data, tool_use_id, context):
        """Log tool usage to KSTAR before execution"""
        tool_name = input_data['tool_name']
        await gateway.memory.store_trace({
            "task": {"goal": f"Execute tool: {tool_name}"},
            "action": {"type": tool_name, ...},
            ...
        })
        return {}

    async def security_audit_hook(input_data, tool_use_id, context):
        """Block dangerous commands"""
        if tool_name == 'Bash':
            command = input_data['tool_input']['command']
            if 'rm -rf /' in command:
                return {
                    'hookSpecificOutput': {
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': 'Dangerous command'
                    }
                }
        return {}

    return {
        'PreToolUse': [
            HookMatcher(hooks=[kstar_pre_tool_hook]),
            HookMatcher(matcher='Bash', hooks=[security_audit_hook])
        ],
        'PostToolUse': [
            HookMatcher(hooks=[kstar_post_tool_hook])
        ]
    }
```

**Hook Types:**
- `kstar_pre_tool_hook` - Log actions to KSTAR before execution
- `kstar_post_tool_hook` - Log results after execution
- `security_audit_hook` - Block dangerous bash commands
- `p3394_compliance_hook` - Validate P3394 requirements

### 3. Custom Tools (`plugins/tools_sdk.py`)

SDK MCP servers for P3394-specific tools:

```python
from claude_agent_sdk import tool, create_sdk_mcp_server

@tool(
    name="query_memory",
    description="Query KSTAR memory for past traces",
    input_schema={...}
)
async def query_memory_tool(args):
    domain = args["domain"]
    goal = args["goal"]
    results = await gateway.memory.query(domain, goal)
    return {"content": [{"type": "text", "text": ...}]}

@tool(name="store_trace", ...)
async def store_trace_tool(args):
    trace_id = await gateway.memory.store_trace(args)
    return {"content": [{"type": "text", "text": f"Stored: {trace_id}"}]}

# Create SDK MCP server
server = create_sdk_mcp_server(
    name="p3394_tools",
    version="0.1.0",
    tools=[query_memory_tool, store_trace_tool, list_skills_tool]
)
```

**Benefits over external MCP:**
- No subprocess management
- Better performance (no IPC overhead)
- Easier debugging
- Type safety

### 4. Skill Loader (`core/skill_loader.py`)

Automatically loads skills from `.claude/skills/`:

```python
class SkillLoader:
    async def load_all_skills(self):
        """Scan .claude/skills/ and load SKILL.md files"""
        for skill_dir in self.skills_dir.iterdir():
            skill_file = skill_dir / "SKILL.md"
            skill = await self.load_skill(skill_file)
            self.skills[skill['name']] = skill

    def _parse_frontmatter(self, content: str):
        """Parse YAML frontmatter from SKILL.md"""
        # Extract ---frontmatter---
        # Parse with pyyaml
        # Return (metadata, instructions)
```

**Skill Format:**
```markdown
---
name: p3394-explainer
description: Explain P3394 concepts
triggers:
  - "explain p3394"
  - "what is umf"
---

# Skill Instructions

When users ask about P3394, provide clear explanations...
```

### 5. SDK Options Configuration

```python
def get_sdk_options(self) -> ClaudeAgentOptions:
    from ..plugins.hooks_sdk import create_sdk_hooks
    from ..plugins.tools_sdk import create_sdk_tools

    return ClaudeAgentOptions(
        system_prompt=self._get_system_prompt(),

        # Built-in tools
        allowed_tools=[
            "Read", "Write", "Edit", "Bash", "Glob", "Grep",
            "WebSearch", "WebFetch", "Task",
            # Custom P3394 tools
            "mcp__p3394_tools__query_memory",
            "mcp__p3394_tools__store_trace",
            "mcp__p3394_tools__list_skills",
        ],

        # Hooks for KSTAR logging and security
        hooks=create_sdk_hooks(self),

        # Custom MCP server with P3394 tools
        mcp_servers={
            "p3394_tools": create_sdk_tools(self)
        },

        permission_mode="acceptEdits",
        cwd=self.working_dir,
    )
```

## Skills System

Skills are automatically loaded from `.claude/skills/`:

```
.claude/
└── skills/
    ├── p3394-explainer/
    │   └── SKILL.md
    └── site-generator/
        └── SKILL.md
```

### Skill Lifecycle

1. **Loading** - `SkillLoader` scans `.claude/skills/` on startup
2. **Registration** - Skills registered with gateway, triggers indexed
3. **Triggering** - When user input matches trigger pattern, skill is invoked
4. **Execution** - Skill instructions prepended to Claude's prompt
5. **Response** - Claude follows skill instructions to respond

### Example: Using a Skill

```
User: "Explain what UMF is"

Gateway:
  ↓
Matches trigger "what is umf" → p3394-explainer skill
  ↓
Prepends skill instructions:
  [SKILL: p3394-explainer]

  You are an expert at explaining IEEE P3394...

  User request: Explain what UMF is
  ↓
Routes to Claude via SDK
  ↓
Claude responds following skill instructions
```

## Migration Guide

### For Channel Adapters

Channel adapters don't need major changes - they still:
1. Transform native protocol ↔ UMF
2. Send UMF messages to gateway
3. Receive UMF responses from gateway

The gateway internally uses SDK instead of direct API.

### For Custom Tools

Before (External MCP):
```python
# Start external MCP server process
mcp_servers = {
    "kstar": {
        "type": "stdio",
        "command": "node",
        "args": ["kstar-server.js"]
    }
}
```

After (SDK MCP):
```python
# In-process SDK MCP server
@tool(name="query_memory", ...)
async def query_memory(args):
    return await memory.query(...)

server = create_sdk_mcp_server(
    name="p3394_tools",
    tools=[query_memory, ...]
)

mcp_servers = {"p3394_tools": server}
```

### For Hooks

Before (Not available):
```python
# No hook system in direct API implementation
```

After (SDK Hooks):
```python
async def my_hook(input_data, tool_use_id, context):
    # Pre-process tool calls
    return {}

hooks = {
    'PreToolUse': [HookMatcher(hooks=[my_hook])]
}
```

## Testing

### Test SDK Integration

```bash
# Install dependencies
uv sync

# Run with SDK
uv run ieee3394-agent --daemon

# Test via CLI
uv run ieee3394-cli
>>> /help
>>> explain what P3394 is  # Should trigger p3394-explainer skill
```

### Test Custom Tools

```bash
>>> Ask Claude to "query memory for traces about testing"
# Should invoke mcp__p3394_tools__query_memory
```

### Test Hooks

```bash
>>> Ask Claude to "run: rm -rf /"
# Should be blocked by security_audit_hook
```

## Benefits of SDK Integration

### 1. Native Skills Support
- Drop skills into `.claude/skills/` - automatic loading
- No custom skill routing code needed
- Compatible with Claude Code skill format

### 2. Better Performance
- Custom tools run in-process (no subprocess overhead)
- No JSON serialization for tool calls
- Faster response times

### 3. Improved Developer Experience
- Type-safe tool definitions with `@tool` decorator
- Easier debugging (everything in same process)
- Better error messages

### 4. Extensibility
- Easy to add new hooks
- Simple to create new custom tools
- Skills can be added without code changes

### 5. Standards Compliance
- Uses official Anthropic SDK
- Compatible with Claude Code ecosystem
- Future-proof as SDK evolves

## Current Status

✅ **Completed:**
- Dependencies updated to `claude-agent-sdk`
- Gateway refactored to use `ClaudeSDKClient`
- SDK hooks implemented (KSTAR logging, security)
- Custom tools as SDK MCP servers
- Skill loader with `.claude/skills/` support
- Example skills created (p3394-explainer, site-generator)

🚧 **In Progress:**
- Channel adapter integration testing
- End-to-end testing with skills
- Documentation updates

📋 **Remaining:**
- Update all channel adapters to work with SDK gateway
- Comprehensive test suite
- Performance benchmarks
- Migration guide for master → SDK branch

## How to Use This Branch

```bash
# Switch to SDK branch
git checkout feature/agent-sdk-refactor

# Install dependencies
uv sync

# Run daemon
uv run ieee3394-agent --daemon

# Test in CLI
uv run ieee3394-cli
>>> /listSkills
>>> explain what is UMF
>>> generate the website
```

## Sources

- [Claude Agent SDK for Python](https://github.com/anthropics/claude-agent-sdk-python)
- [Getting started with Anthropic Claude Agent SDK](https://medium.com/@aiablog/getting-started-with-anthropic-claude-agent-sdk-python-826a2216381d)
- [Claude Agent SDK Documentation](https://docs.anthropic.com/en/docs/claude-code/agent-sdk)

## Next Steps

1. Complete channel adapter integration
2. Add comprehensive tests
3. Benchmark performance vs master branch
4. Document migration process
5. Consider merging to master once stable
