# Custom Commands

This directory contains custom slash command definitions.

## Creating a Command

Create a markdown file `<command-name>.md`:

```markdown
---
name: command-name
description: What the command does
aliases:
  - /alias1
  - /alias2
---

# Command Name

## Usage
`/command-name [arguments]`

## Description
[What this command does and when to use it]

## Arguments
- `arg1` - Description
- `arg2` - Description (optional)

## Examples
```
/command-name arg1
/command-name arg1 arg2
```

## Implementation
[Instructions for how to execute this command]
```

## Built-in Commands

The agent framework provides these built-in commands:
- `/help` - Show help
- `/about` - About the agent
- `/status` - Agent status
- `/version` - Version info
