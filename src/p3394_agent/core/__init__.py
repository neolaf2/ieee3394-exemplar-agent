"""
P3394 Agent Core

Core components for the P3394-compliant agent.
"""

from .gateway_sdk import AgentGateway
from .session import Session, SessionManager, ChannelRole, ChannelBinding
from .umf import P3394Message, P3394Content, ContentType, MessageType, P3394Address
from .capability import AgentCapabilityDescriptor, CapabilityKind, ExecutionSubstrate
from .capability_registry import CapabilityRegistry
from .capability_engine import CapabilityInvocationEngine
from .capability_acl import (
    CapabilityVisibility,
    CapabilityPermission,
    CapabilityAccessControl,
    CapabilityACLRegistry,
    RolePermissionEntry,
)
from .capability_access import CapabilityAccessManager, AccessDecision

__all__ = [
    # Gateway
    "AgentGateway",
    # Session
    "Session",
    "SessionManager",
    "ChannelRole",
    "ChannelBinding",
    # UMF
    "P3394Message",
    "P3394Content",
    "ContentType",
    "MessageType",
    "P3394Address",
    # Capabilities
    "AgentCapabilityDescriptor",
    "CapabilityKind",
    "ExecutionSubstrate",
    "CapabilityRegistry",
    "CapabilityInvocationEngine",
    # ACL
    "CapabilityVisibility",
    "CapabilityPermission",
    "CapabilityAccessControl",
    "CapabilityACLRegistry",
    "RolePermissionEntry",
    # Access Manager
    "CapabilityAccessManager",
    "AccessDecision",
]
