"""
Principal Identity Model

Implements P3394's semantic principal model:
- Principal: Org-Role-Person composite URN
- AssuranceLevel: Confidence in identity assertion
- ClientPrincipalAssertion: Channel-emitted identity claims
- ServicePrincipalContext: Agent's operating context
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any
from uuid import uuid4


class PrincipalType(str, Enum):
    """Type of principal"""
    HUMAN = "human"          # Human user
    AGENT = "agent"          # AI agent
    SERVICE = "service"      # Service account
    SYSTEM = "system"        # System/internal principal
    ANONYMOUS = "anonymous"  # Unauthenticated


class AssuranceLevel(str, Enum):
    """
    Confidence level in principal identity assertion.

    Based on NIST 800-63-3 Identity Assurance Levels (IAL).
    """
    NONE = "none"                    # No authentication (anonymous)
    LOW = "low"                      # Self-asserted identity
    MEDIUM = "medium"                # Platform-verified (phone, email)
    HIGH = "high"                    # Multi-factor or local access
    CRYPTOGRAPHIC = "cryptographic"  # Certificate/signature-based


@dataclass
class Principal:
    """
    Semantic principal identity (P3394 Org-Role-Person composite).

    Principal URN format:
        urn:principal:org:{org_id}:role:{role_id}:person:{person_id}

    Example:
        urn:principal:org:ieee:role:chair:person:rtong

    This composite structure enables:
    - Organizational grouping (all IEEE members)
    - Role-based access (all chairs regardless of org)
    - Individual tracking (specific person across roles)
    """
    principal_id: str                  # Full URN
    org: str                           # urn:org:{org_id}
    role: str                          # urn:role:{role_id}
    person: str                        # urn:person:{person_id}
    principal_type: PrincipalType
    display_name: Optional[str] = None
    email: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    is_active: bool = True
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    @classmethod
    def from_urn(cls, urn: str, principal_type: PrincipalType = PrincipalType.HUMAN, **kwargs) -> "Principal":
        """
        Parse a principal URN.

        Format: urn:principal:org:{org}:role:{role}:person:{person}
        """
        if not urn.startswith("urn:principal:"):
            raise ValueError(f"Invalid principal URN: {urn}")

        parts = urn.split(":")
        if len(parts) < 8:
            raise ValueError(f"Malformed principal URN: {urn}")

        org = f"urn:org:{parts[3]}"
        role = f"urn:role:{parts[5]}"
        person = f"urn:person:{parts[7]}"

        return cls(
            principal_id=urn,
            org=org,
            role=role,
            person=person,
            principal_type=principal_type,
            **kwargs
        )

    @classmethod
    def system_principal(cls) -> "Principal":
        """Create the system principal (for internal operations)"""
        return cls(
            principal_id="urn:principal:org:ieee3394:role:system:person:agent",
            org="urn:org:ieee3394",
            role="urn:role:system",
            person="urn:person:agent",
            principal_type=PrincipalType.SYSTEM,
            display_name="System",
            is_active=True
        )

    @classmethod
    def anonymous_principal(cls) -> "Principal":
        """Create an anonymous principal (unauthenticated)"""
        return cls(
            principal_id="urn:principal:org:public:role:anonymous:person:guest",
            org="urn:org:public",
            role="urn:role:anonymous",
            person="urn:person:guest",
            principal_type=PrincipalType.ANONYMOUS,
            display_name="Anonymous",
            is_active=True
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "principal_id": self.principal_id,
            "org": self.org,
            "role": self.role,
            "person": self.person,
            "principal_type": self.principal_type.value,
            "display_name": self.display_name,
            "email": self.email,
            "metadata": self.metadata,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Principal":
        """Deserialize from dictionary"""
        return cls(
            principal_id=data["principal_id"],
            org=data["org"],
            role=data["role"],
            person=data["person"],
            principal_type=PrincipalType(data["principal_type"]),
            display_name=data.get("display_name"),
            email=data.get("email"),
            metadata=data.get("metadata", {}),
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


@dataclass
class ClientPrincipalAssertion:
    """
    Client Principal assertion emitted by channel adapters.

    This is what channels emit during authentication. It contains:
    - Unresolved identity (channel-specific, e.g., "whatsapp:+1234567890")
    - Channel context
    - Assurance level
    - Authentication method used

    The Gateway resolves this to a semantic Principal via PrincipalRegistry.
    """
    assertion_id: str = field(default_factory=lambda: str(uuid4()))
    channel_id: str = ""                           # Which channel
    channel_identity: str = ""                     # Channel-specific ID (phone, email, etc.)
    assurance_level: AssuranceLevel = AssuranceLevel.NONE
    authentication_method: str = ""                # How was identity verified
    authenticated_at: datetime = field(default_factory=datetime.utcnow)

    # Resolution state
    is_resolved: bool = False                      # Has this been resolved to Principal?
    resolved_principal_id: Optional[str] = None    # Semantic principal URN

    # Additional context
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize for message metadata"""
        return {
            "assertion_id": self.assertion_id,
            "channel_id": self.channel_id,
            "channel_identity": self.channel_identity,
            "assurance_level": self.assurance_level.value,
            "authentication_method": self.authentication_method,
            "authenticated_at": self.authenticated_at.isoformat(),
            "is_resolved": self.is_resolved,
            "resolved_principal_id": self.resolved_principal_id,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ClientPrincipalAssertion":
        """Deserialize from dictionary"""
        return cls(
            assertion_id=data.get("assertion_id", str(uuid4())),
            channel_id=data.get("channel_id", ""),
            channel_identity=data.get("channel_identity", ""),
            assurance_level=AssuranceLevel(data.get("assurance_level", "none")),
            authentication_method=data.get("authentication_method", ""),
            authenticated_at=datetime.fromisoformat(data["authenticated_at"]) if data.get("authenticated_at") else datetime.utcnow(),
            is_resolved=data.get("is_resolved", False),
            resolved_principal_id=data.get("resolved_principal_id"),
            metadata=data.get("metadata", {}),
        )

    @classmethod
    def anonymous(cls, channel_id: str = "unknown") -> "ClientPrincipalAssertion":
        """Create an anonymous assertion"""
        return cls(
            channel_id=channel_id,
            channel_identity="anonymous",
            assurance_level=AssuranceLevel.NONE,
            authentication_method="none",
        )


@dataclass
class ServicePrincipalContext:
    """
    Service Principal context (on whose behalf is the agent operating).

    This represents the agent's operational identity and permissions.
    Used for:
    - Accessing external services with service credentials
    - Logging and audit (who authorized this agent to act)
    - Delegation chains (agent acts on behalf of service, which acts on behalf of user)
    """
    service_principal_id: str                      # Semantic principal URN
    service_name: str                              # Human-readable service name
    granted_permissions: list[str] = field(default_factory=list)  # What can this service do
    credentials: Dict[str, Any] = field(default_factory=dict)     # Service credentials (tokens, etc.)
    metadata: Dict[str, Any] = field(default_factory=dict)
    expires_at: Optional[datetime] = None          # Credential expiry

    def is_expired(self) -> bool:
        """Check if service credentials are expired"""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def has_permission(self, permission: str) -> bool:
        """Check if service has a specific permission"""
        return permission in self.granted_permissions or "*" in self.granted_permissions

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "service_principal_id": self.service_principal_id,
            "service_name": self.service_name,
            "granted_permissions": self.granted_permissions,
            "credentials": self.credentials,  # In production, encrypt this
            "metadata": self.metadata,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ServicePrincipalContext":
        """Deserialize from dictionary"""
        return cls(
            service_principal_id=data["service_principal_id"],
            service_name=data["service_name"],
            granted_permissions=data.get("granted_permissions", []),
            credentials=data.get("credentials", {}),
            metadata=data.get("metadata", {}),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
        )
