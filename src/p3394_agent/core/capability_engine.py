"""
Capability Invocation Engine

Executes capabilities based on their execution substrate.
Replaces separate handlers for commands, skills, and subagents.
"""

from typing import Any, Dict, Optional, Callable, TYPE_CHECKING
import logging
import importlib
from datetime import datetime

from .capability import (
    AgentCapabilityDescriptor,
    ExecutionSubstrate,
    CapabilityStatus
)
from .capability_registry import CapabilityRegistry
from .umf import P3394Message, P3394Content, ContentType, MessageType
from .session import Session

if TYPE_CHECKING:
    from .gateway_sdk import AgentGateway

logger = logging.getLogger(__name__)


class CapabilityInvocationEngine:
    """
    Executes capabilities based on their execution substrate.

    This is the runtime that replaces:
    - _handle_symbolic (for commands)
    - _handle_skill (for skills)
    - _handle_subagent (for subagents)
    """

    def __init__(
        self,
        registry: CapabilityRegistry,
        gateway: "AgentGateway"
    ):
        self.registry = registry
        self.gateway = gateway

        # Substrate handlers
        self._substrate_handlers: Dict[ExecutionSubstrate, Callable] = {
            ExecutionSubstrate.SYMBOLIC: self._execute_symbolic,
            ExecutionSubstrate.LLM: self._execute_llm,
            ExecutionSubstrate.SHELL: self._execute_shell,
            ExecutionSubstrate.AGENT: self._execute_agent,
            ExecutionSubstrate.EXTERNAL_SERVICE: self._execute_external,
            ExecutionSubstrate.TRANSPORT: self._execute_transport,
        }

    async def invoke(
        self,
        capability_id: str,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """
        Invoke a capability.

        This is the single entry point for all capability execution.
        """
        # Get capability descriptor
        capability = self.registry.get(capability_id)
        if not capability:
            raise ValueError(f"Capability not found: {capability_id}")

        # Check if enabled
        if capability.status and not capability.status.enabled:
            raise ValueError(f"Capability disabled: {capability_id}")

        # Check permissions
        await self._check_permissions(capability, session)

        # Execute pre-invoke hooks
        if capability.lifecycle and capability.lifecycle.pre_invoke:
            await self._execute_hooks(capability.lifecycle.pre_invoke, message, session)

        # Log invocation (if audit enabled)
        if not capability.audit or capability.audit.log_invocation:
            await self._log_invocation(capability, message, session)

        # Dispatch to substrate handler
        try:
            handler = self._substrate_handlers.get(capability.execution.substrate)
            if not handler:
                raise ValueError(f"Unknown substrate: {capability.execution.substrate}")

            response = await handler(capability, message, session, **kwargs)

            # Execute post-invoke hooks
            if capability.lifecycle and capability.lifecycle.post_invoke:
                await self._execute_hooks(capability.lifecycle.post_invoke, message, session)

            return response

        except Exception as e:
            # Execute error hooks
            if capability.lifecycle and capability.lifecycle.on_error:
                await self._execute_hooks(capability.lifecycle.on_error, message, session)

            logger.exception(f"Error invoking capability {capability_id}: {e}")
            raise

    # Substrate Handlers

    async def _execute_symbolic(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute symbolic (Python function) capability"""
        # Get entrypoint (module:function)
        entrypoint = capability.execution.entrypoint
        if not entrypoint:
            raise ValueError(f"Symbolic capability missing entrypoint: {capability.capability_id}")

        # Check if handler is in metadata (for legacy commands)
        if 'handler' in capability.metadata:
            handler = capability.metadata['handler']
            return await handler(message, session, gateway=self.gateway, **kwargs)

        # Import and execute from entrypoint
        try:
            module_path, func_name = entrypoint.rsplit(':', 1)
            module = importlib.import_module(module_path)
            func = getattr(module, func_name)

            # Call handler with standard signature
            return await func(message, session, gateway=self.gateway, **kwargs)

        except Exception as e:
            logger.error(f"Failed to execute symbolic capability {capability.capability_id}: {e}")
            raise

    async def _execute_llm(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute LLM capability via Claude SDK"""
        # For skills: Add skill instructions to message
        text = self._extract_text(message)

        if capability.kind.value == "composite" and 'instructions' in capability.metadata:
            # This is a skill - prepend instructions
            skill_prompt = f"""[SKILL: {capability.name}]
{capability.description}

Instructions:
{capability.metadata['instructions']}

User request: {text}"""

            modified_message = P3394Message(
                type=message.type,
                source=message.source,
                destination=message.destination,
                reply_to=message.reply_to,
                session_id=message.session_id,
                content=[P3394Content(type=ContentType.TEXT, data=skill_prompt)]
            )
        else:
            # Generic LLM capability
            capability_prompt = f"""[CAPABILITY: {capability.name}]
{capability.description}

{capability.metadata.get('prompt', '')}

User request: {text}"""

            modified_message = P3394Message(
                type=message.type,
                source=message.source,
                destination=message.destination,
                reply_to=message.reply_to,
                session_id=message.session_id,
                content=[P3394Content(type=ContentType.TEXT, data=capability_prompt)]
            )

        # Delegate to gateway's LLM handler
        return await self.gateway._handle_llm(modified_message, session)

    async def _execute_shell(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute shell capability (RESTRICTED)"""
        # Shell execution requires elevated permissions
        if not self._has_shell_permission(session):
            raise PermissionError(f"Shell access denied for capability: {capability.capability_id}")

        # Implement shell execution with sandboxing
        # This is a placeholder - production would use proper sandboxing
        logger.warning(f"Shell substrate not fully implemented: {capability.capability_id}")
        return self._create_error_response(
            message,
            "Shell substrate not yet implemented"
        )

    async def _execute_agent(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute agent (subagent) capability"""
        # Delegate to gateway's subagent handler
        return await self.gateway._handle_subagent(message, session)

    async def _execute_external(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute external service capability"""
        # Call external API
        logger.warning(f"External service substrate not implemented: {capability.capability_id}")
        return self._create_error_response(
            message,
            "External service substrate not yet implemented"
        )

    async def _execute_transport(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session,
        **kwargs
    ) -> P3394Message:
        """Execute transport (channel adapter) capability"""
        # Channel adapters handle their own execution
        # This shouldn't normally be invoked directly
        logger.warning(f"Transport capabilities not directly invokable: {capability.capability_id}")
        return self._create_error_response(
            message,
            "Transport capabilities cannot be invoked directly"
        )

    # Permission and Audit

    async def _check_permissions(self, capability: AgentCapabilityDescriptor, session: Session):
        """Check if session has required permissions"""
        if not capability.permissions:
            return

        for required_perm in capability.permissions.required:
            if not session.has_permission(required_perm):
                raise PermissionError(f"Missing permission: {required_perm}")

    def _has_shell_permission(self, session: Session) -> bool:
        """Check if session has shell access"""
        return session.has_permission("shell") or session.is_authenticated

    async def _log_invocation(
        self,
        capability: AgentCapabilityDescriptor,
        message: P3394Message,
        session: Session
    ):
        """Log capability invocation to KSTAR"""
        if self.gateway.memory:
            try:
                await self.gateway.memory.store_trace({
                    "situation": {
                        "domain": "capability_invocation",
                        "actor": session.client_id or "anonymous",
                        "capability_id": capability.capability_id,
                        "now": datetime.utcnow().isoformat()
                    },
                    "task": {
                        "goal": f"Invoke {capability.name}"
                    },
                    "action": {
                        "type": "invoke_capability",
                        "capability": capability.capability_id,
                        "substrate": capability.execution.substrate.value
                    },
                    "mode": "performance",
                    "session_id": session.id
                })
            except Exception as e:
                logger.warning(f"Failed to log invocation to KSTAR: {e}")

    async def _execute_hooks(
        self,
        hook_capability_ids: list,
        message: P3394Message,
        session: Session
    ):
        """Execute lifecycle hooks"""
        for hook_cap_id in hook_capability_ids:
            try:
                await self.invoke(hook_cap_id, message, session)
            except Exception as e:
                logger.error(f"Hook {hook_cap_id} failed: {e}")

    # Helper methods

    def _extract_text(self, message: P3394Message) -> str:
        """Extract text content from message"""
        for content in message.content:
            if content.type == ContentType.TEXT:
                return content.data
        return ""

    def _create_error_response(self, original: P3394Message, error_message: str) -> P3394Message:
        """Create an error response message"""
        return P3394Message(
            type=MessageType.ERROR,
            reply_to=original.id,
            session_id=original.session_id,
            content=[P3394Content(
                type=ContentType.JSON,
                data={"code": "ERROR", "message": error_message}
            )]
        )
