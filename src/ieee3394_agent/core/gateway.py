"""
Agent Gateway (Message Router)

The central message router that:
1. Receives all incoming messages (from any channel)
2. Determines how to route them (symbolic, LLM, skill)
3. Dispatches to appropriate handler
4. Returns responses
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum
import logging

from anthropic import Anthropic, AsyncAnthropic
from .umf import P3394Message, P3394Content, ContentType, MessageType
from .session import SessionManager, Session
from ..memory.kstar import KStarMemory
from uuid import uuid4

logger = logging.getLogger(__name__)


class MessageRoute(str, Enum):
    """How to route a message"""
    SYMBOLIC = "symbolic"      # Direct function dispatch (no LLM)
    LLM = "llm"               # Route to Claude
    SKILL = "skill"           # Invoke a registered skill (via LLM)
    SUBAGENT = "subagent"     # Delegate to specialized subagent


@dataclass
class SymbolicCommand:
    """A command that executes without LLM involvement"""
    name: str
    handler: Callable[[P3394Message, Session], Awaitable[P3394Message]]
    description: str
    usage: str = ""
    requires_auth: bool = False
    aliases: List[str] = field(default_factory=list)


class AgentGateway:
    """
    The Agent Shell / Service Orchestrator

    Think of it as an HTTP router, but for agent messages.
    """

    # Agent identity
    AGENT_ID = "ieee3394-exemplar"
    AGENT_NAME = "IEEE 3394 Exemplar Agent"
    AGENT_VERSION = "0.1.0"

    def __init__(
        self,
        kstar_memory: KStarMemory,
        anthropic_api_key: Optional[str] = None
    ):
        self.memory = kstar_memory
        self.session_manager = SessionManager()

        # Command registry
        self.commands: Dict[str, SymbolicCommand] = {}
        self._register_builtin_commands()

        # Skill triggers (pattern -> skill name)
        self.skill_triggers: Dict[str, str] = {}

        # Active channels
        self.channels: Dict[str, Any] = {}

        # Anthropic client (for LLM routing)
        self._anthropic_client: Optional[AsyncAnthropic] = None
        self._anthropic_api_key = anthropic_api_key

    def _get_anthropic_client(self) -> AsyncAnthropic:
        """Lazy initialize Anthropic client"""
        if not self._anthropic_client:
            self._anthropic_client = AsyncAnthropic(api_key=self._anthropic_api_key)
        return self._anthropic_client

    def _get_system_prompt(self) -> str:
        """System prompt for P3394 agent identity"""
        return """You are the IEEE 3394 Exemplar Agent, a reference implementation of the P3394 Agent Interface Standard.

Your role:
1. Explain and demonstrate the P3394 standard clearly with examples
2. Help developers understand and implement P3394 in their agents
3. Showcase agent capabilities through your behavior

When responding:
- For P3394 questions: Explain the standard with concrete examples
- For technical questions: Demonstrate capabilities rather than just describing them
- Always be helpful, clear, and educational
- Use the /help command pattern to discover available capabilities

Remember: You ARE the documentation. Your behavior demonstrates the standard."""

    # =========================================================================
    # COMMAND REGISTRATION
    # =========================================================================

    def _register_builtin_commands(self):
        """Register all symbolic commands"""

        self.register_command(SymbolicCommand(
            name="/help",
            handler=self._cmd_help,
            description="Show available commands and capabilities",
            aliases=["/?", "/commands"]
        ))

        self.register_command(SymbolicCommand(
            name="/about",
            handler=self._cmd_about,
            description="About this agent and P3394",
            aliases=["/info"]
        ))

        self.register_command(SymbolicCommand(
            name="/status",
            handler=self._cmd_status,
            description="Get agent status and health"
        ))

        self.register_command(SymbolicCommand(
            name="/version",
            handler=self._cmd_version,
            description="Get agent version information"
        ))

    def register_command(self, command: SymbolicCommand):
        """Register a symbolic command"""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command
        logger.debug(f"Registered command: {command.name}")

    def register_channel(self, channel_id: str, adapter: Any):
        """Register a channel adapter"""
        self.channels[channel_id] = adapter
        logger.info(f"Registered channel: {channel_id}")

    # =========================================================================
    # MESSAGE ROUTING
    # =========================================================================

    async def route(self, message: P3394Message) -> MessageRoute:
        """Determine how to route an incoming message"""

        text = message.extract_text()

        # Check for symbolic command
        if text.startswith("/"):
            cmd_name = text.split()[0]
            if cmd_name in self.commands:
                return MessageRoute.SYMBOLIC

        # Check for skill triggers
        for pattern, skill_name in self.skill_triggers.items():
            if pattern in text.lower():
                return MessageRoute.SKILL

        # Check for subagent delegation keywords
        if self._should_delegate(text):
            return MessageRoute.SUBAGENT

        # Default: route to LLM
        return MessageRoute.LLM

    async def handle(self, message: P3394Message) -> P3394Message:
        """
        Main entry point for all messages.

        This is the core dispatch loop:
        1. Route the message
        2. Dispatch to appropriate handler
        3. Log to KSTAR memory
        4. Return response
        """
        session = await self._get_or_create_session(message)
        route = await self.route(message)

        # Log incoming message to KSTAR
        await self._log_to_kstar(message, route, session)

        try:
            if route == MessageRoute.SYMBOLIC:
                response = await self._handle_symbolic(message, session)
            elif route == MessageRoute.SKILL:
                response = await self._handle_skill(message, session)
            elif route == MessageRoute.SUBAGENT:
                response = await self._handle_subagent(message, session)
            else:
                response = await self._handle_llm(message, session)

            # Log response to KSTAR
            await self._log_response_to_kstar(message, response, session)

            return response

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return self._create_error_response(message, str(e))

    # =========================================================================
    # HANDLER IMPLEMENTATIONS
    # =========================================================================

    async def _handle_symbolic(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle symbolic commands (no LLM needed)"""
        text = message.extract_text()
        cmd_name = text.split()[0]
        command = self.commands.get(cmd_name)

        if not command:
            return self._create_error_response(message, f"Unknown command: {cmd_name}")

        if command.requires_auth and not session.is_authenticated:
            return self._create_error_response(message, "Authentication required")

        return await command.handler(message, session)

    async def _handle_llm(self, message: P3394Message, session: Session) -> P3394Message:
        """Route message to Claude"""
        text = message.extract_text()

        # Add session context
        context_prompt = f"""[Session: {session.id}]
[Channel: {message.source.channel_id if message.source else 'unknown'}]
[User: {session.client_id or 'anonymous'}]

{text}"""

        client = self._get_anthropic_client()

        # Generate call ID for logging
        call_id = str(uuid4())

        # Prepare request for logging
        request_data = {
            "model": "claude-opus-4-20250514",
            "max_tokens": 4096,
            "system": self._get_system_prompt(),
            "messages": [
                {
                    "role": "user",
                    "content": context_prompt
                }
            ],
            "timestamp": message.timestamp,
            "call_id": call_id
        }

        # Log outbound LLM call (request)
        if self.memory.storage:
            self.memory.storage.log_outbound_llm_call(
                session.id,
                call_id,
                request_data
            )

        # Call Claude API
        response = await client.messages.create(
            model="claude-opus-4-20250514",
            max_tokens=4096,
            system=self._get_system_prompt(),
            messages=[
                {
                    "role": "user",
                    "content": context_prompt
                }
            ]
        )

        # Extract response text
        response_text = ""
        for block in response.content:
            if hasattr(block, 'text'):
                response_text += block.text

        # Log outbound LLM call (response)
        if self.memory.storage:
            response_data = {
                "id": response.id,
                "model": response.model,
                "usage": {
                    "input_tokens": response.usage.input_tokens,
                    "output_tokens": response.usage.output_tokens
                },
                "content": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                "call_id": call_id
            }
            self.memory.storage.log_outbound_llm_call(
                session.id,
                call_id,
                request_data,
                response_data
            )

        return P3394Message(
            type=MessageType.RESPONSE,
            reply_to=message.id,
            session_id=session.id,
            content=[P3394Content(type=ContentType.TEXT, data=response_text)]
        )

    async def _handle_skill(self, message: P3394Message, session: Session) -> P3394Message:
        """Invoke a registered skill (via LLM with skill context)"""
        # For MVP, just route to LLM
        # Full implementation would prepend skill-specific instructions
        return await self._handle_llm(message, session)

    async def _handle_subagent(self, message: P3394Message, session: Session) -> P3394Message:
        """Delegate to specialized subagent"""
        # For MVP, inform user about subagent capability
        return P3394Message(
            type=MessageType.RESPONSE,
            reply_to=message.id,
            session_id=session.id,
            content=[P3394Content(
                type=ContentType.TEXT,
                data="SubAgent delegation is a planned feature. For now, I'll handle your request directly."
            )]
        )

    # =========================================================================
    # SYMBOLIC COMMAND HANDLERS
    # =========================================================================

    async def _cmd_help(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /help command"""
        help_text = f"""# {self.AGENT_NAME} v{self.AGENT_VERSION}

## Available Commands

"""
        seen = set()
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                help_text += f"**{cmd.name}** - {cmd.description}\n"
                seen.add(cmd.name)

        help_text += """
## Capabilities

This agent can:
- Explain the IEEE P3394 standard
- Demonstrate agent communication patterns
- Help you understand agent interoperability

Just send a message or use a command to get started!
"""
        return P3394Message.text(help_text, reply_to=message.id, session_id=session.id)

    async def _cmd_about(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /about command"""
        about_text = f"""# About {self.AGENT_NAME}

**Version:** {self.AGENT_VERSION}
**Agent ID:** {self.AGENT_ID}
**Standard:** IEEE P3394 (Agent Interface Standard)

## What is P3394?

IEEE P3394 defines a universal standard for agent communication, enabling:
- **Interoperability**: Agents from different vendors can communicate
- **Universal Message Format (UMF)**: Standard message structure
- **Channel Abstraction**: Same agent, multiple interfaces
- **Capability Discovery**: Agents can discover each other's abilities

## This Agent

This agent serves as the **reference implementation** of P3394.
Everything you see here demonstrates the standard in action.

## Learn More

- Send questions about P3394 and I'll explain with examples
- Use /help to see available commands
- Source: https://github.com/neolaf2/ieee3394-exemplar-agent
"""
        return P3394Message.text(about_text, reply_to=message.id, session_id=session.id)

    async def _cmd_status(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /status command"""
        memory_stats = await self.memory.get_stats()

        status_text = f"""# Agent Status

**Agent:** {self.AGENT_NAME}
**Version:** {self.AGENT_VERSION}
**Status:** 🟢 Operational

## Memory
- Traces: {memory_stats.get('trace_count', 0)}
- Skills: {memory_stats.get('skill_count', 0)}
- Perceptions: {memory_stats.get('perception_count', 0)}

## Channels
- Active: {len(self.channels)}

## Sessions
- Active: {len(self.session_manager.active_sessions)}
"""
        return P3394Message.text(status_text, reply_to=message.id, session_id=session.id)

    async def _cmd_version(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /version command"""
        return P3394Message.text(
            f"{self.AGENT_NAME} v{self.AGENT_VERSION}",
            reply_to=message.id,
            session_id=session.id
        )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _should_delegate(self, text: str) -> bool:
        """Check if message should be delegated to subagent"""
        delegation_keywords = [
            "document", "create docs", "write documentation",
            "tutorial", "help me start", "getting started",
            "demo", "show me", "demonstrate"
        ]
        text_lower = text.lower()
        return any(kw in text_lower for kw in delegation_keywords)

    async def _get_or_create_session(self, message: P3394Message) -> Session:
        """Get existing session or create new one"""
        session_id = message.session_id
        if session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                return session

        return await self.session_manager.create_session()

    async def _log_to_kstar(self, message: P3394Message, route: MessageRoute, session: Session):
        """Log incoming message to KSTAR memory"""
        await self.memory.store_trace({
            "situation": {
                "domain": "ieee3394_agent",
                "actor": message.source.agent_id if message.source else "unknown",
                "protocol": "p3394",
                "now": message.timestamp
            },
            "task": {
                "goal": f"Handle {route.value} message"
            },
            "action": {
                "type": "receive_message",
                "parameters": {
                    "message_id": message.id,
                    "route": route.value,
                    "session_id": session.id
                }
            },
            "mode": "performance",
            "session_id": session.id
        })

    async def _log_response_to_kstar(
        self,
        request: P3394Message,
        response: P3394Message,
        session: Session
    ):
        """Log response to KSTAR memory"""
        await self.memory.store_perception({
            "content": f"Responded to message {request.id}",
            "context": {
                "domain": "ieee3394_agent",
                "response_id": response.id,
                "session_id": session.id
            },
            "tags": ["message_handling"],
            "importance": 0.5
        })

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
