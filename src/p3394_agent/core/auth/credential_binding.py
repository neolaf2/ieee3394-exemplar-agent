"""
Credential Binding

Maps channel-specific identities to semantic principals.

Example:
    WhatsApp phone number "+1234567890" -> urn:principal:org:ieee:role:chair:person:rtong
    CLI user "local:owner" -> urn:principal:org:ieee3394:role:admin:person:owner
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class BindingType(str, Enum):
    """Type of credential binding"""
    ACCOUNT = "account"          # Username/password style
    OAUTH = "oauth"              # OAuth2 token
    API_KEY = "api_key"          # API key
    CERTIFICATE = "certificate"  # X.509 certificate
    SSH_KEY = "ssh_key"          # SSH public key
    PHONE = "phone"              # Phone number (WhatsApp, SMS)
    EMAIL = "email"              # Email address
    BIOMETRIC = "biometric"      # Fingerprint, face ID, etc.
    HARDWARE_TOKEN = "hardware_token"  # YubiKey, etc.
    OS_USER = "os_user"          # OS username (CLI)
    LOCAL_SOCKET = "local_socket"  # Local Unix socket connection (CLI)


@dataclass
class CredentialBinding:
    """
    Maps a channel-specific credential to a semantic principal.

    This is the bridge between "whatsapp:+1234567890" and
    "urn:principal:org:ieee:role:chair:person:rtong".
    """
    binding_id: str                                # Unique binding ID (URN)
    principal_id: str                              # Semantic principal URN
    channel: str                                   # Channel ID (whatsapp, cli, p3394, etc.)
    binding_type: BindingType
    external_subject: str                          # Channel-specific identity
    scopes: list[str] = field(default_factory=list)  # Granted scopes for this binding
    secret_hash: Optional[str] = None              # Hashed secret (for password/API key)
    public_key: Optional[str] = None               # Public key (for SSH/cert)
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_used_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None

    def is_expired(self) -> bool:
        """Check if binding is expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_scope(self, scope: str) -> bool:
        """Check if binding grants a specific scope"""
        return scope in self.scopes or "*" in self.scopes

    def touch(self) -> None:
        """Update last used timestamp"""
        self.last_used_at = datetime.utcnow()

    def verify_secret(self, secret: str) -> bool:
        """
        Verify a secret against stored hash.

        In production, use bcrypt or argon2.
        """
        if not self.secret_hash:
            return False

        import hashlib
        secret_hash = hashlib.sha256(secret.encode()).hexdigest()
        return secret_hash == self.secret_hash

    def matches(self, channel: str, external_subject: str) -> bool:
        """Check if this binding matches the given channel and subject"""
        if not self.is_active or self.is_expired():
            return False

        # Exact match
        if self.channel == channel and self.external_subject == external_subject:
            return True

        # Wildcard match (e.g., "local:*" matches any local user)
        if self.channel == channel and self.external_subject.endswith("*"):
            prefix = self.external_subject[:-1]
            return external_subject.startswith(prefix)

        return False

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "binding_id": self.binding_id,
            "principal_id": self.principal_id,
            "channel": self.channel,
            "binding_type": self.binding_type.value,
            "external_subject": self.external_subject,
            "scopes": self.scopes,
            "secret_hash": self.secret_hash,  # In production, never serialize this
            "public_key": self.public_key,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_used_at": self.last_used_at.isoformat() if self.last_used_at else None,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CredentialBinding":
        """Deserialize from dictionary"""
        return cls(
            binding_id=data["binding_id"],
            principal_id=data["principal_id"],
            channel=data["channel"],
            binding_type=BindingType(data["binding_type"]),
            external_subject=data["external_subject"],
            scopes=data.get("scopes", []),
            secret_hash=data.get("secret_hash"),
            public_key=data.get("public_key"),
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            last_used_at=datetime.fromisoformat(data["last_used_at"]) if data.get("last_used_at") else None,
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )

    @classmethod
    def create_cli_admin_binding(cls) -> "CredentialBinding":
        """Create the default CLI admin binding"""
        return cls(
            binding_id="urn:cred:cli:admin:local",
            principal_id="urn:principal:org:ieee3394:role:admin:person:owner",
            channel="cli",
            binding_type=BindingType.ACCOUNT,
            external_subject="local:*",  # Matches any local user
            scopes=["*"],  # All permissions
            is_active=True,
        )

    @classmethod
    def create_whatsapp_binding(
        cls,
        phone_number: str,
        principal_id: str,
        scopes: list[str] = None
    ) -> "CredentialBinding":
        """Create a WhatsApp phone number binding"""
        if scopes is None:
            scopes = ["chat", "query"]

        binding_id = f"urn:cred:whatsapp:{phone_number.replace('+', '').replace(' ', '')}"

        return cls(
            binding_id=binding_id,
            principal_id=principal_id,
            channel="whatsapp",
            binding_type=BindingType.PHONE,
            external_subject=phone_number,
            scopes=scopes,
            is_active=True,
        )
