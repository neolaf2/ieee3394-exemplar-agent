"""
Session Management

Manages client sessions with the agent, including session creation,
expiration, cleanup, and shared working directories.

Supports two concurrency modes (configured in agent.yaml):
- "collaborative": Any channel can read/write (default, like Claude/ChatGPT)
- "primary_binding": One primary channel per session, explicit handoff required
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, TYPE_CHECKING
from uuid import uuid4
from pathlib import Path
from enum import Enum
import logging
import shutil

if TYPE_CHECKING:
    from config.schema import SessionConfig

logger = logging.getLogger(__name__)


class ChannelRole(str, Enum):
    """Role of a channel within a session"""
    PRIMARY = "primary"      # Can send/receive, owns the session
    OBSERVER = "observer"    # Can receive broadcasts, cannot send commands
    PENDING = "pending"      # Requested primary, waiting for handoff
    COLLABORATIVE = "collaborative"  # Equal access (collaborative mode)


@dataclass
class ChannelBinding:
    """Represents a channel's connection to a session"""
    channel_id: str
    channel_type: str           # "cli", "web", "p3394", etc.
    role: ChannelRole
    connected_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    client_address: Optional[str] = None  # For P3394 agent-to-agent
    metadata: Dict = field(default_factory=dict)


@dataclass
class Session:
    """Represents a client session with the agent"""
    id: str = field(default_factory=lambda: str(uuid4()))
    client_id: Optional[str] = None
    client_agent_uri: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    is_authenticated: bool = False
    metadata: Dict = field(default_factory=dict)

    # P3394 Authentication fields
    client_principal_id: Optional[str] = None      # Semantic principal URN
    service_principal_id: Optional[str] = None     # Service principal URN
    granted_permissions: list[str] = field(default_factory=list)  # Permissions granted to this session
    assurance_level: str = "none"                  # Authentication assurance level

    # Shared working directory (set during initialization)
    working_dir: Optional[Path] = None

    # Channel binding (for primary_binding mode)
    primary_channel_id: Optional[str] = None
    primary_bound_at: Optional[datetime] = None
    channel_bindings: Dict[str, ChannelBinding] = field(default_factory=dict)

    # Handoff state
    pending_handoff_to: Optional[str] = None
    handoff_requested_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if session has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)

    def has_permission(self, permission: str) -> bool:
        """Check if session has a specific permission"""
        # Check if permission is in granted list or wildcard
        return "*" in self.granted_permissions or permission in self.granted_permissions

    def grant_permission(self, permission: str) -> None:
        """Grant a permission to this session"""
        if permission not in self.granted_permissions:
            self.granted_permissions.append(permission)

    def revoke_permission(self, permission: str) -> None:
        """Revoke a permission from this session"""
        if permission in self.granted_permissions:
            self.granted_permissions.remove(permission)

    def get_workspace_dir(self) -> Path:
        """Get the workspace subdirectory"""
        if not self.working_dir:
            raise RuntimeError("Session working directory not initialized")
        return self.working_dir / "workspace"

    def get_artifacts_dir(self) -> Path:
        """Get the artifacts subdirectory"""
        if not self.working_dir:
            raise RuntimeError("Session working directory not initialized")
        return self.working_dir / "artifacts"

    def get_temp_dir(self) -> Path:
        """Get the temporary files subdirectory"""
        if not self.working_dir:
            raise RuntimeError("Session working directory not initialized")
        return self.working_dir / "temp"

    def get_tools_dir(self) -> Path:
        """Get the tools subdirectory"""
        if not self.working_dir:
            raise RuntimeError("Session working directory not initialized")
        return self.working_dir / "tools"

    # =========================================================================
    # Channel Binding Methods (for primary_binding mode)
    # =========================================================================

    def bind_channel(self, channel_id: str, channel_type: str, role: ChannelRole) -> ChannelBinding:
        """Bind a channel to this session with specified role"""
        binding = ChannelBinding(
            channel_id=channel_id,
            channel_type=channel_type,
            role=role,
            connected_at=datetime.now(timezone.utc)
        )
        self.channel_bindings[channel_id] = binding

        if role == ChannelRole.PRIMARY:
            self.primary_channel_id = channel_id
            self.primary_bound_at = datetime.now(timezone.utc)

        return binding

    def is_primary(self, channel_id: str) -> bool:
        """Check if channel is the primary"""
        return self.primary_channel_id == channel_id

    def get_channel_role(self, channel_id: str) -> Optional[ChannelRole]:
        """Get the role of a channel in this session"""
        if channel_id in self.channel_bindings:
            return self.channel_bindings[channel_id].role
        return None

    def transfer_primary(self, to_channel_id: str) -> bool:
        """Transfer primary role to another connected channel"""
        if to_channel_id not in self.channel_bindings:
            return False

        # Demote current primary to observer
        if self.primary_channel_id and self.primary_channel_id in self.channel_bindings:
            self.channel_bindings[self.primary_channel_id].role = ChannelRole.OBSERVER

        # Promote new channel to primary
        self.channel_bindings[to_channel_id].role = ChannelRole.PRIMARY
        self.primary_channel_id = to_channel_id
        self.primary_bound_at = datetime.now(timezone.utc)
        self.pending_handoff_to = None
        self.handoff_requested_at = None
        return True

    def release_primary(self) -> bool:
        """Release primary binding (session becomes unbound)"""
        if self.primary_channel_id and self.primary_channel_id in self.channel_bindings:
            self.channel_bindings[self.primary_channel_id].role = ChannelRole.OBSERVER
        self.primary_channel_id = None
        self.primary_bound_at = None
        return True

    def remove_channel(self, channel_id: str) -> None:
        """Remove a channel from this session"""
        if channel_id in self.channel_bindings:
            del self.channel_bindings[channel_id]
        if self.primary_channel_id == channel_id:
            self.primary_channel_id = None
            self.primary_bound_at = None


@dataclass
class ChannelAccessResult:
    """Result of channel access validation"""
    allowed: bool
    role: ChannelRole
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    primary_channel_id: Optional[str] = None
    suggestion: Optional[str] = None


class SessionManager:
    """
    Manages agent sessions with configurable concurrency modes.

    Modes:
    - "collaborative": Any channel can read/write (default)
    - "primary_binding": One primary channel, others observe
    """

    DEFAULT_TTL = timedelta(hours=24)

    def __init__(
        self,
        default_ttl: Optional[timedelta] = None,
        storage_dir: Optional[Path] = None,
        session_config: Optional["SessionConfig"] = None
    ):
        self.sessions: Dict[str, Session] = {}
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        self.storage_dir = storage_dir

        # Session concurrency configuration
        self._config = session_config
        self._mode = "collaborative"  # Default
        self._allow_observers = True
        self._allow_switching = True
        self._require_handoff_ack = False

        if session_config:
            self._mode = session_config.mode
            if session_config.primary_binding:
                self._allow_observers = session_config.primary_binding.allow_observers
                self._allow_switching = session_config.primary_binding.allow_channel_switching
                self._require_handoff_ack = session_config.primary_binding.require_handoff_ack
            if session_config.default_ttl_hours:
                self.default_ttl = timedelta(hours=session_config.default_ttl_hours)

    @property
    def is_collaborative(self) -> bool:
        """Check if running in collaborative mode"""
        return self._mode == "collaborative"

    @property
    def is_primary_binding(self) -> bool:
        """Check if running in primary_binding mode"""
        return self._mode == "primary_binding"

    @property
    def active_sessions(self) -> Dict[str, Session]:
        """Get all non-expired sessions"""
        return {k: v for k, v in self.sessions.items() if not v.is_expired()}

    async def create_session(
        self,
        client_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        ttl: Optional[timedelta] = None
    ) -> Session:
        """Create a new session with shared working directory"""
        ttl = ttl or self.default_ttl
        session = Session(
            client_id=client_id,
            channel_id=channel_id,
            expires_at=datetime.now(timezone.utc) + ttl
        )

        # Create shared working directory structure
        if self.storage_dir:
            session.working_dir = self._create_working_directory(session.id)

        self.sessions[session.id] = session
        return session

    def _create_working_directory(self, session_id: str) -> Path:
        """
        Create shared working directory structure for session.

        Structure:
        storage_dir/stm/<session_id>/shared/
        ├── workspace/    # Primary working directory for agent
        ├── artifacts/    # Generated artifacts (docs, PDFs, etc.)
        ├── temp/         # Temporary files
        └── tools/        # Session-specific tools (pandoc, ffmpeg, etc.)
        """
        base_dir = self.storage_dir / "stm" / session_id / "shared"

        # Create subdirectories
        subdirs = ["workspace", "artifacts", "temp", "tools"]
        for subdir in subdirs:
            dir_path = base_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Created session directory: {dir_path}")

        logger.info(f"Created shared working directory for session {session_id}: {base_dir}")
        return base_dir

    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        session = self.sessions.get(session_id)
        if session and not session.is_expired():
            session.touch()
            return session
        return None

    async def end_session(self, session_id: str) -> None:
        """End a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]

    async def cleanup_expired(self) -> None:
        """Remove expired sessions"""
        expired = [k for k, v in self.sessions.items() if v.is_expired()]
        for session_id in expired:
            del self.sessions[session_id]

    # =========================================================================
    # Channel Access Validation
    # =========================================================================

    def validate_channel_access(
        self,
        session_id: str,
        channel_id: str,
        channel_type: str,
        is_write_operation: bool = True
    ) -> ChannelAccessResult:
        """
        Validate if a channel can access a session.

        In collaborative mode: Always allowed (like Claude/ChatGPT)
        In primary_binding mode: Enforces primary channel lock
        """
        session = self.get_session(session_id)

        if not session:
            return ChannelAccessResult(
                allowed=False,
                role=ChannelRole.OBSERVER,
                error_code="SESSION_NOT_FOUND",
                error_message=f"Session {session_id} does not exist",
                suggestion="Create a new session with /startSession"
            )

        # Collaborative mode: everyone can read/write
        if self.is_collaborative:
            # Track channel but don't enforce roles
            if channel_id not in session.channel_bindings:
                session.bind_channel(channel_id, channel_type, ChannelRole.COLLABORATIVE)
            return ChannelAccessResult(
                allowed=True,
                role=ChannelRole.COLLABORATIVE
            )

        # Primary binding mode: enforce roles
        return self._validate_primary_binding_access(
            session, channel_id, channel_type, is_write_operation
        )

    def _validate_primary_binding_access(
        self,
        session: Session,
        channel_id: str,
        channel_type: str,
        is_write_operation: bool
    ) -> ChannelAccessResult:
        """Validate access in primary_binding mode"""

        # Check if channel is already bound
        if channel_id in session.channel_bindings:
            binding = session.channel_bindings[channel_id]

            if binding.role == ChannelRole.PRIMARY:
                return ChannelAccessResult(allowed=True, role=ChannelRole.PRIMARY)

            if binding.role == ChannelRole.OBSERVER:
                if is_write_operation:
                    return ChannelAccessResult(
                        allowed=False,
                        role=ChannelRole.OBSERVER,
                        error_code="OBSERVER_CANNOT_WRITE",
                        error_message="Observer channels cannot send commands",
                        primary_channel_id=session.primary_channel_id,
                        suggestion="Use /claimSession to request primary role"
                    )
                return ChannelAccessResult(allowed=True, role=ChannelRole.OBSERVER)

        # New channel trying to connect to existing session
        if session.primary_channel_id is None:
            # No primary - this channel can claim it
            session.bind_channel(channel_id, channel_type, ChannelRole.PRIMARY)
            return ChannelAccessResult(allowed=True, role=ChannelRole.PRIMARY)

        # Session has a primary, new channel becomes observer or blocked
        if self._allow_observers:
            session.bind_channel(channel_id, channel_type, ChannelRole.OBSERVER)
            if is_write_operation:
                return ChannelAccessResult(
                    allowed=False,
                    role=ChannelRole.OBSERVER,
                    error_code="SESSION_BOUND_TO_OTHER_CHANNEL",
                    error_message=f"Session is bound to channel '{session.primary_channel_id}'",
                    primary_channel_id=session.primary_channel_id,
                    suggestion="Connected as observer. Use /claimSession to request primary role."
                )
            return ChannelAccessResult(allowed=True, role=ChannelRole.OBSERVER)

        # Observers not allowed
        return ChannelAccessResult(
            allowed=False,
            role=ChannelRole.OBSERVER,
            error_code="SESSION_LOCKED",
            error_message=f"Session is locked to channel '{session.primary_channel_id}'",
            primary_channel_id=session.primary_channel_id,
            suggestion="Wait for primary to release, or start a new session"
        )

    def claim_primary(self, session_id: str, channel_id: str) -> ChannelAccessResult:
        """
        Attempt to claim primary role for a channel.

        In collaborative mode: No-op (everyone is equal)
        In primary_binding mode: Transfers primary if allowed
        """
        session = self.get_session(session_id)
        if not session:
            return ChannelAccessResult(
                allowed=False,
                role=ChannelRole.OBSERVER,
                error_code="SESSION_NOT_FOUND",
                error_message=f"Session {session_id} does not exist"
            )

        if self.is_collaborative:
            return ChannelAccessResult(
                allowed=True,
                role=ChannelRole.COLLABORATIVE,
                suggestion="Session is in collaborative mode - all channels have equal access"
            )

        if session.is_primary(channel_id):
            return ChannelAccessResult(
                allowed=True,
                role=ChannelRole.PRIMARY,
                suggestion="You are already the primary channel"
            )

        if session.primary_channel_id is None:
            # No primary, claim it
            if channel_id in session.channel_bindings:
                session.channel_bindings[channel_id].role = ChannelRole.PRIMARY
                session.primary_channel_id = channel_id
                session.primary_bound_at = datetime.now(timezone.utc)
            else:
                session.bind_channel(channel_id, "unknown", ChannelRole.PRIMARY)

            return ChannelAccessResult(
                allowed=True,
                role=ChannelRole.PRIMARY,
                suggestion="Claimed primary role"
            )

        if not self._allow_switching:
            return ChannelAccessResult(
                allowed=False,
                role=ChannelRole.OBSERVER,
                error_code="SWITCHING_DISABLED",
                error_message="Channel switching is disabled",
                primary_channel_id=session.primary_channel_id
            )

        # Transfer primary
        old_primary = session.primary_channel_id
        session.transfer_primary(channel_id)

        return ChannelAccessResult(
            allowed=True,
            role=ChannelRole.PRIMARY,
            suggestion=f"Claimed primary role from '{old_primary}'"
        )

    def release_primary(self, session_id: str, channel_id: str) -> ChannelAccessResult:
        """Release primary role from a channel"""
        session = self.get_session(session_id)
        if not session:
            return ChannelAccessResult(
                allowed=False,
                role=ChannelRole.OBSERVER,
                error_code="SESSION_NOT_FOUND",
                error_message=f"Session {session_id} does not exist"
            )

        if self.is_collaborative:
            return ChannelAccessResult(
                allowed=True,
                role=ChannelRole.COLLABORATIVE,
                suggestion="Session is in collaborative mode - no primary to release"
            )

        if not session.is_primary(channel_id):
            return ChannelAccessResult(
                allowed=False,
                role=session.get_channel_role(channel_id) or ChannelRole.OBSERVER,
                error_code="NOT_PRIMARY",
                error_message="You are not the primary channel"
            )

        session.release_primary()
        return ChannelAccessResult(
            allowed=True,
            role=ChannelRole.OBSERVER,
            suggestion="Released primary role. Session is now unbound."
        )
