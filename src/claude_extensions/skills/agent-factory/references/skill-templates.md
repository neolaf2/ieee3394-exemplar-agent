# Skill Templates for Agent Factory

Reference templates for common skill patterns.

## Basic Skill Template

```markdown
---
name: my-skill
description: Brief description of what this skill does
version: 1.0.0
triggers:
  - "trigger phrase one"
  - "trigger phrase two"
---

# My Skill

## Overview

Brief explanation of the skill's purpose.

## When to Use

- Scenario 1
- Scenario 2

## Instructions

1. Step one
2. Step two
3. Step three

## Examples

### Example 1: Basic Usage

Input: "trigger phrase one with some context"
Output: Expected result

### Example 2: Advanced Usage

Input: "complex request"
Output: Expected result
```

## Echo Skill (Simplest)

```markdown
---
name: echo
description: Echo back user input for testing
triggers:
  - "echo"
---

# Echo

Repeat the user's message back to them.

When triggered with "echo <message>", respond with:

"Echo: <message>"
```

## Help Skill (Navigation)

```markdown
---
name: help
description: Provide contextual help and documentation
triggers:
  - "help"
  - "what can you do"
---

# Help

Provide assistance to users.

## Commands

List available symbolic commands:
- /help - This help message
- /about - About this agent
- /status - Agent status
- /version - Version info

## Capabilities

Describe what the agent can do:
- Natural language conversation
- Code assistance
- Documentation generation
- etc.
```

## Domain Expert Skill

```markdown
---
name: domain-expert
description: Expert knowledge in specific domain
triggers:
  - "explain <domain>"
  - "how does <domain> work"
---

# Domain Expert

Provide expert-level guidance on <domain>.

## Knowledge Base

### Concept 1
Definition and explanation.

### Concept 2
Definition and explanation.

## Common Questions

### Q: Frequently asked question?
A: Detailed answer.

## Best Practices

1. Practice one
2. Practice two
3. Practice three
```

## Task Automation Skill

```markdown
---
name: task-automation
description: Automate repetitive tasks
triggers:
  - "automate"
  - "run task"
---

# Task Automation

Automate common workflows.

## Available Tasks

### Task 1: Description
Triggers: "run task one"
Steps:
1. Do this
2. Do that
3. Return result

### Task 2: Description
Triggers: "run task two"
Steps:
1. Check prerequisites
2. Execute action
3. Verify result

## Configuration

Tasks can be configured via parameters:
- param1: Description (default: value)
- param2: Description (default: value)
```

## Integration Skill

```markdown
---
name: integration
description: Integrate with external services
triggers:
  - "connect to <service>"
  - "fetch from <service>"
---

# Integration

Connect with external services.

## Supported Services

### Service 1
- Authentication: API key
- Endpoints: list endpoints
- Usage: describe how to use

### Service 2
- Authentication: OAuth
- Endpoints: list endpoints
- Usage: describe how to use

## Configuration

Required environment variables:
- SERVICE_API_KEY: API key for service
- SERVICE_URL: Base URL (optional)

## Error Handling

Common errors and how to resolve:
- Error 1: Solution
- Error 2: Solution
```

## Generator Skill

```markdown
---
name: generator
description: Generate content or code
triggers:
  - "generate <type>"
  - "create <type>"
---

# Generator

Generate various types of content.

## Supported Types

### Type 1
Template:
```
<template content>
```

Customization options:
- option1: Description
- option2: Description

### Type 2
Template:
```
<template content>
```

## Usage

To generate Type 1:
1. Gather requirements
2. Apply template
3. Customize as needed
4. Return result
```

## Skill with Scripts

```markdown
---
name: script-skill
description: Skill that uses helper scripts
triggers:
  - "process <thing>"
---

# Script Skill

Process data using helper scripts.

## Scripts

### process.py
Located at: scripts/process.py
Purpose: Process input data
Usage: python scripts/process.py <input>

### validate.sh
Located at: scripts/validate.sh
Purpose: Validate results
Usage: bash scripts/validate.sh <file>

## Workflow

1. Validate input
2. Run process.py with input
3. Validate output
4. Return results
```

## Skill with References

```markdown
---
name: reference-skill
description: Skill with external reference documents
triggers:
  - "look up <topic>"
---

# Reference Skill

Provide information from reference documents.

## Reference Documents

### API Reference
File: references/api.md
Contains: API documentation
Search patterns: "endpoint", "method", "response"

### Schema Reference
File: references/schema.md
Contains: Data model definitions
Search patterns: "table", "field", "type"

## Lookup Process

1. Identify topic from user request
2. Search relevant reference file
3. Extract pertinent information
4. Format and present to user
```
