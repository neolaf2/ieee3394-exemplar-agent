---
name: control-tokens
description: Manage KSTAR+ Control Tokens - the 4th memory class that authorizes execution
triggers:
  - "store token"
  - "save token"
  - "store api key"
  - "store credential"
  - "get token"
  - "lookup token"
  - "verify token"
  - "revoke token"
  - "token lineage"
  - "list tokens"
---

# Control Tokens Skill

## Overview

Control Tokens are the **4th irreducible memory class** in KSTAR+. They represent the "gate" between thought and action - the authority required to execute.

Unlike semantic memory (traces, perceptions, skills), control tokens are:
- **Non-derivable**: Cannot be inferred from knowledge
- **Exact**: Require precise key-value lookup (no fuzzy matching)
- **Time-sensitive**: Must be valid at moment of execution
- **Non-compressible**: Cannot be baked into model weights

## The Thought-Energy Boundary

```
THOUGHT REALM                      EXECUTION REALM
─────────────────                  ─────────────────
Situation → Task → Action Plan  ─┬─▶  CONTROL TOKEN  ─▶  Physical Action
                                 │        │
                                 │    THE GATE
                                 │   (Authority)
```

## Available Tools

### 1. Store Control Token
Store a token for guaranteed key-value resolution.

```
Use: mcp__p3394_tools__store_control_token

Parameters:
  - key: The lookup key (e.g., "anthropic", "whatsapp:+1234567890")
  - value: The secret value (will be hashed)
  - token_type: api_key, oauth, phone, capability, etc.
  - binding_target: What this token unlocks
  - scopes: [read, write, execute, admin, delete, *]
  - provenance_source: Who issued it
  - provenance_method: issued, delegated, discovered, user_provided, generated
```

### 2. Get Control Token
Retrieve token metadata by key (exact lookup).

```
Use: mcp__p3394_tools__get_control_token

Parameters:
  - key: The lookup key
  - token_type: Optional type filter
```

### 3. Verify Control Token
Verify a value against stored hash before executing.

```
Use: mcp__p3394_tools__verify_control_token

Parameters:
  - key: The token key
  - value: The value to verify
```

### 4. Revoke Control Token
Close the gate permanently for a token.

```
Use: mcp__p3394_tools__revoke_control_token

Parameters:
  - token_id: The token ID to revoke
  - reason: Why it's being revoked
```

### 5. Get Token Lineage
Trace the provenance chain - who issued, delegated, etc.

```
Use: mcp__p3394_tools__get_token_lineage

Parameters:
  - token_id: The token to trace
```

### 6. List Tokens by Type
Audit all tokens of a specific type.

```
Use: mcp__p3394_tools__list_tokens_by_type

Parameters:
  - token_type: Type to list
  - include_revoked: Whether to include revoked tokens
```

## Token Types

| Domain | Types |
|--------|-------|
| Digital | api_key, oauth, session, password |
| File System | file_path, inode, permission |
| Skill System | skill_id, capability, manifest, mcp_tool |
| Human Identity | phone, email, biometric, badge |
| Agentic | function_ptr, agent_uri, channel_binding |

## Examples

### Store an API Key
```
"Store my Anthropic API key: sk-ant-api03-xxxxx with binding target claude-sonnet-4"

→ store_control_token(
    key="anthropic",
    value="sk-ant-api03-xxxxx",
    token_type="api_key",
    binding_target="claude-sonnet-4",
    scopes=["execute"],
    provenance_method="user_provided"
  )
```

### Store a Phone Binding
```
"Bind WhatsApp +1234567890 to principal urn:principal:alice with chat scope"

→ store_control_token(
    key="whatsapp:+1234567890",
    value="+1234567890",
    token_type="phone",
    binding_target="urn:principal:alice",
    scopes=["chat", "query"],
    provenance_method="issued"
  )
```

### Verify Before Action
```
"Check if the anthropic key is valid before calling the LLM"

→ verify_control_token(
    key="anthropic",
    value="sk-ant-api03-xxxxx"
  )
```

### Trace Lineage
```
"Show me where this token came from"

→ get_token_lineage(
    token_id="urn:token:api_key:abc123"
  )
```

## Security Notes

1. **Never include raw token values in prompts or embeddings**
2. **Values are hashed** - the actual secret is never stored in plaintext
3. **Revocation is permanent** - once revoked, a token cannot be reactivated
4. **Provenance is immutable** - the chain of custody is append-only
5. **Usage is logged** - every use of a token is recorded for audit

## Setup

### Environment Variables
```bash
export SUPABASE_URL="https://your-project.supabase.co"
export SUPABASE_KEY="your-service-role-key"
```

### Database Schema
Run the schema in Supabase SQL editor:
```python
from p3394_agent.memory.supabase_token_store import SUPABASE_SCHEMA
print(SUPABASE_SCHEMA)
```

## Why Control Tokens?

The distinction between **knowing how to act** and **having the authority to act** is foundational.

- KSTAR stores the record of what worked (epistemic memory)
- Control Tokens store what unlocks reality (authority)

Without both, an agent remains a reasoning engine that can think but cannot act.
