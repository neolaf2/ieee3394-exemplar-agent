---
name: skill-transfer
description: "Transfer skills between agents, projects, and environments. Handles packaging, dependency resolution, and configuration adaptation."
version: 1.0.0
---

# Skill Transfer

System for transferring skills between P3394 agents, projects, and environments.

## Core Capabilities

| Capability | Description |
|------------|-------------|
| **Export** | Package skill with all dependencies |
| **Import** | Install skill from package or remote source |
| **Adapt** | Adjust skill configuration for new environment |
| **Validate** | Verify skill works in target environment |

## Triggers

- "transfer skill [name] to [destination]"
- "export skill [name]"
- "import skill from [source]"
- "share skill [name]"
- "copy skill [name] to [project]"

## Transfer Package Format

```
skill-name.zip
├── SKILL.md              # Main skill definition
├── manifest.json         # Transfer metadata
├── scripts/              # Helper scripts
├── references/           # Reference documents
├── evolution.json        # User learnings (optional)
└── dependencies.lock     # Resolved dependencies
```

## Manifest Schema

```json
{
  "name": "my-skill",
  "version": "1.0.0",
  "exported_at": "2026-01-31T...",
  "source_project": "ieee3394Agent",
  "source_agent": "p3394://ieee3394-exemplar",
  "dependencies": {
    "tools": ["Bash", "Read", "Write"],
    "skills": ["pdf", "docx"],
    "packages": [
      {"name": "pdfplumber", "manager": "pip", "version": ">=0.9.0"}
    ]
  },
  "configuration": {
    "required_env": ["SUPABASE_URL"],
    "optional_env": ["DEBUG_MODE"]
  },
  "compatibility": {
    "min_claude_code_version": "1.0.0",
    "platforms": ["darwin", "linux", "win32"]
  }
}
```

## Transfer Workflow

### Step 1: Export

```bash
# Export skill to package
skill-transfer export my-skill --output ./exports/

# With dependencies
skill-transfer export my-skill --include-deps

# Include evolution/learnings
skill-transfer export my-skill --include-evolution
```

### Step 2: Transfer

Options:
- **Local copy**: Direct file copy
- **Git push**: Push to repository
- **Supabase sync**: Store in control tokens
- **P3394 message**: Send via UMF to target agent

### Step 3: Import

```bash
# Import from local package
skill-transfer import ./my-skill.zip

# Import from URL
skill-transfer import https://github.com/user/skills/my-skill.zip

# Import from another project
skill-transfer import ~/Local/OtherProject/.claude/skills/my-skill
```

### Step 4: Adapt Configuration

The system automatically:
1. Checks for missing environment variables
2. Resolves dependency conflicts
3. Adjusts paths for new project structure
4. Migrates evolution.json preferences

## Integration with Memory System

Skill transfers are tracked as Control Tokens:

| Key | Value | Category |
|-----|-------|----------|
| `skill:exported:{name}` | Export timestamp + destination | `CAPABILITY` |
| `skill:imported:{name}` | Source + import timestamp | `CAPABILITY` |
| `skill:transferred:{name}` | Full transfer record | `BINDING` |

This enables:
- Recovery of transferred skill history
- Audit trail of skill provenance
- Sync of skills across agent instances

## Examples

### Export and Share

```
User: Transfer the pdf skill to my other project

1. Package pdf skill with dependencies
2. Create manifest with compatibility info
3. Copy to target: ~/Local/OtherProject/.claude/skills/
4. Validate in target environment
5. Track in both source and target memory
```

### Import from Remote

```
User: Import the scientific-writing skill from my personal directory

1. Locate: ~/.claude/skills/scientific-writing
2. Check dependencies: research-lookup, venue-templates
3. Resolve: Import missing dependencies first
4. Copy and adapt configuration
5. Register in SKILLS.lock
```

### Cross-Agent Transfer

```
User: Send the whatsapp-config skill to the demo agent

1. Package skill with P3394 compatibility
2. Create UMF message with skill payload
3. Send to p3394://demo-agent/skills
4. Target agent imports and adapts
5. Confirm transfer via UMF response
```

## Flags

- `--output <path>`: Export destination
- `--include-deps`: Include dependent skills
- `--include-evolution`: Include learned preferences
- `--dry-run`: Show what would be transferred
- `--force`: Overwrite existing skill
- `--adapt-config`: Auto-adapt configuration for target

## Related Skills

- **skill-management**: Core skill lifecycle
- **skill-evolution**: Meta-learning system
- **memory-system**: Token persistence for tracking
