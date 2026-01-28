"""
Session Management

Manages client sessions with the agent, including session creation,
expiration, and cleanup.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional
from uuid import uuid4


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

    def is_expired(self) -> bool:
        """Check if session has expired"""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at

    def touch(self) -> None:
        """Update last activity timestamp"""
        self.last_activity = datetime.now(timezone.utc)


class SessionManager:
    """Manages agent sessions"""

    DEFAULT_TTL = timedelta(hours=24)

    def __init__(self, default_ttl: Optional[timedelta] = None):
        self.sessions: Dict[str, Session] = {}
        self.default_ttl = default_ttl or self.DEFAULT_TTL

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
        """Create a new session"""
        ttl = ttl or self.default_ttl
        session = Session(
            client_id=client_id,
            channel_id=channel_id,
            expires_at=datetime.now(timezone.utc) + ttl
        )
        self.sessions[session.id] = session
        return session

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
