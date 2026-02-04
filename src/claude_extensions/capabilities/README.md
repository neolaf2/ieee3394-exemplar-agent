# Capabilities

This directory contains capability definitions for the Student Companion Agent.

## What are Capabilities?

Capabilities define what the agent can do. They serve as:
- **Documentation**: Human-readable description of agent abilities
- **Discovery**: Allow other agents to discover what this agent can do
- **Routing**: Help the gateway route requests to appropriate handlers

## Capability Types

### Symbolic Capabilities
Fast, deterministic operations without LLM involvement:
- `/help` - Show help information
- `/about` - About the agent
- `/status` - Agent status
- `/version` - Version information

### LLM Capabilities
Natural language operations routed through Claude:
- Answer questions
- Generate content
- Explain concepts
- Provide tutoring

### Skill-Based Capabilities
Triggered by specific patterns:
- Study planning
- Concept explanation
- Quiz generation
- Homework assistance

## Defining Capabilities

### YAML Format

```yaml
# capabilities/tutoring.yaml
capability:
  name: tutoring
  description: Interactive tutoring for academic subjects
  version: "1.0"

  triggers:
    - "help me understand"
    - "explain"
    - "teach me"

  parameters:
    - name: subject
      type: string
      required: true
      description: Academic subject area
    - name: level
      type: string
      enum: ["beginner", "intermediate", "advanced"]
      default: "intermediate"

  examples:
    - input: "Help me understand calculus derivatives"
      output: "Explanation with examples and practice problems"
```

## Built-in Capabilities

See `builtin/` directory for pre-installed capabilities:
- `list_capabilities.yaml` - Lists all available capabilities

## Directory Structure

```
capabilities/
├── README.md                # This file
├── builtin/                 # Pre-installed capabilities
│   └── list_capabilities.yaml
└── custom/                  # User-defined capabilities
    └── tutoring.yaml
```
