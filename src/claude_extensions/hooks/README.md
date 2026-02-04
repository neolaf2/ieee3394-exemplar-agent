# Hooks

This directory contains Claude Code hook definitions for the Student Companion Agent.

## What are Hooks?

Hooks are scripts that execute automatically at specific points in Claude Code's lifecycle:
- **PreToolUse**: Runs before a tool is executed (can block or modify)
- **PostToolUse**: Runs after a tool completes (for logging, notifications)
- **Notification**: Runs when Claude sends a notification
- **Stop**: Runs when Claude stops processing

## Creating a Hook

### YAML Format

Create a YAML file with hook configuration:

```yaml
# hooks/security-audit.yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      command: "python scripts/audit_command.py"
      timeout: 5000

  PostToolUse:
    - matcher: "*"
      command: "python scripts/log_tool_use.py"
```

### Hook Properties

| Property | Description |
|----------|-------------|
| `matcher` | Tool name to match (`*` for all, or specific tool name) |
| `command` | Shell command to execute |
| `timeout` | Maximum execution time in milliseconds |
| `input` | How to pass input (`stdin`, `args`) |

### Hook Input/Output

Hooks receive JSON on stdin with:
```json
{
  "hook_type": "PreToolUse",
  "tool_name": "Bash",
  "tool_input": { "command": "ls -la" },
  "session_id": "abc123"
}
```

For PreToolUse, hooks can output:
```json
{
  "decision": "allow",  // or "block"
  "reason": "Optional explanation",
  "modified_input": {}  // Optional modified tool input
}
```

## Built-in Hook Ideas

### KSTAR Logging Hook
Log all tool uses to KSTAR memory for learning:
```yaml
hooks:
  PostToolUse:
    - matcher: "*"
      command: "python -m p3394_agent.plugins.hooks kstar_log"
```

### Security Audit Hook
Block dangerous commands:
```yaml
hooks:
  PreToolUse:
    - matcher: "Bash"
      command: "python -m p3394_agent.plugins.hooks security_check"
```

### P3394 Compliance Hook
Ensure all operations conform to P3394 standards:
```yaml
hooks:
  PreToolUse:
    - matcher: "*"
      command: "python -m p3394_agent.plugins.hooks p3394_validate"
```

## Directory Structure

```
hooks/
├── README.md           # This file
├── security-audit.yaml # Security-related hooks
├── kstar-logging.yaml  # KSTAR memory integration
└── scripts/           # Hook implementation scripts
    ├── audit.py
    └── log_trace.py
```

## Notes

- Hooks run synchronously and can slow down operations if slow
- Keep hook scripts fast (under 1 second)
- Use PostToolUse for logging (non-blocking)
- Use PreToolUse sparingly for security checks only
