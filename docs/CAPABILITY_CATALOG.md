# Capability Catalog System

The P3394 Agent maintains a **Capability Catalog** - a unified view of all agent capabilities that synchronizes between system truth (code/config) and memory truth (KSTAR long-term memory).

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Capability Catalog                                │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  System Truth (Top-Down Discovery)                                   │
│  ─────────────────────────────────                                  │
│  • Commands (built-in and custom)                                   │
│  • Skills (.claude/skills/)                                         │
│  • SDK Tools (Read, Write, Bash, etc.)                              │
│  • Channels (CLI, Web, WhatsApp, etc.)                              │
│  • Core capabilities (chat, session, llm)                           │
│                         ↕ Sync                                       │
│  Memory Truth (KSTAR Long-Term Memory)                              │
│  ────────────────────────────────────                               │
│  • Persisted catalog entries                                         │
│  • Learned capabilities                                              │
│  • Evolved capability metadata                                       │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Key Concepts

### Two Sources of Truth

| Source | Description | Updates |
|--------|-------------|---------|
| **System Truth** | Capabilities from code, config, and skills directories | On startup, on channel registration |
| **Memory Truth** | Capabilities stored in KSTAR memory | Persisted across restarts |

### Capability Types

| Type | Description | Example |
|------|-------------|---------|
| `command` | Symbolic commands (instant, no LLM) | `/help`, `/status` |
| `skill` | LLM-guided capabilities | `site-generator`, `p3394-explainer` |
| `tool` | SDK tools | `Read`, `Write`, `Bash` |
| `channel` | Communication channels | `cli`, `unified-web` |
| `core` | Core internal capabilities | `chat`, `session.create` |
| `mcp_tool` | MCP server tools | External integrations |
| `hook` | Pre/post hooks | Logging, security |
| `subagent` | Delegated subagents | Task delegation |

### Capability Sources

| Source | Description |
|--------|-------------|
| `builtin` | Hardcoded in agent code |
| `sdk` | From Claude Agent SDK |
| `skill` | From `.claude/skills/` directory |
| `config` | From `agent.yaml` |
| `learned` | Agent learned/created |

### Capability Power Levels

Power levels classify capabilities by their potential impact on the agent:

| Level | Description | Security |
|-------|-------------|----------|
| `standard` | Isolated task execution, safe for all users | Anonymous, Client, Service, Admin |
| `meta` | Can invoke other capabilities recursively | Service, Admin |
| `self_modifying` | Can modify agent state, memory, or capabilities | Admin only |
| `bootstrap` | Factory-essential, system-level capabilities | System/Factory only |

#### Power Level Classification

```python
# BOOTSTRAP level - SDK and factory essentials
"tool.sdk.read", "tool.sdk.write", "tool.sdk.bash", "tool.sdk.task"
"core.llm.invoke", "core.session.create", "core.session.destroy"

# SELF_MODIFYING level - Can mutate agent
"skill.skill-creator", "skill.skill-evolution", "skill.skill-management"
"skill.control-tokens"  # KSTAR+ control tokens
"admin.principal_manage", "admin.acl_manage", "admin.channel_manage"

# META level - Can invoke other capabilities
"skill.skill-discovery"
"skill.agent-sdk-basics", "skill.agent-sdk-advanced"
"core.chat.with_tools", "core.skill_dispatch", "core.subagent_dispatch"

# STANDARD level - Everything else (task-specific, isolated)
```

#### Security Implications

- **Anonymous users**: STANDARD only (public capabilities)
- **Client principals**: STANDARD only (no agent mutation)
- **Service principals**: STANDARD + META + controlled SELF_MODIFYING
- **Admin/System**: All levels

## Discovery Process

### Startup Discovery

At agent initialization, the catalog performs top-down inspection:

```
1. Load from memory (what agent already knows)
2. Discover from system sources:
   - Commands (gateway.commands)
   - Skills (.claude/skills/, ~/.claude/skills/)
   - Subagents (.claude/agents/)
   - SDK Tools (built-in list)
   - MCP Tools (from agent.yaml, settings.json)
   - Hooks (from settings.json)
   - Core capabilities (hardcoded list)
3. Sync to memory (add new, update changed)
4. Report out-of-sync items
```

### Incremental Updates

Channels are registered after startup, so the catalog supports incremental refresh:

```python
# When a channel is registered
await gateway.register_channel("cli", cli_adapter)
# Catalog automatically refreshes channel discovery
```

### Example Startup Log

```
INFO - Loaded 51 capabilities from memory
INFO - Discovered 53 capabilities: {
    'commands': 8,
    'skills': 28,
    'tools': 9,
    'channels': 2,
    'core': 6
}
INFO - Synced catalog to memory: {'added': 2, 'updated': 0, 'unchanged': 51}
INFO - Capability catalog initialized: 53 total, 53 synced, 0 new, 0 orphaned
```

## Catalog Entry Schema

Each capability in the catalog has:

```python
@dataclass
class CatalogEntry:
    id: str                    # e.g., "command.help", "skill.site-generator"
    name: str                  # Display name
    type: CapabilityType       # command, skill, tool, channel, core, etc.
    source: CapabilitySource   # builtin, sdk, skill, config, learned
    description: str           # Human-readable description
    version: str               # Capability version
    enabled: bool              # Is it enabled?
    power_level: PowerLevel    # standard, meta, self_modifying, bootstrap
    source_path: str           # File path if applicable
    in_memory: bool            # Synced to KSTAR memory?
    in_system: bool            # Found in system?
```

Power levels are auto-classified based on capability ID when not explicitly set.

## API Reference

### Query Endpoints

```bash
# Get full catalog
GET /api/catalog

# Filter by type
GET /api/catalog?type_filter=skill

# Filter by source
GET /api/catalog?source_filter=builtin

# Filter by power level
GET /api/catalog?power_level=standard

# Get only client-safe capabilities (STANDARD level only)
GET /api/catalog?safe_for_client=true

# Combine filters
GET /api/catalog?type_filter=skill&power_level=meta

# Get catalog manifest
GET /api/catalog/manifest
```

### Response Format

```json
{
    "stats": {
        "total": 53,
        "by_type": {
            "command": 8,
            "skill": 28,
            "tool": 9,
            "core": 6,
            "channel": 2
        },
        "by_source": {
            "builtin": 16,
            "skill": 28,
            "sdk": 9
        },
        "by_power_level": {
            "standard": 45,
            "meta": 5,
            "self_modifying": 3,
            "bootstrap": 0
        },
        "enabled": 53,
        "sync_status": {
            "in_both": 53,
            "only_system": 0,
            "only_memory": 0
        }
    },
    "count": 53,
    "entries": [
        {
            "id": "command.help",
            "name": "/help",
            "type": "command",
            "source": "builtin",
            "description": "Show available commands and capabilities",
            "enabled": true,
            "power_level": "standard",
            "in_memory": true,
            "in_system": true
        }
        // ... more entries
    ]
}
```

## Sync Status

The catalog tracks synchronization between system and memory:

| Status | Meaning |
|--------|---------|
| `in_both` | Capability exists in both system and memory (synced) |
| `only_system` | New capability found in system, not yet in memory |
| `only_memory` | Capability in memory but removed from system (orphaned) |

### Handling Out-of-Sync

```python
# List out-of-sync capabilities
out_of_sync = catalog.list_out_of_sync()

# Force re-sync
await catalog.sync_to_memory()
```

## Programmatic API

### CapabilityCatalog Class

```python
from p3394_agent.core.capability_catalog import CapabilityCatalog

# Access via gateway
catalog = gateway.capability_catalog

# Query methods
all_caps = catalog.list_all()
skills = catalog.list_by_type(CapabilityType.SKILL)
builtin = catalog.list_by_source(CapabilitySource.BUILTIN)
enabled = catalog.list_enabled()

# Get specific capability
entry = catalog.get("command.help")

# Get statistics
stats = catalog.get_stats()

# Export as manifest
manifest = catalog.to_manifest()
```

### Adding Capabilities Dynamically

```python
from p3394_agent.core.capability_catalog import CatalogEntry, CapabilityType, CapabilitySource

# Create a new learned capability
entry = CatalogEntry(
    id="learned.my-capability",
    name="My Learned Capability",
    type=CapabilityType.SKILL,
    source=CapabilitySource.LEARNED,
    description="A capability the agent learned"
)

# Add to catalog (syncs to memory)
await catalog.add_capability(entry)
```

### Refreshing Channels

Channels are discovered after initialization, so refresh is needed:

```python
# Called automatically by gateway.register_channel()
await catalog.refresh_channels()
```

## Integration with ACL System

The Capability Catalog works with the CACL (Capability Access Control) system:

1. **Catalog** tracks what capabilities exist
2. **ACL Registry** controls who can access them
3. **Access Manager** enforces permissions at runtime

```
Catalog Entry (capability exists)
        ↓
ACL Definition (visibility, permissions)
        ↓
Session Access (computed permissions for user)
```

## Factory Agent Process

The catalog enables "factory agent" configuration:

1. Create agent with base capabilities
2. Export catalog manifest
3. Deploy with custom capability profile
4. Agent loads profile on startup

```yaml
# capability_profile.yaml
capabilities:
  enabled:
    - command.*
    - skill.help
    - skill.site-generator
  disabled:
    - admin.*
```

## Self-Improvement Tracking

As the agent learns, new capabilities can be added:

```python
# Agent learns a new skill
new_skill = CatalogEntry(
    id="learned.summarization",
    name="Document Summarization",
    type=CapabilityType.SKILL,
    source=CapabilitySource.LEARNED,
    description="Learned from user feedback"
)
await catalog.add_capability(new_skill)
```

## Best Practices

1. **Discovery at Startup**: Let the catalog discover capabilities automatically
2. **Incremental Updates**: Use `refresh_channels()` after late registrations
3. **Check Sync Status**: Monitor `only_system` and `only_memory` counts
4. **Use Manifests**: Export manifests for deployment and auditing
5. **ACL Integration**: Ensure ACLs exist for new capabilities

## Troubleshooting

### Channels Not Appearing

**Symptom**: Channels show 0 in catalog

**Solution**: Channels are registered after initialization. The catalog now automatically refreshes when `register_channel()` is called.

### Capabilities Out of Sync

**Symptom**: `only_memory` count > 0

**Cause**: Capability removed from system but still in memory

**Solution**: These are "orphaned" capabilities. They're preserved in memory but won't be available. Clear with `delete_capability_catalog_entry()`.

### Skills Not Discovered

**Symptom**: Skills directory not found

**Solution**: Ensure skills are in `.claude/skills/` or `~/.claude/skills/` with `SKILL.md` files.

## Related Documentation

- **[CAPABILITY_ACL.md](./CAPABILITY_ACL.md)** - Access control for capabilities
- **[.claude/skills/README.md](../.claude/skills/README.md)** - Skills development guide
- **[ACD_IMPLEMENTATION_SUMMARY.md](../ACD_IMPLEMENTATION_SUMMARY.md)** - Agent Capability Descriptor
