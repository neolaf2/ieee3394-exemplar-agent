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

### Cognitive Patterns

Cognitive patterns classify HOW a capability operates (its methodology). This is orthogonal to power level (WHAT it can access).

| Pattern | Description | Examples |
|---------|-------------|----------|
| `execution` | Single-shot task, direct output | echo, pdf, docx |
| `procedural` | Step-by-step workflow | skill-creator, site-generator |
| `iterative` | Loop until condition met | ralph-loop, progressive-discovery |
| `diagnostic` | Hypothesis → test → refine | systematic-debugging, TDD |
| `generative` | Divergent ideation | brainstorming |
| `orchestration` | Coordinates multiple capabilities | dispatching-parallel-agents |
| `reflective` | Self-monitoring, quality gates | code-review, verification |

#### Cognitive Pattern Classification

```python
# ITERATIVE - Loop until condition/completion
"skill.ralph-loop", "skill.verification-before-completion"

# DIAGNOSTIC - Hypothesis → test → refine
"skill.systematic-debugging", "skill.test-driven-development"

# GENERATIVE - Divergent ideation
"skill.brainstorming", "skill.scientific-brainstorming"

# ORCHESTRATION - Coordinates multiple capabilities
"skill.dispatching-parallel-agents", "skill.subagent-driven-development"

# REFLECTIVE - Self-monitoring, quality gates
"skill.code-review", "skill.requesting-code-review"

# PROCEDURAL - Step-by-step workflow
"skill.skill-creator", "skill.site-generator", "skill.mcp-builder"

# EXECUTION - Default for task-specific skills
"skill.echo", "skill.pdf", "skill.docx"
```

### Compute Substrate

Compute substrate classifies the computational basis of each capability:

| Substrate | Value | Description | Characteristics |
|-----------|-------|-------------|-----------------|
| `symbolic` | 0 | Pure symbolic execution, no LLM | Instant, deterministic, free, works offline |
| `neural` | 1 | LLM-based processing | Latency, cost, non-deterministic |
| `composite` | 2 | Combines symbolic and neural | Hybrid approach, most skills |

#### Compute Substrate Classification

```python
# SYMBOLIC (0) - Instant, deterministic, no LLM needed
"command.help", "command.about", "command.status", "command.version"
"command.login", "command.listSkills", "command.endpoints"
"tool.sdk.read", "tool.sdk.write", "tool.sdk.edit", "tool.sdk.bash"
"core.session.create", "core.session.destroy"
"channel.cli", "channel.unified-web", "channel.whatsapp"

# NEURAL (1) - Requires LLM, non-deterministic
"core.llm.invoke", "core.chat", "core.chat.with_tools"
"core.message.handle"

# COMPOSITE (2) - Default for most skills
"skill.*"  # Most skills combine symbolic routing with neural processing
```

#### Use Cases for Compute Substrate

- **Offline Mode**: Query `compute_substrate=symbolic` for capabilities available without network
- **Cost Optimization**: Prefer symbolic capabilities to reduce LLM usage
- **Latency Sensitive**: Use symbolic for instant response requirements
- **Determinism**: Symbolic operations are repeatable with identical outputs

#### Three-Dimensional Classification

Capabilities are now classified on three orthogonal dimensions:

```
┌─────────────────────────────────────────────────────────────────────┐
│           Capability Classification Matrix (3D)                       │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Dimension 1: Power Level (WHAT it can access)                     │
│   ─────────────────────────────────────────────                     │
│   STANDARD (33)     - Isolated task execution                       │
│   META (6)          - Can invoke other capabilities                 │
│   SELF_MODIFYING (4) - Can modify agent state                       │
│   BOOTSTRAP (10)    - Factory-essential                             │
│                                                                      │
│   Dimension 2: Cognitive Pattern (HOW it operates)                  │
│   ────────────────────────────────────────────────                  │
│   execution (47)    - Single-shot task                              │
│   procedural (3)    - Step-by-step workflow                         │
│   generative (1)    - Divergent ideation                            │
│   orchestration (1) - Coordinates multiple capabilities             │
│   reflective (1)    - Self-monitoring, quality gates                │
│                                                                      │
│   Dimension 3: Compute Substrate (computational basis)              │
│   ─────────────────────────────────────────────────                 │
│   symbolic (0)      - No LLM, instant, deterministic                │
│   neural (1)        - LLM-based, latency, non-deterministic        │
│   composite (2)     - Hybrid symbolic + neural                      │
│                                                                      │
│   Example Classifications:                                           │
│   ┌─────────────────────┬─────────────┬──────────────┬────────────┐│
│   │ Capability          │ Power       │ Cognitive    │ Substrate  ││
│   ├─────────────────────┼─────────────┼──────────────┼────────────┤│
│   │ command.help        │ STANDARD    │ execution    │ symbolic   ││
│   │ core.llm.invoke     │ BOOTSTRAP   │ execution    │ neural     ││
│   │ skill.site-generator│ STANDARD    │ procedural   │ composite  ││
│   │ tool.sdk.read       │ BOOTSTRAP   │ execution    │ symbolic   ││
│   │ skill.brainstorming │ META        │ generative   │ composite  ││
│   └─────────────────────┴─────────────┴──────────────┴────────────┘│
└─────────────────────────────────────────────────────────────────────┘
```

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
    cognitive_pattern: Pattern # execution, procedural, iterative, diagnostic, etc.
    compute_substrate: Substrate # symbolic (0), neural (1), composite (2)
    source_path: str           # File path if applicable
    in_memory: bool            # Synced to KSTAR memory?
    in_system: bool            # Found in system?
```

All three dimensions (power_level, cognitive_pattern, compute_substrate) are auto-classified based on capability ID when not explicitly set.

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

# Filter by cognitive pattern
GET /api/catalog?cognitive_pattern=iterative

# Filter by compute substrate
GET /api/catalog?compute_substrate=symbolic

# Get only methodological skills (non-execution patterns)
GET /api/catalog?methodological_only=true

# Get only offline-capable capabilities (symbolic substrate)
GET /api/catalog?offline_only=true

# Combine filters
GET /api/catalog?type_filter=skill&power_level=meta
GET /api/catalog?compute_substrate=symbolic&type_filter=command

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
            "standard": 33,
            "meta": 6,
            "self_modifying": 4,
            "bootstrap": 10
        },
        "by_cognitive_pattern": {
            "execution": 47,
            "procedural": 3,
            "generative": 1,
            "orchestration": 1,
            "reflective": 1
        },
        "by_compute_substrate": {
            "symbolic": 22,
            "neural": 4,
            "composite": 27
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
            "cognitive_pattern": "execution",
            "compute_substrate": "symbolic",
            "in_memory": true,
            "in_system": true
        }
        // ... more entries
    ]
}
```

### Tested API Examples

These examples have been verified against a running agent:

```bash
# Get methodological skills (non-execution cognitive patterns)
$ curl -s "http://localhost:8000/api/catalog?methodological_only=true" | jq '.entries[] | {id, power_level, cognitive_pattern}'
{
  "id": "skill.Hook Development",
  "power_level": "self_modifying",
  "cognitive_pattern": "procedural"
}
{
  "id": "skill.scientific-brainstorming",
  "power_level": "meta",
  "cognitive_pattern": "generative"
}
{
  "id": "skill.skill-creator",
  "power_level": "self_modifying",
  "cognitive_pattern": "procedural"
}
{
  "id": "tool.sdk.task",
  "power_level": "bootstrap",
  "cognitive_pattern": "orchestration"
}

# Get bootstrap-level capabilities (factory essentials)
$ curl -s "http://localhost:8000/api/catalog?power_level=bootstrap" | jq '.entries[] | .id'
"core.llm.invoke"
"core.session.create"
"core.session.destroy"
"tool.sdk.bash"
"tool.sdk.edit"
"tool.sdk.glob"
"tool.sdk.grep"
"tool.sdk.read"
"tool.sdk.task"
"tool.sdk.write"

# Get self-modifying capabilities (admin only)
$ curl -s "http://localhost:8000/api/catalog?power_level=self_modifying" | jq '.entries[] | {id, cognitive_pattern}'
{
  "id": "command.configure",
  "cognitive_pattern": "execution"
}
{
  "id": "skill.Hook Development",
  "cognitive_pattern": "procedural"
}
{
  "id": "skill.skill-creator",
  "cognitive_pattern": "procedural"
}

# Get client-safe capabilities (33 capabilities)
$ curl -s "http://localhost:8000/api/catalog?safe_for_client=true" | jq '.count'
33
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
from p3394_agent.core.capability_catalog import (
    CapabilityCatalog, CapabilityType, CapabilitySource,
    CapabilityPowerLevel, CognitivePattern, ComputeSubstrate
)

# Access via gateway
catalog = gateway.capability_catalog

# Basic query methods
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

### Power Level Queries

```python
# Query by power level
standard = catalog.list_by_power_level(CapabilityPowerLevel.STANDARD)
meta = catalog.list_by_power_level(CapabilityPowerLevel.META)
self_mod = catalog.list_by_power_level(CapabilityPowerLevel.SELF_MODIFYING)
bootstrap = catalog.list_by_power_level(CapabilityPowerLevel.BOOTSTRAP)

# Convenience methods
safe_caps = catalog.list_safe_for_client()      # STANDARD only, enabled
meta_skills = catalog.list_meta_skills()         # META level
self_mod_caps = catalog.list_self_modifying()    # SELF_MODIFYING level
factory_caps = catalog.list_bootstrap_essential() # BOOTSTRAP level
```

### Cognitive Pattern Queries

```python
# Query by cognitive pattern
execution = catalog.list_by_cognitive_pattern(CognitivePattern.EXECUTION)
procedural = catalog.list_by_cognitive_pattern(CognitivePattern.PROCEDURAL)
iterative = catalog.list_by_cognitive_pattern(CognitivePattern.ITERATIVE)
diagnostic = catalog.list_by_cognitive_pattern(CognitivePattern.DIAGNOSTIC)
generative = catalog.list_by_cognitive_pattern(CognitivePattern.GENERATIVE)
orchestration = catalog.list_by_cognitive_pattern(CognitivePattern.ORCHESTRATION)
reflective = catalog.list_by_cognitive_pattern(CognitivePattern.REFLECTIVE)

# Get all methodological skills (non-execution patterns)
methodological = catalog.list_methodological_skills()

# Convenience methods
iterative_skills = catalog.list_iterative_skills()    # Loop-until patterns
diagnostic_skills = catalog.list_diagnostic_skills()  # Hypothesis-test patterns
generative_skills = catalog.list_generative_skills()  # Creative ideation
orchestration_skills = catalog.list_orchestration_skills()  # Multi-capability coordination
```

### Compute Substrate Queries

```python
from p3394_agent.core.capability_catalog import ComputeSubstrate

# Query by compute substrate
symbolic = catalog.list_by_compute_substrate(ComputeSubstrate.SYMBOLIC)
neural = catalog.list_by_compute_substrate(ComputeSubstrate.NEURAL)
composite = catalog.list_by_compute_substrate(ComputeSubstrate.COMPOSITE)

# Convenience methods
symbolic_caps = catalog.list_symbolic_capabilities()  # Pure symbolic, no LLM
neural_caps = catalog.list_neural_capabilities()      # LLM-based
offline = catalog.list_offline_capable()              # Symbolic + enabled (works offline)
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
