# P3394 Agent Long-Term Memory Specification

**Version:** 1.0.0-draft
**Date:** 2026-01-31
**Status:** Proposal
**Author:** Richard Tong, Claude

---

## 1. Executive Summary

This document specifies the Long-Term Memory (LTM) architecture for P3394-compliant agents. The memory system follows the KSTAR framework (Knowledge, Situation, Task, Action, Result) and is designed to be:

- **Local-first** - Memory primarily resides on user's machine
- **Portable** - Exportable format allows migration across machines/agents
- **User-owned** - Memory belongs to the user, not the service
- **Sync-capable** - Can synchronize with remote authoritative data sources
- **Domain-agnostic** - Core infrastructure supports any domain schema

The base `p3394_agent` SDK provides the memory infrastructure. Domain-specific schemas (education, healthcare, enterprise, etc.) are implemented as extensions.

---

## 2. Design Principles

### 2.1 Local-First
The agent runs primarily on the user's local machine. Memory is stored locally and remains accessible offline. Remote sync is optional and additive.

### 2.2 User Ownership
The user owns their agent's memory. They can:
- Export their complete memory at any time
- Import memory into a new agent instance
- Delete their memory
- Control what syncs to remote services

### 2.3 Portable Format
Memory uses an open, documented format (KSTAR Bundle) that any compliant agent can import. Users are never locked into a specific agent implementation.

### 2.4 Separation of Concerns
- **Infrastructure** (this spec) - Storage, sync, export/import, indexing
- **Schema** (domain-specific) - What facts, profiles, and traces look like

---

## 3. Memory Architecture

### 3.1 KSTAR Memory Classes

```
┌─────────────────────────────────────────────────────────────────┐
│                     KSTAR Memory System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐  │
│  │    EPISODIC     │  │   DECLARATIVE   │  │   PROCEDURAL    │  │
│  │    (Traces)     │  │  (Perceptions)  │  │    (Skills)     │  │
│  ├─────────────────┤  ├─────────────────┤  ├─────────────────┤  │
│  │ What happened   │  │ What I know     │  │ How to do       │  │
│  │ • Actions taken │  │ • Facts         │  │ • Learned       │  │
│  │ • Outcomes      │  │ • Observations  │  │   patterns      │  │
│  │ • Context       │  │ • Profiles      │  │ • Strategies    │  │
│  │ • Timestamps    │  │ • Relationships │  │ • Workflows     │  │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐│
│  │                    CONTROL TOKENS                            ││
│  │              (Authority to Execute)                          ││
│  ├─────────────────────────────────────────────────────────────┤│
│  │ • Capability grants    • Delegation chains                  ││
│  │ • Scope restrictions   • Expiration                         ││
│  │ • Revocation status    • Lineage tracking                   ││
│  └─────────────────────────────────────────────────────────────┘│
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

### 3.2 Memory Class Definitions

#### 3.2.1 Episodic Memory (Traces)

Records of agent actions following the STAR pattern:

```yaml
trace:
  id: "trace-uuid"
  timestamp: "ISO-8601"

  situation:
    domain: string           # e.g., "education.evaluation"
    actor: string            # Principal who triggered
    channel: string          # Channel used
    context: object          # Domain-specific context

  task:
    goal: string             # What was to be achieved
    constraints: list        # Any limitations

  action:
    type: string             # Action category
    parameters: object       # Action inputs
    tools_used: list         # Tools/skills invoked

  result:
    success: boolean
    outcome: object          # Domain-specific result
    side_effects: list       # Unintended consequences

  metadata:
    mode: string             # "interactive", "autonomous", "background"
    tags: list
    linked_traces: list      # Related trace IDs
```

#### 3.2.2 Declarative Memory (Perceptions & Facts)

Observations, beliefs, and factual knowledge:

```yaml
perception:
  id: "perception-uuid"
  type: string               # Perception category
  subject: string            # What/who this is about
  content: string            # Natural language description
  confidence: float          # 0.0 - 1.0
  evidence: list             # Trace IDs supporting this
  created_at: "ISO-8601"
  updated_at: "ISO-8601"
  valid_until: "ISO-8601"    # Optional expiration

fact:
  id: "fact-uuid"
  schema: string             # Domain-specific schema name
  data: object               # Schema-conformant data
  source: string             # Where this came from
  verified: boolean          # Has been validated
  created_at: "ISO-8601"
  updated_at: "ISO-8601"
```

#### 3.2.3 Procedural Memory (Skills)

Learned patterns and strategies:

```yaml
skill:
  id: "skill-uuid"
  name: string
  description: string

  # How this was learned
  learned_from:
    traces: list             # Trace IDs that contributed
    explicit_training: boolean

  # Skill definition
  definition:
    triggers: list           # When to apply
    preconditions: list      # Requirements
    procedure: string        # How to execute (or reference)

  # Maturity tracking
  maturity:
    level: enum              # "novice", "competent", "proficient", "expert"
    success_rate: float
    last_used: "ISO-8601"
    usage_count: integer
```

#### 3.2.4 Control Tokens

Authority grants for agent capabilities:

```yaml
control_token:
  token_id: string
  type: string               # Token type (capability-specific)

  # Authority
  scope: string              # What this grants access to
  permissions: list          # Specific permissions

  # Provenance
  granted_by: string         # Principal who granted
  granted_at: "ISO-8601"
  delegation_chain: list     # Full chain of custody

  # Validity
  expires_at: "ISO-8601"
  revoked: boolean
  revoked_at: "ISO-8601"
  revocation_reason: string

  # Verification
  signature: string          # Cryptographic signature
  lineage_hash: string       # Hash of delegation chain
```

---

## 4. Storage Architecture

### 4.1 Local Storage Structure

```
~/.p3394/
├── agents/
│   └── {agent-id}/
│       ├── config.yaml              # Agent configuration
│       ├── memory/
│       │   ├── traces/
│       │   │   ├── index.sqlite     # Trace index for queries
│       │   │   └── data/
│       │   │       ├── 2026-01/     # Partitioned by month
│       │   │       │   └── traces.jsonl
│       │   │       └── 2026-02/
│       │   ├── perceptions/
│       │   │   ├── index.sqlite
│       │   │   └── perceptions.jsonl
│       │   ├── facts/
│       │   │   ├── index.sqlite
│       │   │   └── facts.jsonl
│       │   ├── skills/
│       │   │   └── skills.yaml
│       │   └── tokens/
│       │       ├── active.yaml
│       │       └── revoked.yaml
│       ├── sync/
│       │   ├── state.yaml           # Last sync timestamps
│       │   └── pending/             # Queued sync operations
│       └── export/
│           └── {timestamp}.kstar    # Exported bundles
└── shared/
    └── schemas/                     # Domain schemas
        ├── education.yaml
        └── ...
```

### 4.2 Storage Backend Interface

The memory system uses a pluggable storage backend:

```python
class MemoryStorageBackend(ABC):
    """Abstract storage backend for KSTAR memory."""

    @abstractmethod
    async def store_trace(self, trace: Trace) -> str:
        """Store a trace, return ID."""
        pass

    @abstractmethod
    async def get_trace(self, trace_id: str) -> Optional[Trace]:
        """Retrieve a trace by ID."""
        pass

    @abstractmethod
    async def query_traces(
        self,
        filters: dict,
        limit: int = 100,
        offset: int = 0
    ) -> list[Trace]:
        """Query traces with filters."""
        pass

    @abstractmethod
    async def store_perception(self, perception: Perception) -> str:
        pass

    @abstractmethod
    async def store_fact(self, fact: Fact, schema: str) -> str:
        pass

    @abstractmethod
    async def store_skill(self, skill: Skill) -> str:
        pass

    @abstractmethod
    async def store_control_token(self, token: ControlToken) -> str:
        pass

    @abstractmethod
    async def verify_control_token(self, token_id: str) -> TokenVerification:
        pass

    @abstractmethod
    async def export_all(self) -> KStarBundle:
        """Export complete memory as bundle."""
        pass

    @abstractmethod
    async def import_bundle(self, bundle: KStarBundle) -> ImportResult:
        """Import memory from bundle."""
        pass
```

### 4.3 Supported Backends

| Backend | Use Case | Persistence | Sync Support |
|---------|----------|-------------|--------------|
| `LocalFileBackend` | Default, local-first | Yes | Yes |
| `SQLiteBackend` | Fast queries | Yes | Yes |
| `MemoryBackend` | Testing, ephemeral | No | No |
| `SupabaseBackend` | Cloud sync | Yes | Primary |
| `S3Backend` | Archive/backup | Yes | Export only |

---

## 5. Export/Import Format

### 5.1 KSTAR Bundle Format

```json
{
  "format": "kstar-bundle",
  "version": "1.0.0",
  "exported_at": "2026-01-31T15:00:00Z",

  "agent": {
    "id": "agent-uuid",
    "type": "student_companion",
    "version": "1.0.0"
  },

  "memory": {
    "traces": [
      { "id": "...", "timestamp": "...", "situation": {...}, ... }
    ],
    "perceptions": [
      { "id": "...", "type": "...", "content": "...", ... }
    ],
    "facts": [
      { "id": "...", "schema": "education.learner_profile", "data": {...}, ... }
    ],
    "skills": [
      { "id": "...", "name": "...", "maturity": {...}, ... }
    ],
    "control_tokens": [
      // Included only with explicit --include-tokens flag
      // Tokens are sensitive and may be excluded by default
    ]
  },

  "schemas_used": [
    "education.learner_profile",
    "education.study_pattern"
  ],

  "statistics": {
    "trace_count": 1523,
    "perception_count": 89,
    "fact_count": 12,
    "skill_count": 7,
    "date_range": {
      "earliest": "2025-09-01T00:00:00Z",
      "latest": "2026-01-31T15:00:00Z"
    }
  },

  "integrity": {
    "checksum": "sha256:abc123...",
    "signature": "optional-user-signature"
  }
}
```

### 5.2 Export Options

```bash
# Full export (excluding control tokens by default)
p3394-agent export-memory --output my-memory.kstar

# Include control tokens (requires confirmation)
p3394-agent export-memory --include-tokens --output my-memory.kstar

# Export specific date range
p3394-agent export-memory --from 2025-09-01 --to 2026-01-31 --output semester.kstar

# Export specific memory types
p3394-agent export-memory --types traces,facts --output traces-only.kstar

# Encrypt export
p3394-agent export-memory --encrypt --passphrase-file key.txt --output encrypted.kstar
```

### 5.3 Import Options

```bash
# Import (merge with existing)
p3394-agent import-memory --from my-memory.kstar

# Import (replace existing - requires confirmation)
p3394-agent import-memory --from my-memory.kstar --replace

# Import specific types only
p3394-agent import-memory --from my-memory.kstar --types facts,skills

# Verify bundle integrity without importing
p3394-agent verify-bundle my-memory.kstar
```

---

## 6. Synchronization

### 6.1 Sync Model

```
┌─────────────────────┐                    ┌─────────────────────┐
│   Local Memory      │                    │   Remote Service    │
│   (Primary)         │                    │   (Secondary)       │
├─────────────────────┤                    ├─────────────────────┤
│ • Traces            │◄──── Sync ────────►│ • Inbox messages    │
│ • Perceptions       │     (bi-dir)       │ • Authoritative data│
│ • Facts             │                    │ • Token grants      │
│ • Skills            │                    │                     │
│ • Control Tokens    │                    │                     │
└─────────────────────┘                    └─────────────────────┘
        │                                           │
        └───────────────────┬───────────────────────┘
                            │
                    ┌───────▼───────┐
                    │  Sync Engine  │
                    ├───────────────┤
                    │ • Conflict    │
                    │   resolution  │
                    │ • Delta sync  │
                    │ • Retry queue │
                    └───────────────┘
```

### 6.2 Sync Triggers

| Trigger | Description |
|---------|-------------|
| `on_wake` | When agent starts |
| `on_idle` | After period of inactivity |
| `on_action` | After significant action (configurable) |
| `periodic` | Background interval (configurable) |
| `manual` | User-initiated |

### 6.3 Sync Configuration

```yaml
sync:
  enabled: true

  triggers:
    on_wake: true
    on_idle: true
    idle_threshold: "5m"
    periodic:
      enabled: true
      interval: "1h"

  remote:
    endpoint: "https://lms.example.com/api/v1"
    auth:
      method: "api_key"
      key_env: "LMS_API_KEY"

  # What to sync
  push:
    - traces        # Push local traces to remote
    - facts         # Push local facts

  pull:
    - inbox         # Pull pending messages
    - tokens        # Pull token grants/revocations
    - facts         # Pull authoritative facts

  conflict_resolution:
    traces: "local_wins"      # Local is authoritative
    facts: "remote_wins"      # Remote is authoritative
    tokens: "remote_wins"     # Remote is authoritative
```

### 6.4 Sync Protocol

```python
async def sync(self, direction: str = "bidirectional"):
    """Execute sync with remote service."""

    # 1. Get local sync state
    local_state = await self.get_sync_state()

    # 2. Request remote changes since last sync
    remote_changes = await self.remote.get_changes_since(
        local_state.last_sync_timestamp
    )

    # 3. Get local changes since last sync
    local_changes = await self.get_local_changes_since(
        local_state.last_sync_timestamp
    )

    # 4. Resolve conflicts
    resolved = await self.resolve_conflicts(local_changes, remote_changes)

    # 5. Apply remote changes locally
    await self.apply_changes(resolved.to_apply_locally)

    # 6. Push local changes to remote
    await self.remote.push_changes(resolved.to_push_remotely)

    # 7. Update sync state
    await self.update_sync_state(resolved.new_timestamp)

    return SyncResult(
        pulled=len(resolved.to_apply_locally),
        pushed=len(resolved.to_push_remotely),
        conflicts=len(resolved.conflicts)
    )
```

---

## 7. Control Token System

### 7.1 Token Types

| Type | Purpose | Example |
|------|---------|---------|
| `capability_grant` | Authority to use a capability | "Can evaluate artifacts" |
| `resource_access` | Access to specific resource | "Can read course CS101" |
| `delegation` | Authority to grant to others | "Can grant submission rights" |
| `session` | Temporary session authority | "Active learning session" |

### 7.2 Token Lifecycle

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   CREATED   │────►│   ACTIVE    │────►│   EXPIRED   │
└─────────────┘     └──────┬──────┘     └─────────────┘
                          │
                          │ revoke()
                          ▼
                   ┌─────────────┐
                   │   REVOKED   │
                   └─────────────┘
```

### 7.3 Token Operations

```python
class ControlTokenManager:
    """Manage control tokens for agent capabilities."""

    async def store_token(self, token: ControlToken) -> str:
        """Store a new control token."""
        # Validate token signature
        if not self.verify_signature(token):
            raise InvalidTokenError("Invalid signature")

        # Check delegation chain
        if token.delegation_chain:
            await self.verify_delegation_chain(token)

        # Store token
        return await self.storage.store_control_token(token)

    async def verify_token(self, token_id: str, scope: str) -> TokenVerification:
        """Verify token is valid for given scope."""
        token = await self.storage.get_control_token(token_id)

        if not token:
            return TokenVerification(valid=False, reason="Token not found")

        if token.revoked:
            return TokenVerification(valid=False, reason="Token revoked")

        if token.expires_at < datetime.now():
            return TokenVerification(valid=False, reason="Token expired")

        if not self.scope_matches(token.scope, scope):
            return TokenVerification(valid=False, reason="Scope mismatch")

        return TokenVerification(valid=True, token=token)

    async def revoke_token(self, token_id: str, reason: str) -> bool:
        """Revoke a control token."""
        token = await self.storage.get_control_token(token_id)
        if not token:
            return False

        token.revoked = True
        token.revoked_at = datetime.now()
        token.revocation_reason = reason

        await self.storage.update_control_token(token)

        # Sync revocation to remote
        await self.sync_revocation(token_id)

        return True

    async def get_token_lineage(self, token_id: str) -> list[ControlToken]:
        """Get full delegation chain for a token."""
        token = await self.storage.get_control_token(token_id)
        if not token:
            return []

        lineage = [token]
        for parent_id in token.delegation_chain:
            parent = await self.storage.get_control_token(parent_id)
            if parent:
                lineage.append(parent)

        return lineage
```

---

## 8. Query Interface

### 8.1 Trace Queries

```python
# Query by time range
traces = await memory.query_traces(
    filters={
        "timestamp": {"gte": "2026-01-01", "lte": "2026-01-31"}
    }
)

# Query by situation domain
traces = await memory.query_traces(
    filters={
        "situation.domain": "education.evaluation"
    }
)

# Query by result success
traces = await memory.query_traces(
    filters={
        "result.success": True,
        "action.type": "artifact_evaluation"
    }
)

# Full-text search in traces
traces = await memory.search_traces(
    query="recursion feedback",
    fields=["situation.context", "result.outcome"]
)
```

### 8.2 Perception Queries

```python
# Get perceptions about a subject
perceptions = await memory.get_perceptions(
    subject="student-123",
    min_confidence=0.7
)

# Get recent perceptions
perceptions = await memory.query_perceptions(
    filters={
        "updated_at": {"gte": "2026-01-01"}
    },
    order_by="-confidence"
)
```

### 8.3 Fact Queries

```python
# Get facts by schema
facts = await memory.get_facts(schema="learner_profile")

# Query facts with JSONPath
facts = await memory.query_facts(
    schema="learner_profile",
    path="$.learning_style",
    value="visual"
)
```

---

## 9. API Reference

### 9.1 KStarMemory Class

```python
class KStarMemory:
    """Main interface for KSTAR long-term memory."""

    def __init__(
        self,
        storage_backend: MemoryStorageBackend,
        sync_config: Optional[SyncConfig] = None
    ):
        """Initialize memory with storage backend."""
        pass

    # Trace operations
    async def store_trace(self, trace: dict) -> str: ...
    async def get_trace(self, trace_id: str) -> Optional[Trace]: ...
    async def query_traces(self, filters: dict, **kwargs) -> list[Trace]: ...
    async def search_traces(self, query: str, **kwargs) -> list[Trace]: ...

    # Perception operations
    async def store_perception(self, perception: dict) -> str: ...
    async def get_perceptions(self, subject: str, **kwargs) -> list[Perception]: ...
    async def update_perception(self, perception_id: str, updates: dict) -> bool: ...

    # Fact operations
    async def store_fact(self, fact: dict, schema: str) -> str: ...
    async def get_facts(self, schema: str) -> list[Fact]: ...
    async def query_facts(self, schema: str, path: str, value: Any) -> list[Fact]: ...

    # Skill operations
    async def store_skill(self, skill: dict) -> str: ...
    async def get_skill(self, skill_name: str) -> Optional[Skill]: ...
    async def update_skill_maturity(self, skill_name: str, outcome: bool) -> None: ...

    # Control token operations
    async def store_control_token(self, token: dict) -> str: ...
    async def verify_control_token(self, token_id: str, scope: str) -> TokenVerification: ...
    async def revoke_control_token(self, token_id: str, reason: str) -> bool: ...
    async def get_token_lineage(self, token_id: str) -> list[ControlToken]: ...
    async def list_tokens_by_type(self, token_type: str) -> list[ControlToken]: ...

    # Sync operations
    async def sync(self, direction: str = "bidirectional") -> SyncResult: ...
    async def get_sync_state(self) -> SyncState: ...

    # Export/Import
    async def export_bundle(self, options: ExportOptions) -> KStarBundle: ...
    async def import_bundle(self, bundle: KStarBundle, options: ImportOptions) -> ImportResult: ...

    # Statistics
    async def get_stats(self) -> MemoryStats: ...
```

### 9.2 MCP Tools

The memory system exposes MCP tools for agent use:

```yaml
tools:
  - name: "mcp__kstar__store_trace"
    description: "Store an episodic trace in long-term memory"

  - name: "mcp__kstar__query_memory"
    description: "Query traces, perceptions, or facts"

  - name: "mcp__kstar__store_perception"
    description: "Store an observation or insight"

  - name: "mcp__kstar__store_fact"
    description: "Store a factual record"

  - name: "mcp__kstar__update_skill"
    description: "Update skill maturity after use"

  - name: "mcp__kstar__store_control_token"
    description: "Store a capability token"

  - name: "mcp__kstar__verify_control_token"
    description: "Verify token validity for scope"

  - name: "mcp__kstar__revoke_control_token"
    description: "Revoke a control token"

  - name: "mcp__kstar__get_token_lineage"
    description: "Get delegation chain for token"

  - name: "mcp__kstar__export_memory"
    description: "Export memory to portable bundle"
```

---

## 10. Extension Points

### 10.1 Domain Schemas

Domain-specific implementations define their own fact schemas:

```yaml
# schemas/education.yaml
schemas:
  learner_profile:
    type: object
    properties:
      learning_style:
        type: string
        enum: ["visual", "auditory", "kinesthetic", "reading"]
      strengths:
        type: array
        items: { type: string }
      growth_areas:
        type: array
        items: { type: string }
      preferred_ai_tools:
        type: array
        items: { type: string }
      study_patterns:
        type: object
        properties:
          peak_hours: { type: array }
          session_length_preferred: { type: string }

  teacher_profile:
    type: object
    properties:
      teaching_style:
        type: string
      feedback_tone:
        type: string
      expertise_areas:
        type: array
        items: { type: string }
```

### 10.2 Custom Trace Categories

Domains can register custom trace categories:

```python
# Education domain trace categories
memory.register_trace_category(
    name="artifact_evaluation",
    domain="education.evaluation",
    required_fields=["artifact_id", "rubric_id", "scores"]
)

memory.register_trace_category(
    name="module_authoring",
    domain="education.curriculum",
    required_fields=["module_id", "learning_objectives"]
)
```

### 10.3 Custom Token Types

Domains can define custom control token types:

```python
# Education domain token types
memory.register_token_type(
    name="evaluation_authority",
    description="Authority to evaluate student artifacts",
    scope_pattern="course:{course_id}",
    required_permissions=["evaluate", "feedback"]
)

memory.register_token_type(
    name="submission_authority",
    description="Authority to submit artifacts",
    scope_pattern="assignment:{assignment_id}",
    required_permissions=["submit", "resubmit"]
)
```

---

## 11. Security Considerations

### 11.1 Local Storage Security
- Memory files should use appropriate file permissions (600)
- Sensitive facts can be marked for encryption at rest
- Control tokens should be stored separately with stricter permissions

### 11.2 Export Security
- Control tokens excluded from exports by default
- Optional encryption for export bundles
- Checksum verification on import

### 11.3 Sync Security
- All sync communication over HTTPS
- API key or OAuth authentication
- Token revocations propagate immediately

### 11.4 Token Security
- Cryptographic signatures on control tokens
- Delegation chain verification
- Automatic expiration enforcement

---

## 12. Implementation Checklist

### 12.1 Core Infrastructure (p3394_agent)
- [ ] `KStarMemory` class with all operations
- [ ] `LocalFileBackend` storage implementation
- [ ] `SQLiteBackend` for fast queries
- [ ] Control token manager
- [ ] Export/import functionality
- [ ] Sync engine
- [ ] MCP tools for memory access
- [ ] Schema registry for domain extensions

### 12.2 Domain Extensions (per domain)
- [ ] Domain-specific fact schemas
- [ ] Custom trace categories
- [ ] Custom token types
- [ ] Profile schemas (learner, teacher, etc.)

### 12.3 P3394 Subagent Architecture
- [ ] KSTAR Memory P3394 manifest definition
- [ ] Session registry for subagent registration
- [ ] Outbound channel adapter framework
- [ ] Transport adapters:
  - [ ] Direct Python transport (in-process)
  - [ ] MCP stdio transport
  - [ ] HTTP REST transport
  - [ ] Unix socket transport
- [ ] P3394 client libraries:
  - [ ] Python client
  - [ ] JavaScript/TypeScript client
  - [ ] CLI tool (`p3394 send`)
- [ ] Transport health monitoring
- [ ] Automatic transport failover

---

## 13. KSTAR Memory as P3394 Subagent

### 13.1 Architectural Overview

The KSTAR Memory system operates as a **registered P3394 subagent**, not as a direct library call. This design principle ensures:

- **Consistent agentic interface** - Memory operations look the same whether invoked from Python, JavaScript, Bash, or any channel
- **Transport abstraction** - The same P3394 message can be delivered via MCP, HTTP, direct call, or Unix socket
- **Semantic transparency** - Memory operations are channel-agnostic; the P3394 UMF captures the semantic meaning regardless of transport
- **Composability** - Memory server can run in-process, as a sidecar, or as a remote service

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        P3394 Agent Gateway                               │
│                    (Message Router / Orchestrator)                       │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   Inbound Channels              Session Registry          Outbound Routing│
│  ┌─────────────┐              ┌───────────────────┐     ┌─────────────┐  │
│  │  WhatsApp   │              │ Registered        │     │  Outbound   │  │
│  │  Web Chat   │─────────────►│ Subagents:        │────►│  Channel    │  │
│  │  CLI        │  P3394 UMF   │ • kstar-memory    │     │  Adapter    │  │
│  │  MCP        │              │ • other-subagent  │     │  (P3394→    │  │
│  │  HTTP API   │              │ ...               │     │   Transport)│  │
│  └─────────────┘              └───────────────────┘     └──────┬──────┘  │
│                                                                 │        │
└─────────────────────────────────────────────────────────────────┼────────┘
                                                                  │
                              ┌────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                     KSTAR Memory Subagent                                │
│                  (P3394-Compliant Memory Server)                         │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   P3394 Manifest                    Transport Adapters                   │
│  ┌───────────────────┐            ┌────────────────────┐                │
│  │ agent_id:         │            │ • MCP stdio        │                │
│  │   kstar-memory    │            │ • HTTP REST        │                │
│  │ capabilities:     │            │ • Direct Python    │                │
│  │   store_trace     │            │ • Unix Socket      │                │
│  │   query_memory    │            │ • gRPC (future)    │                │
│  │   store_token     │            └────────────────────┘                │
│  │   ...             │                                                   │
│  └───────────────────┘                                                   │
│                                                                          │
│   Storage Backend (Pluggable)                                            │
│  ┌─────────────────────────────────────────────────────────────────────┐│
│  │  LocalFile │ SQLite │ Supabase │ Memory (ephemeral) │ S3 (archive)  ││
│  └─────────────────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────────────────┘
```

### 13.2 P3394 Manifest for Memory Server

The KSTAR Memory subagent declares its capabilities through a P3394 manifest:

```yaml
# kstar-memory-manifest.yaml
agent:
  agent_id: "kstar-memory"
  display_name: "KSTAR Long-Term Memory"
  version: "1.0.0"
  type: "subagent"

  # How this subagent can be reached
  transports:
    - type: "mcp_stdio"
      command: "p3394-memory-server"
      args: ["--mode", "stdio"]
    - type: "http"
      endpoint: "http://localhost:8001"
    - type: "direct"
      module: "p3394_agent.memory.kstar"
      class: "KStarMemoryServer"
    - type: "unix_socket"
      path: "/tmp/kstar-memory.sock"

capabilities:
  # Episodic Memory (Traces)
  - capability_id: "kstar:store_trace"
    description: "Store a KSTAR trace (episodic memory)"
    input_schema:
      type: object
      required: ["situation", "task", "action"]
      properties:
        situation: { type: object }
        task: { type: object }
        action: { type: object }
        result: { type: object }
    output_schema:
      type: object
      properties:
        trace_id: { type: string }

  - capability_id: "kstar:query_traces"
    description: "Query episodic memory"
    input_schema:
      type: object
      properties:
        filters: { type: object }
        limit: { type: integer, default: 100 }
        offset: { type: integer, default: 0 }
    output_schema:
      type: array
      items: { $ref: "#/definitions/Trace" }

  # Declarative Memory (Perceptions & Facts)
  - capability_id: "kstar:store_perception"
    description: "Store an observation or insight"
    input_schema:
      type: object
      required: ["content"]
      properties:
        type: { type: string }
        subject: { type: string }
        content: { type: string }
        confidence: { type: number, minimum: 0, maximum: 1 }
    output_schema:
      type: object
      properties:
        perception_id: { type: string }

  - capability_id: "kstar:store_fact"
    description: "Store a factual record"
    input_schema:
      type: object
      required: ["schema", "data"]
      properties:
        schema: { type: string }
        data: { type: object }
        source: { type: string }
    output_schema:
      type: object
      properties:
        fact_id: { type: string }

  # Procedural Memory (Skills)
  - capability_id: "kstar:store_skill"
    description: "Store or update a learned skill"
    input_schema:
      type: object
      required: ["name", "definition"]
    output_schema:
      type: object
      properties:
        skill_id: { type: string }

  - capability_id: "kstar:update_skill_maturity"
    description: "Update skill maturity after use"
    input_schema:
      type: object
      required: ["skill_name", "outcome"]

  # Control Tokens
  - capability_id: "kstar:store_control_token"
    description: "Store a capability token"
    input_schema:
      type: object
      required: ["token_type", "scope"]
    output_schema:
      type: object
      properties:
        token_id: { type: string }

  - capability_id: "kstar:verify_control_token"
    description: "Verify token validity for scope"
    input_schema:
      type: object
      required: ["token_id", "scope"]
    output_schema:
      type: object
      properties:
        valid: { type: boolean }
        reason: { type: string }

  - capability_id: "kstar:revoke_control_token"
    description: "Revoke a control token"
    input_schema:
      type: object
      required: ["token_id", "reason"]

  - capability_id: "kstar:get_token_lineage"
    description: "Get delegation chain for token"
    input_schema:
      type: object
      required: ["token_id"]

  # Export/Import
  - capability_id: "kstar:export_bundle"
    description: "Export memory to portable bundle"
    input_schema:
      type: object
      properties:
        include_tokens: { type: boolean, default: false }
        types: { type: array, items: { type: string } }
    output_schema:
      type: object
      properties:
        bundle: { $ref: "#/definitions/KStarBundle" }

  - capability_id: "kstar:import_bundle"
    description: "Import memory from bundle"
    input_schema:
      type: object
      required: ["bundle"]
    output_schema:
      type: object
      properties:
        imported_count: { type: integer }
        conflicts: { type: array }
```

### 13.3 Registration in Session Registry

When the P3394 agent starts, it registers the KSTAR Memory subagent in its session registry:

```python
# During agent initialization
class AgentGateway:
    async def _register_subagents(self):
        """Register built-in subagents including KSTAR memory."""

        # Load KSTAR memory manifest
        kstar_manifest = await self._load_manifest("kstar-memory")

        # Register in session registry
        self.session_registry.register_subagent(
            agent_id="kstar-memory",
            manifest=kstar_manifest,
            transport_preference=["direct", "mcp_stdio", "http"],
            auto_start=True
        )

        # The subagent is now addressable via P3394 messages
        # p3394://kstar-memory/store_trace
        # p3394://kstar-memory/query_memory
```

**Session Registry Structure:**

```yaml
session_registry:
  parent_agent:
    agent_id: "ieee3394-exemplar"
    capabilities: [...]

  registered_subagents:
    - agent_id: "kstar-memory"
      manifest_ref: "kstar-memory-manifest.yaml"
      status: "active"
      transport_active: "direct"  # Currently using direct Python calls
      last_heartbeat: "2026-01-31T15:00:00Z"

    - agent_id: "other-subagent"
      manifest_ref: "other-manifest.yaml"
      status: "active"
      transport_active: "mcp_stdio"
```

### 13.4 P3394 Message Flow for Memory Operations

All memory operations are expressed as P3394 Universal Message Format (UMF) messages. The transport layer is transparent to the sender.

**Example: Storing a Trace**

```yaml
# P3394 UMF Message
message:
  id: "msg-uuid-123"
  type: "request"
  timestamp: "2026-01-31T15:00:00Z"

  source:
    agent_id: "ieee3394-exemplar"
    channel_id: "web"
    session_id: "sess-456"

  destination:
    agent_id: "kstar-memory"
    capability_id: "kstar:store_trace"

  content:
    - type: "json"
      data:
        situation:
          domain: "education.evaluation"
          actor: "urn:principal:org:ieee:role:teacher:person:smith"
          channel: "web"
          now: "2026-01-31T15:00:00Z"
        task:
          goal: "Evaluate student submission"
          constraints: ["rubric-v2"]
        action:
          type: "artifact_evaluation"
          parameters:
            artifact_id: "artifact-789"
            rubric_id: "rubric-v2"
        result:
          success: true
          outcome:
            score: 85
            feedback: "Good work on recursion examples"
```

**Response:**

```yaml
message:
  id: "msg-uuid-124"
  type: "response"
  reply_to: "msg-uuid-123"

  source:
    agent_id: "kstar-memory"

  destination:
    agent_id: "ieee3394-exemplar"
    session_id: "sess-456"

  content:
    - type: "json"
      data:
        trace_id: "trace-xyz-789"
        stored_at: "2026-01-31T15:00:01Z"
```

### 13.5 Outbound Channel Adapter Transformation

The Outbound Channel Adapter transforms P3394 UMF messages to the appropriate transport format:

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Outbound Channel Adapter                          │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   Input: P3394 UMF Message                                           │
│                                                                      │
│   ┌───────────────────────────────────────────────────────────────┐ │
│   │ 1. Lookup destination agent in session registry               │ │
│   │ 2. Get preferred transport from registry                      │ │
│   │ 3. Transform UMF to transport-specific format                 │ │
│   │ 4. Send via transport                                         │ │
│   │ 5. Transform response back to UMF                             │ │
│   └───────────────────────────────────────────────────────────────┘ │
│                                                                      │
│   Output: P3394 UMF Response                                         │
└─────────────────────────────────────────────────────────────────────┘
```

**Transport Transformations:**

#### MCP stdio Transport

```python
class MCPOutboundAdapter:
    """Transform P3394 UMF to MCP tool calls."""

    def transform_request(self, umf_message: P3394Message) -> MCPToolCall:
        """Transform UMF request to MCP tool call."""
        capability = umf_message.destination.capability_id
        content = umf_message.content[0].data

        # Map P3394 capability to MCP tool name
        tool_name = self._capability_to_tool(capability)
        # e.g., "kstar:store_trace" -> "mcp__kstar__store_trace"

        return MCPToolCall(
            name=tool_name,
            arguments=content
        )

    def transform_response(self, mcp_result: MCPToolResult, original: P3394Message) -> P3394Message:
        """Transform MCP result back to UMF response."""
        return P3394Message(
            type="response",
            reply_to=original.id,
            source=P3394Address(agent_id=original.destination.agent_id),
            destination=original.source,
            content=[P3394Content(type="json", data=mcp_result.content)]
        )
```

#### HTTP REST Transport

```python
class HTTPOutboundAdapter:
    """Transform P3394 UMF to HTTP requests."""

    async def transform_and_send(self, umf_message: P3394Message) -> P3394Message:
        """Transform UMF to HTTP and send."""
        endpoint = self._get_endpoint(umf_message.destination.agent_id)
        capability = umf_message.destination.capability_id
        content = umf_message.content[0].data

        # POST /capabilities/{capability_id}
        url = f"{endpoint}/capabilities/{capability}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "message_id": umf_message.id,
                    "source": umf_message.source.to_dict(),
                    "content": content
                },
                headers={
                    "X-P3394-Message-ID": umf_message.id,
                    "X-P3394-Source": umf_message.source.agent_id
                }
            )

        return self._transform_response(response, umf_message)
```

#### Direct Python Transport

```python
class DirectOutboundAdapter:
    """Direct in-process calls (no serialization overhead)."""

    def __init__(self, subagent_instances: dict):
        self.instances = subagent_instances

    async def send(self, umf_message: P3394Message) -> P3394Message:
        """Route directly to in-process subagent."""
        agent_id = umf_message.destination.agent_id
        capability = umf_message.destination.capability_id
        content = umf_message.content[0].data

        # Get the subagent instance
        subagent = self.instances.get(agent_id)
        if not subagent:
            raise SubagentNotFoundError(agent_id)

        # Call the capability method directly
        method = getattr(subagent, self._capability_to_method(capability))
        result = await method(**content)

        return P3394Message(
            type="response",
            reply_to=umf_message.id,
            source=P3394Address(agent_id=agent_id),
            destination=umf_message.source,
            content=[P3394Content(type="json", data=result)]
        )
```

### 13.6 Supported Transport Channels

| Transport | Latency | Process Boundary | Use Case |
|-----------|---------|------------------|----------|
| **Direct Python** | ~1ms | Same process | Default for in-process memory |
| **MCP stdio** | ~10ms | Child process | Standard MCP server integration |
| **Unix Socket** | ~5ms | Same machine | High-performance local IPC |
| **HTTP REST** | ~50ms | Network | Remote memory server |
| **gRPC** (future) | ~20ms | Network | High-performance remote |

**Transport Selection Logic:**

```python
class OutboundRouter:
    """Route P3394 messages to appropriate transport."""

    def select_transport(self, agent_id: str, preference: list[str] = None) -> str:
        """Select best available transport for subagent."""
        registration = self.registry.get_subagent(agent_id)
        available = registration.manifest.transports

        preference = preference or ["direct", "unix_socket", "mcp_stdio", "http"]

        for transport_type in preference:
            if transport_type in [t.type for t in available]:
                if self._is_transport_healthy(agent_id, transport_type):
                    return transport_type

        raise NoTransportAvailableError(agent_id)
```

### 13.7 Multi-Language Client Support

The P3394 subagent architecture enables consistent access from any language:

**Python:**

```python
from p3394_agent import P3394Client

async with P3394Client() as client:
    result = await client.send(
        destination="kstar-memory",
        capability="kstar:store_trace",
        content={"situation": {...}, "task": {...}, "action": {...}}
    )
```

**JavaScript/TypeScript:**

```typescript
import { P3394Client } from '@ieee3394/client';

const client = new P3394Client();
const result = await client.send({
  destination: 'kstar-memory',
  capability: 'kstar:store_trace',
  content: { situation: {...}, task: {...}, action: {...} }
});
```

**Bash (via CLI):**

```bash
# Using p3394-cli
p3394 send kstar-memory kstar:store_trace \
  --content '{"situation": {...}, "task": {...}, "action": {...}}'

# Or as MCP tool call
p3394 mcp call mcp__kstar__store_trace \
  --arg situation='{"domain": "education"}' \
  --arg task='{"goal": "evaluate"}'
```

### 13.8 Semantic Transparency Principle

The key architectural insight is that **P3394 UMF provides semantic transparency**:

```
┌─────────────────────────────────────────────────────────────────────┐
│                     Same Semantic Meaning                            │
│                                                                      │
│   "Store this trace in long-term memory"                            │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│   P3394 UMF:                                                        │
│   { destination: "kstar-memory",                                    │
│     capability: "kstar:store_trace",                                │
│     content: {...} }                                                │
│                                                                      │
│         │                   │                   │                   │
│         ▼                   ▼                   ▼                   │
│   ┌─────────────┐    ┌─────────────┐    ┌─────────────┐           │
│   │   MCP Tool  │    │  HTTP POST  │    │   Python    │           │
│   │   Call      │    │  /store     │    │   method()  │           │
│   └─────────────┘    └─────────────┘    └─────────────┘           │
│                                                                      │
│   Transport-specific format differs, semantic meaning identical      │
└─────────────────────────────────────────────────────────────────────┘
```

This means:
- An LLM calling `mcp__kstar__store_trace`
- A Python function calling `client.send("kstar-memory", "kstar:store_trace", {...})`
- A Bash script running `p3394 send kstar-memory kstar:store_trace`

All result in **the same P3394 UMF message** being delivered to the KSTAR Memory subagent, with **identical semantic meaning and outcome**.

---

## 14. References

- KSTAR Memory Framework (internal)
- P3394 Universal Message Format Specification
- P3394 Principal and Credential Specification
- P3394 Channel Adapter Specification
- Claude Agent SDK Documentation
- Model Context Protocol (MCP) Specification

---

**Document Status:** Draft for review
**Target Implementation:** p3394_agent v0.3.0
