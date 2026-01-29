"""
Agent Gateway (Message Router) - SDK Version

The central message router that:
1. Receives all incoming messages (from any channel)
2. Determines how to route them (symbolic, LLM, skill)
3. Dispatches to appropriate handler using Claude Agent SDK
4. Returns responses
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum
import logging
from pathlib import Path

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher
from .umf import P3394Message, P3394Content, ContentType, MessageType
from .session import SessionManager, Session
from .skill_loader import SkillLoader
from ..memory.kstar import KStarMemory
from .capability_registry import CapabilityRegistry
from .capability_engine import CapabilityInvocationEngine
from uuid import uuid4

logger = logging.getLogger(__name__)


class MessageRoute(str, Enum):
    """How to route a message"""
    SYMBOLIC = "symbolic"      # Direct function dispatch (no LLM)
    LLM = "llm"               # Route to Claude via SDK
    SKILL = "skill"           # Invoke a registered skill (via Claude with skill context)
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
    The Agent Shell / Service Orchestrator (SDK Version)

    This is the central message router that:
    1. Receives all incoming messages (from any channel)
    2. Determines how to route them (symbolic, LLM, skill)
    3. Dispatches to appropriate handler using Claude Agent SDK
    4. Returns responses
    """

    # Agent identity
    AGENT_ID = "ieee3394-exemplar"
    AGENT_NAME = "IEEE 3394 Exemplar Agent"
    AGENT_VERSION = "0.2.0-sdk"

    def __init__(
        self,
        memory: KStarMemory,
        working_dir: Optional[Path] = None
    ):
        self.memory = memory
        self.session_manager = SessionManager(storage_dir=self.memory.storage.base_dir if self.memory.storage else None)
        self.working_dir = working_dir if isinstance(working_dir, Path) else Path(working_dir) if working_dir else Path.cwd()

        # NEW: Unified capability system
        self.capability_registry = CapabilityRegistry(
            persistence_path=self.working_dir / ".claude" / "capabilities.json"
        )
        self.capability_engine = CapabilityInvocationEngine(
            registry=self.capability_registry,
            gateway=self
        )

        # LEGACY: Command registry (will be migrated to capabilities)
        self.commands: Dict[str, SymbolicCommand] = {}
        self._register_builtin_commands()

        # LEGACY: Skill loader and registry (will be migrated to capabilities)
        self.skill_loader = SkillLoader(self.working_dir / ".claude" / "skills")
        self.skills: Dict[str, Any] = {}  # skill_name -> skill definition
        self.skill_triggers: Dict[str, str] = {}  # pattern -> skill_name

        # Active channels
        self.channels: Dict[str, Any] = {}

        # Claude Agent SDK options (lazy initialized)
        self._sdk_options: Optional[ClaudeAgentOptions] = None
        self._sdk_client: Optional[ClaudeSDKClient] = None

    async def initialize(self):
        """
        Initialize async components (load skills, migrate to capabilities).
        Call this after creating the gateway.
        """
        # Load skills from .claude/skills/
        logger.info("Loading skills from .claude/skills/...")
        self.skills = await self.skill_loader.load_all_skills()
        self.skill_triggers = self.skill_loader.get_skill_triggers()
        logger.info(f"Loaded {len(self.skills)} skills with {len(self.skill_triggers)} triggers")

        # NEW: Migrate legacy components to capability registry
        logger.info("Migrating legacy components to capability registry...")
        await self._migrate_to_capabilities()

        # Load built-in capabilities from YAML descriptors
        builtin_caps_dir = self.working_dir / ".claude" / "capabilities" / "builtin"
        if builtin_caps_dir.exists():
            count = self.capability_registry.load_from_directory(builtin_caps_dir)
            logger.info(f"Loaded {count} built-in capabilities from {builtin_caps_dir}")

        logger.info(f"Capability registry initialized with {self.capability_registry.count()} capabilities")

    def get_sdk_options(self) -> ClaudeAgentOptions:
        """
        Get Claude Agent SDK options.

        This is called lazily to allow channels to be registered first
        (so hooks and tools can access them).
        """
        if self._sdk_options:
            return self._sdk_options

        # Import hooks and tools
        from ..plugins.hooks_sdk import create_sdk_hooks
        from ..plugins.tools_sdk import create_sdk_tools

        # Create SDK options
        self._sdk_options = ClaudeAgentOptions(
            system_prompt=self._get_system_prompt(),
            allowed_tools=[
                "Read", "Write", "Edit", "Bash", "Glob", "Grep",
                "WebSearch", "WebFetch", "Task",
                # Custom P3394 tools (via SDK MCP)
                "mcp__p3394_tools__query_memory",
                "mcp__p3394_tools__store_trace",
                "mcp__p3394_tools__list_skills",
            ],
            hooks=create_sdk_hooks(self),
            mcp_servers={
                "p3394_tools": create_sdk_tools(self)
            },
            permission_mode="acceptEdits",
            cwd=self.working_dir,
        )

        return self._sdk_options

    def _get_system_prompt(self) -> str:
        """Get system prompt for Claude"""
        return f"""You are the {self.AGENT_NAME} (v{self.AGENT_VERSION}).

You are a reference implementation of the IEEE P3394 standard for agent interfaces.

Your role:
- Demonstrate P3394 Universal Message Format (UMF) in action
- Help users understand and implement the P3394 standard
- Provide examples of agent-to-agent communication
- Show best practices for channel adapters and content negotiation

Current capabilities:
- Symbolic commands: {', '.join(sorted(set(cmd.name for cmd in self.commands.values())))}
- Active channels: {', '.join(self.channels.keys())}
- Skills: {', '.join(self.skills.keys()) if self.skills else 'None yet'}

When responding:
1. Structure all outputs as valid P3394 messages internally
2. Log interactions to KSTAR memory for learning
3. Explain P3394 concepts clearly when asked
4. Demonstrate capabilities rather than just describing them
"""

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
            description="About this agent and P3394"
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

        self.register_command(SymbolicCommand(
            name="/listSkills",
            handler=self._cmd_list_skills,
            description="List acquired skills and capabilities"
        ))

    def register_command(self, command: SymbolicCommand):
        """Register a symbolic command"""
        self.commands[command.name] = command
        for alias in command.aliases:
            self.commands[alias] = command

    def register_channel(self, channel_id: str, adapter: Any):
        """Register a channel adapter"""
        self.channels[channel_id] = adapter
        logger.info(f"Registered channel: {channel_id}")

    def register_skill(self, skill_name: str, skill_definition: Any):
        """Register a skill"""
        self.skills[skill_name] = skill_definition
        logger.info(f"Registered skill: {skill_name}")

    async def _migrate_to_capabilities(self):
        """Migrate legacy components (commands, skills, channels) to capability registry"""
        from ..migrations.legacy_adapter import migrate_gateway_components

        count = migrate_gateway_components(self)
        logger.info(f"Migrated {count} legacy components to capability registry")

        # Log registry state for debugging
        if logger.isEnabledFor(logging.DEBUG):
            logger.debug(f"\n{self.capability_registry.dump_registry()}")

    # =========================================================================
    # MESSAGE ROUTING
    # =========================================================================

    async def route(self, message: P3394Message) -> Optional[str]:
        """
        Determine how to route an incoming message.

        Returns capability_id if a capability should handle it,
        or None for LLM fallback.
        """
        # Extract text content for routing decisions
        text = self._extract_text(message)

        # NEW: Check capability registry first
        # Check for command (starts with / or --)
        if text.startswith("/") or text.startswith("--"):
            cmd_text = text.split()[0]
            capability = self.capability_registry.find_by_command(cmd_text)
            if capability:
                logger.debug(f"Routed to capability: {capability.capability_id}")
                return capability.capability_id

        # Check for message trigger
        capability = self.capability_registry.find_by_trigger(text)
        if capability:
            logger.debug(f"Routed to capability: {capability.capability_id} (trigger match)")
            return capability.capability_id

        # FALLBACK: Check legacy command registry
        if text.startswith("/"):
            cmd_name = text.split()[0]
            if cmd_name in self.commands:
                # Find the migrated capability
                cap_id = f"legacy.command.{cmd_name.lstrip('/').replace('-', '_')}"
                return cap_id

        # No matching capability - will use LLM
        return None

    async def handle(self, message: P3394Message) -> P3394Message:
        """
        Main entry point for all messages.

        This is the core dispatch loop:
        1. Route the message (get capability_id or None)
        2. Invoke via capability engine or fall back to LLM
        3. Return response
        """
        session = await self._get_or_create_session(message)
        capability_id = await self.route(message)

        logger.info(f"Routing message {message.id}: capability={capability_id or 'LLM fallback'}")

        try:
            if capability_id:
                # NEW: Route via capability engine
                response = await self.capability_engine.invoke(
                    capability_id, message, session
                )
            else:
                # FALLBACK: Route to LLM
                response = await self._handle_llm(message, session)

            return response

        except Exception as e:
            logger.exception(f"Error handling message: {e}")
            return self._create_error_response(message, str(e))

    # =========================================================================
    # HANDLER IMPLEMENTATIONS
    # =========================================================================

    async def _handle_symbolic(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle symbolic commands (no LLM needed)"""
        text = self._extract_text(message)
        cmd_name = text.split()[0]
        command = self.commands.get(cmd_name)

        if not command:
            return self._create_error_response(message, f"Unknown command: {cmd_name}")

        if command.requires_auth and not session.is_authenticated:
            return self._create_error_response(message, "Authentication required")

        return await command.handler(message, session)

    async def _handle_llm(self, message: P3394Message, session: Session) -> P3394Message:
        """Route message to Claude via Agent SDK"""

        # Initialize SDK client if needed
        if not self._sdk_client:
            options = self.get_sdk_options()
            self._sdk_client = ClaudeSDKClient(options=options)
            await self._sdk_client.connect()

        text = self._extract_text(message)

        # Add session context
        context_prompt = f"""[Session: {session.id}]
[Channel: {message.source.channel_id if message.source else 'unknown'}]

{text}"""

        # Query Claude via SDK
        await self._sdk_client.query(context_prompt)

        # Collect response
        response_text = ""
        async for msg in self._sdk_client.receive_response():
            # Handle different message types
            if hasattr(msg, 'content'):
                for block in msg.content:
                    if hasattr(block, 'text'):
                        response_text += block.text

        return P3394Message(
            type=MessageType.RESPONSE,
            reply_to=message.id,
            session_id=session.id,
            content=[P3394Content(type=ContentType.TEXT, data=response_text)]
        )

    async def _handle_skill(self, message: P3394Message, session: Session) -> P3394Message:
        """Invoke a registered skill (via Claude with skill context)"""
        text = self._extract_text(message)

        # Find matching skill
        skill_name = None
        for pattern, name in self.skill_triggers.items():
            if pattern in text.lower():
                skill_name = name
                break

        if skill_name and skill_name in self.skills:
            skill_def = self.skills[skill_name]

            # Prepend skill instructions to the message
            skill_prompt = f"""[SKILL: {skill_name}]
{skill_def.get('instructions', '')}

User request: {text}"""

            # Create modified message with skill context
            modified_message = P3394Message(
                type=message.type,
                source=message.source,
                destination=message.destination,
                reply_to=message.reply_to,
                session_id=message.session_id,
                content=[P3394Content(type=ContentType.TEXT, data=skill_prompt)]
            )

            return await self._handle_llm(modified_message, session)

        # Fallback to regular LLM handling
        return await self._handle_llm(message, session)

    async def _handle_subagent(self, message: P3394Message, session: Session) -> P3394Message:
        """Delegate to specialized subagent"""
        # Use Claude's Task tool to spawn subagent
        text = self._extract_text(message)

        subagent_prompt = f"""Use the Task tool to delegate this request to an appropriate specialized agent:

{text}

Available subagents:
- documentation-agent: For documentation tasks
- onboarding-agent: For helping new users
- demo-agent: For interactive demonstrations
"""

        modified_message = P3394Message(
            type=message.type,
            source=message.source,
            destination=message.destination,
            reply_to=message.reply_to,
            session_id=message.session_id,
            content=[P3394Content(type=ContentType.TEXT, data=subagent_prompt)]
        )

        return await self._handle_llm(modified_message, session)

    # =========================================================================
    # SYMBOLIC COMMAND HANDLERS
    # =========================================================================

    async def _cmd_help(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /help command"""
        help_text = f"""# {self.AGENT_NAME} v{self.AGENT_VERSION}

## Available Commands

"""
        seen = set()
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                help_text += f"**{cmd.name}** - {cmd.description}\n"
                if cmd.aliases:
                    help_text += f"  _Aliases: {', '.join(cmd.aliases)}_\n"
                help_text += "\n"
                seen.add(cmd.name)

        help_text += """
## Capabilities

This agent demonstrates the IEEE P3394 standard through:
- **Universal Message Format (UMF)** - All communication uses P3394 messages
- **Channel Abstraction** - Same agent, multiple interfaces (CLI, Web, P3394)
- **Content Negotiation** - Automatic adaptation to channel capabilities
- **Agent Discovery** - Self-documenting manifest with capabilities

Just send a message or use a command to get started!
"""
        return P3394Message.text(help_text, reply_to=message.id, session_id=session.id)

    async def _cmd_about(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /about command"""
        about_text = f"""# About {self.AGENT_NAME}

**Version:** {self.AGENT_VERSION}
**Agent ID:** {self.AGENT_ID}
**Standard:** IEEE P3394 (Agent Interface Standard)
**Built with:** Claude Agent SDK

## What is P3394?

IEEE P3394 defines a universal standard for agent communication, enabling:
- **Interoperability**: Agents from different vendors can communicate
- **Universal Message Format (UMF)**: Standard message structure
- **Channel Abstraction**: Same agent, multiple interfaces
- **Capability Discovery**: Agents can discover each other's abilities

## This Agent

This agent serves as the **reference implementation** of P3394, demonstrating:
- P3394 UMF message format
- Channel adapters (Web, CLI, P3394-to-P3394)
- Content negotiation and adaptation
- Command syntax mapping
- Agent-to-agent discovery

## Learn More

- Use `/help` for available commands
- Try asking questions about P3394
- Test agent-to-agent communication via the P3394 server
"""
        return P3394Message.text(about_text, reply_to=message.id, session_id=session.id)

    async def _cmd_status(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /status command"""
        memory_stats = await self.memory.get_stats() if self.memory else {}

        status_text = f"""# Agent Status

**Agent:** {self.AGENT_NAME}
**Version:** {self.AGENT_VERSION}
**Status:** 🟢 Operational
**Runtime:** Claude Agent SDK

## Memory (KSTAR)
- Traces: {memory_stats.get('trace_count', 0)}
- Skills: {len(self.skills)}
- Perceptions: {memory_stats.get('perception_count', 0)}

## Channels
- Active: {len([c for c in self.channels.values() if getattr(c, 'is_active', False)])}
- Total: {len(self.channels)}

## Sessions
- Active: {len(self.session_manager.active_sessions)}

## SDK Integration
- Hooks: Active
- Custom Tools: {len(self.get_sdk_options().mcp_servers) if self._sdk_options else 0} MCP servers
- Working Directory: {self.working_dir}
"""
        return P3394Message.text(status_text, reply_to=message.id, session_id=session.id)

    async def _cmd_version(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /version command"""
        return P3394Message.text(
            f"{self.AGENT_NAME} v{self.AGENT_VERSION}",
            reply_to=message.id,
            session_id=session.id
        )

    async def _cmd_list_skills(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /listSkills command"""
        if not self.skills:
            skills_text = "# Skills\n\nNo skills loaded yet. Skills can be added to `.claude/skills/` directory."
        else:
            skills_text = "# Acquired Skills\n\n"
            for skill_name, skill_def in self.skills.items():
                description = skill_def.get('description', 'No description')
                triggers = skill_def.get('triggers', [])
                skills_text += f"**{skill_name}**\n"
                skills_text += f"  {description}\n"
                if triggers:
                    skills_text += f"  _Triggers: {', '.join(triggers)}_\n"
                skills_text += "\n"

        return P3394Message.text(skills_text, reply_to=message.id, session_id=session.id)

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _extract_text(self, message: P3394Message) -> str:
        """Extract text content from message"""
        for content in message.content:
            if content.type == ContentType.TEXT:
                return content.data
        return ""

    async def _get_or_create_session(self, message: P3394Message) -> Session:
        """Get existing session or create new one"""
        session_id = message.session_id
        if session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                return session

        return await self.session_manager.create_session()

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

    async def shutdown(self):
        """Shutdown the gateway and clean up resources"""
        if self._sdk_client:
            await self._sdk_client.close()
        logger.info("Gateway shutdown complete")
