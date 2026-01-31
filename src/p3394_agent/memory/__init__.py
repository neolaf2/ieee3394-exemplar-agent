"""
KSTAR+ Memory Module

Implements the 4 irreducible memory classes:
1. Traces (Episodic) - K→S→T→A→R episodes
2. Perceptions (Declarative) - Facts and observations
3. Skills (Procedural) - How to act
4. Control Tokens (Authority) - The gate between thought and action

Plus the Memory System (meta-skill) that:
- Hooks into the agent loop at key stages
- Runs necessity evaluation to auto-detect tokens
- Persists tokens with searchable indexes and categories
"""

from .kstar import KStarMemory
from .control_tokens import (
    ControlToken,
    TokenType,
    TokenScope,
    TokenProvenance,
    ProvenanceMethod,
    TokenUsage,
    ConsumptionMode
)
from .supabase_token_store import (
    SupabaseTokenStore,
    get_token_store,
    store_token,
    get_token,
    verify_token,
    revoke_token,
    get_lineage,
    SUPABASE_SCHEMA
)
from .necessity_evaluator import (
    NecessityEvaluator,
    NecessityCategory,
    DetectedToken
)
from .memory_system import (
    MemorySystem,
    MemorySystemConfig,
    get_memory_system,
    initialize_memory_system
)

__all__ = [
    # KSTAR Memory (Classes 1-3)
    "KStarMemory",

    # Control Tokens (Class 4)
    "ControlToken",
    "TokenType",
    "TokenScope",
    "TokenProvenance",
    "ProvenanceMethod",
    "TokenUsage",
    "ConsumptionMode",

    # Supabase Store
    "SupabaseTokenStore",
    "get_token_store",
    "store_token",
    "get_token",
    "verify_token",
    "revoke_token",
    "get_lineage",
    "SUPABASE_SCHEMA",

    # Necessity Evaluator (auto-detection)
    "NecessityEvaluator",
    "NecessityCategory",
    "DetectedToken",

    # Memory System (meta-skill)
    "MemorySystem",
    "MemorySystemConfig",
    "get_memory_system",
    "initialize_memory_system",
]
