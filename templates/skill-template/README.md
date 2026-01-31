# Skill Template

Use this template to create new skills for your P3394 agent.

## Quick Start

1. **Copy the template:**
   ```bash
   cp -r templates/skill-template .claude/skills/my-skill
   ```

2. **Rename SKILL.md placeholders:**
   - `{{SKILL_NAME}}` - Your skill's name (e.g., "calculator")
   - `{{SKILL_DESCRIPTION}}` - Brief description
   - `{{TRIGGER_1}}`, `{{TRIGGER_2}}` - Trigger phrases

3. **Customize the skill:**
   - Update the instructions section
   - Add examples
   - Define error handling

4. **Test your skill:**
   - Restart your agent
   - Use one of your trigger phrases
   - Verify the response

## Template Structure

```
skill-template/
├── SKILL.md      # Main skill definition (required)
└── README.md     # This file (optional)
```

## SKILL.md Format

### YAML Frontmatter (Required)

```yaml
---
name: my-skill
description: What this skill does
triggers:
  - "trigger phrase 1"
  - "another trigger"
---
```

**Fields:**
- `name` - Unique skill identifier
- `description` - Brief description (shown in /listSkills)
- `triggers` - Phrases that activate this skill

### Markdown Body (Required)

The rest of the file contains instructions for the LLM. Be clear and specific:

- Explain what the skill does
- Describe the expected input format
- Define the output format
- Include examples
- Handle edge cases

## Best Practices

### 1. Clear Triggers

Use specific, unambiguous trigger phrases:

```yaml
# Good
triggers:
  - "calculate taxes for"
  - "compute tax on"

# Avoid
triggers:
  - "calculate"  # Too broad
  - "help"       # Too generic
```

### 2. Structured Instructions

Organize instructions logically:

```markdown
## Instructions

1. Parse the input
2. Validate parameters
3. Process the request
4. Format the response
```

### 3. Examples

Include concrete examples:

```markdown
## Examples

**Input:** calculate taxes for $50000
**Output:**
Tax breakdown for $50,000:
- Federal: $8,000
- State: $2,500
- Total: $10,500
```

### 4. Error Handling

Define how to handle invalid input:

```markdown
## Error Handling

If the amount is missing, respond with:
"Usage: calculate taxes for <amount>
Example: calculate taxes for $50000"
```

## Testing Skills

After creating a skill:

1. **Restart the agent:**
   ```bash
   # Stop the daemon (Ctrl+C)
   # Start again
   uv run python -m p3394_agent --daemon
   ```

2. **List skills:**
   ```
   >>> /listSkills
   ```

3. **Test with triggers:**
   ```
   >>> your trigger phrase here
   ```

4. **Check edge cases:**
   - Missing parameters
   - Invalid input
   - Empty input

## Advanced Features

### Multiple Files

For complex skills, add supporting files:

```
my-skill/
├── SKILL.md
├── examples/
│   ├── example1.md
│   └── example2.md
└── references/
    └── data.json
```

### Referencing Files

In your SKILL.md:

```markdown
See examples/example1.md for detailed usage.
```

### Skill Dependencies

If your skill requires specific tools or capabilities:

```markdown
## Requirements

This skill uses:
- WebSearch tool for current information
- Read tool for file access
```
