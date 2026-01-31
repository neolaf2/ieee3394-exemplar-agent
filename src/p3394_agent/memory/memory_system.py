"""
KSTAR+ Memory System

The unified memory system that integrates all 4 memory classes:
1. Traces (Episodic) - What happened
2. Perceptions (Declarative) - What is known
3. Skills (Procedural) - How to act
4. Control Tokens (Authority) - The gate to action

This is a system-level meta-skill that:
- Runs at key stages of the agent loop
- Automatically detects and persists critical tokens
- Maintains searchable indexes by category and tag
- Ensures nothing important is lost

Configuration is tied to the agent's persistence store.
"""

import os
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set
from pathlib import Path

from .kstar import KStarMemory
from .control_tokens import ControlToken, TokenType, TokenScope
from .supabase_token_store import SupabaseTokenStore, get_token_store
from .necessity_evaluator import NecessityEvaluator, DetectedToken, NecessityCategory

logger = logging.getLogger(__name__)


@dataclass
class MemorySystemConfig:
    """Configuration for the memory system"""
    # Auto-persistence settings
    auto_persist_enabled: bool = True
    min_confidence_threshold: float = 0.6
    persist_on_tool_use: bool = True
    persist_on_message: bool = True

    # Supabase settings (from environment if not specified)
    supabase_url: Optional[str] = None
    supabase_key: Optional[str] = None

    # Local fallback settings
    local_fallback_enabled: bool = True
    local_storage_path: Optional[Path] = None

    # Categories to auto-persist
    auto_persist_categories: Set[NecessityCategory] = field(default_factory=lambda: {
        NecessityCategory.CREDENTIAL,
        NecessityCategory.BINDING,
        NecessityCategory.IDENTITY,
        NecessityCategory.CAPABILITY,
    })

    # Token types that require confirmation before persistence
    require_confirmation: Set[TokenType] = field(default_factory=lambda: {
        TokenType.PASSWORD_HASH,
        TokenType.BIOMETRIC_HASH,
    })

    @classmethod
    def from_agent_config(cls, agent_config: "AgentConfig") -> "MemorySystemConfig":
        """Create from agent configuration"""
        storage_config = agent_config.storage if hasattr(agent_config, 'storage') else None

        return cls(
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_key=os.environ.get("SUPABASE_KEY"),
            local_storage_path=Path(storage_config.path) if storage_config else None,
        )

    @classmethod
    def from_environment(cls) -> "MemorySystemConfig":
        """Create from environment variables"""
        return cls(
            supabase_url=os.environ.get("SUPABASE_URL"),
            supabase_key=os.environ.get("SUPABASE_KEY"),
            auto_persist_enabled=os.environ.get("MEMORY_AUTO_PERSIST", "true").lower() == "true",
            min_confidence_threshold=float(os.environ.get("MEMORY_MIN_CONFIDENCE", "0.6")),
        )


class MemorySystem:
    """
    The unified KSTAR+ Memory System.

    This is the central memory manager that:
    1. Coordinates all 4 memory classes
    2. Runs the necessity evaluator at key agent loop stages
    3. Auto-persists detected tokens to Supabase
    4. Maintains searchable indexes

    This is registered as a system-level meta-skill that's always active.
    """

    def __init__(
        self,
        config: Optional[MemorySystemConfig] = None,
        kstar_memory: Optional[KStarMemory] = None,
        token_store: Optional[SupabaseTokenStore] = None,
    ):
        """
        Initialize the memory system.

        Args:
            config: Memory system configuration
            kstar_memory: Existing KSTAR memory instance
            token_store: Existing token store instance
        """
        self.config = config or MemorySystemConfig.from_environment()
        self.kstar = kstar_memory or KStarMemory()
        self._token_store = token_store
        self.evaluator = NecessityEvaluator(
            min_confidence=self.config.min_confidence_threshold
        )

        # Track what's been persisted in this session
        self._persisted_keys: Set[str] = set()

        # Pending confirmations (for sensitive tokens)
        self._pending_confirmations: Dict[str, DetectedToken] = {}

        logger.info("MemorySystem initialized with auto_persist=%s", self.config.auto_persist_enabled)

    @property
    def token_store(self) -> Optional[SupabaseTokenStore]:
        """Get token store (lazy initialization)"""
        if self._token_store is None and self.config.supabase_url:
            try:
                self._token_store = get_token_store()
            except Exception as e:
                logger.warning(f"Failed to initialize Supabase token store: {e}")
        return self._token_store

    # =========================================================================
    # Agent Loop Integration Points
    # =========================================================================

    async def on_message_received(
        self,
        message_content: str,
        message_type: str = "user",
        session_id: str = None,
        metadata: Dict[str, Any] = None
    ) -> List[DetectedToken]:
        """
        Hook: Called when a message is received.

        Evaluates the message for tokens that should be persisted.

        Args:
            message_content: The message text
            message_type: Type of message (user, assistant, system)
            session_id: Optional session ID
            metadata: Additional metadata

        Returns:
            List of tokens that were detected and need attention
        """
        if not self.config.persist_on_message:
            return []

        detected = self.evaluator.evaluate_message(
            message_content, message_type, session_id
        )

        if detected:
            logger.info(f"Message analysis detected {len(detected)} potential tokens")
            await self._process_detected_tokens(detected, f"message:{message_type}")

        return detected

    async def on_pre_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        session_id: str = None
    ) -> List[DetectedToken]:
        """
        Hook: Called before a tool is executed.

        Evaluates tool input for tokens that should be persisted.
        This is critical for catching credentials passed to tools.

        Args:
            tool_name: Name of the tool
            tool_input: The tool's input parameters
            session_id: Optional session ID

        Returns:
            List of detected tokens
        """
        if not self.config.persist_on_tool_use:
            return []

        detected = self.evaluator.evaluate_tool_input(
            tool_name, tool_input, f"pre_tool:{session_id or 'unknown'}"
        )

        if detected:
            logger.info(f"Pre-tool analysis for {tool_name} detected {len(detected)} tokens")
            await self._process_detected_tokens(detected, f"tool:{tool_name}:input")

        return detected

    async def on_post_tool_use(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        tool_result: Any,
        is_error: bool = False,
        session_id: str = None
    ) -> List[DetectedToken]:
        """
        Hook: Called after a tool is executed.

        Evaluates tool result for tokens that should be persisted.
        Captures tokens that are returned from external services.

        Args:
            tool_name: Name of the tool
            tool_input: The tool's input parameters
            tool_result: The tool's output
            is_error: Whether the tool errored
            session_id: Optional session ID

        Returns:
            List of detected tokens
        """
        if not self.config.persist_on_tool_use or is_error:
            return []

        detected = self.evaluator.evaluate_tool_result(
            tool_name, tool_result, f"post_tool:{session_id or 'unknown'}"
        )

        if detected:
            logger.info(f"Post-tool analysis for {tool_name} detected {len(detected)} tokens")
            await self._process_detected_tokens(detected, f"tool:{tool_name}:result")

        return detected

    async def on_session_end(self, session_id: str):
        """
        Hook: Called when a session ends.

        Persists any pending tokens and logs session summary.

        Args:
            session_id: The session that's ending
        """
        # Store session memory trace
        await self.kstar.store_trace({
            "situation": {
                "domain": "memory_system",
                "actor": "system",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            },
            "task": {
                "goal": "Session memory consolidation"
            },
            "action": {
                "type": "session_end",
                "tokens_persisted": len(self._persisted_keys),
                "pending_confirmations": len(self._pending_confirmations)
            },
            "result": {
                "success": True
            },
            "mode": "system",
            "tags": ["memory", "session_end"]
        })

        # Clear session-specific caches
        self.evaluator.clear_cache()

    # =========================================================================
    # Token Persistence
    # =========================================================================

    async def _process_detected_tokens(
        self,
        detected: List[DetectedToken],
        source: str
    ):
        """Process detected tokens - persist or queue for confirmation"""
        for token in detected:
            # Skip if already persisted
            if token.key in self._persisted_keys:
                continue

            # Check if auto-persist is allowed for this category
            if token.category not in self.config.auto_persist_categories:
                logger.debug(f"Skipping {token.key} - category {token.category} not in auto-persist list")
                continue

            # Check if confirmation is required
            if token.token_type in self.config.require_confirmation:
                self._pending_confirmations[token.key] = token
                logger.info(f"Token {token.key} queued for confirmation (sensitive type)")
                continue

            # Persist the token
            await self._persist_token(token, source)

    async def _persist_token(self, detected: DetectedToken, source: str):
        """Persist a detected token to storage"""
        if not self.token_store:
            logger.warning("Token store not available - cannot persist token")
            return

        try:
            token = detected.to_control_token(provenance_source=source)
            token_id = await self.token_store.store(token)

            self._persisted_keys.add(detected.key)

            logger.info(
                f"Auto-persisted token: key={detected.key}, type={detected.token_type.value}, "
                f"category={detected.category.value}, confidence={detected.confidence:.2f}"
            )

            # Log to KSTAR trace
            await self.kstar.store_trace({
                "situation": {
                    "domain": "memory_system.auto_persist",
                    "actor": "necessity_evaluator",
                    "source": source,
                    "timestamp": datetime.now(timezone.utc).isoformat()
                },
                "task": {
                    "goal": "Persist detected control token"
                },
                "action": {
                    "type": "store_control_token",
                    "token_key": detected.key,
                    "token_type": detected.token_type.value,
                    "category": detected.category.value,
                    "confidence": detected.confidence
                },
                "result": {
                    "success": True,
                    "token_id": token_id
                },
                "mode": "system",
                "tags": ["memory", "auto_persist", detected.category.value] + detected.tags
            })

        except Exception as e:
            logger.exception(f"Failed to persist token {detected.key}: {e}")

    async def confirm_pending(self, key: str, confirmed: bool = True) -> Optional[str]:
        """
        Confirm or reject a pending token.

        Args:
            key: The token key
            confirmed: Whether to persist

        Returns:
            Token ID if persisted, None otherwise
        """
        if key not in self._pending_confirmations:
            return None

        token = self._pending_confirmations.pop(key)

        if confirmed:
            await self._persist_token(token, "user_confirmed")
            return token.key
        else:
            logger.info(f"Token {key} rejected by user")
            return None

    # =========================================================================
    # Direct Token Operations
    # =========================================================================

    async def store_token(
        self,
        key: str,
        value: str,
        token_type: TokenType,
        binding_target: str,
        scopes: List[TokenScope] = None,
        category: NecessityCategory = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> Optional[str]:
        """
        Directly store a control token.

        Args:
            key: Lookup key
            value: Secret value
            token_type: Type of token
            binding_target: What this unlocks
            scopes: Permissions
            category: Necessity category
            tags: Searchable tags
            metadata: Additional metadata

        Returns:
            Token ID if stored, None on failure
        """
        if not self.token_store:
            logger.error("Token store not available")
            return None

        token = ControlToken.create(
            key=key,
            value=value,
            token_type=token_type,
            binding_target=binding_target,
            scopes=scopes or [TokenScope.READ],
            provenance_source="direct_store",
            metadata={
                "category": (category or NecessityCategory.CONFIGURATION).value,
                "tags": tags or [],
                **(metadata or {})
            }
        )

        try:
            token_id = await self.token_store.store(token)
            self._persisted_keys.add(key)
            return token_id
        except Exception as e:
            logger.exception(f"Failed to store token: {e}")
            return None

    async def get_token(self, key: str) -> Optional[ControlToken]:
        """Get a token by key"""
        if not self.token_store:
            return None
        return await self.token_store.get_by_key(key)

    async def search_by_category(self, category: NecessityCategory) -> List[ControlToken]:
        """Search tokens by category"""
        if not self.token_store:
            return []

        try:
            # Query using metadata category
            result = self.token_store.client.table("control_tokens").select("*").contains(
                "metadata", {"category": category.value}
            ).eq(
                "is_revoked", False
            ).execute()

            return [ControlToken.from_dict(row) for row in result.data]
        except Exception as e:
            logger.exception(f"Failed to search by category: {e}")
            return []

    async def search_by_tag(self, tag: str) -> List[ControlToken]:
        """Search tokens by tag"""
        if not self.token_store:
            return []

        try:
            # Query using metadata tags (contains)
            result = self.token_store.client.table("control_tokens").select("*").contains(
                "metadata->>tags", tag
            ).eq(
                "is_revoked", False
            ).execute()

            return [ControlToken.from_dict(row) for row in result.data]
        except Exception as e:
            logger.exception(f"Failed to search by tag: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """Get memory system statistics"""
        kstar_stats = await self.kstar.get_stats()

        token_stats = {}
        if self.token_store:
            try:
                token_stats["active_tokens"] = await self.token_store.count_active_tokens()
            except:
                token_stats["active_tokens"] = "unavailable"

        return {
            "kstar": kstar_stats,
            "tokens": {
                **token_stats,
                "session_persisted": len(self._persisted_keys),
                "pending_confirmations": len(self._pending_confirmations),
            },
            "config": {
                "auto_persist_enabled": self.config.auto_persist_enabled,
                "min_confidence": self.config.min_confidence_threshold,
            }
        }


# =============================================================================
# Global Memory System Instance
# =============================================================================

_memory_system: Optional[MemorySystem] = None


def get_memory_system() -> MemorySystem:
    """Get the global memory system instance"""
    global _memory_system
    if _memory_system is None:
        _memory_system = MemorySystem()
    return _memory_system


def initialize_memory_system(
    config: Optional[MemorySystemConfig] = None,
    kstar_memory: Optional[KStarMemory] = None,
    token_store: Optional[SupabaseTokenStore] = None,
) -> MemorySystem:
    """Initialize the global memory system"""
    global _memory_system
    _memory_system = MemorySystem(config, kstar_memory, token_store)
    return _memory_system
