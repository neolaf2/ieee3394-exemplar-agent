# Merge Strategies

When syncing skills with upstream changes while preserving local modifications, the skill-manager offers several merge strategies.

## Strategy Overview

| Strategy | Description | Best For |
|----------|-------------|----------|
| `three-way-merge` | Git-style merge combining both | Most situations |
| `keep-local` | Keep local, ignore upstream | Intentional forks |
| `take-upstream` | Discard local, take upstream | Reset to clean |
| `overlay` | Re-apply local on fresh upstream | Isolated additions |
| `manual` | User decides each conflict | Complex conflicts |

## Three-Way Merge (Default)

Compares three versions:
- **Base**: Content at install time (or last sync)
- **Local**: Current content with your modifications
- **Upstream**: Latest content from source

### How It Works

```
        Base
       /    \
      /      \
   Local    Upstream
      \      /
       \    /
       Merged
```

1. Compute diff: Base → Local (your changes)
2. Compute diff: Base → Upstream (their changes)
3. Apply both diffs to Base
4. If same lines changed differently → CONFLICT

### Auto-Mergeable Cases

| Your Change | Their Change | Result |
|-------------|--------------|--------|
| Added lines at end | Changed line 5 | Both applied |
| Modified line 10 | Modified line 20 | Both applied |
| Deleted lines 5-10 | Added lines 50-55 | Both applied |

### Conflict Cases

| Your Change | Their Change | Result |
|-------------|--------------|--------|
| Modified line 10 | Modified line 10 | CONFLICT |
| Deleted lines 5-10 | Modified line 7 | CONFLICT |
| Renamed function | Modified same function | CONFLICT |

### Conflict Resolution

When conflicts occur, the merge-assistant agent presents:

```
CONFLICT in SKILL.md at line 45-50
────────────────────────────────────────
BASE:
  Use rotate_page() function for rotation

YOUR VERSION:
  Use custom_template() for rotation
  with my special settings

THEIR VERSION:
  Use rotate_page() with preserve_metadata=True

? Resolution:
> Keep yours
  Take theirs
  Combine both
  Edit manually
```

## Keep Local

Preserves all local modifications, ignoring upstream entirely.

### When to Use
- Intentionally diverged from upstream
- Your modifications are more important
- Upstream changes are not relevant

### What Happens
1. Local content unchanged
2. Lockfile updated to acknowledge check
3. `upstream.lastChecked` updated
4. `local.modified` remains true

### Example
```bash
/skill-sync pdf-processing --strategy keep-local

Keeping local version.
✓ Acknowledged upstream at commit abc123
✓ Your 3 local modifications preserved
```

## Take Upstream

Discards all local modifications and resets to upstream.

### When to Use
- Local changes are obsolete
- Want to start fresh
- Upstream has complete rewrite

### What Happens
1. Local content replaced with upstream
2. `evolution.json` PRESERVED (learnings kept)
3. After replacement, `smart_stitch.py` re-applies learnings
4. `local.modified` reset to false

### Example
```bash
/skill-sync pdf-processing --strategy take-upstream

⚠ This will discard your local modifications:
  - SKILL.md (custom template section)
  - scripts/rotate_pdf.py (backup feature)

✓ evolution.json will be PRESERVED (2 preferences, 1 fix)

? Proceed? [y/N]

Applying upstream version...
✓ Replaced with upstream abc123
✓ Re-stitched evolution.json learnings
```

## Overlay

Starts with fresh upstream, then re-applies local changes as patches.

### When to Use
- Local changes are isolated additions
- Context hasn't changed significantly
- Want upstream base with your extras

### How It Works
1. Compute diff: Base → Local (your changes)
2. Replace local with upstream
3. Apply your diff as patches
4. If patch fails → manual intervention

### Best For
- Added new sections (not modifying existing)
- Added new scripts (not modifying existing)
- Configuration additions

### Example
```bash
/skill-sync pdf-processing --strategy overlay

Computing your changes as patches...
  + Added section "Custom Templates"
  + Added script backup_before_rotate.py
  ~ Modified scripts/rotate_pdf.py (may need adjustment)

Applying patches to upstream...
✓ Added "Custom Templates" section
✓ Added backup_before_rotate.py
⚠ Patch for rotate_pdf.py needs manual review

Opening rotate_pdf.py for manual merge...
```

## Manual

User decides each change interactively.

### When to Use
- Complex conflicts
- Want full control
- Need to understand all changes

### What Happens
1. Present each difference
2. User chooses: keep local, take upstream, combine, or edit
3. Build merged result from choices
4. Write final version

### Example
```bash
/skill-sync pdf-processing --strategy manual

Starting manual merge...

[1/5] Description (line 3)
  Local:    "PDF manipulation with custom templates"
  Upstream: "PDF manipulation with rotation and extraction"
  ? Keep local / Take upstream / Combine / Edit: combine
  Combined: "PDF manipulation with rotation, extraction, and custom templates"

[2/5] Step 3: Rotate Pages (lines 45-55)
  Local:    (10 lines with custom_template)
  Upstream: (8 lines with preserve_metadata)
  ? Keep local / Take upstream / Edit: edit
  [Opening editor...]

...

Manual merge complete.
✓ 5 sections resolved
✓ Merged content written
✓ Lockfile updated
```

## Evolution Preservation

**All strategies preserve evolution.json.**

The evolution system stores learnings separately:
1. `evolution.json` is never overwritten by upstream
2. After any merge, `smart_stitch.py` re-stitches learnings
3. "User-Learned Best Practices" section is regenerated

```bash
# This happens automatically after merge
python3 "${CLAUDE_PLUGIN_ROOT}/scripts/smart_stitch.py" ~/.claude/skills/<skill-name>
```

## Strategy Selection Guide

```
               ┌─────────────────────────────────┐
               │ Are your local changes important │
               │ to preserve?                     │
               └────────────┬────────────────────┘
                           │
              ┌────────────┴────────────┐
              │                         │
             YES                        NO
              │                         │
              ▼                         ▼
┌─────────────────────────┐   ┌─────────────────────────┐
│ Are upstream changes    │   │ take-upstream           │
│ also important?         │   │ (reset to clean)        │
└───────────┬─────────────┘   └─────────────────────────┘
            │
   ┌────────┴────────┐
   │                 │
  YES                NO
   │                 │
   ▼                 ▼
┌─────────────────┐ ┌─────────────────────────┐
│ Are changes     │ │ keep-local              │
│ isolated/       │ │ (intentional fork)      │
│ non-overlapping?│ └─────────────────────────┘
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
   YES        NO
    │         │
    ▼         ▼
┌─────────┐ ┌─────────────────────────┐
│ overlay │ │ three-way-merge or     │
│         │ │ manual (if complex)     │
└─────────┘ └─────────────────────────┘
```
