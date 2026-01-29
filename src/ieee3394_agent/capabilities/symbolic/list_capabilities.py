"""
List Capabilities Command

Unified command that replaces:
- /listSkills → /listCapabilities?kind=composite
- /listCommands → /listCapabilities?invocation=command
- /listSubAgents → /listCapabilities?execution=agent
- /listChannels → /listCapabilities?execution=transport
"""

from typing import Optional
from ...core.umf import P3394Message, P3394Content, ContentType, MessageType
from ...core.session import Session
from ...core.capability import CapabilityKind, ExecutionSubstrate, InvocationMode


async def handle_list_capabilities(
    message: P3394Message,
    session: Session,
    gateway=None,
    **kwargs
) -> P3394Message:
    """
    List capabilities with optional filtering.

    Query parameters (parsed from message text):
    - ?kind=<kind> → Filter by capability kind
    - ?substrate=<substrate> → Filter by execution substrate
    - ?invocation=<mode> → Filter by invocation mode

    Examples:
    - /listCapabilities → List all
    - /listCapabilities?kind=composite → List skills
    - /listCapabilities?invocation=command → List commands
    - /listCapabilities?substrate=agent → List subagents
    - /listCapabilities?substrate=transport → List channels
    """
    if not gateway:
        return _create_error("Gateway not provided")

    text = _extract_text(message)

    # Parse query parameters
    filters = {}
    if '?kind=' in text:
        kind_str = text.split('?kind=')[1].split()[0]
        try:
            filters['kind'] = CapabilityKind(kind_str)
        except ValueError:
            return _create_error(f"Invalid kind: {kind_str}")

    if '?substrate=' in text:
        substrate_str = text.split('?substrate=')[1].split()[0]
        try:
            filters['substrate'] = ExecutionSubstrate(substrate_str)
        except ValueError:
            return _create_error(f"Invalid substrate: {substrate_str}")

    if '?invocation=' in text:
        # Filter by invocation mode (more complex - need to check capability.invocation.modes)
        mode_str = text.split('?invocation=')[1].split()[0]
        try:
            mode_filter = InvocationMode(mode_str)
            # We'll filter after querying
            filters['_invocation_mode'] = mode_filter
        except ValueError:
            return _create_error(f"Invalid invocation mode: {mode_str}")

    # Query registry
    registry = gateway.capability_registry

    # Get filtered capabilities
    capabilities = registry.query(**{k: v for k, v in filters.items() if not k.startswith('_')})

    # Additional filtering for invocation mode (can't filter directly in query)
    if '_invocation_mode' in filters:
        mode_filter = filters['_invocation_mode']
        capabilities = [c for c in capabilities if mode_filter in c.invocation.modes]

    # Format response
    if not capabilities:
        response_text = "# Capabilities\n\nNo capabilities match the specified filters."
    else:
        response_text = f"# Capabilities ({len(capabilities)})\n\n"

        # Group by kind for better readability
        by_kind = {}
        for cap in capabilities:
            kind = cap.kind.value
            if kind not in by_kind:
                by_kind[kind] = []
            by_kind[kind].append(cap)

        for kind, caps in sorted(by_kind.items()):
            response_text += f"## {kind.capitalize()} ({len(caps)})\n\n"

            for cap in sorted(caps, key=lambda c: c.name):
                response_text += f"### {cap.name}\n"
                response_text += f"**ID:** `{cap.capability_id}`\n\n"
                response_text += f"{cap.description}\n\n"

                # Show invocation methods
                if cap.invocation.command_aliases:
                    response_text += f"**Commands:** {', '.join(f'`{a}`' for a in cap.invocation.command_aliases[:3])}\n\n"

                if cap.invocation.message_triggers:
                    response_text += f"**Triggers:** {', '.join(cap.invocation.message_triggers[:3])}\n\n"

                # Show substrate
                response_text += f"**Substrate:** {cap.execution.substrate.value}\n\n"

                # Show status
                status_emoji = "✓" if not cap.status or cap.status.enabled else "✗"
                response_text += f"**Status:** {status_emoji} {'enabled' if not cap.status or cap.status.enabled else 'disabled'}\n\n"

                response_text += "---\n\n"

    return P3394Message(
        type=MessageType.RESPONSE,
        reply_to=message.id,
        session_id=session.id,
        content=[P3394Content(type=ContentType.TEXT, data=response_text)]
    )


def _extract_text(message: P3394Message) -> str:
    """Extract text content from message"""
    for content in message.content:
        if content.type == ContentType.TEXT:
            return content.data
    return ""


def _create_error(error_message: str) -> P3394Message:
    """Create an error response"""
    return P3394Message(
        type=MessageType.ERROR,
        content=[P3394Content(
            type=ContentType.JSON,
            data={"code": "ERROR", "message": error_message}
        )]
    )
