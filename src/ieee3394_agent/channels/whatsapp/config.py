"""
WhatsApp Channel Configuration and Service Principal Binding

Implements secure channel identity binding per P3394 security requirements.
Each channel adapter must authenticate with a service principal to establish
its identity and authorization scope.
"""

from dataclasses import dataclass, field
from typing import Optional, Dict, Any
from pathlib import Path
import json
import hashlib
import secrets
from datetime import datetime, timedelta, timezone


@dataclass
class ServicePrincipal:
    """
    Service Principal for channel authentication.

    A service principal is a security identity used by the adapter to
    authenticate itself to the agent gateway. It establishes:
    - Channel identity (who is this adapter?)
    - Authorization scope (what can it do?)
    - Audit trail (for security logging)

    Similar to Azure Service Principals or AWS IAM roles.
    """

    client_id: str  # Unique identifier for this adapter instance
    client_secret: str  # Secret key for authentication
    channel_type: str  # e.g., "whatsapp", "telegram", "slack"
    permissions: list[str] = field(default_factory=list)  # Granted permissions
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    expires_at: Optional[str] = None  # Optional expiration
    metadata: Dict[str, Any] = field(default_factory=dict)

    @property
    def is_expired(self) -> bool:
        """Check if the service principal has expired."""
        if not self.expires_at:
            return False

        expiry = datetime.fromisoformat(self.expires_at)
        return datetime.now(timezone.utc) > expiry

    def verify_secret(self, secret: str) -> bool:
        """
        Verify the provided secret matches the stored secret.

        Uses constant-time comparison to prevent timing attacks.
        """
        return secrets.compare_digest(self.client_secret, secret)

    def has_permission(self, permission: str) -> bool:
        """Check if this principal has a specific permission."""
        return permission in self.permissions or "*" in self.permissions

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "channel_type": self.channel_type,
            "permissions": self.permissions,
            "created_at": self.created_at,
            "expires_at": self.expires_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServicePrincipal":
        """Create from dictionary."""
        return cls(
            client_id=data["client_id"],
            client_secret=data["client_secret"],
            channel_type=data["channel_type"],
            permissions=data.get("permissions", []),
            created_at=data.get("created_at", datetime.now(timezone.utc).isoformat()),
            expires_at=data.get("expires_at"),
            metadata=data.get("metadata", {}),
        )


@dataclass
class WhatsAppChannelConfig:
    """
    Configuration for WhatsApp channel adapter.

    Includes service principal for secure binding and operational parameters.
    """

    # Service Principal (REQUIRED for security binding)
    service_principal: ServicePrincipal

    # Bridge connection
    bridge_url: str = "http://localhost:3000"
    bridge_ws_url: str = "ws://localhost:3000/ws"

    # Authentication
    auth_dir: Optional[Path] = None
    require_phone_verification: bool = True

    # Message handling
    max_message_length: int = 4096
    enable_media_download: bool = True
    enable_group_messages: bool = True

    # Rate limiting
    max_messages_per_minute: int = 20
    max_media_size_mb: int = 16

    # Security
    allowed_phone_numbers: list[str] = field(default_factory=list)  # Whitelist
    blocked_phone_numbers: list[str] = field(default_factory=list)  # Blacklist
    require_verified_senders: bool = False

    # Logging and audit
    log_all_messages: bool = True
    include_media_in_logs: bool = False

    def validate(self) -> tuple[bool, list[str]]:
        """
        Validate configuration.

        Returns:
            (is_valid, error_messages)
        """
        errors = []

        # Validate service principal
        if not self.service_principal:
            errors.append("Service principal is required for channel binding")
        elif self.service_principal.is_expired:
            errors.append("Service principal has expired")
        elif self.service_principal.channel_type != "whatsapp":
            errors.append(
                f"Service principal channel type mismatch: "
                f"expected 'whatsapp', got '{self.service_principal.channel_type}'"
            )

        # Validate permissions
        required_perms = [
            "channel.whatsapp.read",
            "channel.whatsapp.write",
            "gateway.message.send",
            "gateway.message.receive",
        ]

        for perm in required_perms:
            if not self.service_principal.has_permission(perm):
                errors.append(f"Service principal missing required permission: {perm}")

        # Validate URLs
        if not self.bridge_url.startswith(("http://", "https://")):
            errors.append("Invalid bridge_url: must start with http:// or https://")

        if not self.bridge_ws_url.startswith(("ws://", "wss://")):
            errors.append("Invalid bridge_ws_url: must start with ws:// or wss://")

        return (len(errors) == 0, errors)

    @classmethod
    def from_file(cls, config_path: Path) -> "WhatsAppChannelConfig":
        """Load configuration from JSON file."""
        with open(config_path, "r") as f:
            data = json.load(f)

        # Parse service principal
        sp_data = data.pop("service_principal")
        service_principal = ServicePrincipal.from_dict(sp_data)

        # Parse auth_dir if present
        if "auth_dir" in data and data["auth_dir"]:
            data["auth_dir"] = Path(data["auth_dir"])

        return cls(service_principal=service_principal, **data)

    def to_file(self, config_path: Path):
        """Save configuration to JSON file."""
        data = {
            "service_principal": self.service_principal.to_dict(),
            "bridge_url": self.bridge_url,
            "bridge_ws_url": self.bridge_ws_url,
            "auth_dir": str(self.auth_dir) if self.auth_dir else None,
            "require_phone_verification": self.require_phone_verification,
            "max_message_length": self.max_message_length,
            "enable_media_download": self.enable_media_download,
            "enable_group_messages": self.enable_group_messages,
            "max_messages_per_minute": self.max_messages_per_minute,
            "max_media_size_mb": self.max_media_size_mb,
            "allowed_phone_numbers": self.allowed_phone_numbers,
            "blocked_phone_numbers": self.blocked_phone_numbers,
            "require_verified_senders": self.require_verified_senders,
            "log_all_messages": self.log_all_messages,
            "include_media_in_logs": self.include_media_in_logs,
        }

        config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(config_path, "w") as f:
            json.dump(data, f, indent=2)


class ServicePrincipalManager:
    """
    Manages service principals for channel adapters.

    Provides:
    - Creation of new service principals
    - Validation and authentication
    - Permission management
    - Secure storage
    """

    def __init__(self, storage_dir: Path):
        """
        Initialize manager.

        Args:
            storage_dir: Directory to store service principal data
        """
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def create_service_principal(
        self,
        channel_type: str,
        permissions: list[str],
        expires_in_days: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ServicePrincipal:
        """
        Create a new service principal for a channel adapter.

        Args:
            channel_type: Type of channel (e.g., "whatsapp")
            permissions: List of granted permissions
            expires_in_days: Optional expiration in days
            metadata: Optional metadata

        Returns:
            New ServicePrincipal with generated credentials
        """
        # Generate client ID
        client_id = f"{channel_type}-{secrets.token_hex(16)}"

        # Generate client secret (256-bit)
        client_secret = secrets.token_urlsafe(32)

        # Calculate expiration
        expires_at = None
        if expires_in_days:
            expiry = datetime.now(timezone.utc) + timedelta(days=expires_in_days)
            expires_at = expiry.isoformat()

        sp = ServicePrincipal(
            client_id=client_id,
            client_secret=client_secret,
            channel_type=channel_type,
            permissions=permissions,
            expires_at=expires_at,
            metadata=metadata or {},
        )

        # Save to storage
        self._save_principal(sp)

        return sp

    def load_service_principal(self, client_id: str) -> Optional[ServicePrincipal]:
        """
        Load a service principal by client ID.

        Args:
            client_id: Client ID to load

        Returns:
            ServicePrincipal or None if not found
        """
        sp_file = self.storage_dir / f"{client_id}.json"
        if not sp_file.exists():
            return None

        with open(sp_file, "r") as f:
            data = json.load(f)

        return ServicePrincipal.from_dict(data)

    def authenticate(self, client_id: str, client_secret: str) -> Optional[ServicePrincipal]:
        """
        Authenticate a service principal.

        Args:
            client_id: Client ID
            client_secret: Client secret

        Returns:
            ServicePrincipal if authentication succeeds, None otherwise
        """
        sp = self.load_service_principal(client_id)
        if not sp:
            return None

        if sp.is_expired:
            return None

        if not sp.verify_secret(client_secret):
            return None

        return sp

    def revoke_service_principal(self, client_id: str):
        """
        Revoke a service principal.

        Args:
            client_id: Client ID to revoke
        """
        sp_file = self.storage_dir / f"{client_id}.json"
        if sp_file.exists():
            sp_file.unlink()

    def list_service_principals(self) -> list[ServicePrincipal]:
        """
        List all service principals.

        Returns:
            List of ServicePrincipal objects
        """
        principals = []
        for sp_file in self.storage_dir.glob("*.json"):
            with open(sp_file, "r") as f:
                data = json.load(f)
                principals.append(ServicePrincipal.from_dict(data))

        return principals

    def _save_principal(self, sp: ServicePrincipal):
        """Save service principal to storage."""
        sp_file = self.storage_dir / f"{sp.client_id}.json"
        with open(sp_file, "w") as f:
            json.dump(sp.to_dict(), f, indent=2)


def create_default_whatsapp_config(
    service_principal: ServicePrincipal,
    bridge_url: str = "http://localhost:3000",
) -> WhatsAppChannelConfig:
    """
    Create a default WhatsApp channel configuration.

    Args:
        service_principal: Service principal for authentication
        bridge_url: URL of the WhatsApp bridge

    Returns:
        WhatsAppChannelConfig with sensible defaults
    """
    return WhatsAppChannelConfig(
        service_principal=service_principal,
        bridge_url=bridge_url,
        bridge_ws_url=bridge_url.replace("http://", "ws://").replace("https://", "wss://") + "/ws",
        auth_dir=Path.home() / ".ieee3394" / "whatsapp_auth",
        require_phone_verification=True,
        enable_media_download=True,
        enable_group_messages=True,
        max_messages_per_minute=20,
        log_all_messages=True,
    )
