# SubAgents

This directory contains SubAgent definitions for task delegation.

## Creating a SubAgent

Create a markdown file `<agent-name>.md`:

```markdown
# Agent Name

You are a specialized agent for [purpose].

## Role
[What this agent does]

## Capabilities
- Capability 1
- Capability 2

## Constraints
- Only modify files in [directories]
- Follow [specific guidelines]

## When to Delegate
This agent should be invoked when:
- [trigger condition 1]
- [trigger condition 2]
```

## Example SubAgents

- `documentation-agent.md` - Creates and maintains documentation
- `onboarding-agent.md` - Helps new users get started
- `research-agent.md` - Investigates topics and gathers information
