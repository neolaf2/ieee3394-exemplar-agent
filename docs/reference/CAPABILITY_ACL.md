# Capability Access Control (CACL) System

The P3394 Agent implements a **three-layer authorization cascade** that provides fine-grained control over capability visibility and access.

## Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    Authorization Cascade                             │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  Layer 1: Channel Authentication                                     │
│  ─────────────────────────────────                                  │
│  • Channel adapter authenticates connection                          │
│  • Determines channel-specific identity                              │
│  • Maps to AssuranceLevel (NONE → CRYPTOGRAPHIC)                    │
│                         ↓                                            │
│  Layer 2: Principal Resolution                                       │
│  ─────────────────────────────                                      │
│  • Maps channel identity to Principal                                │
│  • Resolves roles from principal registry                            │
│  • Caches in session for performance                                 │
│                         ↓                                            │
│  Layer 3: Capability Role Mapping                                    │
│  ────────────────────────────────                                   │
│  • Each capability declares role→permission mappings                 │
│  • ACL registry determines visibility and access                     │
│  • Session caches computed permissions                               │
│                                                                      │
└─────────────────────────────────────────────────────────────────────┘
```

## Core Concepts

### Visibility Tiers

Capabilities have one of five visibility levels:

| Tier | Listed | Accessible | Description |
|------|--------|------------|-------------|
| `PUBLIC` | ✓ Everyone | ✓ Everyone | Publicly available capabilities |
| `LISTED` | ✓ Everyone | Auth Required | Visible but requires authentication |
| `PROTECTED` | Auth Required | Auth Required | Hidden until authenticated |
| `PRIVATE` | Never | Internal Only | Agent↔SubAgent internal use |
| `ADMIN` | Admin Only | Admin Only | Administrative functions |

### Permission Model (LRXMD)

Each capability can grant five distinct permissions:

| Permission | Description |
|------------|-------------|
| `LIST` | Can see the capability exists |
| `READ` | Can read capability metadata/schema |
| `EXECUTE` | Can invoke the capability |
| `MODIFY` | Can update capability configuration |
| `DELETE` | Can remove/disable the capability |

### Assurance Levels

Based on NIST 800-63-3, authentication strength is measured in assurance levels:

| Level | Value | Description |
|-------|-------|-------------|
| `NONE` | 0 | Anonymous/unauthenticated |
| `LOW` | 1 | Basic identity assertion |
| `MEDIUM` | 2 | Single factor authentication |
| `HIGH` | 3 | Multi-factor authentication |
| `CRYPTOGRAPHIC` | 4 | Cryptographic proof (certificates, signatures) |

### Principal Model

Principals are identified using URN format:

```
urn:principal:org:{organization}:role:{role}:person:{person}
```

Examples:
- `urn:principal:org:ieee:role:admin:person:alice`
- `urn:principal:org:public:role:user:person:anonymous`
- `urn:principal:channel:cli:role:owner:person:self`

## Configuration

### Defining Capability ACLs

Each capability's ACL is defined at creation time:

```python
from p3394_agent.core.capability_acl import (
    CapabilityAccessControl,
    CapabilityVisibility,
    CapabilityPermission,
    RolePermissionEntry,
    AssuranceLevel
)

# Example: A protected capability requiring authentication
acl = CapabilityAccessControl(
    capability_id="skill.document-generator",
    visibility=CapabilityVisibility.PROTECTED,
    default_permissions={CapabilityPermission.LIST},
    role_permissions=[
        RolePermissionEntry(
            role="user",
            permissions={
                CapabilityPermission.LIST,
                CapabilityPermission.READ,
                CapabilityPermission.EXECUTE
            },
            min_assurance=AssuranceLevel.MEDIUM
        ),
        RolePermissionEntry(
            role="admin",
            permissions={
                CapabilityPermission.LIST,
                CapabilityPermission.READ,
                CapabilityPermission.EXECUTE,
                CapabilityPermission.MODIFY,
                CapabilityPermission.DELETE
            },
            min_assurance=AssuranceLevel.HIGH
        )
    ]
)
```

### Built-in ACLs

The system includes 16 built-in capability ACLs:

| Capability | Visibility | Default Access |
|------------|------------|----------------|
| `legacy.command.help` | PUBLIC | Everyone can execute |
| `legacy.command.about` | PUBLIC | Everyone can execute |
| `legacy.command.version` | PUBLIC | Everyone can execute |
| `legacy.command.status` | LISTED | Authenticated users |
| `legacy.command.login` | LISTED | Login flow |
| `legacy.command.listSkills` | LISTED | Authenticated users |
| `legacy.command.endpoints` | PROTECTED | Authenticated users |
| `legacy.command.configure` | ADMIN | Admin only |
| `core.llm` | PROTECTED | Authenticated users |
| `core.skill_dispatch` | PROTECTED | Authenticated users |
| `core.subagent_dispatch` | PRIVATE | Internal only |
| `core.session_create` | LISTED | Users |
| `core.session_end` | PROTECTED | Owner only |
| `admin.principal_manage` | ADMIN | Admin only |
| `admin.acl_manage` | ADMIN | Admin only |
| `admin.channel_manage` | ADMIN | Admin only |

## Session Caching

For performance, capability access is computed once at session creation/login and cached:

```python
class Session:
    # Computed on authentication
    visible_capabilities: Set[str]      # Capabilities user can see
    accessible_capabilities: Set[str]   # Capabilities user can invoke
    capability_permissions: Dict[str, Set[str]]  # Per-capability permissions

    def can_list_capability(self, capability_id: str) -> bool: ...
    def can_execute_capability(self, capability_id: str) -> bool: ...
```

### Cache Invalidation

The session cache is recomputed when:
- User authenticates or re-authenticates
- User's role changes
- ACL configuration is modified (admin action)

## MCP Memory Integration

ACL configuration can be stored in the MCP memory server for:
- Persistent storage across restarts
- Swappable memory backends
- Dynamic capability provisioning

### Bootstrap Process

1. Agent starts and connects to MCP memory server
2. Loads ACL configurations from memory
3. Merges with built-in defaults
4. Applies to capability registry

### Memory Server Swapping

Different memory servers can provide different capability sets:

```yaml
# Standard deployment
memory:
  server: local-memory-server
  bootstrap:
    - default_acls.json

# Enterprise deployment
memory:
  server: enterprise-memory-server
  bootstrap:
    - default_acls.json
    - enterprise_acls.json
    - custom_acls.json
```

## Channel-Specific Authentication

Each channel adapter provides authentication appropriate to its transport:

### CLI Channel
- Detects if user is the owner (self)
- Owner gets `CRYPTOGRAPHIC` assurance (trusted local access)
- Other users get `LOW` assurance

### Web Channel
- Anonymous: `NONE`
- Session cookie: `LOW`
- API key: `MEDIUM`
- OAuth/JWT: `HIGH`
- mTLS certificate: `CRYPTOGRAPHIC`

### P3394 Protocol Channel
- Agent-to-agent: Based on agent credential binding
- Uses cryptographic verification when available

## API Reference

### CapabilityAccessManager

```python
class CapabilityAccessManager:
    def compute_session_access(
        self,
        session: Session,
        principal: Optional[Principal],
        assurance_level: AssuranceLevel
    ) -> None:
        """Compute and cache capability access for session."""

    def filter_visible_capabilities(
        self,
        session: Session,
        capabilities: List[AgentCapabilityDescriptor]
    ) -> List[AgentCapabilityDescriptor]:
        """Filter capabilities to those visible to session."""

    def check_access(
        self,
        session: Session,
        capability_id: str,
        permission: CapabilityPermission
    ) -> AccessDecision:
        """Check if session has specific permission."""

    def authorize_invocation(
        self,
        session: Session,
        capability_id: str
    ) -> AccessDecision:
        """Check if session can invoke capability."""
```

### AccessDecision

```python
@dataclass
class AccessDecision:
    allowed: bool
    reason: str
    required_assurance: Optional[AssuranceLevel] = None
    missing_permissions: Set[CapabilityPermission] = field(default_factory=set)
```

## Security Considerations

1. **Defense in Depth**: Three layers provide redundant security
2. **Least Privilege**: Default to minimal permissions
3. **Fail Closed**: Unknown capabilities default to PRIVATE
4. **Audit Trail**: All access decisions can be logged
5. **No Implicit Trust**: Even internal subagents use session-based access

## Example Flows

### Anonymous User Listing Capabilities

```
1. User connects via web channel (no auth)
2. Channel reports: AssuranceLevel.NONE, no principal
3. Session created with role="anonymous"
4. Visible capabilities = PUBLIC tier only
5. /help shows only: help, about, version
```

### Authenticated User Invoking Protected Capability

```
1. User authenticates via API key (MEDIUM assurance)
2. Principal resolved: urn:principal:org:acme:role:developer:person:bob
3. Session updated with role="developer"
4. Capability "core.llm" checked:
   - Visibility: PROTECTED ✓ (authenticated)
   - Permission: EXECUTE ✓ (developer role has it)
   - Assurance: MEDIUM ≥ LOW ✓
5. Invocation proceeds
```

### Admin Managing ACLs

```
1. Admin authenticates with MFA (HIGH assurance)
2. Principal: urn:principal:org:ieee:role:admin:person:alice
3. Session role="admin"
4. Capability "admin.acl_manage":
   - Visibility: ADMIN ✓
   - Permission: MODIFY ✓
   - Assurance: HIGH ≥ HIGH ✓
5. ACL modification allowed
```
