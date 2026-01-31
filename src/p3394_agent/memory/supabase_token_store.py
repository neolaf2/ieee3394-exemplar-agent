"""
Supabase-backed Control Token Store

Provides reliable key-value storage for KSTAR+ Control Tokens with:
- Exact key lookup (guaranteed resolution)
- Lineage/provenance queries
- Token lifecycle management (create, revoke, expire)
- Usage audit trail

Environment Variables:
    SUPABASE_URL: Your Supabase project URL
    SUPABASE_KEY: Your Supabase API key (service role for server-side)
"""

import os
import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from dataclasses import asdict

from .control_tokens import (
    ControlToken, TokenType, TokenScope, TokenProvenance,
    ProvenanceMethod, TokenUsage, ConsumptionMode
)

logger = logging.getLogger(__name__)

# Supabase client (lazy initialized)
_supabase_client = None


def get_supabase_client():
    """Get or create Supabase client"""
    global _supabase_client
    if _supabase_client is None:
        try:
            from supabase import create_client, Client
            url = os.environ.get("SUPABASE_URL")
            key = os.environ.get("SUPABASE_KEY")

            if not url or not key:
                raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")

            _supabase_client = create_client(url, key)
            logger.info("Supabase client initialized")
        except ImportError:
            logger.error("supabase-py not installed. Run: uv add supabase")
            raise
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            raise

    return _supabase_client


# =============================================================================
# SQL Schema for Supabase (run this in Supabase SQL editor)
# =============================================================================

SUPABASE_SCHEMA = """
-- KSTAR+ Control Tokens Table
CREATE TABLE IF NOT EXISTS control_tokens (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id TEXT UNIQUE NOT NULL,
    token_type TEXT NOT NULL,
    key TEXT NOT NULL,
    value_hash TEXT NOT NULL,
    scopes JSONB DEFAULT '["read"]',
    binding_target TEXT,

    -- Validity
    valid_from TIMESTAMPTZ DEFAULT NOW(),
    valid_until TIMESTAMPTZ,
    is_revoked BOOLEAN DEFAULT FALSE,
    revoked_at TIMESTAMPTZ,
    revoked_by TEXT,
    revocation_reason TEXT,

    -- Provenance
    provenance JSONB,

    -- Consumption
    consumption_mode TEXT DEFAULT 'reusable',
    remaining_uses INTEGER,
    use_count INTEGER DEFAULT 0,
    last_used_at TIMESTAMPTZ,

    -- Metadata
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    -- Lineage
    parent_token_id TEXT,
    child_token_ids JSONB DEFAULT '[]',

    -- Indexes for fast lookup
    CONSTRAINT valid_token_type CHECK (token_type IN (
        'api_key', 'oauth', 'session', 'password',
        'file_path', 'inode', 'permission',
        'skill_id', 'capability', 'manifest', 'mcp_tool',
        'phone', 'email', 'biometric', 'badge',
        'function_ptr', 'agent_uri', 'channel_binding'
    ))
);

-- Index for key lookup (most common operation)
CREATE INDEX IF NOT EXISTS idx_control_tokens_key ON control_tokens(key);

-- Index for type-based queries
CREATE INDEX IF NOT EXISTS idx_control_tokens_type ON control_tokens(token_type);

-- Index for lineage queries
CREATE INDEX IF NOT EXISTS idx_control_tokens_parent ON control_tokens(parent_token_id);

-- Index for finding active tokens
CREATE INDEX IF NOT EXISTS idx_control_tokens_active
    ON control_tokens(is_revoked, valid_until)
    WHERE is_revoked = FALSE;

-- Token Usage Log Table
CREATE TABLE IF NOT EXISTS token_usage_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    token_id TEXT NOT NULL REFERENCES control_tokens(token_id),
    used_at TIMESTAMPTZ DEFAULT NOW(),
    action_id TEXT NOT NULL,
    action_type TEXT NOT NULL,
    target TEXT,
    success BOOLEAN DEFAULT TRUE,
    error_message TEXT,

    -- Index for querying usage by token
    CONSTRAINT fk_token FOREIGN KEY (token_id) REFERENCES control_tokens(token_id)
);

CREATE INDEX IF NOT EXISTS idx_token_usage_token ON token_usage_log(token_id);
CREATE INDEX IF NOT EXISTS idx_token_usage_time ON token_usage_log(used_at DESC);

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger to auto-update updated_at
DROP TRIGGER IF EXISTS control_tokens_updated_at ON control_tokens;
CREATE TRIGGER control_tokens_updated_at
    BEFORE UPDATE ON control_tokens
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at();

-- Function to increment token usage count
CREATE OR REPLACE FUNCTION increment_token_usage(p_token_id TEXT)
RETURNS VOID AS $$
BEGIN
    UPDATE control_tokens
    SET use_count = use_count + 1,
        last_used_at = NOW(),
        remaining_uses = CASE
            WHEN remaining_uses IS NOT NULL THEN remaining_uses - 1
            ELSE NULL
        END
    WHERE token_id = p_token_id;
END;
$$ LANGUAGE plpgsql;

-- Row Level Security (optional, enable if needed)
-- ALTER TABLE control_tokens ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE token_usage_log ENABLE ROW LEVEL SECURITY;
"""


class SupabaseTokenStore:
    """
    Supabase-backed storage for KSTAR+ Control Tokens.

    Provides guaranteed key-value resolution for the 4th memory class.
    """

    TABLE_NAME = "control_tokens"
    USAGE_TABLE = "token_usage_log"

    def __init__(self, supabase_client=None):
        """
        Initialize token store.

        Args:
            supabase_client: Optional pre-configured Supabase client
        """
        self._client = supabase_client

    @property
    def client(self):
        """Lazy-load Supabase client"""
        if self._client is None:
            self._client = get_supabase_client()
        return self._client

    # =========================================================================
    # Core CRUD Operations
    # =========================================================================

    async def store(self, token: ControlToken) -> str:
        """
        Store a control token.

        Args:
            token: The ControlToken to store

        Returns:
            The token_id of the stored token
        """
        try:
            data = token.to_dict()

            # Supabase expects JSON-serializable data
            result = self.client.table(self.TABLE_NAME).upsert(
                data,
                on_conflict="token_id"
            ).execute()

            logger.info(f"Stored token: {token.token_id} (key={token.key})")
            return token.token_id

        except Exception as e:
            logger.exception(f"Failed to store token: {e}")
            raise

    async def get_by_id(self, token_id: str) -> Optional[ControlToken]:
        """
        Get a token by its ID (exact lookup).

        Args:
            token_id: The token ID to look up

        Returns:
            ControlToken if found, None otherwise
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "token_id", token_id
            ).execute()

            if result.data and len(result.data) > 0:
                return ControlToken.from_dict(result.data[0])
            return None

        except Exception as e:
            logger.exception(f"Failed to get token by ID: {e}")
            return None

    async def get_by_key(self, key: str) -> Optional[ControlToken]:
        """
        Get a token by its key (guaranteed resolution).

        This is the primary lookup method - exact key match.

        Args:
            key: The lookup key (e.g., "anthropic", "whatsapp:+1234567890")

        Returns:
            ControlToken if found and valid, None otherwise
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "key", key
            ).eq(
                "is_revoked", False
            ).execute()

            if result.data and len(result.data) > 0:
                token = ControlToken.from_dict(result.data[0])
                if token.is_valid():
                    return token
                logger.warning(f"Token for key '{key}' exists but is not valid")
            return None

        except Exception as e:
            logger.exception(f"Failed to get token by key: {e}")
            return None

    async def get_by_key_and_type(self, key: str, token_type: TokenType) -> Optional[ControlToken]:
        """
        Get a token by key and type (more specific lookup).

        Args:
            key: The lookup key
            token_type: The type of token

        Returns:
            ControlToken if found and valid, None otherwise
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "key", key
            ).eq(
                "token_type", token_type.value
            ).eq(
                "is_revoked", False
            ).execute()

            if result.data and len(result.data) > 0:
                token = ControlToken.from_dict(result.data[0])
                if token.is_valid():
                    return token
            return None

        except Exception as e:
            logger.exception(f"Failed to get token by key and type: {e}")
            return None

    async def delete(self, token_id: str) -> bool:
        """
        Delete a token (hard delete).

        For most cases, use revoke() instead for audit trail.

        Args:
            token_id: The token ID to delete

        Returns:
            True if deleted, False otherwise
        """
        try:
            result = self.client.table(self.TABLE_NAME).delete().eq(
                "token_id", token_id
            ).execute()

            logger.info(f"Deleted token: {token_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to delete token: {e}")
            return False

    # =========================================================================
    # Token Lifecycle
    # =========================================================================

    async def revoke(self, token_id: str, by: str, reason: str = None) -> bool:
        """
        Revoke a token (soft delete with audit trail).

        Args:
            token_id: The token to revoke
            by: Who is revoking (principal ID)
            reason: Optional reason for revocation

        Returns:
            True if revoked, False otherwise
        """
        try:
            result = self.client.table(self.TABLE_NAME).update({
                "is_revoked": True,
                "revoked_at": datetime.now(timezone.utc).isoformat(),
                "revoked_by": by,
                "revocation_reason": reason
            }).eq(
                "token_id", token_id
            ).execute()

            logger.info(f"Revoked token: {token_id} by {by}")
            return True

        except Exception as e:
            logger.exception(f"Failed to revoke token: {e}")
            return False

    async def record_usage(
        self,
        token_id: str,
        action_id: str,
        action_type: str,
        target: str,
        success: bool,
        error_message: str = None
    ) -> bool:
        """
        Record that a token was used.

        Args:
            token_id: The token that was used
            action_id: ID of the action (message ID, etc.)
            action_type: Type of action performed
            target: What resource was accessed
            success: Whether the action succeeded
            error_message: Error message if failed

        Returns:
            True if recorded, False otherwise
        """
        try:
            # Insert usage log
            self.client.table(self.USAGE_TABLE).insert({
                "token_id": token_id,
                "used_at": datetime.now(timezone.utc).isoformat(),
                "action_id": action_id,
                "action_type": action_type,
                "target": target,
                "success": success,
                "error_message": error_message
            }).execute()

            # Update token usage stats
            self.client.rpc("increment_token_usage", {
                "p_token_id": token_id
            }).execute()

            return True

        except Exception as e:
            # Log but don't fail - usage logging is best-effort
            logger.warning(f"Failed to record token usage: {e}")
            return False

    # =========================================================================
    # Lineage Queries
    # =========================================================================

    async def get_by_lineage(self, parent_token_id: str) -> List[ControlToken]:
        """
        Get all tokens derived from a parent token.

        Args:
            parent_token_id: The parent token ID

        Returns:
            List of child tokens
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "parent_token_id", parent_token_id
            ).execute()

            return [ControlToken.from_dict(row) for row in result.data]

        except Exception as e:
            logger.exception(f"Failed to get tokens by lineage: {e}")
            return []

    async def get_provenance_chain(self, token_id: str) -> List[ControlToken]:
        """
        Get the full provenance chain for a token (all ancestors).

        Args:
            token_id: The token to trace

        Returns:
            List of tokens in the chain, from root to current
        """
        chain = []
        current_id = token_id

        try:
            while current_id:
                token = await self.get_by_id(current_id)
                if token:
                    chain.insert(0, token)  # Insert at beginning
                    current_id = token.parent_token_id
                else:
                    break

            return chain

        except Exception as e:
            logger.exception(f"Failed to get provenance chain: {e}")
            return chain

    async def get_by_provenance_source(self, source: str) -> List[ControlToken]:
        """
        Get all tokens issued by a specific source.

        Args:
            source: The provenance source to search for

        Returns:
            List of matching tokens
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").contains(
                "provenance", {"source": source}
            ).execute()

            return [ControlToken.from_dict(row) for row in result.data]

        except Exception as e:
            logger.exception(f"Failed to get tokens by provenance source: {e}")
            return []

    # =========================================================================
    # Query Operations
    # =========================================================================

    async def list_by_type(self, token_type: TokenType, include_revoked: bool = False) -> List[ControlToken]:
        """
        List all tokens of a specific type.

        Args:
            token_type: The token type to filter by
            include_revoked: Whether to include revoked tokens

        Returns:
            List of matching tokens
        """
        try:
            query = self.client.table(self.TABLE_NAME).select("*").eq(
                "token_type", token_type.value
            )

            if not include_revoked:
                query = query.eq("is_revoked", False)

            result = query.execute()
            return [ControlToken.from_dict(row) for row in result.data]

        except Exception as e:
            logger.exception(f"Failed to list tokens by type: {e}")
            return []

    async def list_by_binding_target(self, binding_target: str) -> List[ControlToken]:
        """
        List all tokens that unlock a specific target.

        Args:
            binding_target: The binding target to search for

        Returns:
            List of matching tokens
        """
        try:
            result = self.client.table(self.TABLE_NAME).select("*").eq(
                "binding_target", binding_target
            ).eq(
                "is_revoked", False
            ).execute()

            return [ControlToken.from_dict(row) for row in result.data]

        except Exception as e:
            logger.exception(f"Failed to list tokens by binding target: {e}")
            return []

    async def get_usage_log(self, token_id: str, limit: int = 100) -> List[TokenUsage]:
        """
        Get usage log for a token.

        Args:
            token_id: The token to get usage for
            limit: Maximum records to return

        Returns:
            List of TokenUsage records
        """
        try:
            result = self.client.table(self.USAGE_TABLE).select("*").eq(
                "token_id", token_id
            ).order(
                "used_at", desc=True
            ).limit(limit).execute()

            return [TokenUsage.from_dict(row) for row in result.data]

        except Exception as e:
            logger.exception(f"Failed to get usage log: {e}")
            return []

    async def count_active_tokens(self) -> int:
        """Count all active (non-revoked, non-expired) tokens."""
        try:
            result = self.client.table(self.TABLE_NAME).select(
                "id", count="exact"
            ).eq(
                "is_revoked", False
            ).execute()

            return result.count or 0

        except Exception as e:
            logger.exception(f"Failed to count active tokens: {e}")
            return 0

    # =========================================================================
    # Utility
    # =========================================================================

    async def verify_value(self, key: str, value: str) -> bool:
        """
        Verify a value against stored hash for a key.

        Args:
            key: The token key
            value: The value to verify

        Returns:
            True if value matches, False otherwise
        """
        token = await self.get_by_key(key)
        if token:
            return token.verify_value(value)
        return False

    async def cleanup_expired(self) -> int:
        """
        Clean up expired tokens (mark as revoked).

        Returns:
            Number of tokens cleaned up
        """
        try:
            now = datetime.now(timezone.utc).isoformat()

            result = self.client.table(self.TABLE_NAME).update({
                "is_revoked": True,
                "revoked_at": now,
                "revoked_by": "system:cleanup",
                "revocation_reason": "Token expired"
            }).lt(
                "valid_until", now
            ).eq(
                "is_revoked", False
            ).execute()

            count = len(result.data) if result.data else 0
            if count > 0:
                logger.info(f"Cleaned up {count} expired tokens")
            return count

        except Exception as e:
            logger.exception(f"Failed to cleanup expired tokens: {e}")
            return 0

    def get_schema_sql(self) -> str:
        """Get the SQL schema for Supabase setup."""
        return SUPABASE_SCHEMA


# =============================================================================
# Convenience Functions for MCP Tools
# =============================================================================

# Global store instance
_token_store: Optional[SupabaseTokenStore] = None


def get_token_store() -> SupabaseTokenStore:
    """Get the global token store instance."""
    global _token_store
    if _token_store is None:
        _token_store = SupabaseTokenStore()
    return _token_store


async def store_token(
    key: str,
    value: str,
    token_type: str,
    binding_target: str,
    scopes: List[str] = None,
    provenance_source: str = "agent",
    provenance_method: str = "generated",
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    Store a control token (MCP-friendly function).

    Args:
        key: The lookup key
        value: The secret value (will be hashed)
        token_type: Type of token (api_key, phone, etc.)
        binding_target: What this token unlocks
        scopes: Permissions granted (default: ["read"])
        provenance_source: Who issued this token
        provenance_method: How it was obtained
        metadata: Additional metadata

    Returns:
        Result dict with token_id
    """
    store = get_token_store()

    token = ControlToken.create(
        key=key,
        value=value,
        token_type=TokenType(token_type),
        binding_target=binding_target,
        scopes=[TokenScope(s) for s in (scopes or ["read"])],
        provenance_source=provenance_source,
        provenance_method=ProvenanceMethod(provenance_method),
        metadata=metadata or {}
    )

    token_id = await store.store(token)

    return {
        "success": True,
        "token_id": token_id,
        "key": key,
        "message": f"Token stored successfully with ID: {token_id}"
    }


async def get_token(key: str, token_type: str = None) -> Dict[str, Any]:
    """
    Get a control token by key (MCP-friendly function).

    Args:
        key: The lookup key
        token_type: Optional type filter

    Returns:
        Token data (without secret value)
    """
    store = get_token_store()

    if token_type:
        token = await store.get_by_key_and_type(key, TokenType(token_type))
    else:
        token = await store.get_by_key(key)

    if token:
        return {
            "success": True,
            "token": token.to_dict()
        }
    else:
        return {
            "success": False,
            "error": f"No valid token found for key: {key}"
        }


async def verify_token(key: str, value: str) -> Dict[str, Any]:
    """
    Verify a token value (MCP-friendly function).

    Args:
        key: The token key
        value: The value to verify

    Returns:
        Verification result
    """
    store = get_token_store()
    is_valid = await store.verify_value(key, value)

    return {
        "success": True,
        "valid": is_valid,
        "message": "Token verified" if is_valid else "Token verification failed"
    }


async def revoke_token(token_id: str, by: str, reason: str = None) -> Dict[str, Any]:
    """
    Revoke a token (MCP-friendly function).

    Args:
        token_id: The token to revoke
        by: Who is revoking
        reason: Optional reason

    Returns:
        Result dict
    """
    store = get_token_store()
    success = await store.revoke(token_id, by, reason)

    return {
        "success": success,
        "message": f"Token {token_id} revoked" if success else "Failed to revoke token"
    }


async def get_lineage(token_id: str) -> Dict[str, Any]:
    """
    Get the provenance chain for a token (MCP-friendly function).

    Args:
        token_id: The token to trace

    Returns:
        Lineage chain
    """
    store = get_token_store()
    chain = await store.get_provenance_chain(token_id)

    return {
        "success": True,
        "chain": [t.to_dict() for t in chain],
        "chain_length": len(chain)
    }
