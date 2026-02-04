---
name: skill-evolution
description: "Meta-learning system for capturing and persisting learnings from skill usage. Enables skills to evolve based on user feedback and experience."
version: 1.0.0
---

# Skill Evolution (Meta-Learning)

System for capturing learnings from skill usage and persisting them for continuous improvement.

## Core Concept

When using skills, you discover:
- **Preferences**: "I prefer outputs in JSON format"
- **Fixes**: "On Windows, need to escape backslashes"
- **Contexts**: "My project uses Python 3.11+"

The evolution system captures these in `evolution.json` and stitches them into SKILL.md.

## Triggers

- "evolve skill [name]"
- "capture learnings"
- "remember this for [skill]"
- "save preference"

## How It Works

1. **Extract learnings** from conversation context
2. **Persist to evolution.json** in the skill folder
3. **Stitch into SKILL.md** as "User-Learned Best Practices"
4. **Survive upstream updates** - learnings are preserved on sync

## Evolution Data Structure

```json
{
  "last_updated": "2026-01-31T...",
  "preferences": ["User prefers JSON output"],
  "fixes": ["Windows path escaping needed"],
  "contexts": ["Corporate environment"],
  "custom_prompts": "Always confirm destructive ops"
}
```

## Integration with Memory System

Skill evolution data is also tracked as Control Tokens:
- Key: `skill:evolved:{skill_name}`
- Category: `CAPABILITY`
- Tags: `["skill", "evolution", "meta-learning"]`

This enables recovery of skill customizations after restart.

## Related Commands

- `/skill-evolve [skill-name]` - Capture learnings
- `/skill-status` - View evolution state
- `/skill-sync` - Updates preserve evolution.json
