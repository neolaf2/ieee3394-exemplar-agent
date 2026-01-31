"""
Service Principal and Service Credential Management

This module handles the agent's own identity and credentials for each channel,
as opposed to client authentication (handled by credential_binding.py).

Example:
    The agent's WhatsApp service principal includes:
    - The phone number the agent uses to receive messages
    - WhatsApp Business API credentials to send messages
    - Webhook configuration for incoming messages
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import json
import logging
from pathlib import Path
from cryptography.fernet import Fernet
import os

logger = logging.getLogger(__name__)


@dataclass
class ServiceCredential:
    """
    Credentials for the agent to authenticate to a channel platform.

    These are the agent's OWN credentials (like WhatsApp Business API token),
    not the credentials for authenticating incoming users.
    """
    credential_id: str
    credential_type: str  # bearer_token, api_key, certificate, etc.
    channel: str
    encrypted_value: str
    expires_at: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_rotated_at: Optional[datetime] = None

    def to_dict(self) -> dict:
        return {
            "credential_id": self.credential_id,
            "credential_type": self.credential_type,
            "channel": self.channel,
            "encrypted_value": self.encrypted_value,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "last_rotated_at": self.last_rotated_at.isoformat() if self.last_rotated_at else None
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServiceCredential":
        return cls(
            credential_id=data["credential_id"],
            credential_type=data["credential_type"],
            channel=data["channel"],
            encrypted_value=data["encrypted_value"],
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            last_rotated_at=datetime.fromisoformat(data["last_rotated_at"]) if data.get("last_rotated_at") else None
        )


@dataclass
class ChannelConfiguration:
    """
    Configuration for the agent's presence on a specific channel.

    This defines how the agent is reachable and operates on each channel.
    """
    channel_id: str
    endpoint: str  # Where users can reach this channel (URL, phone number, etc.)
    credential_refs: List[str] = field(default_factory=list)  # References to ServiceCredential IDs
    metadata: Dict = field(default_factory=dict)  # Channel-specific config
    is_active: bool = True

    def to_dict(self) -> dict:
        return {
            "channel_id": self.channel_id,
            "endpoint": self.endpoint,
            "credential_refs": self.credential_refs,
            "metadata": self.metadata,
            "is_active": self.is_active
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ChannelConfiguration":
        return cls(
            channel_id=data["channel_id"],
            endpoint=data["endpoint"],
            credential_refs=data.get("credential_refs", []),
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True)
        )


@dataclass
class ServicePrincipal:
    """
    The agent's own identity as a service provider.

    This declares who the agent IS across all channels, as opposed to
    who is CALLING the agent (Client Principals).
    """
    service_principal_id: str
    display_name: str
    organization: str
    channels: Dict[str, ChannelConfiguration] = field(default_factory=dict)
    metadata: Dict = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def to_dict(self) -> dict:
        return {
            "service_principal_id": self.service_principal_id,
            "display_name": self.display_name,
            "organization": self.organization,
            "channels": {k: v.to_dict() for k, v in self.channels.items()},
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat()
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ServicePrincipal":
        return cls(
            service_principal_id=data["service_principal_id"],
            display_name=data["display_name"],
            organization=data["organization"],
            channels={k: ChannelConfiguration.from_dict(v) for k, v in data.get("channels", {}).items()},
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.now(timezone.utc),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.now(timezone.utc)
        )

    def get_channel_endpoint(self, channel_id: str) -> Optional[str]:
        """Get the public endpoint for a channel."""
        channel = self.channels.get(channel_id)
        return channel.endpoint if channel and channel.is_active else None

    def add_channel(self, channel_id: str, endpoint: str, credential_refs: List[str] = None, metadata: Dict = None):
        """Add or update a channel configuration."""
        self.channels[channel_id] = ChannelConfiguration(
            channel_id=channel_id,
            endpoint=endpoint,
            credential_refs=credential_refs or [],
            metadata=metadata or {},
            is_active=True
        )
        self.updated_at = datetime.now(timezone.utc)


class ServicePrincipalRegistry:
    """
    Registry for managing the agent's service principal and credentials.

    This is the configuration layer that stores:
    1. The agent's identity (ServicePrincipal)
    2. The agent's credentials for each channel (ServiceCredential)
    3. Encryption keys for secure credential storage
    """

    def __init__(self, storage_dir: Path):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.service_principal_file = storage_dir / "service_principal.json"
        self.service_credentials_file = storage_dir / "service_credentials.json"
        self.encryption_key_file = storage_dir / ".encryption_key"

        # Initialize encryption
        self.cipher = self._init_encryption()

        # Load or create service principal
        self.service_principal = self._load_service_principal()
        self._service_credentials: Dict[str, ServiceCredential] = {}
        self._load_service_credentials()

    def _init_encryption(self) -> Fernet:
        """Initialize encryption for credential storage."""
        if self.encryption_key_file.exists():
            key = self.encryption_key_file.read_bytes()
        else:
            key = Fernet.generate_key()
            self.encryption_key_file.write_bytes(key)
            # Restrict permissions
            os.chmod(self.encryption_key_file, 0o600)

        return Fernet(key)

    def _load_service_principal(self) -> ServicePrincipal:
        """Load or create the service principal."""
        if self.service_principal_file.exists():
            data = json.loads(self.service_principal_file.read_text())
            return ServicePrincipal.from_dict(data)
        else:
            # Create default service principal
            sp = ServicePrincipal(
                service_principal_id="urn:principal:org:ieee3394:role:service:person:exemplar-agent",
                display_name="IEEE 3394 Exemplar Agent",
                organization="IEEE 3394 Working Group",
                metadata={
                    "version": "0.1.0",
                    "standard": "IEEE P3394"
                }
            )
            self._save_service_principal(sp)
            return sp

    def _save_service_principal(self, sp: ServicePrincipal):
        """Save service principal to disk."""
        self.service_principal_file.write_text(json.dumps(sp.to_dict(), indent=2))

    def _load_service_credentials(self):
        """Load service credentials from disk."""
        if self.service_credentials_file.exists():
            data = json.loads(self.service_credentials_file.read_text())
            for cred_data in data:
                cred = ServiceCredential.from_dict(cred_data)
                self._service_credentials[cred.credential_id] = cred

    def _save_service_credentials(self):
        """Save service credentials to disk."""
        data = [cred.to_dict() for cred in self._service_credentials.values()]
        self.service_credentials_file.write_text(json.dumps(data, indent=2))
        # Restrict permissions
        os.chmod(self.service_credentials_file, 0o600)

    def store_credential(self, credential_id: str, credential_type: str, channel: str,
                        plaintext_value: str, expires_at: Optional[datetime] = None,
                        metadata: Dict = None) -> ServiceCredential:
        """
        Store a service credential securely.

        Args:
            credential_id: Unique identifier for this credential
            credential_type: Type (bearer_token, api_key, etc.)
            channel: Channel this credential is for
            plaintext_value: The actual credential value (will be encrypted)
            expires_at: Optional expiration time
            metadata: Optional metadata

        Returns:
            The created ServiceCredential
        """
        # Encrypt the credential value
        encrypted_value = self.cipher.encrypt(plaintext_value.encode()).decode()

        credential = ServiceCredential(
            credential_id=credential_id,
            credential_type=credential_type,
            channel=channel,
            encrypted_value=encrypted_value,
            expires_at=expires_at,
            metadata=metadata or {}
        )

        self._service_credentials[credential_id] = credential
        self._save_service_credentials()

        logger.info(f"Stored service credential: {credential_id} for channel: {channel}")
        return credential

    def get_credential(self, credential_id: str) -> Optional[str]:
        """
        Retrieve and decrypt a service credential.

        Returns:
            The decrypted credential value, or None if not found
        """
        cred = self._service_credentials.get(credential_id)
        if not cred or not cred.is_active:
            return None

        # Check expiration
        if cred.expires_at and datetime.now(timezone.utc) > cred.expires_at:
            logger.warning(f"Credential {credential_id} has expired")
            return None

        # Decrypt
        try:
            decrypted = self.cipher.decrypt(cred.encrypted_value.encode()).decode()
            return decrypted
        except Exception as e:
            logger.error(f"Failed to decrypt credential {credential_id}: {e}")
            return None

    def configure_channel(self, channel_id: str, endpoint: str, credentials: Dict[str, str],
                         metadata: Dict = None):
        """
        Configure a channel for the service principal.

        Args:
            channel_id: Channel identifier (e.g., "whatsapp", "web", "cli")
            endpoint: Public endpoint for this channel (e.g., phone number, URL)
            credentials: Dict of credential_id -> plaintext_value
            metadata: Optional channel-specific metadata
        """
        credential_refs = []

        # Store each credential
        for cred_id, plaintext in credentials.items():
            # Determine credential type from ID
            if "token" in cred_id.lower():
                cred_type = "bearer_token"
            elif "key" in cred_id.lower():
                cred_type = "api_key"
            else:
                cred_type = "secret"

            self.store_credential(
                credential_id=cred_id,
                credential_type=cred_type,
                channel=channel_id,
                plaintext_value=plaintext
            )
            credential_refs.append(cred_id)

        # Add channel to service principal
        self.service_principal.add_channel(
            channel_id=channel_id,
            endpoint=endpoint,
            credential_refs=credential_refs,
            metadata=metadata or {}
        )

        self._save_service_principal(self.service_principal)
        logger.info(f"Configured channel {channel_id} with endpoint {endpoint}")

    def get_channel_configuration(self, channel_id: str) -> Optional[ChannelConfiguration]:
        """Get channel configuration."""
        return self.service_principal.channels.get(channel_id)

    def get_channel_credentials(self, channel_id: str) -> Dict[str, str]:
        """
        Get all decrypted credentials for a channel.

        Returns:
            Dict of credential_id -> decrypted_value
        """
        channel = self.service_principal.channels.get(channel_id)
        if not channel:
            return {}

        credentials = {}
        for cred_id in channel.credential_refs:
            value = self.get_credential(cred_id)
            if value:
                credentials[cred_id] = value

        return credentials

    def is_channel_configured(self, channel_id: str) -> bool:
        """Check if a channel is configured and active."""
        channel = self.service_principal.channels.get(channel_id)
        return channel is not None and channel.is_active

    def get_public_endpoints(self) -> Dict[str, str]:
        """
        Get all public endpoints where the agent can be reached.

        Returns:
            Dict of channel_id -> endpoint
        """
        return {
            channel_id: channel.endpoint
            for channel_id, channel in self.service_principal.channels.items()
            if channel.is_active
        }
