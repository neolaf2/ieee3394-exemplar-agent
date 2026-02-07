# IEEE 3394 Exemplar Agent

## Agent Identity

You are the **IEEE 3394 Exemplar Agent**, a living demonstration of the IEEE P3394 Standard for Agent Interfaces. You serve as both:
1. The reference implementation of P3394-compliant agent architecture
2. The public-facing agent for ieee3394.org, helping visitors understand and adopt the standard

You are built on the Claude Agent SDK and implement the P3394 Universal Message Format (UMF) for all communications. You are self-documenting—your capabilities, skills, and architecture ARE the documentation.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                    IEEE 3394 Exemplar Agent                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                      │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                 Agent Gateway (Shell)                          │  │
│  │              Message Router / Service Orchestrator             │  │
│  │                                                                │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐           │  │
│  │  │  Symbolic   │  │    LLM      │  │  SubAgent   │           │  │
│  │  │  Commands   │  │   Router    │  │ Dispatcher  │           │  │
│  │  │ (no LLM)    │  │  (Hooks)    │  │             │           │  │
│  │  └─────────────┘  └─────────────┘  └─────────────┘           │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │              Claude Agent SDK + P3394 Plugins                  │  │
│  │  • Hooks (KSTAR logging, P3394 compliance)                    │  │
│  │  • Skills (site generation, documentation, demos)             │  │
│  │  • Tools (MCP servers for KSTAR DB, external services)        │  │
│  │  • SubAgents (documentation, demo, onboarding)                │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                              │                                       │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    KSTAR Memory Layer                          │  │
│  │  • Traces (episodic memory of all interactions)               │  │
│  │  • Skills (learned capabilities)                              │  │
│  │  • Perceptions (facts, observations)                          │  │
│  │  • Tokens (credentials, API keys)                             │  │
│  └───────────────────────────────────────────────────────────────┘  │
│                                                                      │
├─────────────────────────────────────────────────────────────────────┤
│                      Channel Adapters                                │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │
│  │   Web    │  │   CLI    │  │   MCP    │  │  Future  │           │
│  │ Channel  │  │ Channel  │  │ Channel  │  │ Channels │           │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Implementation Instructions

### Project Setup

Create the following project structure:

```
ieee3394-agent/
├── pyproject.toml
├── README.md
├── CLAUDE.md                        # This file
├── .claude/
│   ├── settings.json
│   ├── skills/
│   │   ├── site-generator/SKILL.md
│   │   ├── p3394-explainer/SKILL.md
│   │   └── demo-builder/SKILL.md
│   ├── agents/
│   │   ├── documentation-agent.md
│   │   ├── onboarding-agent.md
│   │   └── demo-agent.md
│   └── commands/
│       ├── deploy.md
│       └── generate-site.md
├── src/
│   └── ieee3394_agent/
│       ├── __init__.py
│       ├── __main__.py              # Entry point
│       ├── core/
│       │   ├── __init__.py
│       │   ├── gateway.py           # Message router (Shell)
│       │   ├── session.py           # Session management
│       │   ├── umf.py               # P3394 UMF message types
│       │   └── config.py            # Configuration
│       ├── channels/
│       │   ├── __init__.py
│       │   ├── base.py              # Abstract channel adapter
│       │   ├── web.py               # FastAPI + WebSocket
│       │   ├── cli.py               # REPL interface
│       │   └── mcp.py               # Agent-to-agent (P3394 native)
│       ├── plugins/
│       │   ├── __init__.py
│       │   ├── hooks.py             # P3394 + KSTAR hooks
│       │   ├── commands.py          # Symbolic command handlers
│       │   └── tools.py             # Custom MCP tools
│       └── memory/
│           ├── __init__.py
│           └── kstar.py             # KSTAR DB integration
├── static/                          # Agent-generated website
│   ├── index.html
│   ├── about.html
│   ├── docs/
│   ├── demo/
│   └── assets/
│       ├── css/
│       └── js/
├── templates/                       # Jinja2 templates for site generation
│   ├── base.html
│   ├── landing.html
│   ├── chat.html
│   └── docs.html
├── tests/
│   ├── test_gateway.py
│   ├── test_channels.py
│   └── test_umf.py
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Core Components

### 1. P3394 Universal Message Format (UMF)

```python
# src/ieee3394_agent/core/umf.py

from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional
from datetime import datetime
from uuid import uuid4
from enum import Enum

class MessageType(str, Enum):
    """P3394 message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"

class ContentType(str, Enum):
    """P3394 content types"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    BINARY = "binary"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"

@dataclass
class P3394Address:
    """Agent addressing per P3394"""
    agent_id: str                    # Unique agent identifier
    channel_id: Optional[str] = None # Channel within agent
    session_id: Optional[str] = None # Session context
    
    def to_uri(self) -> str:
        """Convert to P3394 URI format: p3394://{agent_id}/{channel_id}?session={session_id}"""
        uri = f"p3394://{self.agent_id}"
        if self.channel_id:
            uri += f"/{self.channel_id}"
        if self.session_id:
            uri += f"?session={self.session_id}"
        return uri
    
    @classmethod
    def from_uri(cls, uri: str) -> "P3394Address":
        """Parse P3394 URI"""
        # Implementation: parse p3394://{agent_id}/{channel_id}?session={session_id}
        pass

@dataclass
class P3394Content:
    """Message content block"""
    type: ContentType
    data: Any
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

@dataclass
class P3394Message:
    """
    IEEE P3394 Universal Message Format
    
    This is the canonical message structure for all agent communication.
    All channel adapters transform their native formats to/from this structure.
    """
    # Header
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.REQUEST
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    
    # Addressing
    source: Optional[P3394Address] = None
    destination: Optional[P3394Address] = None
    reply_to: Optional[str] = None  # Message ID for threading
    
    # Content
    content: List[P3394Content] = field(default_factory=list)
    
    # Context
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "source": self.source.to_uri() if self.source else None,
            "destination": self.destination.to_uri() if self.destination else None,
            "reply_to": self.reply_to,
            "content": [
                {
                    "type": c.type.value,
                    "data": c.data,
                    "mime_type": c.mime_type,
                    "metadata": c.metadata
                }
                for c in self.content
            ],
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "P3394Message":
        """Deserialize from dictionary"""
        pass
    
    @classmethod
    def text(cls, text: str, **kwargs) -> "P3394Message":
        """Convenience constructor for text messages"""
        return cls(
            content=[P3394Content(type=ContentType.TEXT, data=text)],
            **kwargs
        )

@dataclass  
class P3394Error:
    """Standard error format"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
```

### 2. Agent Gateway (Message Router)

```python
# src/ieee3394_agent/core/gateway.py

import asyncio
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Awaitable
from enum import Enum
import logging

from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions
from .umf import P3394Message, P3394Content, ContentType, MessageType
from .session import SessionManager, Session
from ..memory.kstar import KStarMemory

logger = logging.getLogger(__name__)

class MessageRoute(str, Enum):
    """How to route a message"""
    SYMBOLIC = "symbolic"      # Direct function dispatch (no LLM)
    LLM = "llm"               # Route to Claude via Agent SDK
    SUBAGENT = "subagent"     # Delegate to specialized subagent
    SKILL = "skill"           # Invoke a registered skill
    BROADCAST = "broadcast"   # Send to multiple handlers

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
    
    This is the central message router that:
    1. Receives all incoming messages (from any channel)
    2. Determines how to route them (symbolic, LLM, subagent, skill)
    3. Dispatches to appropriate handler
    4. Returns responses
    
    Think of it as an HTTP router, but for agent messages.
    """
    
    # Agent identity
    AGENT_ID = "ieee3394-exemplar"
    AGENT_NAME = "IEEE 3394 Exemplar Agent"
    AGENT_VERSION = "0.1.0"
    
    def __init__(
        self,
        kstar_memory: KStarMemory,
        claude_options: Optional[ClaudeAgentOptions] = None
    ):
        self.memory = kstar_memory
        self.claude_options = claude_options or self._default_claude_options()
        self.session_manager = SessionManager()
        
        # Command registry
        self.commands: Dict[str, SymbolicCommand] = {}
        self._register_builtin_commands()
        
        # Skill triggers (pattern -> skill name)
        self.skill_triggers: Dict[str, str] = {}
        
        # Active channels
        self.channels: Dict[str, "ChannelAdapter"] = {}
        
        # Claude SDK client (lazy initialized)
        self._claude_client: Optional[ClaudeSDKClient] = None
    
    def _default_claude_options(self) -> ClaudeAgentOptions:
        """Default Claude Agent SDK configuration"""
        from ..plugins.hooks import P3394_HOOKS
        from ..plugins.tools import create_p3394_tools
        
        return ClaudeAgentOptions(
            system_prompt={
                "type": "preset",
                "preset": "claude_code",
                "append": self._get_agent_system_prompt()
            },
            allowed_tools=[
                "Read", "Write", "Edit", "Bash", "Glob", "Grep",
                "WebSearch", "WebFetch", "Task",
                # Custom P3394 tools
                "mcp__kstar__query", "mcp__kstar__store_trace",
                "mcp__kstar__store_perception", "mcp__kstar__find_skills"
            ],
            hooks=P3394_HOOKS,
            mcp_servers={
                "kstar": {
                    "type": "stdio",
                    "command": "npx",
                    "args": ["-y", "@anthropic/kstar-memory-server"]
                }
            },
            permission_mode="acceptEdits",
            setting_sources=["project"]
        )
    
    def _get_agent_system_prompt(self) -> str:
        """Additional system prompt for P3394 agent identity"""
        return """
You are the IEEE 3394 Exemplar Agent. You demonstrate the P3394 standard through your actions.

When responding to users:
1. For questions about P3394, explain the standard clearly with examples
2. For technical questions, demonstrate capabilities rather than just describing them
3. Always structure responses as valid P3394 messages internally
4. Log all interactions to KSTAR memory for learning

Your capabilities include:
- Explaining and demonstrating P3394 message formats
- Generating static website content
- Creating documentation
- Running interactive demos
- Onboarding new developers to the standard

Remember: You ARE the documentation. Your behavior demonstrates the standard.
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
            description="About this agent and P3394",
            aliases=["/info"]
        ))
        
        self.register_command(SymbolicCommand(
            name="/listChannels",
            handler=self._cmd_list_channels,
            description="List active communication channels"
        ))
        
        self.register_command(SymbolicCommand(
            name="/listSkills",
            handler=self._cmd_list_skills,
            description="List acquired skills and capabilities"
        ))
        
        self.register_command(SymbolicCommand(
            name="/listSubAgents",
            handler=self._cmd_list_subagents,
            description="List available specialized subagents"
        ))
        
        self.register_command(SymbolicCommand(
            name="/listCommands",
            handler=self._cmd_list_commands,
            description="List all symbolic commands"
        ))
        
        self.register_command(SymbolicCommand(
            name="/startSession",
            handler=self._cmd_start_session,
            description="Start a new session",
            usage="/startSession [client_id]"
        ))
        
        self.register_command(SymbolicCommand(
            name="/endSession",
            handler=self._cmd_end_session,
            description="End current session",
            requires_auth=True
        ))
        
        self.register_command(SymbolicCommand(
            name="/identifyClientAgent",
            handler=self._cmd_identify_client,
            description="Identify connecting client agent",
            usage="/identifyClientAgent <agent_uri>"
        ))
        
        self.register_command(SymbolicCommand(
            name="/sendUMF",
            handler=self._cmd_send_umf,
            description="Send a P3394 Universal Message Format message",
            usage="/sendUMF <json_message>",
            requires_auth=True
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
    
    def register_channel(self, channel_id: str, adapter: "ChannelAdapter"):
        """Register a channel adapter"""
        self.channels[channel_id] = adapter
        logger.info(f"Registered channel: {channel_id}")
    
    # =========================================================================
    # MESSAGE ROUTING
    # =========================================================================
    
    async def route(self, message: P3394Message) -> MessageRoute:
        """Determine how to route an incoming message"""
        
        # Extract text content for routing decisions
        text = self._extract_text(message)
        
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
        if not self._claude_client:
            self._claude_client = ClaudeSDKClient(self.claude_options)
            await self._claude_client.connect()
        
        text = self._extract_text(message)
        
        # Add session context to prompt
        context_prompt = f"""
[Session: {session.id}]
[Channel: {message.source.channel_id if message.source else 'unknown'}]
[User: {session.client_id or 'anonymous'}]

{text}
"""
        
        await self._claude_client.query(context_prompt)
        
        response_text = ""
        async for msg in self._claude_client.receive_response():
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
        """Invoke a registered skill"""
        # Skills are handled by Claude with specific skill context
        # The skill trigger is detected, then we route to LLM with skill instructions
        text = self._extract_text(message)
        
        skill_name = None
        for pattern, name in self.skill_triggers.items():
            if pattern in text.lower():
                skill_name = name
                break
        
        if skill_name:
            # Prepend skill invocation instruction
            skill_prompt = f"[Invoke skill: {skill_name}]\n\n{text}"
            message.content = [P3394Content(type=ContentType.TEXT, data=skill_prompt)]
        
        return await self._handle_llm(message, session)
    
    async def _handle_subagent(self, message: P3394Message, session: Session) -> P3394Message:
        """Delegate to a specialized subagent"""
        # Use Claude's Task tool to spawn subagent
        text = self._extract_text(message)
        
        subagent_prompt = f"""
Use the Task tool to delegate this request to an appropriate specialized agent:

{text}

Available subagents:
- documentation-agent: For documentation tasks
- onboarding-agent: For helping new users
- demo-agent: For interactive demonstrations
"""
        message.content = [P3394Content(type=ContentType.TEXT, data=subagent_prompt)]
        return await self._handle_llm(message, session)
    
    # =========================================================================
    # SYMBOLIC COMMAND HANDLERS
    # =========================================================================
    
    async def _cmd_help(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /help command"""
        help_text = f"""
# {self.AGENT_NAME} v{self.AGENT_VERSION}

## Available Commands

| Command | Description |
|---------|-------------|
"""
        seen = set()
        for name, cmd in self.commands.items():
            if cmd.name not in seen:
                help_text += f"| `{cmd.name}` | {cmd.description} |\n"
                seen.add(cmd.name)
        
        help_text += """
## Capabilities

This agent can:
- Explain the IEEE P3394 standard
- Generate documentation and examples
- Run interactive demos
- Help you implement P3394 in your agents

Just send a message or use a command to get started!
"""
        return P3394Message.text(help_text, reply_to=message.id, session_id=session.id)
    
    async def _cmd_about(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /about command"""
        about_text = f"""
# About {self.AGENT_NAME}

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
Everything you see here demonstrates the standard in action:

- The web interface is a **Web Channel Adapter**
- The CLI is a **stdio Channel Adapter**
- All messages use **P3394 UMF** internally
- Agent state is stored in **KSTAR memory**

## Learn More

- Documentation: /docs
- Interactive Demo: /demo
- Source Code: https://github.com/ieee-sa/3394-exemplar-agent
"""
        return P3394Message.text(about_text, reply_to=message.id, session_id=session.id)
    
    async def _cmd_list_channels(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /listChannels command"""
        channels_info = "# Active Channels\n\n"
        
        for channel_id, adapter in self.channels.items():
            status = "🟢 Active" if adapter.is_active else "🔴 Inactive"
            channels_info += f"- **{channel_id}**: {adapter.__class__.__name__} ({status})\n"
        
        if not self.channels:
            channels_info += "_No channels registered_"
        
        return P3394Message.text(channels_info, reply_to=message.id, session_id=session.id)
    
    async def _cmd_list_skills(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /listSkills command"""
        skills = await self.memory.list_skills()
        
        skills_text = "# Acquired Skills\n\n"
        for skill in skills:
            skills_text += f"- **{skill.get('name', 'Unknown')}**: {skill.get('description', '')}\n"
        
        if not skills:
            skills_text += "_No skills acquired yet_"
        
        return P3394Message.text(skills_text, reply_to=message.id, session_id=session.id)
    
    async def _cmd_list_subagents(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /listSubAgents command"""
        subagents_text = """# Available SubAgents

| Agent | Description | Trigger |
|-------|-------------|---------|
| documentation-agent | Creates and maintains documentation | "document", "explain" |
| onboarding-agent | Helps new users get started | "help me start", "tutorial" |
| demo-agent | Runs interactive demonstrations | "demo", "show me" |
"""
        return P3394Message.text(subagents_text, reply_to=message.id, session_id=session.id)
    
    async def _cmd_list_commands(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /listCommands command"""
        return await self._cmd_help(message, session)
    
    async def _cmd_start_session(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /startSession command"""
        text = self._extract_text(message)
        parts = text.split()
        client_id = parts[1] if len(parts) > 1 else None
        
        new_session = await self.session_manager.create_session(client_id=client_id)
        
        response_text = f"""# Session Started

**Session ID:** `{new_session.id}`
**Client ID:** `{new_session.client_id or 'anonymous'}`
**Created:** {new_session.created_at}

Use this session ID for subsequent requests, or it will be associated automatically via your connection.
"""
        return P3394Message.text(response_text, reply_to=message.id, session_id=new_session.id)
    
    async def _cmd_end_session(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /endSession command"""
        await self.session_manager.end_session(session.id)
        
        return P3394Message.text(
            f"Session `{session.id}` ended. Goodbye!",
            reply_to=message.id
        )
    
    async def _cmd_identify_client(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /identifyClientAgent command"""
        text = self._extract_text(message)
        parts = text.split()
        
        if len(parts) < 2:
            return self._create_error_response(message, "Usage: /identifyClientAgent <agent_uri>")
        
        agent_uri = parts[1]
        
        # Parse and validate the agent URI
        # In a full implementation, this would verify the agent exists
        response_text = f"""# Client Agent Identified

**Agent URI:** `{agent_uri}`
**Session:** `{session.id}`

Client agent registered for this session. P3394 agent-to-agent communication enabled.
"""
        return P3394Message.text(response_text, reply_to=message.id, session_id=session.id)
    
    async def _cmd_send_umf(self, message: P3394Message, session: Session) -> P3394Message:
        """Handle /sendUMF command - send raw P3394 message"""
        text = self._extract_text(message)
        
        # Extract JSON from command
        json_start = text.find('{')
        if json_start == -1:
            return self._create_error_response(message, "Usage: /sendUMF <json_message>")
        
        import json
        try:
            umf_data = json.loads(text[json_start:])
            umf_message = P3394Message.from_dict(umf_data)
            
            # Process the UMF message
            response = await self.handle(umf_message)
            return response
            
        except json.JSONDecodeError as e:
            return self._create_error_response(message, f"Invalid JSON: {e}")
    
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
- Active: {len([c for c in self.channels.values() if c.is_active])}
- Total: {len(self.channels)}

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
    
    def _extract_text(self, message: P3394Message) -> str:
        """Extract text content from message"""
        for content in message.content:
            if content.type == ContentType.TEXT:
                return content.data
        return ""
    
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
    
    async def _log_response_to_kstar(self, request: P3394Message, response: P3394Message, session: Session):
        """Log response to KSTAR memory"""
        # Update the trace with result
        pass
    
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
```

### 3. Session Management

```python
# src/ieee3394_agent/core/session.py

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, Optional
from uuid import uuid4
import asyncio

@dataclass
class Session:
    """Represents a client session with the agent"""
    id: str = field(default_factory=lambda: str(uuid4()))
    client_id: Optional[str] = None
    client_agent_uri: Optional[str] = None
    channel_id: Optional[str] = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    last_activity: datetime = field(default_factory=datetime.utcnow)
    expires_at: Optional[datetime] = None
    is_authenticated: bool = False
    metadata: Dict = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at
    
    def touch(self):
        """Update last activity timestamp"""
        self.last_activity = datetime.utcnow()

class SessionManager:
    """Manages agent sessions"""
    
    DEFAULT_TTL = timedelta(hours=24)
    
    def __init__(self, default_ttl: timedelta = None):
        self.sessions: Dict[str, Session] = {}
        self.default_ttl = default_ttl or self.DEFAULT_TTL
        self._cleanup_task: Optional[asyncio.Task] = None
    
    @property
    def active_sessions(self) -> Dict[str, Session]:
        return {k: v for k, v in self.sessions.items() if not v.is_expired()}
    
    async def create_session(
        self,
        client_id: Optional[str] = None,
        channel_id: Optional[str] = None,
        ttl: Optional[timedelta] = None
    ) -> Session:
        """Create a new session"""
        ttl = ttl or self.default_ttl
        session = Session(
            client_id=client_id,
            channel_id=channel_id,
            expires_at=datetime.utcnow() + ttl
        )
        self.sessions[session.id] = session
        return session
    
    def get_session(self, session_id: str) -> Optional[Session]:
        """Get a session by ID"""
        session = self.sessions.get(session_id)
        if session and not session.is_expired():
            session.touch()
            return session
        return None
    
    async def end_session(self, session_id: str):
        """End a session"""
        if session_id in self.sessions:
            del self.sessions[session_id]
    
    async def cleanup_expired(self):
        """Remove expired sessions"""
        expired = [k for k, v in self.sessions.items() if v.is_expired()]
        for session_id in expired:
            del self.sessions[session_id]
```

### 4. Channel Adapters

```python
# src/ieee3394_agent/channels/base.py

from abc import ABC, abstractmethod
from typing import AsyncIterator, Optional
from ..core.umf import P3394Message
from ..core.gateway import AgentGateway

class ChannelAdapter(ABC):
    """
    Base class for P3394 channel adapters.
    
    A channel adapter transforms between a native protocol (HTTP, WebSocket, stdio, etc.)
    and P3394 UMF messages.
    """
    
    def __init__(self, gateway: AgentGateway, channel_id: str):
        self.gateway = gateway
        self.channel_id = channel_id
        self.is_active = False
    
    @abstractmethod
    async def start(self):
        """Start the channel"""
        pass
    
    @abstractmethod
    async def stop(self):
        """Stop the channel"""
        pass
    
    @abstractmethod
    async def send(self, message: P3394Message) -> None:
        """Send a message to the client"""
        pass
    
    @abstractmethod
    async def receive(self) -> AsyncIterator[P3394Message]:
        """Receive messages from the client"""
        pass
    
    def transform_inbound(self, native_message: any) -> P3394Message:
        """Transform native protocol message to P3394 UMF"""
        raise NotImplementedError
    
    def transform_outbound(self, message: P3394Message) -> any:
        """Transform P3394 UMF to native protocol message"""
        raise NotImplementedError
```

```python
# src/ieee3394_agent/channels/web.py

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse
from typing import Dict, Optional
import json
import logging

from .base import ChannelAdapter
from ..core.umf import P3394Message, P3394Content, ContentType, P3394Address
from ..core.gateway import AgentGateway

logger = logging.getLogger(__name__)

class WebChannelAdapter(ChannelAdapter):
    """
    Web channel adapter providing:
    - Static site serving (agent-generated pages)
    - REST API for symbolic commands
    - WebSocket for real-time chat
    """
    
    def __init__(
        self,
        gateway: AgentGateway,
        static_dir: str = "./static",
        templates_dir: str = "./templates",
        host: str = "0.0.0.0",
        port: int = 8000
    ):
        super().__init__(gateway, "web")
        self.static_dir = static_dir
        self.templates_dir = templates_dir
        self.host = host
        self.port = port
        
        self.app = FastAPI(
            title="IEEE 3394 Exemplar Agent",
            description="Reference implementation of IEEE P3394 Agent Interface Standard",
            version=gateway.AGENT_VERSION
        )
        self.templates = Jinja2Templates(directory=templates_dir)
        self.active_websockets: Dict[str, WebSocket] = {}
        
        self._setup_routes()
    
    def _setup_routes(self):
        """Setup all HTTP routes"""
        
        # Static files
        self.app.mount("/static", StaticFiles(directory=self.static_dir), name="static")
        
        # =====================================================================
        # HTML PAGES
        # =====================================================================
        
        @self.app.get("/", response_class=HTMLResponse)
        async def landing_page(request: Request):
            """Landing page"""
            return self.templates.TemplateResponse("landing.html", {
                "request": request,
                "agent_name": self.gateway.AGENT_NAME,
                "agent_version": self.gateway.AGENT_VERSION
            })
        
        @self.app.get("/chat", response_class=HTMLResponse)
        async def chat_page(request: Request):
            """Chat interface"""
            return self.templates.TemplateResponse("chat.html", {
                "request": request,
                "agent_name": self.gateway.AGENT_NAME
            })
        
        @self.app.get("/docs", response_class=HTMLResponse)
        async def docs_page(request: Request):
            """Documentation page"""
            return self.templates.TemplateResponse("docs.html", {
                "request": request,
                "agent_name": self.gateway.AGENT_NAME
            })
        
        # =====================================================================
        # REST API - SYMBOLIC COMMANDS
        # =====================================================================
        
        @self.app.get("/api/help")
        async def api_help():
            """Get help information"""
            message = P3394Message.text("/help")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/about")
        async def api_about():
            """Get about information"""
            message = P3394Message.text("/about")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/status")
        async def api_status():
            """Get agent status"""
            message = P3394Message.text("/status")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/version")
        async def api_version():
            """Get version"""
            return {
                "agent_id": self.gateway.AGENT_ID,
                "name": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "standard": "IEEE P3394"
            }
        
        @self.app.get("/api/channels")
        async def api_channels():
            """List channels"""
            message = P3394Message.text("/listChannels")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/skills")
        async def api_skills():
            """List skills"""
            message = P3394Message.text("/listSkills")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/subagents")
        async def api_subagents():
            """List subagents"""
            message = P3394Message.text("/listSubAgents")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.get("/api/commands")
        async def api_commands():
            """List commands"""
            commands = []
            seen = set()
            for name, cmd in self.gateway.commands.items():
                if cmd.name not in seen:
                    commands.append({
                        "name": cmd.name,
                        "description": cmd.description,
                        "usage": cmd.usage,
                        "requires_auth": cmd.requires_auth,
                        "aliases": cmd.aliases
                    })
                    seen.add(cmd.name)
            return {"commands": commands}
        
        # =====================================================================
        # REST API - SESSION MANAGEMENT
        # =====================================================================
        
        @self.app.post("/api/session/start")
        async def api_start_session(client_id: Optional[str] = None):
            """Start a new session"""
            session = await self.gateway.session_manager.create_session(
                client_id=client_id,
                channel_id="web"
            )
            return {
                "session_id": session.id,
                "client_id": session.client_id,
                "expires_at": session.expires_at.isoformat() if session.expires_at else None
            }
        
        @self.app.post("/api/session/{session_id}/end")
        async def api_end_session(session_id: str):
            """End a session"""
            await self.gateway.session_manager.end_session(session_id)
            return {"status": "ended", "session_id": session_id}
        
        # =====================================================================
        # REST API - MESSAGE SENDING
        # =====================================================================
        
        @self.app.post("/api/message")
        async def api_send_message(
            text: str,
            session_id: Optional[str] = None
        ):
            """Send a text message"""
            message = P3394Message.text(text, session_id=session_id)
            response = await self.gateway.handle(message)
            return self._format_api_response(response)
        
        @self.app.post("/api/umf")
        async def api_send_umf(umf: dict):
            """Send a raw P3394 UMF message"""
            message = P3394Message.from_dict(umf)
            response = await self.gateway.handle(message)
            return response.to_dict()
        
        # =====================================================================
        # WEBSOCKET - REAL-TIME CHAT
        # =====================================================================
        
        @self.app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            """WebSocket endpoint for real-time chat"""
            await websocket.accept()
            
            # Create session for this connection
            session = await self.gateway.session_manager.create_session(channel_id="web-ws")
            self.active_websockets[session.id] = websocket
            
            try:
                # Send welcome message
                welcome = P3394Message.text(
                    f"Connected to {self.gateway.AGENT_NAME}. Session: {session.id}\nType /help for commands.",
                    session_id=session.id
                )
                await websocket.send_json(welcome.to_dict())
                
                # Message loop
                while True:
                    data = await websocket.receive_json()
                    
                    # Transform to P3394 message
                    if isinstance(data, str):
                        message = P3394Message.text(data, session_id=session.id)
                    else:
                        message = P3394Message.from_dict(data)
                        message.session_id = session.id
                    
                    # Handle message
                    response = await self.gateway.handle(message)
                    
                    # Send response
                    await websocket.send_json(response.to_dict())
                    
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnected: {session.id}")
            except Exception as e:
                logger.exception(f"WebSocket error: {e}")
            finally:
                if session.id in self.active_websockets:
                    del self.active_websockets[session.id]
                await self.gateway.session_manager.end_session(session.id)
    
    def _format_api_response(self, message: P3394Message) -> dict:
        """Format P3394 message as API response"""
        # Extract primary content
        content = None
        for c in message.content:
            if c.type == ContentType.TEXT:
                content = c.data
                break
            elif c.type == ContentType.JSON:
                content = c.data
                break
        
        return {
            "message_id": message.id,
            "type": message.type.value,
            "content": content,
            "session_id": message.session_id,
            "timestamp": message.timestamp
        }
    
    async def start(self):
        """Start the web server"""
        import uvicorn
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)
        
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()
    
    async def stop(self):
        """Stop the web server"""
        self.is_active = False
        # Close all websockets
        for ws in self.active_websockets.values():
            await ws.close()
        self.active_websockets.clear()
    
    async def send(self, message: P3394Message) -> None:
        """Send message to connected clients"""
        if message.session_id and message.session_id in self.active_websockets:
            ws = self.active_websockets[message.session_id]
            await ws.send_json(message.to_dict())
    
    async def receive(self):
        """Not used - messages come through HTTP/WebSocket handlers"""
        pass
```

```python
# src/ieee3394_agent/channels/cli.py

import asyncio
import sys
from typing import Optional

from .base import ChannelAdapter
from ..core.umf import P3394Message, ContentType
from ..core.gateway import AgentGateway

class CLIChannelAdapter(ChannelAdapter):
    """
    CLI channel adapter for terminal interaction.
    Useful for development and testing.
    """
    
    def __init__(self, gateway: AgentGateway):
        super().__init__(gateway, "cli")
        self.session_id: Optional[str] = None
    
    async def start(self):
        """Start the CLI REPL"""
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)
        
        # Create session
        session = await self.gateway.session_manager.create_session(channel_id="cli")
        self.session_id = session.id
        
        # Print banner
        self._print_banner()
        
        # REPL loop
        while self.is_active:
            try:
                user_input = await self._async_input(">>> ")
                
                if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                    print("Goodbye!")
                    break
                
                if not user_input.strip():
                    continue
                
                # Create message
                message = P3394Message.text(user_input, session_id=self.session_id)
                
                # Handle message
                response = await self.gateway.handle(message)
                
                # Display response
                self._display_response(response)
                
            except KeyboardInterrupt:
                print("\nUse 'exit' or '/exit' to quit")
            except EOFError:
                break
            except Exception as e:
                print(f"Error: {e}")
        
        await self.gateway.session_manager.end_session(self.session_id)
        self.is_active = False
    
    async def stop(self):
        """Stop the CLI"""
        self.is_active = False
    
    async def send(self, message: P3394Message) -> None:
        """Send message to terminal"""
        self._display_response(message)
    
    async def receive(self):
        """Not used - input comes from REPL loop"""
        pass
    
    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║                 IEEE 3394 Exemplar Agent                     ║
║                      CLI Channel                             ║
╠══════════════════════════════════════════════════════════════╣
║  Version: {self.gateway.AGENT_VERSION:<15}                              ║
║  Session: {self.session_id[:20]}...                        ║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                     ║
║  Type 'exit' to quit                                         ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)
    
    def _display_response(self, message: P3394Message):
        """Display a response message"""
        print()  # Blank line before response
        
        for content in message.content:
            if content.type == ContentType.TEXT:
                print(content.data)
            elif content.type == ContentType.JSON:
                import json
                print(json.dumps(content.data, indent=2))
            elif content.type == ContentType.MARKDOWN:
                # Could use rich library for better rendering
                print(content.data)
        
        print()  # Blank line after response
    
    async def _async_input(self, prompt: str) -> str:
        """Async-compatible input"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt))
```

### 5. P3394 Hooks (KSTAR Integration)

```python
# src/ieee3394_agent/plugins/hooks.py

from claude_agent_sdk import HookMatcher, HookContext
from typing import Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

# Global reference to KSTAR memory (set during initialization)
_kstar_memory = None

def set_kstar_memory(memory):
    """Set the KSTAR memory instance for hooks"""
    global _kstar_memory
    _kstar_memory = memory

async def kstar_pre_tool_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> Dict[str, Any]:
    """
    Pre-tool hook that logs to KSTAR memory.
    
    This implements the T→A transition in the KSTAR cognitive cycle:
    - Task has been determined
    - Action is about to be executed
    """
    if not _kstar_memory:
        return {}
    
    tool_name = input_data.get('tool_name', 'unknown')
    tool_input = input_data.get('tool_input', {})
    
    logger.debug(f"Pre-tool hook: {tool_name}")
    
    try:
        await _kstar_memory.store_trace({
            "situation": {
                "domain": "ieee3394_agent",
                "actor": "agent",
                "protocol": "claude_agent_sdk",
                "now": datetime.utcnow().isoformat()
            },
            "task": {
                "goal": f"Execute tool: {tool_name}",
                "constraints": [],
                "success_criteria": ["Tool executes without error"]
            },
            "action": {
                "type": tool_name,
                "parameters": tool_input,
                "skill_used": f"builtin:{tool_name}"
            },
            "mode": "performance",
            "session_id": input_data.get('session_id', 'unknown'),
            "tags": ["tool_use", tool_name]
        })
    except Exception as e:
        logger.warning(f"Failed to log to KSTAR: {e}")
    
    return {}

async def kstar_post_tool_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> Dict[str, Any]:
    """
    Post-tool hook that records results to KSTAR.
    
    This implements the A→R transition in the KSTAR cognitive cycle:
    - Action has been executed
    - Result is being recorded
    """
    if not _kstar_memory:
        return {}
    
    tool_name = input_data.get('tool_name', 'unknown')
    tool_response = input_data.get('tool_response', None)
    is_error = input_data.get('is_error', False)
    
    logger.debug(f"Post-tool hook: {tool_name}, error={is_error}")
    
    try:
        # Store perception about the result
        await _kstar_memory.store_perception({
            "content": f"Tool {tool_name} {'failed' if is_error else 'succeeded'}",
            "context": {
                "domain": "ieee3394_agent",
                "source": "tool_execution",
                "confidence": 1.0
            },
            "tags": ["tool_result", tool_name],
            "importance": 0.5 if not is_error else 0.8
        })
    except Exception as e:
        logger.warning(f"Failed to log result to KSTAR: {e}")
    
    return {}

async def p3394_compliance_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> Dict[str, Any]:
    """
    Hook that ensures P3394 compliance in all operations.
    
    - Validates message formats
    - Ensures proper addressing
    - Logs compliance events
    """
    # For now, just pass through
    # In production, this would validate P3394 requirements
    return {}

async def security_audit_hook(
    input_data: Dict[str, Any],
    tool_use_id: str | None,
    context: HookContext
) -> Dict[str, Any]:
    """
    Security audit hook for sensitive operations.
    """
    tool_name = input_data.get('tool_name', '')
    tool_input = input_data.get('tool_input', {})
    
    # Block dangerous operations
    if tool_name == 'Bash':
        command = tool_input.get('command', '')
        dangerous_patterns = ['rm -rf /', 'sudo rm', ':(){:|:&};:']
        
        for pattern in dangerous_patterns:
            if pattern in command:
                logger.warning(f"Blocked dangerous command: {command}")
                return {
                    'hookSpecificOutput': {
                        'hookEventName': 'PreToolUse',
                        'permissionDecision': 'deny',
                        'permissionDecisionReason': f'Dangerous command pattern detected: {pattern}'
                    }
                }
    
    return {}

# Hook configuration for Claude Agent SDK
P3394_HOOKS = {
    'PreToolUse': [
        HookMatcher(hooks=[kstar_pre_tool_hook, p3394_compliance_hook]),
        HookMatcher(matcher='Bash', hooks=[security_audit_hook])
    ],
    'PostToolUse': [
        HookMatcher(hooks=[kstar_post_tool_hook])
    ]
}
```

### 6. KSTAR Memory Integration

```python
# src/ieee3394_agent/memory/kstar.py

from typing import Any, Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class KStarMemory:
    """
    KSTAR Memory integration for the IEEE 3394 Agent.
    
    This wraps the KSTAR MCP server or provides a local implementation.
    
    KSTAR = Knowledge, Situation, Task, Action, Result
    - A universal representation schema for agent memory
    - Stores traces (episodes), skills, perceptions, and tokens
    """
    
    def __init__(self, mcp_client=None, local_db_path: str = None):
        """
        Initialize KSTAR memory.
        
        Args:
            mcp_client: MCP client connected to KSTAR server
            local_db_path: Path for local SQLite fallback
        """
        self.mcp = mcp_client
        self.local_db_path = local_db_path
        self._local_db = None
        
        if not mcp_client and local_db_path:
            self._init_local_db()
    
    def _init_local_db(self):
        """Initialize local SQLite database"""
        import sqlite3
        self._local_db = sqlite3.connect(self.local_db_path)
        # Create tables...
    
    async def store_trace(self, trace: Dict[str, Any]) -> str:
        """
        Store a KSTAR trace (episode).
        
        A trace represents a complete K→S→T→A→R cycle.
        """
        if self.mcp:
            result = await self.mcp.call_tool("kstar_store_trace", trace)
            return result.get("id")
        else:
            # Local implementation
            return self._store_trace_local(trace)
    
    async def store_perception(self, perception: Dict[str, Any]) -> str:
        """
        Store a perception (fact/observation).
        
        Perceptions are declarative knowledge without action plans.
        """
        if self.mcp:
            result = await self.mcp.call_tool("kstar_store_perception", perception)
            return result.get("id")
        else:
            return self._store_perception_local(perception)
    
    async def store_skill(self, skill: Dict[str, Any]) -> str:
        """
        Store a skill definition.
        """
        if self.mcp:
            result = await self.mcp.call_tool("kstar_store_skill", skill)
            return result.get("id")
        else:
            return self._store_skill_local(skill)
    
    async def query(self, domain: str, goal: str) -> Optional[Dict[str, Any]]:
        """
        Query KSTAR memory for matching traces and skills.
        """
        if self.mcp:
            return await self.mcp.call_tool("kstar_query", {
                "domain": domain,
                "goal": goal
            })
        else:
            return self._query_local(domain, goal)
    
    async def find_skills(self, domain: str, goal: str) -> List[Dict[str, Any]]:
        """
        Find skills capable of handling a task.
        """
        if self.mcp:
            result = await self.mcp.call_tool("kstar_find_skills", {
                "domain": domain,
                "goal": goal
            })
            return result.get("skills", [])
        else:
            return self._find_skills_local(domain, goal)
    
    async def list_skills(self) -> List[Dict[str, Any]]:
        """
        List all stored skills.
        """
        if self.mcp:
            result = await self.mcp.call_tool("kstar_list_skills", {})
            return result.get("skills", [])
        else:
            return self._list_skills_local()
    
    async def get_stats(self) -> Dict[str, Any]:
        """
        Get storage statistics.
        """
        if self.mcp:
            return await self.mcp.call_tool("kstar_stats", {})
        else:
            return self._get_stats_local()
    
    # Local implementation methods (fallback when no MCP server)
    
    def _store_trace_local(self, trace: Dict) -> str:
        # SQLite implementation
        pass
    
    def _store_perception_local(self, perception: Dict) -> str:
        pass
    
    def _store_skill_local(self, skill: Dict) -> str:
        pass
    
    def _query_local(self, domain: str, goal: str) -> Optional[Dict]:
        pass
    
    def _find_skills_local(self, domain: str, goal: str) -> List[Dict]:
        pass
    
    def _list_skills_local(self) -> List[Dict]:
        pass
    
    def _get_stats_local(self) -> Dict:
        pass
```

### 7. Entry Point

```python
# src/ieee3394_agent/__main__.py

import asyncio
import argparse
import logging
from pathlib import Path

from .core.gateway import AgentGateway
from .core.config import Config
from .memory.kstar import KStarMemory
from .channels.web import WebChannelAdapter
from .channels.cli import CLIChannelAdapter
from .plugins.hooks import set_kstar_memory

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

async def main():
    parser = argparse.ArgumentParser(
        description="IEEE 3394 Exemplar Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start web server
  python -m ieee3394_agent --channel web --port 8000
  
  # Start CLI
  python -m ieee3394_agent --channel cli
  
  # Start both
  python -m ieee3394_agent --channel web --channel cli
"""
    )
    
    parser.add_argument(
        '--channel', '-c',
        action='append',
        choices=['web', 'cli'],
        default=[],
        help='Channels to start (can be specified multiple times)'
    )
    
    parser.add_argument(
        '--port', '-p',
        type=int,
        default=8000,
        help='Port for web channel (default: 8000)'
    )
    
    parser.add_argument(
        '--host',
        default='0.0.0.0',
        help='Host for web channel (default: 0.0.0.0)'
    )
    
    parser.add_argument(
        '--static-dir',
        default='./static',
        help='Directory for static files'
    )
    
    parser.add_argument(
        '--kstar-db',
        default='./kstar.db',
        help='Path to KSTAR SQLite database'
    )
    
    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )
    
    args = parser.parse_args()
    
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Default to CLI if no channel specified
    if not args.channels:
        args.channels = ['cli']
    
    # Initialize KSTAR memory
    kstar = KStarMemory(local_db_path=args.kstar_db)
    set_kstar_memory(kstar)
    
    # Initialize gateway
    gateway = AgentGateway(kstar_memory=kstar)
    
    # Start channels
    tasks = []
    
    if 'web' in args.channels:
        web_channel = WebChannelAdapter(
            gateway=gateway,
            static_dir=args.static_dir,
            host=args.host,
            port=args.port
        )
        tasks.append(web_channel.start())
        logger.info(f"Starting web channel on http://{args.host}:{args.port}")
    
    if 'cli' in args.channels:
        cli_channel = CLIChannelAdapter(gateway=gateway)
        tasks.append(cli_channel.start())
        logger.info("Starting CLI channel")
    
    # Run all channels
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    asyncio.run(main())
```

---

## Static Site Templates

Create these Jinja2 templates for the web channel:

### templates/base.html

```html
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{% block title %}{{ agent_name }}{% endblock %}</title>
    <link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">
    <link rel="stylesheet" href="/static/assets/css/style.css">
    {% block head %}{% endblock %}
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <a href="/" class="text-xl font-bold text-blue-600">{{ agent_name }}</a>
            <div class="space-x-4">
                <a href="/docs" class="text-gray-600 hover:text-blue-600">Documentation</a>
                <a href="/chat" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Chat</a>
            </div>
        </div>
    </nav>
    
    <main>
        {% block content %}{% endblock %}
    </main>
    
    <footer class="bg-gray-800 text-white py-8 mt-16">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p>IEEE P3394 Standard for Agent Interfaces</p>
            <p class="text-gray-400 text-sm mt-2">{{ agent_name }} v{{ agent_version }}</p>
        </div>
    </footer>
    
    {% block scripts %}{% endblock %}
</body>
</html>
```

### templates/landing.html

```html
{% extends "base.html" %}

{% block content %}
<div class="max-w-7xl mx-auto px-4 py-16">
    <!-- Hero -->
    <div class="text-center mb-16">
        <h1 class="text-5xl font-bold text-gray-900 mb-4">
            IEEE P3394
        </h1>
        <p class="text-xl text-gray-600 mb-8">
            The Standard for Agent Interoperability
        </p>
        <div class="space-x-4">
            <a href="/chat" class="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg hover:bg-blue-700">
                Try the Agent
            </a>
            <a href="/docs" class="border border-gray-300 px-8 py-3 rounded-lg text-lg hover:border-blue-600">
                Read the Docs
            </a>
        </div>
    </div>
    
    <!-- Features -->
    <div class="grid md:grid-cols-3 gap-8 mb-16">
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-xl font-semibold mb-2">Universal Message Format</h3>
            <p class="text-gray-600">
                One message format for all agent communication. 
                Compatible with any transport protocol.
            </p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-xl font-semibold mb-2">Channel Abstraction</h3>
            <p class="text-gray-600">
                Same agent, multiple interfaces. Web, CLI, API, 
                agent-to-agent—all through unified channels.
            </p>
        </div>
        <div class="bg-white p-6 rounded-lg shadow">
            <h3 class="text-xl font-semibold mb-2">Capability Discovery</h3>
            <p class="text-gray-600">
                Agents discover each other's capabilities automatically.
                No manual configuration needed.
            </p>
        </div>
    </div>
    
    <!-- This Agent -->
    <div class="bg-blue-50 rounded-lg p-8 text-center">
        <h2 class="text-2xl font-bold mb-4">This Site IS the Agent</h2>
        <p class="text-gray-700 mb-4">
            Everything you see here is generated and served by an IEEE P3394 compliant agent.
            The agent demonstrates the standard through its own operation.
        </p>
        <code class="bg-gray-800 text-green-400 px-4 py-2 rounded inline-block">
            p3394://ieee3394-exemplar/web
        </code>
    </div>
</div>
{% endblock %}
```

### templates/chat.html

```html
{% extends "base.html" %}

{% block title %}Chat - {{ agent_name }}{% endblock %}

{% block content %}
<div class="flex h-[calc(100vh-140px)]">
    <!-- Sidebar -->
    <div class="w-64 bg-white border-r p-4 hidden md:block">
        <h3 class="font-semibold mb-4">Commands</h3>
        <ul class="space-y-2 text-sm" id="commands-list">
            <li><code class="text-blue-600">/help</code> - Get help</li>
            <li><code class="text-blue-600">/about</code> - About agent</li>
            <li><code class="text-blue-600">/status</code> - Agent status</li>
            <li><code class="text-blue-600">/listSkills</code> - List skills</li>
        </ul>
    </div>
    
    <!-- Chat Area -->
    <div class="flex-1 flex flex-col">
        <!-- Messages -->
        <div class="flex-1 overflow-y-auto p-4 space-y-4" id="messages">
            <!-- Messages will be inserted here -->
        </div>
        
        <!-- Input -->
        <div class="border-t p-4">
            <form id="chat-form" class="flex space-x-2">
                <input 
                    type="text" 
                    id="message-input"
                    class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-600"
                    placeholder="Type a message or /command..."
                    autocomplete="off"
                >
                <button 
                    type="submit"
                    class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700"
                >
                    Send
                </button>
            </form>
        </div>
    </div>
</div>
{% endblock %}

{% block scripts %}
<script>
const messagesContainer = document.getElementById('messages');
const chatForm = document.getElementById('chat-form');
const messageInput = document.getElementById('message-input');

let ws = null;
let sessionId = null;

function connect() {
    ws = new WebSocket(`ws://${window.location.host}/ws/chat`);
    
    ws.onopen = () => {
        console.log('Connected to agent');
    };
    
    ws.onmessage = (event) => {
        const message = JSON.parse(event.data);
        displayMessage(message, 'agent');
        
        if (message.session_id) {
            sessionId = message.session_id;
        }
    };
    
    ws.onclose = () => {
        console.log('Disconnected');
        setTimeout(connect, 3000);
    };
    
    ws.onerror = (error) => {
        console.error('WebSocket error:', error);
    };
}

function displayMessage(message, sender) {
    const div = document.createElement('div');
    div.className = sender === 'user' 
        ? 'flex justify-end' 
        : 'flex justify-start';
    
    const content = message.content?.[0]?.data || message;
    const bubble = document.createElement('div');
    bubble.className = sender === 'user'
        ? 'bg-blue-600 text-white rounded-lg px-4 py-2 max-w-2xl'
        : 'bg-gray-100 rounded-lg px-4 py-2 max-w-2xl prose';
    
    // Simple markdown rendering for agent messages
    if (sender === 'agent' && typeof content === 'string') {
        bubble.innerHTML = content
            .replace(/^### (.*$)/gim, '<h3>$1</h3>')
            .replace(/^## (.*$)/gim, '<h2>$1</h2>')
            .replace(/^# (.*$)/gim, '<h1>$1</h1>')
            .replace(/\*\*(.*)\*\*/gim, '<strong>$1</strong>')
            .replace(/\*(.*)\*/gim, '<em>$1</em>')
            .replace(/`([^`]+)`/gim, '<code>$1</code>')
            .replace(/\n/gim, '<br>');
    } else {
        bubble.textContent = typeof content === 'string' ? content : JSON.stringify(content);
    }
    
    div.appendChild(bubble);
    messagesContainer.appendChild(div);
    messagesContainer.scrollTop = messagesContainer.scrollHeight;
}

chatForm.addEventListener('submit', (e) => {
    e.preventDefault();
    
    const text = messageInput.value.trim();
    if (!text) return;
    
    displayMessage(text, 'user');
    
    if (ws && ws.readyState === WebSocket.OPEN) {
        ws.send(JSON.stringify({
            type: 'request',
            content: [{ type: 'text', data: text }],
            session_id: sessionId
        }));
    }
    
    messageInput.value = '';
});

connect();
</script>
{% endblock %}
```

---

## Configuration Files

### pyproject.toml

```toml
[project]
name = "ieee3394-agent"
version = "0.1.0"
description = "IEEE P3394 Exemplar Agent - Reference implementation of the Agent Interface Standard"
readme = "README.md"
requires-python = ">=3.10"
license = {text = "MIT"}
authors = [
    {name = "IEEE 3394 Working Group"}
]
keywords = ["agent", "ai", "ieee", "p3394", "llm"]

dependencies = [
    "claude-agent-sdk>=0.1.20",
    "fastapi>=0.109.0",
    "uvicorn>=0.27.0",
    "websockets>=12.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.6",
    "anyio>=4.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.23.0",
    "httpx>=0.26.0",
    "ruff>=0.1.0",
    "mypy>=1.8.0",
]

[project.scripts]
ieee3394-agent = "ieee3394_agent.__main__:main"

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.ruff]
line-length = 100
target-version = "py310"

[tool.mypy]
python_version = "3.10"
strict = true
```

### .claude/settings.json

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Write",
      "Edit",
      "Bash",
      "Glob",
      "Grep",
      "WebSearch",
      "WebFetch",
      "Task"
    ]
  },
  "environment": {
    "AGENT_ENV": "development"
  }
}
```

---

## Subagent Definitions

### .claude/agents/documentation-agent.md

```markdown
# Documentation Agent

You are a specialized documentation agent for the IEEE P3394 Exemplar Agent.

## Role
Generate and maintain documentation for the P3394 standard and this agent implementation.

## Capabilities
- Generate API documentation
- Create tutorials and guides
- Update README files
- Generate code examples

## Constraints
- Only modify files in /docs and /static/docs directories
- Follow the P3394 documentation style guide
- Include code examples for all concepts
```

### .claude/agents/onboarding-agent.md

```markdown
# Onboarding Agent

You are a specialized onboarding agent that helps new users understand and use the IEEE P3394 standard.

## Role
Guide new users through:
1. Understanding what P3394 is
2. Why agent interoperability matters
3. How to implement P3394 in their own agents
4. Using this exemplar agent as reference

## Style
- Be friendly and encouraging
- Use analogies to explain complex concepts
- Provide hands-on examples
- Ask clarifying questions

## Resources
- /docs/getting-started.md
- /docs/concepts/
- /static/demo/
```

### .claude/agents/demo-agent.md

```markdown
# Demo Agent

You are a specialized demonstration agent that creates interactive demos of P3394 capabilities.

## Role
Create and run interactive demonstrations showing:
1. P3394 message format in action
2. Channel abstraction
3. Capability discovery
4. Agent-to-agent communication

## Capabilities
- Generate demo HTML pages
- Create interactive code examples
- Simulate multi-agent scenarios
- Visualize message flows

## Constraints
- Demos must be self-contained
- Include clear explanations
- Show both success and error cases
```

---

## Skills

### .claude/skills/site-generator/SKILL.md

```markdown
# Static Site Generator

Generate static HTML pages for the IEEE 3394 agent web channel.

## Triggers
- "generate site"
- "update website"
- "rebuild static pages"

## Process

1. Read current agent state:
   - List all skills
   - List all commands
   - Get agent metadata

2. Generate pages:
   - Landing page (index.html)
   - Documentation pages
   - Demo pages

3. Write to ./static directory

4. Update site manifest

## Templates

Use Jinja2 templates from ./templates/

## Output

Static HTML files in ./static/
```

### .claude/skills/p3394-explainer/SKILL.md

```markdown
# P3394 Explainer

Explain P3394 concepts clearly with examples.

## Triggers
- "explain P3394"
- "what is UMF"
- "how do channels work"

## Knowledge Base

### Core Concepts

1. **Universal Message Format (UMF)**
   - Standard message structure
   - Content blocks
   - Addressing

2. **Channel Adapters**
   - Transform native protocols to UMF
   - Examples: Web, CLI, MCP

3. **Capability Discovery**
   - /listSkills
   - /listCommands
   - Agent manifests

### Examples

Always include concrete code examples.
```

---

## Development Workflow

1. **Initial Setup**
   ```bash
   # Clone/create the project
   mkdir ieee3394-agent && cd ieee3394-agent
   
   # Create virtual environment
   python -m venv venv
   source venv/bin/activate
   
   # Install dependencies
   pip install -e ".[dev]"
   ```

2. **Run Development Server**
   ```bash
   # CLI only
   python -m ieee3394_agent --channel cli
   
   # Web only
   python -m ieee3394_agent --channel web --port 8000
   
   # Both
   python -m ieee3394_agent --channel cli --channel web
   ```

3. **Generate Static Site**
   ```bash
   # Using the agent itself
   python -m ieee3394_agent --channel cli
   >>> generate the static site for ieee3394.org
   ```

4. **Test**
   ```bash
   pytest tests/
   ```

---

## Key Design Decisions

1. **Two-tier message routing**: Symbolic commands execute without LLM (fast, deterministic), while semantic messages route through Claude (flexible, intelligent).

2. **P3394 UMF as internal lingua franca**: All channel adapters transform to/from UMF. This ensures consistency and enables channel-agnostic logic.

3. **KSTAR memory for learning**: Every interaction is logged as a KSTAR trace, enabling the agent to learn and improve over time.

4. **Hooks for extensibility**: P3394 compliance, KSTAR logging, and security are implemented as hooks that can be composed and extended.

5. **Static site as agent artifact**: The website content is generated BY the agent, demonstrating that the agent's capabilities ARE the documentation.

---

## Success Criteria

1. **Functional Web Channel**: Users can access ieee3394.org and interact with the agent via chat and API.

2. **Functional CLI Channel**: Developers can interact via terminal for testing and development.

3. **P3394 Compliance**: All messages conform to UMF, all commands follow the standard interface.

4. **Self-Documenting**: The /help, /about, /listSkills commands provide accurate, live documentation.

5. **KSTAR Integration**: All interactions are logged to KSTAR memory for learning.

6. **Extensible**: New channels, skills, and subagents can be added without modifying core code.

---

## Notes for Implementation

- Start with the core Gateway and UMF classes
- Implement CLI channel first (easier to test)
- Add Web channel with basic static pages
- Integrate KSTAR memory (can use local SQLite initially)
- Add hooks for logging and compliance
- Generate initial static site content
- Test all symbolic commands
- Test LLM routing
- Deploy to ieee3394.org

This agent is a living demonstration of the IEEE P3394 standard. Every feature, every message, every interaction should exemplify the standard in action.
