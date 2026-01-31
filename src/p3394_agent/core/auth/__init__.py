"""
IEEE P3394 Authentication & Authorization

This package implements the P3394 dual-principal security model:
- Client Principal (CP): Who is making the request
- Service Principal (SP): On whose behalf is the agent acting

Core concepts:
- Principal: Semantic identity (Org-Role-Person composite)
- Credential Binding: Channel-specific identity mappings
- Client Principal Assertion: What channels emit during authentication
- Policy Engine: Authorization decision point
"""

from .principal import (
    Principal,
    PrincipalType,
    AssuranceLevel,
    ClientPrincipalAssertion,
    ServicePrincipalContext,
)
from .credential_binding import (
    CredentialBinding,
    BindingType,
)
from .registry import PrincipalRegistry
from .policy import (
    PolicyRule,
    Policy,
    PolicyEngine,
    PolicyDecision,
)

__all__ = [
    "Principal",
    "PrincipalType",
    "AssuranceLevel",
    "ClientPrincipalAssertion",
    "ServicePrincipalContext",
    "CredentialBinding",
    "BindingType",
    "PrincipalRegistry",
    "PolicyRule",
    "Policy",
    "PolicyEngine",
    "PolicyDecision",
]
