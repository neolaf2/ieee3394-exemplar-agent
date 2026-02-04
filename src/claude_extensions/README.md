# Claude Extensions

This directory contains all Claude Code extensions for the Student Companion Agent.
It is symlinked from `.claude/` for IDE compatibility.

## Directory Structure

```
claude_extensions/
├── skills/           # Skill definitions (SKILL.md + resources)
├── agents/           # SubAgent definitions
├── commands/         # Custom slash commands
├── hooks/            # Claude Code hooks (PreToolUse, PostToolUse)
├── capabilities/     # Built-in capability definitions
└── scripts/          # Shared utility scripts
```

## How Symlinks Work

The `.claude/` directory at project root contains symlinks:

```
.claude/
├── skills -> ../src/claude_extensions/skills
├── agents -> ../src/claude_extensions/agents
├── commands -> ../src/claude_extensions/commands
├── capabilities -> ../src/claude_extensions/capabilities
└── settings.json    # (not symlinked - IDE-specific)
```

## Adding New Components

### Skills
Create a new directory in `skills/` with a `SKILL.md` file:
```bash
mkdir skills/my-skill
# Create skills/my-skill/SKILL.md with YAML frontmatter
```

### Agents
Create a markdown file in `agents/`:
```bash
# Create agents/my-agent.md
```

### Commands
Create a markdown file in `commands/`:
```bash
# Create commands/my-command.md
```

### Hooks
Create hook definitions in `hooks/`:
```bash
# Create hooks/my-hook.yaml or hooks/my-hook.md
```

## Benefits of This Structure

1. **Single Source of Truth**: All extensions in `src/`, version-controlled together
2. **IDE Compatibility**: Symlinks make `.claude/` work with Claude Code
3. **Package Distribution**: Extensions can be included in Python package
4. **Testing**: Skills can be tested alongside source code
5. **Cross-Platform**: Works on macOS, Linux, and Windows (with developer mode)
