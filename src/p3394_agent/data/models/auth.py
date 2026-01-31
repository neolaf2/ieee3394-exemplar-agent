"""
Authentication Models

User authentication, API keys, and session management.
Integrates with P3394 Principal identity system.
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Optional, TYPE_CHECKING
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, EmailStr

if TYPE_CHECKING:
    from ...core.auth import Principal


class UserStatus(str, Enum):
    """User account status."""
    PENDING = "pending"  # Awaiting email verification
    ACTIVE = "active"
    SUSPENDED = "suspended"
    DEACTIVATED = "deactivated"


class UserRole(str, Enum):
    """System-level user roles."""
    ADMIN = "admin"
    TEACHER = "teacher"
    STUDENT = "student"
    OBSERVER = "observer"


class APIKeyStatus(str, Enum):
    """API key status."""
    ACTIVE = "active"
    REVOKED = "revoked"
    EXPIRED = "expired"


class User(BaseModel):
    """
    User account for authentication.

    Links to P3394 Principal via person_id for semantic identity.
    """
    id: UUID = Field(default_factory=uuid4)
    person_id: UUID  # Links to Principal.person URN component
    email: EmailStr
    password_hash: str
    salt: str

    # Account status
    status: UserStatus = UserStatus.PENDING
    role: UserRole = UserRole.TEACHER
    email_verified: bool = False
    email_verification_token: Optional[str] = None
    email_verification_expires: Optional[datetime] = None

    # Password reset
    password_reset_token: Optional[str] = None
    password_reset_expires: Optional[datetime] = None

    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    last_login_at: Optional[datetime] = None
    last_login_ip: Optional[str] = None

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: dict = Field(default_factory=dict)

    @staticmethod
    def hash_password(password: str, salt: str = None) -> tuple[str, str]:
        """Hash a password with salt."""
        if salt is None:
            salt = secrets.token_hex(32)
        hash_input = f"{password}{salt}".encode()
        password_hash = hashlib.sha256(hash_input).hexdigest()
        return password_hash, salt

    def verify_password(self, password: str) -> bool:
        """Verify a password against stored hash."""
        test_hash, _ = self.hash_password(password, self.salt)
        return secrets.compare_digest(test_hash, self.password_hash)

    def generate_verification_token(self) -> str:
        """Generate email verification token."""
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_expires = datetime.now(timezone.utc) + timedelta(hours=24)
        return self.email_verification_token

    def generate_password_reset_token(self) -> str:
        """Generate password reset token."""
        self.password_reset_token = secrets.token_urlsafe(32)
        self.password_reset_expires = datetime.now(timezone.utc) + timedelta(hours=1)
        return self.password_reset_token

    @property
    def is_locked(self) -> bool:
        """Check if account is locked."""
        if self.locked_until is None:
            return False
        return datetime.now(timezone.utc) < self.locked_until

    @property
    def principal_id(self) -> str:
        """Get the P3394 Principal URN for this user."""
        return f"urn:principal:org:ieee3394:role:{self.role.value}:person:{self.person_id}"

    def to_principal(self) -> "Principal":
        """
        Convert User to P3394 Principal.

        This bridges the web auth layer to the P3394 identity model.
        """
        from ...core.auth import Principal, PrincipalType

        return Principal(
            principal_id=self.principal_id,
            org="urn:org:ieee3394",
            role=f"urn:role:{self.role.value}",
            person=f"urn:person:{self.person_id}",
            principal_type=PrincipalType.HUMAN,
            display_name=self.email,
            email=self.email,
            is_active=self.status == UserStatus.ACTIVE,
            created_at=self.created_at,
            updated_at=self.updated_at,
        )

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440300",
                "person_id": "550e8400-e29b-41d4-a716-446655440001",
                "email": "teacher@example.com",
                "status": "active",
                "role": "teacher",
                "email_verified": True
            }
        }


class APIKey(BaseModel):
    """
    API key for programmatic access.

    Used for connecting external tools to the agent.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    name: str  # User-friendly name like "My Claude Code Integration"

    # Key details (prefix is shown, secret is hashed)
    key_prefix: str  # First 8 chars shown: "p3394_xxxx..."
    key_hash: str  # SHA256 of full key
    key_hint: str  # Last 4 chars: "...xxxx"

    # Permissions
    scopes: list[str] = Field(default_factory=list)  # ["read", "write", "admin"]
    rate_limit: int = 1000  # Requests per hour

    # Status
    status: APIKeyStatus = APIKeyStatus.ACTIVE
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    usage_count: int = 0

    # Timestamps
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    revoked_at: Optional[datetime] = None
    metadata: dict = Field(default_factory=dict)

    @staticmethod
    def generate() -> tuple[str, str, str, str]:
        """
        Generate a new API key.

        Returns: (full_key, key_prefix, key_hash, key_hint)
        """
        key = f"p3394_{secrets.token_urlsafe(32)}"
        key_prefix = key[:14]
        key_hint = key[-4:]
        key_hash = hashlib.sha256(key.encode()).hexdigest()
        return key, key_prefix, key_hash, key_hint

    @staticmethod
    def hash_key(key: str) -> str:
        """Hash a key for comparison."""
        return hashlib.sha256(key.encode()).hexdigest()

    def verify_key(self, key: str) -> bool:
        """Verify a key against stored hash."""
        test_hash = self.hash_key(key)
        return secrets.compare_digest(test_hash, self.key_hash)

    @property
    def is_valid(self) -> bool:
        """Check if key is valid (active and not expired)."""
        if self.status != APIKeyStatus.ACTIVE:
            return False
        if self.expires_at and datetime.now(timezone.utc) > self.expires_at:
            return False
        return True

    @property
    def display_key(self) -> str:
        """Get display-safe key representation."""
        return f"{self.key_prefix}...{self.key_hint}"

    class Config:
        json_schema_extra = {
            "example": {
                "id": "550e8400-e29b-41d4-a716-446655440310",
                "user_id": "550e8400-e29b-41d4-a716-446655440300",
                "name": "Claude Code Integration",
                "key_prefix": "p3394_abc123xy",
                "key_hint": "wxyz",
                "scopes": ["read", "write"],
                "status": "active"
            }
        }


class Session(BaseModel):
    """
    User session for web authentication.
    """
    id: UUID = Field(default_factory=uuid4)
    user_id: UUID
    token_hash: str  # SHA256 of session token
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    expires_at: datetime
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    last_activity_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def generate_token() -> tuple[str, str]:
        """Generate session token. Returns (token, token_hash)."""
        token = secrets.token_urlsafe(64)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        return token, token_hash

    @property
    def is_expired(self) -> bool:
        """Check if session is expired."""
        return datetime.now(timezone.utc) > self.expires_at


class SignupRequest(BaseModel):
    """Request model for user signup."""
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str = Field(min_length=2, max_length=100)
    organization: Optional[str] = None
    invite_code: Optional[str] = None  # For invite-only signups

    class Config:
        json_schema_extra = {
            "example": {
                "email": "user@example.com",
                "password": "securePassword123!",
                "display_name": "Dr. Jane Smith",
                "organization": "Example University"
            }
        }


class LoginRequest(BaseModel):
    """Request model for login."""
    email: EmailStr
    password: str


class PasswordChangeRequest(BaseModel):
    """Request model for password change."""
    current_password: str
    new_password: str = Field(min_length=8)


class PasswordResetRequest(BaseModel):
    """Request model for password reset."""
    email: EmailStr


class CreateAPIKeyRequest(BaseModel):
    """Request model for creating an API key."""
    name: str = Field(min_length=1, max_length=100)
    scopes: list[str] = Field(default=["read", "write"])
    expires_days: Optional[int] = Field(default=None, ge=1, le=365)
