# P3394 Authentication & Authorization - Implementation Summary

## Phase 1: Core Infrastructure (COMPLETED)

### What Was Implemented

#### 1. Core Data Models (`src/ieee3394_agent/core/auth/`)

**principal.py** - Semantic identity model
- `Principal`: Org-Role-Person composite URN structure
- `PrincipalType`: HUMAN, AGENT, SERVICE, SYSTEM, ANONYMOUS
- `AssuranceLevel`: NONE, LOW, MEDIUM, HIGH, CRYPTOGRAPHIC
- `ClientPrincipalAssertion`: Channel-emitted identity claims
- `ServicePrincipalContext`: Agent operating context

**credential_binding.py** - Channel identity mappings
- `CredentialBinding`: Maps channel identities to principals
- `BindingType`: ACCOUNT, OAUTH, API_KEY, CERTIFICATE, SSH_KEY, PHONE, EMAIL, etc.
- Wildcard matching support (e.g., `local:*` matches any local user)

**registry.py** - Principal storage and resolution
- `PrincipalRegistry`: Persistent storage in `.claude/principals/`
- `resolve_channel_identity()`: Core P3394 requirement - maps channel IDs to principals
- Auto-creates system, anonymous, and CLI admin principals

**policy.py** - Authorization policy engine
- `PolicyEngine`: Policy Decision Point (PDP)
- `PolicyRule`: Condition-based authorization rules with priority
- `Policy`: Collection of rules evaluated in order
- Default policy with 8 rules covering system/admin/anonymous/assurance checks

#### 2. Gateway Integration

**gateway_sdk.py** - Modified
- Added `PrincipalRegistry` and `PolicyEngine` initialization
- Environment variable: `ENFORCE_AUTHENTICATION` (default: false)
- `_extract_client_assertion()`: Extracts CP from message metadata
- `_get_or_create_session_with_auth()`: Resolves principals and grants permissions
- Logging: All principal resolutions logged (non-enforcing in Phase 1)

**session.py** - Modified
- Added fields:
  - `client_principal_id`: Semantic principal URN
  - `service_principal_id`: Service principal URN
  - `granted_permissions`: List of granted permissions
  - `assurance_level`: Authentication assurance level
- Updated `has_permission()` to check granted permissions
- Added `grant_permission()` and `revoke_permission()` methods

#### 3. Channel Adapter Authentication

**base.py** - Modified
- Added abstract `authenticate_client()` method
- Added `create_client_assertion()` helper

**cli.py** - Modified
- Implemented `authenticate_client()`:
  - Extracts OS username via `getpass.getuser()`
  - Returns HIGH assurance (local access)
  - Identity format: `local:{username}`
- Modified `_cli_to_umf()` to embed client assertion in message metadata

#### 4. Storage

**Created files:**
```
.claude/principals/
├── principals.json          # 3 principals: system, anonymous, CLI admin
└── credential_bindings.json # 1 binding: CLI admin with scopes=["*"]
```

### Built-in Principals

1. **System Principal**
   - ID: `urn:principal:org:ieee3394:role:system:person:agent`
   - Type: SYSTEM
   - Usage: Internal operations
   - Always allowed for all operations

2. **Anonymous Principal**
   - ID: `urn:principal:org:public:role:anonymous:person:guest`
   - Type: ANONYMOUS
   - Usage: Unauthenticated users
   - Denied for privileged operations

3. **CLI Admin Principal**
   - ID: `urn:principal:org:ieee3394:role:admin:person:owner`
   - Type: HUMAN
   - Role: admin
   - Binding: `cli:local:*` (matches any local user)
   - Permissions: `["*"]` (all)

### Default Authorization Policy

Rules evaluated in priority order (first match wins):

1. **Allow System** (priority: 1) - System principal → ALLOW all
2. **Allow Admin** (priority: 2) - Admin role → ALLOW all
3. **Deny Anonymous Privileged** (priority: 10) - Anonymous + {admin, write, execute} → DENY
4. **Require HIGH Assurance for Admin** (priority: 20) - Admin perms need HIGH/CRYPTO assurance
5. **Require MEDIUM Assurance for Write** (priority: 30) - Write perms need ≥MEDIUM assurance
6. **Check Granted Permissions** (priority: 40) - Granted list contains all requested → ALLOW
7. **Allow Read for Authenticated** (priority: 50) - Auth user + read-only → ALLOW
8. **Default Deny** (priority: 999) - No rule matched → DENY

### Feature Flags

**Global Enforcement** (default: disabled)
```bash
export ENFORCE_AUTHENTICATION=true
```

**Per-Channel Enforcement** (runtime API)
```python
gateway.policy_engine.enable_enforcement_for_channel("cli")
gateway.policy_engine.disable_enforcement_for_channel("whatsapp")
```

**Current State**: Phase 1
- Principals are resolved and logged
- Authorization checks occur but always return ALLOW
- No existing functionality is broken

### Verification Tests

All tests passing:

1. ✅ All auth modules import successfully
2. ✅ PrincipalRegistry initializes and loads 3 principals + 1 binding
3. ✅ PolicyEngine initializes with 1 default policy (8 rules)
4. ✅ CLI assertion `local:rich` resolves to admin principal
5. ✅ Admin principal gets `scopes=["*"]`
6. ✅ Policy engine allows admin with enforcement disabled
7. ✅ Policy engine allows admin with enforcement enabled (admin rule)
8. ✅ Policy engine denies anonymous for privileged capabilities
9. ✅ Policy engine allows authenticated users with granted permissions

### What's Working

**Phase 1 Goal: Authentication infrastructure without breaking existing workflows**

✅ **CLI Workflow Unchanged**
- CLI users auto-resolve to admin principal
- Admin has all permissions (`["*"]`)
- Authorization logged but not enforced

✅ **Principal Resolution**
- Channel identities resolve to semantic principals
- Wildcard bindings work (`local:*` → admin)
- Fallback to anonymous principal when no binding found

✅ **Policy Evaluation**
- Rules evaluated in priority order
- Logging shows which rule matched
- Can toggle enforcement globally or per-channel

✅ **Backward Compatibility**
- Existing sessions work (missing fields treated as anonymous)
- Legacy `requires_auth` flag still works
- Emergency disable: `export ENFORCE_AUTHENTICATION=false`

### Example Log Output

When CLI user connects:
```
INFO: P3394 Authentication initialized (enforcement=False)
INFO: Created system principal
INFO: Created anonymous principal
INFO: Created CLI admin principal
INFO: Created CLI admin credential binding
INFO: Loaded 3 principals
INFO: Loaded 1 credential bindings
DEBUG: Received CLI message: {'text': '/help'}
INFO: Principal resolved: cli:local:rich → urn:principal:org:ieee3394:role:admin:person:owner (assurance=high)
DEBUG: Authorization check (enforcement disabled): capability=help, principal=urn:principal:org:ieee3394:role:admin:person:owner
```

With enforcement enabled:
```
INFO: Authorization ALLOW: help for urn:principal:org:ieee3394:role:admin:person:owner - default:allow-admin - Admin role
```

## API Key ↔ Principal Integration

### Overview

Web-generated API keys are now fully integrated with the KSTAR+ identity system through three storage mechanisms:

```
┌─────────────────────────────────────────────────────────────┐
│                API Key Creation Flow                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. User creates API key via /auth/api/keys                 │
│                         ↓                                    │
│  2. APIKeyRepository                                         │
│     └─ Stores key in auth database (existing)               │
│                         ↓                                    │
│  3. ControlToken (KSTAR+ LTM)                               │
│     └─ Stores with principal_id binding                     │
│     └─ Enables: token → principal resolution                │
│                         ↓                                    │
│  4. CredentialBinding (PrincipalRegistry)                   │
│     └─ Maps api_key:{prefix} → principal URN                │
│     └─ Enables: channel identity → principal resolution     │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### ControlToken Principal Binding

ControlTokens now support principal binding through two new fields:

```python
@dataclass
class ControlToken:
    # ... existing fields ...

    # Principal binding (who is authorized to use this token)
    principal_id: Optional[str] = None       # Primary principal URN
    authorized_principals: List[str] = []    # Additional authorized principals
```

**Authorization check:**
```python
def is_authorized_principal(self, principal_id: str) -> bool:
    """Check if a principal is authorized to use this token."""
    # No restriction = anyone with the value can use it
    if self.principal_id is None and not self.authorized_principals:
        return True
    # Check owner
    if self.principal_id == principal_id:
        return True
    # Check authorized list
    return principal_id in self.authorized_principals
```

### Unified Identity Resolution

API keys can now be traced back to principals through multiple paths:

```
API Key Prefix → ControlToken → principal_id → Principal
       ↓
       └────→ CredentialBinding → principal_id → Principal
```

This enables:
- **Audit trails**: Who created which API key
- **Revocation**: Revoke all tokens for a principal
- **Access control**: API key → principal → permissions

### Creating API Keys (Updated Flow)

When a user creates an API key via the web interface:

```python
# auth_router.py - create_api_key()

# 1. Create in auth database (existing)
api_key = APIKey(...)
await auth_repo.api_keys.create(api_key)

# 2. Store as ControlToken with principal binding (new)
control_token = ControlToken.create(
    key=f"api_key:{key_prefix}",
    value=full_key,
    token_type=TokenType.API_KEY,
    binding_target="p3394_agent:api",
    scopes=[TokenScope.READ, TokenScope.WRITE],
    principal_id=user.principal_id,           # NEW
    authorized_principals=[user.principal_id], # NEW
)

# 3. Create CredentialBinding (new)
binding = CredentialBinding(
    binding_id=f"urn:cred:api_key:{key_prefix}",
    principal_id=user.principal_id,
    channel="api",
    binding_type=BindingType.API_KEY,
    external_subject=key_prefix,
    scopes=["read", "write"],
)
principal_registry.register_binding(binding)
```

### Revoking API Keys (Updated Flow)

When an API key is revoked:

1. Revoked in APIKeyRepository (existing)
2. CredentialBinding deleted from PrincipalRegistry (new)
3. ControlToken marked as revoked in KSTAR+ LTM (future)

## Next Steps

### Phase 2: Principal Resolution & CLI Admin (Ready to Implement)

**Goal**: Enable enforcement for CLI channel with pre-configured admin

**Tasks**:
1. CLI already resolves to admin ✅
2. Test enforcement for CLI:
   ```python
   gateway.policy_engine.enable_enforcement()
   gateway.policy_engine.enable_enforcement_for_channel("cli")
   ```
3. Verify all CLI commands still work (admin has all perms)

**Duration**: 1 day
**Risk**: Low (admin has wildcard permissions)
**Breaking**: None

### Phase 3: Policy Enforcement (CLI Only)

**Goal**: Enable full enforcement for CLI channel

**Tasks**:
1. Set `ENFORCE_AUTHENTICATION=true` for CLI
2. Add audit logging to KSTAR memory (authorization decisions)
3. Test matrix: (CLI admin) × (all capabilities)

**Duration**: 1 day
**Risk**: Medium
**Breaking**: None (admin pre-allowlisted)

### Phase 4: WhatsApp Channel Integration

**Goal**: Implement WhatsApp authentication and allowlist

**Tasks**:
1. Implement `authenticate_client()` in WhatsApp adapter
2. Extract phone number from sender ID
3. Create WhatsApp principals and bindings in `.claude/principals/`
4. Enable enforcement for WhatsApp channel
5. Test allowlist (allow) and non-allowlist (deny)

**Duration**: 2-3 days
**Risk**: Medium
**Breaking**: Non-allowlisted users denied

### Phase 5: Full Enforcement & Audit

**Goal**: Enable enforcement for all channels and full audit logging

**Tasks**:
1. Implement `authenticate_client()` for P3394 Server channel
2. Enable enforcement globally
3. Add audit logging to KSTAR memory
4. Test all channels × all principals × all capabilities

**Duration**: 3-5 days
**Risk**: High
**Breaking**: All channels enforced

## Emergency Recovery

If authentication system causes issues:

```bash
# Disable enforcement globally
export ENFORCE_AUTHENTICATION=false

# Restart agent
uv run python -m ieee3394_agent --channel cli

# CLI should work immediately (hardcoded admin fallback)
```

**Hardcoded Fallbacks**:
1. CLI always creates admin principal if missing
2. CLI wildcard binding `local:*` matches any user
3. Admin role always allowed in default policy (priority 2)
4. Emergency disable via environment variable

## Files Created

### New Files (5 core auth modules)
- `src/ieee3394_agent/core/auth/__init__.py` (50 lines)
- `src/ieee3394_agent/core/auth/principal.py` (350 lines)
- `src/ieee3394_agent/core/auth/credential_binding.py` (200 lines)
- `src/ieee3394_agent/core/auth/registry.py` (400 lines)
- `src/ieee3394_agent/core/auth/policy.py` (500 lines)

### Modified Files (4 integration points)
- `src/ieee3394_agent/core/session.py` (+10 lines)
- `src/ieee3394_agent/core/gateway_sdk.py` (+100 lines)
- `src/ieee3394_agent/channels/base.py` (+50 lines)
- `src/ieee3394_agent/channels/cli.py` (+40 lines)

### Configuration Files (auto-generated)
- `.claude/principals/principals.json`
- `.claude/principals/credential_bindings.json`

**Total Lines**: ~1,700 lines of new code + integration

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                    P3394 Security Flow                       │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Channel Adapter (e.g., CLI)                             │
│     └─ authenticate_client() → ClientPrincipalAssertion     │
│                              ↓                               │
│  2. Message Creation                                         │
│     └─ Embed assertion in message.metadata["security"]      │
│                              ↓                               │
│  3. Gateway Receives Message                                 │
│     └─ _extract_client_assertion()                          │
│                              ↓                               │
│  4. Principal Registry                                       │
│     ├─ resolve_channel_identity()                          │
│     └─ Returns: Principal + CredentialBinding              │
│                              ↓                               │
│  5. Session Creation                                         │
│     ├─ session.client_principal_id = principal.id          │
│     ├─ session.granted_permissions = binding.scopes        │
│     └─ session.assurance_level = assertion.level           │
│                              ↓                               │
│  6. Policy Engine (if enforcement enabled)                   │
│     ├─ authorize(principal, capability, permissions)       │
│     └─ Returns: (ALLOW|DENY, reason)                       │
│                              ↓                               │
│  7. Capability Execution (or denial)                         │
└─────────────────────────────────────────────────────────────┘
```

## Success Criteria - Phase 1 ✅

- [x] All REQ-AUTH-* requirements have data models
- [x] All REQ-BIND-* requirements have implementation
- [x] All REQ-AUTHZ-* requirements have policy engine
- [x] CLI workflow unchanged (admin with all permissions)
- [x] Principal resolution working and logged
- [x] Policy engine working but not enforcing
- [x] Backward compatibility maintained
- [x] Emergency disable mechanism present
- [x] Auto-creation of system/anonymous/admin principals
- [x] Wildcard binding support for CLI

## P3394 Compliance Status

### Requirements Implemented (Phase 1)

**REQ-AUTH-01**: Dual principal model
- ✅ ClientPrincipal data structure
- ✅ ServicePrincipal data structure
- ✅ Session binds to both

**REQ-AUTH-02**: Service principal declaration
- ✅ ServicePrincipalContext class
- 🔄 Gateway declaration (Phase 5)

**REQ-AUTH-03**: Client principal assertion
- ✅ ClientPrincipalAssertion class
- ✅ Channel adapters emit assertions
- ✅ Gateway resolves assertions

**REQ-BIND-01**: Service credential binding
- ✅ CredentialBinding for service accounts
- 🔄 Service-to-service auth (Phase 5)

**REQ-BIND-02**: Client authentication
- ✅ CLI authentication (HIGH assurance)
- 🔄 WhatsApp authentication (Phase 4)
- 🔄 P3394 Server authentication (Phase 5)

**REQ-BIND-03**: Channel identity mapping
- ✅ `resolve_channel_identity()` implemented
- ✅ Wildcard matching support
- ✅ Persistent storage in `.claude/principals/`

**REQ-AUTHZ-01**: Capability-level authorization
- ✅ Policy engine with capability parameter
- ✅ Permission-based rules
- 🔄 Enforcement (Phase 3-5)

**REQ-AUTHZ-02**: Policy engine
- ✅ Rule-based evaluation
- ✅ Priority ordering
- ✅ Pluggable policies

**REQ-AUTHZ-03**: Assurance-based authorization
- ✅ AssuranceLevel enum
- ✅ Policy rules check assurance
- ✅ CLI provides HIGH assurance

## Known Limitations (Phase 1)

1. **Not Enforcing**: Authorization checks log but don't block (by design)
2. **No Audit Logging**: Authorization decisions not logged to KSTAR yet
3. **CLI Only**: Only CLI channel has authentication implemented
4. **No Multi-Factor**: All auth is single-factor (OS user, phone number)
5. **No Credential Rotation**: Bindings don't expire or rotate
6. **No Rate Limiting**: Policy engine doesn't check rate limits
7. **No Delegation**: No support for "act on behalf of" scenarios

These will be addressed in subsequent phases.

## Testing

Run verification tests:

```bash
# Test imports
uv run python -c "from src.ieee3394_agent.core.auth import *; print('✓')"

# Test registry initialization
uv run python -c "
from pathlib import Path
from src.ieee3394_agent.core.auth import PrincipalRegistry
registry = PrincipalRegistry(Path('.claude/principals'))
print(f'Principals: {len(registry.list_principals())}')
print(f'Bindings: {len(registry.list_bindings())}')
"

# Test CLI resolution
uv run python -c "
from pathlib import Path
from src.ieee3394_agent.core.auth import *
registry = PrincipalRegistry(Path('.claude/principals'))
assertion = ClientPrincipalAssertion(
    channel_id='cli',
    channel_identity='local:testuser',
    assurance_level=AssuranceLevel.HIGH,
    authentication_method='local_access'
)
principal = registry.resolve_assertion(assertion)
print(f'Resolved: {principal.display_name if principal else \"None\"}')
"

# Test policy engine
uv run python -c "
from src.ieee3394_agent.core.auth import *
engine = PolicyEngine(enforcement_enabled=True)
admin = Principal(
    principal_id='urn:principal:org:ieee3394:role:admin:person:owner',
    org='urn:org:ieee3394',
    role='urn:role:admin',
    person='urn:person:owner',
    principal_type=PrincipalType.HUMAN
)
decision, reason = engine.authorize(
    principal=admin,
    assurance_level=AssuranceLevel.HIGH,
    capability='test',
    requested_permissions=['admin'],
    granted_permissions=['*']
)
print(f'Decision: {decision.value} - {reason}')
"
```

All tests should pass.

---

**Phase 1 Status**: ✅ COMPLETE
**Next Phase**: Phase 2 - Principal Resolution & CLI Admin (ready to implement)
**Deployment**: Safe to deploy with `ENFORCE_AUTHENTICATION=false` (default)
