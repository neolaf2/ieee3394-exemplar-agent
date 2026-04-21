"""
P3394 Agent SDK
===============

A Python SDK for building P3394-compliant agents. The SDK provides:

- **Universal Message Format (UMF)**: Standard message types for agent communication
- **Agent Gateway**: Message routing and orchestration
- **Capability Descriptors**: Unified capability abstraction
- **Channel Adapters**: Multi-channel support (CLI, Web, MCP, API)
- **KSTAR Memory**: Episodic, declarative, and procedural memory
- **Session Management**: Client session handling

Quick Start
-----------
Create a simple message::

    from p3394_agent import P3394Message, ContentType

    # Create a text message
    msg = P3394Message.text("Hello, world!")

    # Convert to dict for serialization
    data = msg.to_dict()

Create a capability::

    from p3394_agent import (
        AgentCapabilityDescriptor,
        CapabilityKind,
        ExecutionSubstrate,
        CapabilityExecution,
        CapabilityInvocation,
        CapabilityExposure,
        CapabilityPermissions,
        InvocationMode,
        ExposureScope,
    )

    cap = AgentCapabilityDescriptor(
        capability_id="cmd:help",
        name="Help",
        version="1.0.0",
        description="Show help information",
        kind=CapabilityKind.ATOMIC,
        execution=CapabilityExecution(
            substrate=ExecutionSubstrate.SYMBOLIC,
            entrypoint="gateway._cmd_help"
        ),
        invocation=CapabilityInvocation(
            modes=[InvocationMode.COMMAND],
            command_aliases=["/help", "/?"]
        ),
        exposure=CapabilityExposure(scope=ExposureScope.PUBLIC),
        permissions=CapabilityPermissions()
    )

Connect as a client::

    from p3394_agent import AgentClient

    client = AgentClient()
    await client.connect()
    response = await client.send_message("/help")
"""

from typing import TYPE_CHECKING

# =============================================================================
# Version (synced with pyproject.toml)
# =============================================================================

__version__ = "0.2.0"

# =============================================================================
# Universal Message Format (UMF) - Core P3394 Types
# =============================================================================

from .core.umf import (
    # Message types
    P3394Message,
    P3394Content,
    P3394Address,
    P3394Error,
    # Enums
    MessageType,
    ContentType,
)

# =============================================================================
# Agent Gateway & Session
# =============================================================================

from .core.gateway_sdk import (
    AgentGateway,
    MessageRoute,
    SymbolicCommand,
)
from .core.session import (
    Session,
    SessionManager,
    ChannelRole,
    ChannelBinding,
    ChannelAccessResult,
)

# =============================================================================
# Capability System
# =============================================================================

from .core.capability import (
    # Main descriptor
    AgentCapabilityDescriptor,
    # Kind and substrate enums
    CapabilityKind,
    ExecutionSubstrate,
    InvocationMode,
    ExposureScope,
    # Configuration dataclasses
    CapabilityExecution,
    CapabilityInvocation,
    CapabilityExposure,
    CapabilityPermissions,
    CapabilityLifecycle,
    CapabilityDelegation,
    CapabilityAudit,
    CapabilityStatus,
)

from .core.capability_registry import CapabilityRegistry
from .core.capability_engine import CapabilityInvocationEngine
from .core.capability_acl import (
    CapabilityVisibility,
    CapabilityPermission,
    CapabilityAccessControl,
    CapabilityACLRegistry,
    RolePermissionEntry,
)
from .core.capability_access import CapabilityAccessManager, AccessDecision

# =============================================================================
# Channel Adapters
# =============================================================================

from .channels.base import ChannelAdapter, ChannelCapabilities
from .channels.cli import CLIChannelAdapter
from .channels.unified_web_server import UnifiedWebServer
from .channels.mcp import (
    MCPServerAdapter,
    MCPClientAdapter,
    OutboundChannelRouter,
    MCPToolDefinition,
    MCPToolCall,
    MCPToolResult,
)

# =============================================================================
# Memory System
# =============================================================================

from .memory.kstar import KStarMemory
from .memory.control_tokens import (
    ControlToken,
    TokenType,
    TokenScope,
    TokenProvenance,
    ProvenanceMethod,
    TokenUsage,
    ConsumptionMode,
)
from .memory.necessity_evaluator import (
    NecessityEvaluator,
    NecessityCategory,
    DetectedToken,
)
from .memory.memory_system import (
    MemorySystem,
    MemorySystemConfig,
    get_memory_system,
    initialize_memory_system,
)

# =============================================================================
# Client
# =============================================================================

from .client import AgentClient, run_client

# =============================================================================
# Public API
# =============================================================================

__all__ = [
    # Version
    "__version__",

    # UMF Message Types (Core P3394)
    "P3394Message",
    "P3394Content",
    "P3394Address",
    "P3394Error",
    "MessageType",
    "ContentType",

    # Gateway & Routing
    "AgentGateway",
    "MessageRoute",
    "SymbolicCommand",

    # Session Management
    "Session",
    "SessionManager",
    "ChannelRole",
    "ChannelBinding",
    "ChannelAccessResult",

    # Capability Descriptors
    "AgentCapabilityDescriptor",
    "CapabilityKind",
    "ExecutionSubstrate",
    "InvocationMode",
    "ExposureScope",
    "CapabilityExecution",
    "CapabilityInvocation",
    "CapabilityExposure",
    "CapabilityPermissions",
    "CapabilityLifecycle",
    "CapabilityDelegation",
    "CapabilityAudit",
    "CapabilityStatus",

    # Capability Registry & Engine
    "CapabilityRegistry",
    "CapabilityInvocationEngine",
    "CapabilityVisibility",
    "CapabilityPermission",
    "CapabilityAccessControl",
    "CapabilityACLRegistry",
    "RolePermissionEntry",
    "CapabilityAccessManager",
    "AccessDecision",

    # Channel Adapters
    "ChannelAdapter",
    "ChannelCapabilities",
    "CLIChannelAdapter",
    "UnifiedWebServer",
    "MCPServerAdapter",
    "MCPClientAdapter",
    "OutboundChannelRouter",
    "MCPToolDefinition",
    "MCPToolCall",
    "MCPToolResult",

    # Memory System
    "KStarMemory",
    "ControlToken",
    "TokenType",
    "TokenScope",
    "TokenProvenance",
    "ProvenanceMethod",
    "TokenUsage",
    "ConsumptionMode",
    "NecessityEvaluator",
    "NecessityCategory",
    "DetectedToken",
    "MemorySystem",
    "MemorySystemConfig",
    "get_memory_system",
    "initialize_memory_system",

    # Client
    "AgentClient",
    "run_client",
]
