# Memory System Meta-Skill

System-level skill for the KSTAR+ Memory System. This is a **meta-skill** that runs automatically at key stages of the agent loop and provides direct access to memory functions.

## Automatic Behavior (No Invocation Needed)

The memory system automatically:
- **Pre-tool**: Runs necessity evaluation to detect tokens in tool inputs
- **Post-tool**: Runs necessity evaluation on tool results
- **Skill tracking**: Captures skill folder names for dynamic import recovery
- **Session end**: Consolidates session memory

## Explicit Triggers

Use these phrases to interact with the memory system directly:

- "search memory for [query]"
- "list stored tokens"
- "find credentials for [service]"
- "show skill activations"
- "get token by key [key]"
- "memory stats"

## Token Categories

The necessity evaluator auto-detects and persists:

| Category | Examples | Priority |
|----------|----------|----------|
| `CREDENTIAL` | API keys, passwords, OAuth tokens | High (0.9+) |
| `BINDING` | Channel→Principal mappings | High (0.85+) |
| `IDENTITY` | Phone numbers, emails, agent URIs | Medium (0.7+) |
| `CAPABILITY` | Skill folders, permissions | Medium (0.7+) |
| `PATH` | File paths, URLs, endpoints | Low (0.6+) |
| `CONFIGURATION` | Settings that affect behavior | Low (0.5+) |

## Skill Folder Tracking

**Critical for recovery**: When skills are dynamically imported, created, or assigned, their folder names are automatically captured as tokens with:

- Key format: `skill:folder:{skill_name}`
- Token type: `SKILL_ID`
- Category: `CAPABILITY`
- Tags: `["skill", "dynamic_import", skill_name]`

## MCP Tools

The memory system exposes these MCP tools:

- `store_control_token` - Store a token with key/value
- `get_control_token` - Retrieve by key
- `verify_control_token` - Verify token validity
- `revoke_control_token` - Revoke a token
- `get_token_lineage` - Get provenance chain
- `list_tokens_by_type` - List tokens by type/category

## Searchable Indexes

Tokens are stored in Supabase with indexes for:
- **Key lookup**: Guaranteed O(1) resolution
- **Category search**: Find all credentials, bindings, etc.
- **Tag search**: Find by service name, action, etc.
- **Lineage queries**: Full provenance chain

## Configuration

Set in environment or agent.yaml:

```yaml
memory:
  auto_persist_enabled: true
  min_confidence_threshold: 0.6
  persist_on_tool_use: true
  persist_on_message: true
  supabase_url: ${SUPABASE_URL}
  supabase_key: ${SUPABASE_KEY}
```

## Example: Recovery After Restart

After restart, recover all skill assignments:

```python
# Find all activated skills
skills = await memory.search_by_category(NecessityCategory.CAPABILITY)
for token in skills:
    if token.key.startswith("skill:activated:"):
        skill_name = token.key.replace("skill:activated:", "")
        # Re-load the skill
```

## Process

1. **Detection**: Pattern matching + keyword analysis
2. **Confidence scoring**: Base + context boosters
3. **Category assignment**: Based on token type
4. **Persistence**: Store to Supabase with indexes
5. **Recovery**: Query by key, category, or tag
