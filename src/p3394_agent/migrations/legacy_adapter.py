"""
Legacy Adapter

Wraps existing commands and skills as Capability Descriptors
without requiring immediate rewrites. Enables backward compatibility.
"""

from typing import Dict, Any
import logging

from ..core.capability import (
    AgentCapabilityDescriptor,
    CapabilityKind,
    ExecutionSubstrate,
    CapabilityExecution,
    CapabilityInvocation,
    CapabilityExposure,
    CapabilityPermissions,
    CapabilityStatus,
    InvocationMode,
    ExposureScope
)

logger = logging.getLogger(__name__)


def command_to_capability(command: Any) -> AgentCapabilityDescriptor:
    """
    Convert legacy SymbolicCommand to Capability Descriptor.

    This allows existing commands to work without modification.
    """
    # Extract command properties
    command_name = command.name
    description = command.description
    usage = command.usage if hasattr(command, 'usage') else ""
    aliases = command.aliases if hasattr(command, 'aliases') else []
    requires_auth = command.requires_auth if hasattr(command, 'requires_auth') else False
    handler = command.handler

    # Create capability ID from command name
    cap_id = f"legacy.command.{command_name.lstrip('/').replace('-', '_')}"

    return AgentCapabilityDescriptor(
        capability_id=cap_id,
        name=command_name,
        version="1.0.0",
        description=description,
        kind=CapabilityKind.ATOMIC,

        execution=CapabilityExecution(
            substrate=ExecutionSubstrate.SYMBOLIC,
            runtime="python",
            entrypoint=f"{handler.__module__}:{handler.__name__}" if hasattr(handler, '__module__') else None
        ),

        invocation=CapabilityInvocation(
            modes=[InvocationMode.COMMAND],
            command_aliases=[command_name] + list(aliases)
        ),

        exposure=CapabilityExposure(
            scope=ExposureScope.HUMAN,
            channels=["*"]  # Available on all channels
        ),

        permissions=CapabilityPermissions(
            required=["execute"] if requires_auth else [],
            granted_by_default=not requires_auth,
            danger_level="low"
        ),

        status=CapabilityStatus(
            enabled=True,
            mutable=True,
            signed=False
        ),

        metadata={
            "legacy": True,
            "legacy_type": "command",
            "usage": usage,
            "handler": handler  # Store handler directly for execution
        }
    )


def skill_to_capability(skill_name: str, skill_def: Dict[str, Any]) -> AgentCapabilityDescriptor:
    """
    Convert legacy skill definition to Capability Descriptor.

    This allows existing skills from .claude/skills/ to work without modification.
    """
    description = skill_def.get('description', '')
    triggers = skill_def.get('triggers', [])
    instructions = skill_def.get('instructions', '')

    return AgentCapabilityDescriptor(
        capability_id=f"skill.{skill_name}",
        name=skill_name,
        version="1.0.0",
        description=description,
        kind=CapabilityKind.COMPOSITE,  # Skills are composite

        execution=CapabilityExecution(
            substrate=ExecutionSubstrate.LLM,
            runtime="claude-sonnet-4.5"
        ),

        invocation=CapabilityInvocation(
            modes=[InvocationMode.MESSAGE],
            message_triggers=triggers
        ),

        exposure=CapabilityExposure(
            scope=ExposureScope.HUMAN,
            channels=["*"]
        ),

        permissions=CapabilityPermissions(
            granted_by_default=True,
            danger_level="low"
        ),

        status=CapabilityStatus(
            enabled=True,
            mutable=True,
            signed=False
        ),

        metadata={
            "legacy": True,
            "legacy_type": "skill",
            "skill_file": skill_def.get('file', ''),
            "instructions": instructions
        }
    )


def channel_to_capability(channel_id: str, adapter: Any) -> AgentCapabilityDescriptor:
    """
    Convert channel adapter to Capability Descriptor.

    Channels are represented as transport capabilities.
    """
    adapter_class = adapter.__class__.__name__
    description = f"Channel adapter for {channel_id} protocol"

    # Get capabilities metadata if available
    capabilities_meta = {}
    if hasattr(adapter, 'capabilities'):
        if hasattr(adapter.capabilities, 'to_dict'):
            capabilities_meta = adapter.capabilities.to_dict()
        else:
            capabilities_meta = vars(adapter.capabilities)

    return AgentCapabilityDescriptor(
        capability_id=f"channel.{channel_id}",
        name=f"{channel_id.upper()} Channel",
        version="1.0.0",
        description=description,
        kind=CapabilityKind.PROXY,

        execution=CapabilityExecution(
            substrate=ExecutionSubstrate.TRANSPORT,
            runtime=f"{adapter.__class__.__module__}.{adapter_class}"
        ),

        invocation=CapabilityInvocation(
            modes=[InvocationMode.DIRECT]  # Not directly invokable
        ),

        exposure=CapabilityExposure(
            scope=ExposureScope.INTERNAL,  # Channels aren't directly invokable
            channels=[]
        ),

        permissions=CapabilityPermissions(
            granted_by_default=True,
            danger_level="low"
        ),

        status=CapabilityStatus(
            enabled=adapter.is_active if hasattr(adapter, 'is_active') else True,
            mutable=True,
            signed=False
        ),

        metadata={
            "legacy": True,
            "legacy_type": "channel",
            "capabilities": capabilities_meta,
            "adapter_instance": adapter  # Keep reference to adapter
        }
    )


def migrate_gateway_components(gateway: "AgentGateway") -> int:
    """
    Migrate all legacy components from a gateway to capability registry.

    Returns the count of migrated capabilities.
    """
    count = 0

    # Migrate commands
    if hasattr(gateway, 'commands'):
        for cmd_name, cmd in gateway.commands.items():
            if cmd.name == cmd_name:  # Skip aliases
                try:
                    capability = command_to_capability(cmd)
                    gateway.capability_registry.register(capability)
                    count += 1
                    logger.debug(f"Migrated command: {cmd_name} → {capability.capability_id}")
                except Exception as e:
                    logger.error(f"Failed to migrate command {cmd_name}: {e}")

    # Migrate skills
    if hasattr(gateway, 'skills'):
        for skill_name, skill_def in gateway.skills.items():
            try:
                capability = skill_to_capability(skill_name, skill_def)
                gateway.capability_registry.register(capability)
                count += 1
                logger.debug(f"Migrated skill: {skill_name} → {capability.capability_id}")
            except Exception as e:
                logger.error(f"Failed to migrate skill {skill_name}: {e}")

    # Migrate channels
    if hasattr(gateway, 'channels'):
        for channel_id, adapter in gateway.channels.items():
            try:
                capability = channel_to_capability(channel_id, adapter)
                gateway.capability_registry.register(capability)
                count += 1
                logger.debug(f"Migrated channel: {channel_id} → {capability.capability_id}")
            except Exception as e:
                logger.error(f"Failed to migrate channel {channel_id}: {e}")

    logger.info(f"Migrated {count} legacy components to capability registry")
    return count
