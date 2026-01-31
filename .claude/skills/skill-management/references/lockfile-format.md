# SKILLS.lock Format Specification

The SKILLS.lock file tracks all managed skills with their versions, sources, and modification state.

## Location

- **Global**: `~/.claude/SKILLS.lock` - User-installed skills
- **Project**: `<project>/.claude/SKILLS.lock` - Project-specific skills (overrides global)

## Schema

```json
{
  "version": 1,
  "generated": "2026-01-25T12:00:00Z",
  "skills": {
    "<skill-name>": {
      "version": "1.2.3",
      "resolved": {
        "source": "github|skillsmp|anthropic|local|composed",
        "url": "https://github.com/user/repo",
        "path": "skills/skill-name",
        "commit": "abc123def456789...",
        "branch": "main"
      },
      "installed": {
        "path": "~/.claude/skills/<skill-name>",
        "date": "2026-01-20T08:00:00Z",
        "contentHash": "sha256:abc123..."
      },
      "local": {
        "modified": true,
        "contentHash": "sha256:xyz789...",
        "baseHash": "sha256:abc123...",
        "modifiedFiles": ["SKILL.md", "scripts/helper.py"],
        "modifiedDate": "2026-01-25T10:00:00Z",
        "evolved": true,
        "lastEvolvedDate": "2026-01-25T14:00:00Z"
      },
      "upstream": {
        "lastChecked": "2026-01-25T06:00:00Z",
        "latestCommit": "def456ghi789...",
        "hasUpdates": true
      },
      "dependencies": {
        "skills": ["other-skill@>=1.0.0"],
        "packages": {
          "pip": ["pdfplumber>=0.5.0"]
        }
      },
      "composition": {
        "type": "combines",
        "parents": [
          {"name": "pdf-processing", "version": "1.2.3"},
          {"name": "document-templates", "version": "2.0.0"}
        ]
      }
    }
  }
}
```

## Field Reference

### Top-Level

| Field | Type | Description |
|-------|------|-------------|
| `version` | integer | Lockfile format version (currently 1) |
| `generated` | string | ISO 8601 timestamp of last generation |
| `skills` | object | Map of skill name → skill entry |

### Skill Entry

| Field | Type | Description |
|-------|------|-------------|
| `version` | string | Semantic version of the skill |
| `resolved` | object | Source resolution details |
| `installed` | object | Installation details |
| `local` | object | Local modification tracking |
| `upstream` | object | Upstream status |
| `dependencies` | object | Skill dependencies |
| `composition` | object | Composition metadata (if composed) |

### Resolved Object

| Field | Type | Description |
|-------|------|-------------|
| `source` | string | Source type: github, skillsmp, anthropic, local, composed |
| `url` | string | Source URL (if applicable) |
| `path` | string | Path within source (if applicable) |
| `commit` | string | Git commit SHA at install time |
| `branch` | string | Git branch being tracked |

### Installed Object

| Field | Type | Description |
|-------|------|-------------|
| `path` | string | Local installation path |
| `date` | string | Installation timestamp |
| `contentHash` | string | SHA256 hash at install time |

### Local Object

| Field | Type | Description |
|-------|------|-------------|
| `modified` | boolean | Has local modifications |
| `contentHash` | string | Current content hash |
| `baseHash` | string | Hash at install/last sync |
| `modifiedFiles` | array | List of modified files |
| `modifiedDate` | string | Last modification timestamp |
| `evolved` | boolean | Has evolution.json data |
| `lastEvolvedDate` | string | Last evolution timestamp |

### Upstream Object

| Field | Type | Description |
|-------|------|-------------|
| `lastChecked` | string | Last upstream check timestamp |
| `latestCommit` | string | Latest upstream commit SHA |
| `hasUpdates` | boolean | Updates available |

## Modification States

| State | Condition | Description |
|-------|-----------|-------------|
| **Clean** | `local.modified = false` | No local changes |
| **Modified** | `local.modified = true` | Has local changes |
| **Evolved** | `local.evolved = true` | Has evolution.json learnings |
| **Outdated** | `upstream.hasUpdates = true` | Upstream has updates |
| **Conflict** | Modified AND Outdated | Both local and upstream changed |

## CLI Operations

```bash
# List all skills
python3 lockfile.py list

# Get skill entry
python3 lockfile.py get pdf-processing --json

# Add skill
python3 lockfile.py add pdf-processing \
  --version "1.2.3" \
  --source-type github \
  --source-url "https://github.com/anthropics/skills" \
  --source-commit "abc123" \
  --installed-path "~/.claude/skills/pdf-processing" \
  --content-hash "sha256:..."

# Mark as modified
python3 lockfile.py mark-modified pdf-processing \
  --hash "sha256:new..." \
  --files "SKILL.md" "scripts/helper.py"

# Mark as synced
python3 lockfile.py mark-synced pdf-processing \
  --hash "sha256:synced..." \
  --commit "def456"

# Remove skill
python3 lockfile.py remove pdf-processing

# Merge global + project lockfiles
python3 lockfile.py list --merged
```

## Version History

| Version | Changes |
|---------|---------|
| 1 | Initial format |
