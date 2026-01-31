"""
Session Management

Manages client sessions with the agent, including session creation,
expiration, cleanup, and shared working directories.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4
from pathlib import Path
import logging
import shutil

logger = logging.getLogger(__name__)


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


class SessionManager:
    """Manages agent sessions"""

    DEFAULT_TTL = timedelta(hours=24)

    def __init__(
        self,
        default_ttl: Optional[timedelta] = None,
        storage_dir: Optional[Path] = None
    ):
        self.sessions: Dict[str, Session] = {}
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        self.storage_dir = storage_dir

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
