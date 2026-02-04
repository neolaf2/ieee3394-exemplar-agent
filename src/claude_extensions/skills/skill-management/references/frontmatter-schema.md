# Extended Frontmatter Schema

This document defines the complete frontmatter schema for managed skills. The schema is backward-compatible with standard Claude Code skills (only `name` and `description` required) while supporting advanced lifecycle management.

## Schema Overview

```yaml
---
# ════════════════════════════════════════════════════════════════════════════
# REQUIRED FIELDS (Claude Code standard)
# ════════════════════════════════════════════════════════════════════════════
name: my-skill                           # kebab-case, must match directory name
description: >-                          # Comprehensive description for triggering
  Description of what the skill does and when Claude should use it.
  Include trigger phrases like "use this when..."

# ════════════════════════════════════════════════════════════════════════════
# VERSION & IDENTITY (recommended)
# ════════════════════════════════════════════════════════════════════════════
version: 1.2.3                           # Semantic versioning (MAJOR.MINOR.PATCH)
license: MIT                             # SPDX license identifier
author:
  name: Author Name
  email: author@example.com

# ════════════════════════════════════════════════════════════════════════════
# SOURCE TRACKING (auto-populated by /skill-install)
# Compatible with both skill-manager and Khazix-Skills github-to-skills
# ════════════════════════════════════════════════════════════════════════════

# Khazix-Skills compatible fields (primary)
github_url: https://github.com/user/repo # Original source URL
github_hash: abc123def456789...          # Git commit SHA at install time
created_at: 2026-01-25T10:30:00Z         # ISO 8601 install timestamp
entry_point: scripts/wrapper.py          # Main script (if applicable)

# Extended source tracking (skill-manager)
source:
  type: github | skillsmp | anthropic | local | composed
  url: https://github.com/user/repo      # Same as github_url
  path: skills/my-skill                  # Path within source (if applicable)
  branch: main                           # Branch being tracked
  commit: abc123def456789...             # Same as github_hash
  installDate: 2026-01-25T10:30:00Z      # Same as created_at

# ════════════════════════════════════════════════════════════════════════════
# LOCAL MODIFICATIONS (auto-computed by skill-manager)
# ════════════════════════════════════════════════════════════════════════════
local:
  modified: true                         # Has local changes (auto-computed)
  modifiedDate: 2026-01-26T14:00:00Z     # Last local modification time
  contentHash: sha256:abc123...          # Hash of current content
  baseHash: sha256:def456...             # Hash at install/last sync
  changelog: |                           # Optional: describe local changes
    - Added custom template for project X
    - Fixed bug in PDF rotation script

# ════════════════════════════════════════════════════════════════════════════
# DEPENDENCIES
# ════════════════════════════════════════════════════════════════════════════

# Khazix-Skills compatible (simple list)
dependencies:
  - yt-dlp
  - ffmpeg

# Extended format (skill-manager)
dependencies:
  skills:                                # Other skills this depends on
    - name: pdf-processing
      version: ">=1.0.0"                 # Semver range
      optional: false
    - name: document-templates
      version: "^2.0.0"
      optional: true
  tools:                                 # Claude Code tools required
    - Bash
    - Write
    - Read
  packages:                              # External packages
    - name: pdfplumber
      manager: pip
      version: ">=0.5.0"

# ════════════════════════════════════════════════════════════════════════════
# COMPOSITION (if skill is composed from others)
# ════════════════════════════════════════════════════════════════════════════
composition:
  type: extends | combines | overrides
  parents:
    - name: base-pdf-skill
      version: 1.0.0
      source: anthropic
    - name: custom-templates
      version: 2.1.0
      source: local
  mergeStrategy: overlay                 # How parent content was merged

# ════════════════════════════════════════════════════════════════════════════
# METADATA (for discovery and publishing)
# ════════════════════════════════════════════════════════════════════════════
metadata:
  category: document-processing          # Primary category
  tags:
    - pdf
    - rotation
    - manipulation
  maturity: stable | beta | experimental
  quality:
    tests: true                          # Has test suite
    examples: true                       # Has usage examples
    documentation: comprehensive

# ════════════════════════════════════════════════════════════════════════════
# ALLOWED TOOLS (per Agent Skills Spec)
# ════════════════════════════════════════════════════════════════════════════
allowed-tools:
  - Bash
  - Read
  - Write
---
```

## Field Groups

### Required (Always)
| Field | Type | Description |
|-------|------|-------------|
| `name` | string | Kebab-case skill identifier, must match directory name |
| `description` | string | Comprehensive description including trigger phrases |

### Version & Identity (Recommended)
| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semantic version (MAJOR.MINOR.PATCH) |
| `license` | string | SPDX license identifier (MIT, Apache-2.0, etc.) |
| `author` | object | Author name and email |

### Source Tracking (Auto-populated)
These fields are added automatically when installing via `/skill-install`.

| Field | Khazix Equivalent | Description |
|-------|-------------------|-------------|
| `source.url` | `github_url` | Original source URL |
| `source.commit` | `github_hash` | Git commit SHA at install |
| `source.installDate` | `created_at` | Installation timestamp |
| `source.type` | - | Source type (github, skillsmp, local, etc.) |
| `source.branch` | - | Git branch being tracked |

### Local Modifications (Auto-computed)
| Field | Description |
|-------|-------------|
| `local.modified` | Boolean: has local changes |
| `local.contentHash` | SHA256 of current content |
| `local.baseHash` | SHA256 at install/last sync |
| `local.changelog` | User-provided change notes |

### Dependencies
| Field | Description |
|-------|-------------|
| `dependencies.skills` | Other skills required |
| `dependencies.tools` | Claude Code tools required |
| `dependencies.packages` | External packages (pip, npm, etc.) |

## Backward Compatibility

### With Khazix-Skills
The schema maintains full compatibility with Khazix-Skills `github-to-skills` format:
- `github_url` → also stored as `source.url`
- `github_hash` → also stored as `source.commit`
- `created_at` → also stored as `source.installDate`
- `dependencies` (simple list) → converted to extended format

### With Standard Skills
Skills with only `name` and `description` continue to work normally. They are treated as local, untracked skills until explicitly registered with `/skill-install --track-local`.

## Migration

To upgrade existing skills to the extended schema:

```bash
/skill-audit --migrate
```

This will:
1. Scan all skills in `~/.claude/skills/`
2. Add missing recommended fields
3. Generate initial version (1.0.0)
4. Compute content hashes
5. Create SKILLS.lock entries
6. Preserve all existing content
