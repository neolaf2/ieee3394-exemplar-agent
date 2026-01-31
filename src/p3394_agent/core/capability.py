"""
Agent Capability Descriptor (ACD) Schema

Universal capability abstraction per IEEE P3394.
All agent functionality (commands, skills, channels, hooks, subagents)
is represented as a capability with standardized metadata.
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Literal
from enum import Enum
import json


class CapabilityKind(str, Enum):
    """Type of capability"""
    ATOMIC = "atomic"           # Single indivisible operation
    COMPOSITE = "composite"     # Composed of other capabilities
    PROXY = "proxy"            # Delegates to external agent
    TEMPLATE = "template"      # Generates other capabilities


class ExecutionSubstrate(str, Enum):
    """How the capability is executed"""
    SYMBOLIC = "symbolic"           # Direct Python function
    LLM = "llm"                    # Claude via SDK
    SHELL = "shell"                # Bash commands
    AGENT = "agent"                # SubAgent delegation
    EXTERNAL_SERVICE = "external_service"  # API calls
    TRANSPORT = "transport"        # Channel adapters


class InvocationMode(str, Enum):
    """How the capability can be invoked"""
    DIRECT = "direct"              # Direct function call
    COMMAND = "command"            # /command syntax
    MESSAGE = "message"            # Natural language trigger
    EVENT = "event"                # Event-driven
    UI_ACTION = "ui_action"        # Button/form submission


class ExposureScope(str, Enum):
    """Who can access the capability"""
    INTERNAL = "internal"          # Only callable by other capabilities
    AGENT = "agent"                # Callable by other agents
    CHANNEL = "channel"            # Exposed via specific channel
    HUMAN = "human"                # Human-accessible
    PUBLIC = "public"              # Public API


@dataclass
class CapabilityExecution:
    """Execution configuration"""
    substrate: ExecutionSubstrate
    runtime: Optional[str] = None        # e.g., "python3.10", "claude-opus-4"
    entrypoint: Optional[str] = None     # Module path or function name


@dataclass
class CapabilityInvocation:
    """Invocation configuration"""
    modes: List[InvocationMode] = field(default_factory=list)
    command_aliases: List[str] = field(default_factory=list)
    message_triggers: List[str] = field(default_factory=list)


@dataclass
class CapabilityExposure:
    """Exposure configuration"""
    scope: ExposureScope = ExposureScope.INTERNAL
    channels: List[str] = field(default_factory=list)  # ["cli", "web", "*"]


@dataclass
class CapabilityPermissions:
    """Permission requirements"""
    required: List[str] = field(default_factory=list)
    granted_by_default: bool = False
    danger_level: Literal["low", "medium", "high", "critical"] = "low"


@dataclass
class CapabilityLifecycle:
    """Lifecycle hooks"""
    pre_invoke: List[str] = field(default_factory=list)   # capability_ids
    post_invoke: List[str] = field(default_factory=list)
    on_error: List[str] = field(default_factory=list)


@dataclass
class CapabilityDelegation:
    """Delegation configuration"""
    allowed: bool = False
    creates_subagent: bool = False


@dataclass
class CapabilityAudit:
    """Audit configuration"""
    log_invocation: bool = True
    log_inputs: bool = False
    log_outputs: bool = False


@dataclass
class CapabilityStatus:
    """Runtime status"""
    enabled: bool = True
    mutable: bool = True    # Can be modified at runtime
    signed: bool = False    # Cryptographically signed


@dataclass
class AgentCapabilityDescriptor:
    """
    IEEE P3394 Agent Capability Descriptor

    Universal representation for all agent functionality.
    Collapses skills, commands, sub-agents, adapters, and hooks
    into a single composable abstraction.
    """
    capability_id: str
    name: str
    version: str
    description: str
    kind: CapabilityKind

    execution: CapabilityExecution
    invocation: CapabilityInvocation
    exposure: CapabilityExposure
    permissions: CapabilityPermissions

    # Optional fields
    inputs: Dict[str, Any] = field(default_factory=dict)
    outputs: Dict[str, Any] = field(default_factory=dict)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    lifecycle: Optional[CapabilityLifecycle] = None
    delegation: Optional[CapabilityDelegation] = None
    audit: Optional[CapabilityAudit] = None
    status: Optional[CapabilityStatus] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary for manifest"""
        def _serialize_value(v):
            if isinstance(v, Enum):
                return v.value
            elif isinstance(v, list):
                return [_serialize_value(item) for item in v]
            elif isinstance(v, dict):
                return {k: _serialize_value(val) for k, val in v.items()}
            elif hasattr(v, '__dict__'):
                return {k: _serialize_value(val) for k, val in v.__dict__.items()}
            else:
                return v

        return {k: _serialize_value(v) for k, v in asdict(self).items()}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentCapabilityDescriptor":
        """Deserialize from YAML/JSON"""
        # Parse enums
        data['kind'] = CapabilityKind(data['kind'])

        # Parse nested objects
        if 'execution' in data and isinstance(data['execution'], dict):
            exec_data = data['execution']
            exec_data['substrate'] = ExecutionSubstrate(exec_data['substrate'])
            data['execution'] = CapabilityExecution(**exec_data)

        if 'invocation' in data and isinstance(data['invocation'], dict):
            inv_data = data['invocation']
            if 'modes' in inv_data:
                inv_data['modes'] = [InvocationMode(m) for m in inv_data['modes']]
            data['invocation'] = CapabilityInvocation(**inv_data)

        if 'exposure' in data and isinstance(data['exposure'], dict):
            exp_data = data['exposure']
            exp_data['scope'] = ExposureScope(exp_data['scope'])
            data['exposure'] = CapabilityExposure(**exp_data)

        if 'permissions' in data and isinstance(data['permissions'], dict):
            data['permissions'] = CapabilityPermissions(**data['permissions'])

        # Parse optional nested objects
        if 'lifecycle' in data and data['lifecycle']:
            data['lifecycle'] = CapabilityLifecycle(**data['lifecycle'])

        if 'delegation' in data and data['delegation']:
            data['delegation'] = CapabilityDelegation(**data['delegation'])

        if 'audit' in data and data['audit']:
            data['audit'] = CapabilityAudit(**data['audit'])

        if 'status' in data and data['status']:
            data['status'] = CapabilityStatus(**data['status'])

        return cls(**data)

    def to_json(self) -> str:
        """Serialize to JSON string"""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_json(cls, json_str: str) -> "AgentCapabilityDescriptor":
        """Deserialize from JSON string"""
        return cls.from_dict(json.loads(json_str))
