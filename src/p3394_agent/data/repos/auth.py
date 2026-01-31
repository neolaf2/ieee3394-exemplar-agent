"""
Authentication Repository

Handles User, APIKey, and Session persistence.
Integrates with P3394 Principal registry.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import UUID

from ..models.auth import (
    User,
    UserStatus,
    APIKey,
    APIKeyStatus,
    Session,
)
from .base import Repository


class UserRepository(Repository[User]):
    """Repository for User entities."""

    @property
    def table_name(self) -> str:
        return "users"

    @property
    def model_class(self) -> type[User]:
        return User

    async def get_by_email(self, email: str) -> Optional[User]:
        """Find user by email address."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("email", email.lower())
                .single()
                .execute()
            )
            return User(**response.data) if response.data else None

        # In-memory lookup
        for user in self._in_memory_store.values():
            if user.email.lower() == email.lower():
                return user
        return None

    async def get_by_verification_token(self, token: str) -> Optional[User]:
        """Find user by email verification token."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("email_verification_token", token)
                .single()
                .execute()
            )
            return User(**response.data) if response.data else None

        for user in self._in_memory_store.values():
            if user.email_verification_token == token:
                return user
        return None

    async def get_by_password_reset_token(self, token: str) -> Optional[User]:
        """Find user by password reset token."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("password_reset_token", token)
                .single()
                .execute()
            )
            return User(**response.data) if response.data else None

        for user in self._in_memory_store.values():
            if user.password_reset_token == token:
                return user
        return None

    async def increment_failed_login(self, user_id: UUID) -> None:
        """Increment failed login counter and possibly lock account."""
        user = await self.get(user_id)
        if not user:
            return

        new_attempts = user.failed_login_attempts + 1
        updates = {"failed_login_attempts": new_attempts}

        # Lock after 5 failed attempts for 15 minutes
        if new_attempts >= 5:
            updates["locked_until"] = (
                datetime.utcnow() + timedelta(minutes=15)
            ).isoformat()

        await self.update(user_id, **updates)

    async def reset_failed_login(self, user_id: UUID) -> None:
        """Reset failed login counter on successful login."""
        await self.update(
            user_id,
            failed_login_attempts=0,
            locked_until=None,
            last_login_at=datetime.utcnow().isoformat(),
        )

    async def verify_email(self, user_id: UUID) -> None:
        """Mark email as verified and activate account."""
        await self.update(
            user_id,
            email_verified=True,
            email_verification_token=None,
            email_verification_expires=None,
            status=UserStatus.ACTIVE.value,
        )


class APIKeyRepository(Repository[APIKey]):
    """Repository for API Key entities."""

    @property
    def table_name(self) -> str:
        return "api_keys"

    @property
    def model_class(self) -> type[APIKey]:
        return APIKey

    async def get_by_prefix(self, prefix: str) -> Optional[APIKey]:
        """Find API key by prefix for initial lookup."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("key_prefix", prefix)
                .eq("status", APIKeyStatus.ACTIVE.value)
                .single()
                .execute()
            )
            return APIKey(**response.data) if response.data else None

        for key in self._in_memory_store.values():
            if key.key_prefix == prefix and key.status == APIKeyStatus.ACTIVE:
                return key
        return None

    async def list_by_user(
        self, user_id: UUID, include_revoked: bool = False
    ) -> list[APIKey]:
        """List all API keys for a user."""
        if self.client:
            query = (
                self.client.table(self.table_name)
                .select("*")
                .eq("user_id", str(user_id))
            )
            if not include_revoked:
                query = query.neq("status", APIKeyStatus.REVOKED.value)
            response = query.execute()
            return [APIKey(**r) for r in response.data]

        keys = [
            k for k in self._in_memory_store.values()
            if k.user_id == user_id
        ]
        if not include_revoked:
            keys = [k for k in keys if k.status != APIKeyStatus.REVOKED]
        return keys

    async def revoke(self, key_id: UUID) -> Optional[APIKey]:
        """Revoke an API key."""
        return await self.update(
            key_id,
            status=APIKeyStatus.REVOKED.value,
            revoked_at=datetime.utcnow().isoformat(),
        )

    async def record_usage(self, key_id: UUID) -> None:
        """Record API key usage."""
        key = await self.get(key_id)
        if key:
            await self.update(
                key_id,
                last_used_at=datetime.utcnow().isoformat(),
                usage_count=key.usage_count + 1,
            )


class SessionRepository(Repository[Session]):
    """Repository for Session entities."""

    @property
    def table_name(self) -> str:
        return "sessions"

    @property
    def model_class(self) -> type[Session]:
        return Session

    async def get_by_token_hash(self, token_hash: str) -> Optional[Session]:
        """Find session by token hash."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("token_hash", token_hash)
                .single()
                .execute()
            )
            return Session(**response.data) if response.data else None

        for session in self._in_memory_store.values():
            if session.token_hash == token_hash:
                return session
        return None

    async def list_by_user(self, user_id: UUID) -> list[Session]:
        """List all sessions for a user."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .select("*")
                .eq("user_id", str(user_id))
                .execute()
            )
            return [Session(**r) for r in response.data]

        return [
            s for s in self._in_memory_store.values()
            if s.user_id == user_id
        ]

    async def delete_expired(self) -> int:
        """Delete all expired sessions. Returns count deleted."""
        now = datetime.utcnow()
        if self.client:
            response = (
                self.client.table(self.table_name)
                .delete()
                .lt("expires_at", now.isoformat())
                .execute()
            )
            return len(response.data)

        # In-memory cleanup
        expired_ids = [
            s.id for s in self._in_memory_store.values()
            if s.expires_at < now
        ]
        for sid in expired_ids:
            del self._in_memory_store[sid]
        return len(expired_ids)

    async def delete_all_for_user(self, user_id: UUID) -> int:
        """Delete all sessions for a user (logout everywhere)."""
        if self.client:
            response = (
                self.client.table(self.table_name)
                .delete()
                .eq("user_id", str(user_id))
                .execute()
            )
            return len(response.data)

        user_sessions = [
            s.id for s in self._in_memory_store.values()
            if s.user_id == user_id
        ]
        for sid in user_sessions:
            del self._in_memory_store[sid]
        return len(user_sessions)

    async def touch(self, session_id: UUID) -> None:
        """Update last activity timestamp."""
        await self.update(
            session_id,
            last_activity_at=datetime.utcnow().isoformat(),
        )


class AuthRepository:
    """
    Composite repository for all authentication entities.

    Provides a single interface for authentication operations.
    Integrates with P3394 Principal registry for semantic identity.
    """

    def __init__(self, client: Any = None, principal_registry: Any = None):
        self.client = client
        self.principal_registry = principal_registry
        self.users = UserRepository(client)
        self.api_keys = APIKeyRepository(client)
        self.sessions = SessionRepository(client)

    async def create_user(self, user: User) -> User:
        """
        Create a user and optionally register as Principal.
        """
        result = await self.users.create(user)

        # Also register as P3394 Principal if registry available
        if self.principal_registry:
            principal = user.to_principal()
            await self.principal_registry.register(principal)

        return result

    async def authenticate_user(
        self, email: str, password: str
    ) -> tuple[Optional[User], str]:
        """
        Authenticate user with email and password.

        Returns: (user, error_message)
        """
        user = await self.users.get_by_email(email)

        if not user:
            return None, "Invalid email or password"

        if user.status == UserStatus.SUSPENDED:
            return None, "Account is suspended"

        if user.status == UserStatus.DEACTIVATED:
            return None, "Account has been deactivated"

        if user.is_locked:
            return None, "Account is temporarily locked due to too many failed attempts"

        if not user.verify_password(password):
            await self.users.increment_failed_login(user.id)
            return None, "Invalid email or password"

        if not user.email_verified:
            return None, "Please verify your email address"

        await self.users.reset_failed_login(user.id)
        return user, ""

    async def authenticate_api_key(self, key: str) -> tuple[Optional[APIKey], str]:
        """
        Authenticate with API key.

        Returns: (api_key, error_message)
        """
        if not key.startswith("p3394_"):
            return None, "Invalid API key format"

        prefix = key[:14]
        api_key = await self.api_keys.get_by_prefix(prefix)

        if not api_key:
            return None, "Invalid API key"

        if not api_key.is_valid:
            return None, "API key is expired or revoked"

        if not api_key.verify_key(key):
            return None, "Invalid API key"

        await self.api_keys.record_usage(api_key.id)
        return api_key, ""

    async def authenticate_session(
        self, token: str
    ) -> tuple[Optional[Session], Optional[User], str]:
        """
        Authenticate with session token.

        Returns: (session, user, error_message)
        """
        import hashlib
        token_hash = hashlib.sha256(token.encode()).hexdigest()

        session = await self.sessions.get_by_token_hash(token_hash)

        if not session:
            return None, None, "Invalid session"

        if session.is_expired:
            await self.sessions.delete(session.id)
            return None, None, "Session expired"

        user = await self.users.get(session.user_id)
        if not user or user.status != UserStatus.ACTIVE:
            return None, None, "User not found or inactive"

        await self.sessions.touch(session.id)
        return session, user, ""
