"""
Agent Gateway (Message Router) - SDK Version

The central message router that:
1. Receives all incoming messages (from any channel)
2. Determines how to route them (symbolic, LLM, skill)
3. Dispatches to appropriate handler using Claude Agent SDK
4. Returns responses

Configuration is loaded from AgentConfig (agent.yaml).
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable, TYPE_CHECKING
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
from .capability_acl import CapabilityACLRegistry, CapabilityVisibility
from .capability_access import CapabilityAccessManager
from .capability_catalog import CapabilityCatalog
from uuid import uuid4

if TYPE_CHECKING:
    from config import AgentConfig

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

    Configuration is loaded from AgentConfig (agent.yaml) or defaults.
    """

    def __init__(
        self,
        memory: KStarMemory,
        working_dir: Optional[Path] = None,
        config: Optional["AgentConfig"] = None
    ):
        # Load configuration if not provided
        if config is None:
            try:
                from config import load_config
                config = load_config(working_dir=working_dir)
            except ImportError:
                # Fallback to defaults
                config = None

        # Store configuration
        self._config = config

        # Agent identity from config or defaults
        self.AGENT_ID = config.id if config else "p3394-agent"
        self.AGENT_NAME = config.name if config else "P3394 Agent"
        self.AGENT_VERSION = config.version if config else "0.1.0"

        self.memory = memory
        self.session_manager = SessionManager(storage_dir=self.memory.storage.base_dir if self.memory.storage else None)
        self.working_dir = working_dir if isinstance(working_dir, Path) else Path(working_dir) if working_dir else Path.cwd()

        # P3394 Authentication & Authorization
        from .auth.registry import PrincipalRegistry
        from .auth.policy import PolicyEngine
        from .auth.service_principal import ServicePrincipalRegistry
        import os

        principals_dir = self.working_dir / ".claude" / "principals"
        self.principal_registry = PrincipalRegistry(storage_dir=principals_dir)

        # Service Principal Registry (for agent's own identity and credentials)
        self.service_registry = ServicePrincipalRegistry(storage_dir=principals_dir)

        # Phase 3: Enable enforcement based on environment variable
        enforcement_enabled = os.environ.get("ENFORCE_AUTHENTICATION", "false").lower() == "true"
        self.policy_engine = PolicyEngine(enforcement_enabled=enforcement_enabled)

        # Phase 3: Enable enforcement for CLI channel (safe - admin has all perms)
        # Phase 4: Enable enforcement for WhatsApp channel (allowlist-based)
        if enforcement_enabled:
            self.policy_engine.enable_enforcement_for_channel("cli")
            self.policy_engine.enable_enforcement_for_channel("whatsapp")
            logger.info("CLI and WhatsApp channel enforcement enabled")

        logger.info(f"P3394 Authentication initialized (enforcement={self.policy_engine.enforcement_enabled})")

        # NEW: Unified capability system
        self.capability_registry = CapabilityRegistry(
            persistence_path=self.working_dir / ".claude" / "capabilities.json"
        )

        # NEW: Capability Access Control
        # ACL registry uses memory as primary storage (swappable), file as fallback
        self.acl_registry = CapabilityACLRegistry(
            storage_path=self.working_dir / ".claude" / "capability_acls.json",
            memory=memory  # Connect to memory server for persistent, swappable config
        )
        self.access_manager = CapabilityAccessManager(
            acl_registry=self.acl_registry,
            capability_registry=self.capability_registry
        )

        # Capability Catalog: Unified view of all capabilities (system ↔ memory sync)
        self.capability_catalog = CapabilityCatalog(
            memory=memory,
            working_dir=self.working_dir,
            gateway=self
        )

        self.capability_engine = CapabilityInvocationEngine(
            registry=self.capability_registry,
            gateway=self,
            access_manager=self.access_manager
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
        # Initialize ACL registry from memory server (or fallback to file)
        logger.info("Initializing capability ACLs from memory server...")
        await self.acl_registry.initialize()

        # Bootstrap built-in ACLs if not already in memory
        await self._bootstrap_builtin_acls()

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

        # NEW: Discover and catalog all capabilities (system → memory sync)
        await self._initialize_capability_catalog()

    async def _bootstrap_builtin_acls(self):
        """
        Bootstrap built-in ACLs, principals, and credential bindings.

        Uses the BootstrapManager to load configuration from:
        1. Default in-code config
        2. config/bootstrap_acl.json
        3. Environment-specified config (P3394_BOOTSTRAP_CONFIG)

        This enables swappable memory servers with different capability sets.
        """
        from .bootstrap import BootstrapManager
        from .capability_acl import create_builtin_acls

        # Load bootstrap data (principals, bindings) into memory
        bootstrap_mgr = BootstrapManager(self.memory, self.working_dir)
        bootstrap_results = await bootstrap_mgr.load_all()

        # Check if ACL registry already has entries (from memory)
        existing_count = len(self.acl_registry.list_all())
        if existing_count > 0:
            logger.info(f"ACL registry already has {existing_count} ACLs from memory")
            return

        # Register built-in ACLs if none loaded from memory
        builtin_acls = create_builtin_acls()
        for acl in builtin_acls:
            self.acl_registry.register(acl)

        logger.info(f"Bootstrapped {len(builtin_acls)} built-in capability ACLs")

        # Sync to memory server if available
        if self.memory:
            synced = await self.acl_registry.sync_to_memory()
            logger.info(f"Synced {synced} ACLs to memory server")

    async def _initialize_capability_catalog(self):
        """
        Initialize the capability catalog (system ↔ memory synchronization).

        This performs a top-down inspection of all available capabilities from:
        - Commands (built-in and custom)
        - Skills (.claude/skills/)
        - Subagents (.claude/agents/)
        - SDK tools (Read, Write, Bash, etc.)
        - MCP servers and tools
        - Hooks
        - Channels

        Then synchronizes with long-term memory so the agent "knows" its capabilities.
        """
        logger.info("Initializing capability catalog (system ↔ memory sync)...")

        # Step 1: Load what agent already knows from memory
        memory_count = await self.capability_catalog.load_from_memory()
        logger.info(f"Loaded {memory_count} capabilities from memory")

        # Step 2: Discover all capabilities from system (top-down inspection)
        discovery_counts = await self.capability_catalog.discover_all()

        # Step 3: Synchronize to memory (add new, update changed)
        sync_results = await self.capability_catalog.sync_to_memory()

        # Step 4: Report status
        stats = self.capability_catalog.get_stats()
        logger.info(
            f"Capability catalog initialized: "
            f"{stats['total']} total, "
            f"{stats['sync_status']['in_both']} synced, "
            f"{stats['sync_status']['only_system']} new, "
            f"{stats['sync_status']['only_memory']} orphaned"
        )

        # Log any out-of-sync capabilities
        out_of_sync = self.capability_catalog.list_out_of_sync()
        if out_of_sync:
            logger.warning(f"Found {len(out_of_sync)} capabilities out of sync")
            for entry in out_of_sync[:5]:  # Log first 5
                logger.warning(f"  - {entry.id}: in_system={entry.in_system}, in_memory={entry.in_memory}")

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
                # KSTAR Memory (episodic, declarative, procedural)
                "mcp__p3394_tools__query_memory",
                "mcp__p3394_tools__store_trace",
                "mcp__p3394_tools__list_skills",
                # KSTAR+ Control Tokens (the 4th memory class - authority to execute)
                "mcp__p3394_tools__store_control_token",
                "mcp__p3394_tools__get_control_token",
                "mcp__p3394_tools__verify_control_token",
                "mcp__p3394_tools__revoke_control_token",
                "mcp__p3394_tools__get_token_lineage",
                "mcp__p3394_tools__list_tokens_by_type",
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
        """Get system prompt for Claude from config or default"""
        # Use config's system prompt if available
        if self._config and self._config.llm.system_prompt:
            # Format with agent identity
            return self._config.llm.system_prompt.format(
                agent_id=self.AGENT_ID,
                agent_name=self.AGENT_NAME,
                agent_version=self.AGENT_VERSION,
                agent_description=self._config.description if self._config else "",
            )

        # Default system prompt
        return f"""You are the {self.AGENT_NAME} (v{self.AGENT_VERSION}).

You are a P3394-compliant agent that follows the Universal Message Format standard.

Your role:
- Respond helpfully and accurately to user requests
- Demonstrate P3394 Universal Message Format (UMF) when relevant
- Provide examples and explanations when asked

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
            name="/login",
            handler=self._cmd_login,
            description="Authenticate with API key",
            usage="/login <api_key>",
            requires_auth=False  # Login doesn't require auth
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

        self.register_command(SymbolicCommand(
            name="/endpoints",
            handler=self._cmd_endpoints,
            description="Show where the agent can be reached on each channel",
            aliases=["/contacts", "/reach"]
        ))

        self.register_command(SymbolicCommand(
            name="/configure",
            handler=self._cmd_configure,
            description="Configure a channel (admin only)",
            usage="/configure <channel> [--interactive]",
            requires_auth=True
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
        2. Authorize access (if enforcement enabled)
        3. Invoke via capability engine or fall back to LLM
        4. Return response
        """
        session = await self._get_or_create_session(message)
        capability_id = await self.route(message)

        logger.info(f"Routing message {message.id}: capability={capability_id or 'LLM fallback'}")

        # Authorize access to capability (if enforcement enabled)
        # REQ-CAP-CH-AUTH: Returns credential elevation challenge if applicable
        if capability_id:
            authorized, challenge_message = await self._authorize_capability_access(
                session, capability_id, message
            )
            if not authorized:
                # Authorization denied - return error with challenge if available
                error_message = challenge_message or "Access denied: Insufficient permissions for this capability"
                return self._create_error_response(message, error_message)

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
        # Build command list dynamically, filtered by session visibility
        seen = set()
        commands_list = ""
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                # Check if command capability is visible to this session
                cap_id = f"legacy.command.{cmd.name.lstrip('/')}"
                if session.can_list_capability(cap_id) or session.client_role in ("admin", "system"):
                    commands_list += f"- `{cmd.name}` - {cmd.description}\n"
                    seen.add(cmd.name)
                elif not session.is_authenticated:
                    # Show public commands to anonymous
                    if cmd.name in ("/help", "/about", "/version", "/login"):
                        commands_list += f"- `{cmd.name}` - {cmd.description}\n"
                        seen.add(cmd.name)

        help_text = f"""# {self.AGENT_NAME} - Help

## Quick Start

```bash
# Install dependencies
uv sync

# Set API key
export ANTHROPIC_API_KEY='your-api-key-here'

# Run the agent
uv run python -m p3394_agent --daemon
```

## Available Commands

{commands_list}

## Configuration

Edit `agent.yaml` to customize:
- Agent identity (id, name, version)
- Enabled channels (cli, web, whatsapp)
- LLM settings (model, system prompt)
- Skills to load

## Getting Help

- `/about` - Learn more about this agent
- `/status` - Check agent health and status
- `/listSkills` - See available skills
"""
        return P3394Message.text(help_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

    async def _cmd_about(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /about command"""
        description = self._config.description if self._config else "A P3394-compliant agent"
        metadata = self._config.metadata if self._config else {}

        about_text = f"""# {self.AGENT_NAME}

**Version:** {self.AGENT_VERSION}
**Agent ID:** {self.AGENT_ID}

## Description

{description}

## P3394 Standard

This agent follows the P3394 Universal Message Format (UMF) standard for agent interoperability.

**Key Features:**
- Channel-agnostic message routing
- Symbolic command execution
- LLM integration via Claude Agent SDK
- Extensible skill system
"""
        if metadata:
            about_text += "\n## Additional Information\n\n"
            for key, value in metadata.items():
                about_text += f"- **{key}:** {value}\n"

        return P3394Message.text(about_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

    async def _cmd_login(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """
        Handle /login command - Authenticate with API key.

        Usage: /login <api_key>
        """
        from .auth.principal import AssuranceLevel
        import hashlib

        text = self._extract_text(message)
        parts = text.split()

        if len(parts) < 2:
            return P3394Message.text(
                "Usage: /login <api_key>\n\nExample: /login 3394",
                type=MessageType.RESPONSE,
                reply_to=message.id,
                session_id=session.id
            )

        api_key = parts[1]

        # Hash the provided API key
        api_key_hash = hashlib.sha256(api_key.encode()).hexdigest()

        # Find matching credential binding
        bindings = self.principal_registry.list_bindings(channel="cli")
        matching_binding = None

        for binding in bindings:
            if binding.binding_type.value == "api_key" and binding.secret_hash == api_key_hash:
                matching_binding = binding
                break

        if not matching_binding:
            logger.warning(f"Failed login attempt with invalid API key from session {session.id}")
            return P3394Message.text(
                "❌ Authentication failed: Invalid API key",
                type=MessageType.RESPONSE,
                reply_to=message.id,
                session_id=session.id
            )

        # Get principal
        principal = self.principal_registry.get_principal(matching_binding.principal_id)

        if not principal or not principal.is_active:
            return P3394Message.text(
                "❌ Authentication failed: Principal not active",
                type=MessageType.RESPONSE,
                reply_to=message.id,
                session_id=session.id
            )

        # Update session with authenticated principal
        session.client_principal_id = principal.principal_id
        session.is_authenticated = True
        session.assurance_level = AssuranceLevel.HIGH.value

        # Grant permissions from binding
        for scope in matching_binding.scopes:
            session.grant_permission(scope)

        # Update binding last used
        matching_binding.touch()
        self.principal_registry.update_binding(matching_binding)

        # Log successful authentication to KSTAR
        await self.memory.store_trace({
            "situation": {
                "domain": "p3394_agent.authentication",
                "actor": principal.principal_id,
                "channel": "cli",
                "session_id": session.id,
                "timestamp": message.timestamp
            },
            "task": {
                "goal": "Authenticate via API key"
            },
            "action": {
                "type": "login",
                "method": "api_key",
                "binding_id": matching_binding.binding_id
            },
            "result": {
                "success": True,
                "principal_id": principal.principal_id,
                "permissions_granted": matching_binding.scopes
            },
            "mode": "security",
            "tags": ["authentication", "login", "success"]
        })

        logger.info(f"Successful login: session={session.id}, principal={principal.principal_id}")

        return P3394Message.text(
            f"✓ Authentication successful\n\n"
            f"**Principal:** {principal.display_name or principal.principal_id}\n"
            f"**Role:** {principal.role}\n"
            f"**Permissions:** {', '.join(matching_binding.scopes)}\n"
            f"**Assurance Level:** HIGH\n\n"
            f"You are now authenticated. Use `/help` to see available commands.",
            type=MessageType.RESPONSE,
            reply_to=message.id,
            session_id=session.id
        )

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
        return P3394Message.text(status_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

    async def _cmd_version(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /version command"""
        return P3394Message.text(
            f"{self.AGENT_NAME} v{self.AGENT_VERSION}",
            type=MessageType.RESPONSE,
            reply_to=message.id,
            session_id=session.id
        )

    async def _cmd_list_skills(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /listSkills command - filtered by session visibility"""
        if not self.skills:
            skills_text = "# Skills\n\nNo skills loaded yet. Skills can be added to `.claude/skills/` directory."
        else:
            skills_text = "# Acquired Skills\n\n"
            visible_count = 0

            for skill_name, skill_def in self.skills.items():
                # Check if skill capability is visible to this session
                cap_id = f"skill.{skill_name}"
                if session.can_list_capability(cap_id) or session.client_role in ("admin", "system"):
                    description = skill_def.get('description', 'No description')
                    triggers = skill_def.get('triggers', [])
                    skills_text += f"**{skill_name}**\n"
                    skills_text += f"  {description}\n"
                    if triggers:
                        skills_text += f"  _Triggers: {', '.join(triggers)}_\n"
                    skills_text += "\n"
                    visible_count += 1

            if visible_count == 0:
                skills_text += "_No skills available for your current access level._\n"

            # Show count for admin
            if session.client_role in ("admin", "system") and visible_count < len(self.skills):
                skills_text += f"\n_Showing {visible_count} of {len(self.skills)} skills_\n"

        return P3394Message.text(skills_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

    async def _cmd_endpoints(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /endpoints command - show where the agent can be reached"""
        endpoints = self.service_registry.get_public_endpoints()

        if not endpoints:
            response_text = """# Agent Endpoints

No channels are configured yet.

To configure channels, use:
- `/configure whatsapp` - Configure WhatsApp Business API
- `/configure web` - Configure web interface
- `/configure cli` - Configure CLI interface

Or run the onboarding wizard:
```bash
python -m p3394_agent.core.onboarding
```
"""
        else:
            sp = self.service_registry.service_principal
            response_text = f"""# {sp.display_name}

**Service Principal ID**: `{sp.service_principal_id}`

## 📡 How to Reach This Agent

"""
            for channel_id, endpoint in endpoints.items():
                channel_config = self.service_registry.get_channel_configuration(channel_id)
                if channel_config:
                    response_text += f"### {channel_id.upper()}\n"
                    response_text += f"**Endpoint**: `{endpoint}`\n"

                    # Add channel-specific metadata
                    if channel_id == "whatsapp":
                        phone = channel_config.metadata.get("phone_number", endpoint)
                        response_text += f"📱 Message the agent at: **{phone}**\n"
                        response_text += f"_Platform: WhatsApp Business API_\n"
                    elif channel_id == "web":
                        response_text += f"🌐 Visit: **{endpoint}**\n"
                        response_text += f"💬 Chat: **{endpoint}/chat**\n"
                        response_text += f"📚 Docs: **{endpoint}/docs**\n"
                    elif channel_id == "cli":
                        response_text += f"📟 Run: `python -m p3394_agent --channel cli`\n"

                    response_text += "\n"

            response_text += """---

_These are the P3394-compliant endpoints where the agent is reachable._
_Each channel adapter transforms its native protocol to/from P3394 UMF._
"""

        return P3394Message.text(response_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

    async def _cmd_configure(self, message: P3394Message, session: Session, **kwargs) -> P3394Message:
        """Handle /configure command - configure a channel (admin only)"""
        from .onboarding import ChannelOnboarding

        text = self._extract_text(message)
        parts = text.split()

        if len(parts) < 2:
            usage_text = """# Channel Configuration

**Usage**: `/configure <channel>`

**Available Channels**:
- `whatsapp` - Configure WhatsApp Business API
- `web` - Configure web interface
- `cli` - Configure CLI interface
- `show` - Show current configuration

**Example**: `/configure whatsapp`

**Note**: This is an admin-only command. For detailed configuration,
you can also run the onboarding wizard:
```bash
python -m p3394_agent.core.onboarding
```
"""
            return P3394Message.text(usage_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

        channel_name = parts[1].lower()
        interactive = "--interactive" in parts or "-i" in parts

        # Initialize onboarding
        onboarding = ChannelOnboarding(self.service_registry)

        try:
            if channel_name == "show":
                # Show current configuration
                import io
                import sys

                # Capture print output
                old_stdout = sys.stdout
                sys.stdout = buffer = io.StringIO()

                await onboarding.show_configuration()

                output = buffer.getvalue()
                sys.stdout = old_stdout

                return P3394Message.text(output, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

            elif channel_name == "whatsapp":
                # For CLI-based configuration, we need interactive mode
                response_text = """# WhatsApp Configuration

WhatsApp Business API requires several credentials:
1. Phone Number ID
2. Access Token
3. Webhook Verify Token

**To configure WhatsApp**, run:
```bash
python -m p3394_agent.core.onboarding whatsapp
```

This will guide you through the setup process interactively.

Alternatively, set environment variables:
```bash
export WHATSAPP_PHONE_NUMBER="+15551234567"
export WHATSAPP_PHONE_NUMBER_ID="your_phone_id"
export WHATSAPP_ACCESS_TOKEN="your_access_token"
export WHATSAPP_VERIFY_TOKEN="your_verify_token"
export WHATSAPP_WEBHOOK_URL="https://your-domain.com/webhook/whatsapp"
```

Then restart the agent.
"""
                return P3394Message.text(response_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

            elif channel_name == "web":
                # Configure web channel
                success = await onboarding.configure_web()
                if success:
                    endpoints = self.service_registry.get_public_endpoints()
                    web_endpoint = endpoints.get("web", "Not configured")
                    response_text = f"""# ✅ Web Channel Configured

Your agent is now reachable at:
**{web_endpoint}**

💬 Chat: **{web_endpoint}/chat**
📚 Docs: **{web_endpoint}/docs**
"""
                else:
                    response_text = "❌ Failed to configure web channel. Check logs for details."

                return P3394Message.text(response_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

            elif channel_name == "cli":
                # Configure CLI channel
                success = await onboarding.configure_cli()
                if success:
                    response_text = """# ✅ CLI Channel Configured

Run the agent with:
```bash
python -m p3394_agent --channel cli
```
"""
                else:
                    response_text = "❌ Failed to configure CLI channel. Check logs for details."

                return P3394Message.text(response_text, type=MessageType.RESPONSE, reply_to=message.id, session_id=session.id)

            else:
                return P3394Message.text(
                    f"❌ Unknown channel: {channel_name}\n\nAvailable: whatsapp, web, cli, show",
                    type=MessageType.RESPONSE,
                    reply_to=message.id,
                    session_id=session.id
                )

        except Exception as e:
            logger.exception(f"Error during configuration: {e}")
            return P3394Message.text(
                f"❌ Configuration error: {str(e)}",
                type=MessageType.ERROR,
                reply_to=message.id,
                session_id=session.id
            )

    # =========================================================================
    # HELPER METHODS
    # =========================================================================

    def _extract_text(self, message: P3394Message) -> str:
        """Extract text content from message"""
        for content in message.content:
            if content.type == ContentType.TEXT:
                return content.data
        return ""

    def _extract_client_assertion(self, message: P3394Message) -> Optional[Any]:
        """
        Extract ClientPrincipalAssertion from message metadata.

        Channel adapters embed the assertion in message.metadata["security"]["client_assertion"]
        """
        from .auth.principal import ClientPrincipalAssertion

        security_metadata = message.metadata.get("security", {})
        assertion_data = security_metadata.get("client_assertion")

        if assertion_data:
            try:
                return ClientPrincipalAssertion.from_dict(assertion_data)
            except Exception as e:
                logger.warning(f"Failed to parse client assertion: {e}")

        return None

    async def _authorize_capability_access(
        self,
        session: Session,
        capability_id: str,
        message: P3394Message
    ) -> tuple[bool, Optional[str]]:
        """
        Authorize access to a capability with credential elevation support.

        REQ-CAP-CH-AUTH Implementation:
        When authorization is denied, checks if credential elevation is possible
        for the current channel. If so, returns a challenge message indicating
        how to elevate credentials.

        Phase 3: Full authorization with KSTAR audit logging.

        Args:
            session: Current session (contains principal and permissions)
            capability_id: Capability being accessed
            message: Original message

        Returns:
            Tuple of (authorized: bool, challenge_message: Optional[str])
            - If authorized=True, challenge_message is None
            - If authorized=False and elevation possible, challenge_message explains how
            - If authorized=False and no elevation, challenge_message is denial reason
        """
        from .auth.principal import AssuranceLevel
        from .auth.policy import PolicyDecision
        from datetime import datetime

        # Get principal (fallback to anonymous if not set)
        if session.client_principal_id:
            principal = self.principal_registry.get_principal(session.client_principal_id)
        else:
            principal = self.principal_registry.get_anonymous_principal()

        if not principal:
            logger.error(f"Principal not found: {session.client_principal_id}")
            principal = self.principal_registry.get_anonymous_principal()

        # Get capability descriptor to determine required permissions
        capability = self.capability_registry.get(capability_id)
        required_permissions = []
        if capability and capability.permissions:
            required_permissions = capability.permissions.required or []

        # Get assurance level
        try:
            assurance_level = AssuranceLevel(session.assurance_level)
        except (ValueError, AttributeError):
            assurance_level = AssuranceLevel.NONE

        # Get channel from message
        channel = message.source.channel_id if message.source else session.channel_id

        # Make authorization decision
        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=assurance_level,
            capability=capability_id,
            requested_permissions=required_permissions,
            granted_permissions=session.granted_permissions,
            channel=channel,
            metadata={
                "message_id": message.id,
                "session_id": session.id,
            }
        )

        # Log to KSTAR memory (audit trail)
        await self._log_authorization_to_kstar(
            principal=principal,
            capability=capability_id,
            decision=decision,
            reason=reason,
            session=session,
            message=message,
            required_permissions=required_permissions,
            granted_permissions=session.granted_permissions,
            assurance_level=assurance_level
        )

        if decision == PolicyDecision.ALLOW:
            return True, None

        # Authorization denied - check if credential elevation is available
        elevation_message = self._get_credential_elevation_challenge(
            channel=channel,
            principal=principal,
            assurance_level=assurance_level,
            required_permissions=required_permissions,
            reason=reason
        )

        return False, elevation_message

    def _get_credential_elevation_challenge(
        self,
        channel: str,
        principal: Any,
        assurance_level: "AssuranceLevel",
        required_permissions: list[str],
        reason: str
    ) -> str:
        """
        Generate credential elevation challenge for denied access.

        REQ-CAP-CH-AUTH: Support channel-specific credential elevation flows.

        Args:
            channel: Channel ID
            principal: Current principal
            assurance_level: Current assurance level
            required_permissions: Permissions that were required
            reason: Original denial reason

        Returns:
            Challenge message explaining how to elevate credentials
        """
        from .auth.principal import AssuranceLevel

        # CLI channel: Suggest /login for elevation
        if channel == "cli":
            # If user is anonymous or low assurance, suggest login
            if assurance_level in [AssuranceLevel.NONE, AssuranceLevel.LOW]:
                return f"""Access denied: {reason}

**Credential Elevation Available**

Your current authentication level is insufficient for this capability.
To gain access, use:

    /login <api_key>

For admin access, use the API key: 3394

This will elevate your credentials from {assurance_level.value.upper()} to HIGH assurance.
"""

            # If user has medium assurance but lacks permissions
            elif assurance_level == AssuranceLevel.MEDIUM:
                return f"""Access denied: {reason}

Your authentication is valid but lacks required permissions: {required_permissions}

**Credential Elevation Available**

To gain admin privileges, use:

    /login <api_key>

Admin API key: 3394
"""

        # WhatsApp channel: Allowlist-based, no elevation mechanism
        elif channel == "whatsapp":
            return f"""Access denied: {reason}

Your WhatsApp number is not authorized for this capability.

Contact the administrator to add your number to the allowlist with
required permissions: {required_permissions}
"""

        # Generic denial
        return f"Access denied: {reason}"

    async def _log_authorization_to_kstar(
        self,
        principal: Any,
        capability: str,
        decision: Any,
        reason: str,
        session: Session,
        message: P3394Message,
        required_permissions: list,
        granted_permissions: list,
        assurance_level: Any
    ) -> None:
        """
        Log authorization decision to KSTAR memory for audit trail.

        Creates a trace with:
        - Situation: Who, when, where, what assurance level
        - Task: Access capability with required permissions
        - Action: Authorization check
        - Result: ALLOW or DENY with reason
        """
        from datetime import datetime

        try:
            trace_data = {
                "situation": {
                    "domain": "p3394_agent.authorization",
                    "actor": principal.principal_id,
                    "actor_type": principal.principal_type.value,
                    "actor_name": principal.display_name or principal.principal_id,
                    "channel": session.channel_id or "unknown",
                    "assurance_level": assurance_level.value,
                    "session_id": session.id,
                    "message_id": message.id,
                    "timestamp": datetime.utcnow().isoformat() + "Z"
                },
                "task": {
                    "goal": f"Access capability: {capability}",
                    "required_permissions": required_permissions,
                    "capability_id": capability
                },
                "action": {
                    "type": "authorization_check",
                    "policy_engine": "P3394PolicyEngine",
                    "granted_permissions": granted_permissions,
                    "enforcement_enabled": self.policy_engine.enforcement_enabled
                },
                "result": {
                    "decision": decision.value,
                    "reason": reason,
                    "success": decision.value == "allow"
                },
                "mode": "security",
                "tags": ["authorization", "security", "audit", f"decision:{decision.value}"]
            }

            await self.memory.store_trace(trace_data)

        except Exception as e:
            # Don't fail request if audit logging fails
            logger.error(f"Failed to log authorization to KSTAR: {e}")

    async def _get_or_create_session_with_auth(self, message: P3394Message) -> Session:
        """
        Get or create session with authentication resolution.

        Phase 1: Extract and resolve principal, but don't enforce yet.
        """
        from .auth.principal import AssuranceLevel

        # Try to get existing session
        session_id = message.session_id
        if session_id:
            session = self.session_manager.get_session(session_id)
            if session:
                return session

        # Create new session
        session = await self.session_manager.create_session(
            channel_id=message.source.channel_id if message.source else None
        )

        # Extract client principal assertion from message
        assertion = self._extract_client_assertion(message)

        if assertion:
            # Resolve to semantic principal
            principal = self.principal_registry.resolve_assertion(assertion)

            if principal:
                session.client_principal_id = principal.principal_id
                session.assurance_level = assertion.assurance_level.value
                session.is_authenticated = True

                # Get permissions from credential binding
                bindings = self.principal_registry.list_bindings(
                    principal_id=principal.principal_id,
                    channel=assertion.channel_id
                )
                if bindings:
                    for binding in bindings:
                        for scope in binding.scopes:
                            session.grant_permission(scope)

                logger.info(
                    f"Principal resolved: {assertion.channel_id}:{assertion.channel_identity} "
                    f"→ {principal.principal_id} (assurance={assertion.assurance_level.value})"
                )

                # Compute capability access for session
                self.access_manager.compute_session_access(
                    session=session,
                    principal=principal,
                    assurance=assertion.assurance_level
                )
            else:
                # No principal found - use anonymous
                anonymous = self.principal_registry.get_anonymous_principal()
                session.client_principal_id = anonymous.principal_id
                session.assurance_level = AssuranceLevel.NONE.value
                session.is_authenticated = False

                logger.warning(
                    f"No principal found for {assertion.channel_id}:{assertion.channel_identity}, "
                    f"using anonymous"
                )

                # Compute anonymous capability access
                self.access_manager.compute_session_access(
                    session=session,
                    principal=anonymous,
                    assurance=AssuranceLevel.NONE
                )
        else:
            # No assertion - use anonymous
            anonymous = self.principal_registry.get_anonymous_principal()
            session.client_principal_id = anonymous.principal_id
            session.assurance_level = AssuranceLevel.NONE.value
            session.is_authenticated = False

            # Compute anonymous capability access
            self.access_manager.compute_session_access(
                session=session,
                principal=anonymous,
                assurance=AssuranceLevel.NONE
            )

        return session

    async def _get_or_create_session(self, message: P3394Message) -> Session:
        """Get existing session or create new one (with auth resolution)"""
        return await self._get_or_create_session_with_auth(message)

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
