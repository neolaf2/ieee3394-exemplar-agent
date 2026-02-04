---
name: skill-management
description: "Core knowledge for the skill-manager plugin. Use this when managing skills: installing, tracking versions, syncing with upstream, evolving based on feedback, composing new skills, or publishing. Provides the complete skill lifecycle management system."
version: 1.0.0
license: MIT
---

# Skill Management

This skill provides comprehensive knowledge for managing the Claude Code skill lifecycle.

## Core Capabilities

| Capability | Command | Description |
|------------|---------|-------------|
| **Discovery** | `/skill-search` | Search SkillsMP, GitHub, Anthropic, local |
| **Installation** | `/skill-install` | Install with version tracking |
| **Status** | `/skill-status` | View all tracked skills |
| **Sync** | `/skill-sync` | Check/apply upstream updates |
| **Diff** | `/skill-diff` | View local vs upstream changes |
| **Evolution** | `/skill-evolve` | Capture learnings and improvements |
| **Audit** | `/skill-audit` | Validate skill quality |
| **Creation** | `/skill-create` | Create new skills |
| **Composition** | `/skill-compose` | Compose from existing skills |
| **Publishing** | `/skill-publish` | Publish to platforms |

## The Skill Lifecycle

```
┌─────────────────┐
│    DISCOVER     │ ← /skill-search
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│    INSTALL      │ ← /skill-install (tracks in SKILLS.lock)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│      USE        │ ← Normal skill invocation
└────────┬────────┘
         │
    ┌────┴────┐
    ▼         ▼
┌───────┐ ┌───────┐
│EVOLVE │ │ SYNC  │ ← /skill-evolve captures learnings
└───┬───┘ └───┬───┘   /skill-sync updates from upstream
    │         │
    └────┬────┘
         │
         ▼
┌─────────────────┐
│    PUBLISH      │ ← /skill-publish shares with community
└─────────────────┘
```

## Version Tracking System

### SKILLS.lock

All tracked skills are recorded in `~/.claude/SKILLS.lock`:

```json
{
  "version": 1,
  "skills": {
    "pdf-processing": {
      "version": "1.2.3",
      "resolved": {
        "source": "github",
        "url": "https://github.com/anthropics/skills",
        "commit": "abc123..."
      },
      "local": {
        "modified": true,
        "contentHash": "sha256:xyz..."
      },
      "upstream": {
        "hasUpdates": true
      }
    }
  }
}
```

### Extended Frontmatter

Managed skills have extended metadata in their SKILL.md:

```yaml
---
name: my-skill
description: "..."
version: 1.0.0
github_url: https://github.com/...   # Khazix-Skills compatible
github_hash: abc123...               # Commit at install
source:
  type: github
  url: https://github.com/...
  commit: abc123...
local:
  modified: false
  contentHash: sha256:...
---
```

## Handling Local Modifications

When you modify a skill locally (fix bugs, add templates), the system:

1. **Detects changes** via content hash comparison
2. **Preserves evolution.json** with your learnings
3. **Offers merge strategies** when upstream updates:
   - `three-way-merge`: Combine both changes
   - `keep-local`: Keep your changes, ignore upstream
   - `take-upstream`: Reset to upstream
   - `overlay`: Apply your changes on top of fresh upstream

## Evolution System

The evolution system captures learnings in `evolution.json`:

```json
{
  "preferences": ["Prefer JSON output"],
  "fixes": ["Windows path escaping needed"],
  "custom_prompts": "Always confirm before delete"
}
```

These are "stitched" into SKILL.md as a `## User-Learned Best Practices` section that survives upstream updates.

## Scripts Reference

| Script | Purpose |
|--------|---------|
| `parse_frontmatter.py` | Parse/update YAML frontmatter |
| `compute_checksum.py` | SHA256 content hashing |
| `lockfile.py` | SKILLS.lock management |
| `scan_and_check.py` | Check upstream for updates |
| `fetch_github_info.py` | Fetch repo metadata |
| `merge_evolution.py` | Merge learning data |
| `smart_stitch.py` | Stitch learnings into SKILL.md |

## Agents

| Agent | Role |
|-------|------|
| `skill-auditor` | Validates skill quality |
| `merge-assistant` | Resolves merge conflicts |
| `dependency-resolver` | Resolves skill dependencies |
| `skill-composer` | Composes new skills |
| `publish-assistant` | Prepares for publishing |

## Quick Reference

```bash
# Search for skills
/skill-search pdf

# Install from GitHub
/skill-install https://github.com/user/repo/tree/main/skills/my-skill

# Check status
/skill-status

# Sync with upstream
/skill-sync

# Capture learnings
/skill-evolve

# Validate a skill
/skill-audit ~/.claude/skills/my-skill
```

## References

- [Extended Frontmatter Schema](references/frontmatter-schema.md)
- [SKILLS.lock Format](references/lockfile-format.md)
- [Merge Strategies](references/merge-strategies.md)
- [Publishing Platforms](references/publishing-platforms.md)
