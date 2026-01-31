"""
Base Channel Adapter

Abstract base class for all P3394 channel adapters.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType


@dataclass
class ChannelCapabilities:
    """
    Defines what a channel adapter can handle.

    Used for content negotiation and adaptation.
    """
    # Supported content types
    content_types: List[ContentType] = field(default_factory=lambda: [ContentType.TEXT])

    # Size limits
    max_message_size: int = 4096  # bytes
    max_attachment_size: int = 10 * 1024 * 1024  # 10 MB

    # Feature support
    supports_streaming: bool = False
    supports_attachments: bool = False
    supports_images: bool = False
    supports_folders: bool = False
    supports_multipart: bool = False  # Can send multiple messages
    supports_markdown: bool = False
    supports_html: bool = False

    # Channel-specific limits
    max_concurrent_connections: int = 100
    rate_limit_per_minute: int = 60

    # Command routing
    command_prefix: str = "/"  # How commands start in this channel
    supports_slash_commands: bool = True  # /command syntax
    supports_cli_flags: bool = False  # --command syntax
    supports_http_endpoints: bool = False  # GET /command
    supports_mentions: bool = False  # @agent command


class ChannelAdapter(ABC):
    """
    Base class for P3394 channel adapters.

    A channel adapter:
    1. Authenticates clients on the channel
    2. Transforms native protocol ↔ P3394 UMF
    3. Adapts content based on channel capabilities
    4. Routes responses back to clients
    5. Maps channel-specific command syntax
    """

    def __init__(self, gateway: "AgentGateway", channel_id: str):
        self.gateway = gateway
        self.channel_id = channel_id
        self.is_active = False

    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """Return the capabilities of this channel"""
        pass

    @abstractmethod
    def authenticate_client(self, context: Dict[str, Any]) -> "ClientPrincipalAssertion":
        """
        Authenticate a client on this channel.

        Each channel implements its own authentication logic:
        - CLI: Extract OS user from environment
        - WhatsApp: Extract phone number from sender ID
        - P3394 Server: Extract P3394Address from headers

        Args:
            context: Channel-specific authentication context

        Returns:
            ClientPrincipalAssertion with channel identity and assurance level
        """
        pass

    def create_client_assertion(
        self,
        channel_identity: str,
        assurance_level: "AssuranceLevel",
        authentication_method: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "ClientPrincipalAssertion":
        """
        Helper to create a ClientPrincipalAssertion.

        Args:
            channel_identity: Channel-specific identity (phone, email, username, etc.)
            assurance_level: Confidence in identity assertion
            authentication_method: How identity was verified
            metadata: Additional context

        Returns:
            ClientPrincipalAssertion ready to embed in message metadata
        """
        from ..core.auth.principal import ClientPrincipalAssertion

        return ClientPrincipalAssertion(
            channel_id=self.channel_id,
            channel_identity=channel_identity,
            assurance_level=assurance_level,
            authentication_method=authentication_method,
            metadata=metadata or {}
        )

    def get_endpoints(self) -> Dict[str, str]:
        """
        Get channel-specific endpoints for symbolic commands.

        Maps canonical command names to channel-specific syntax.

        Returns:
            {
                "help": "/help",  # or "--help" or "GET /help"
                "about": "/about",
                "version": "/version",
                ...
            }
        """
        endpoints = {}

        # Get all registered commands from gateway
        if hasattr(self, 'gateway') and hasattr(self.gateway, 'commands'):
            for cmd_name in set(cmd.name for cmd in self.gateway.commands.values()):
                # Map to channel-specific syntax
                endpoints[cmd_name.lstrip('/')] = self._map_command_syntax(cmd_name)

        return endpoints

    def _map_command_syntax(self, canonical_command: str) -> str:
        """
        Map canonical command (e.g., "/help") to channel-specific syntax.

        Args:
            canonical_command: Standard P3394 command (e.g., "/help")

        Returns:
            Channel-specific command syntax
        """
        cmd_name = canonical_command.lstrip('/')

        if self.capabilities.supports_cli_flags:
            # CLI flags: --help
            return f"--{cmd_name}"

        elif self.capabilities.supports_http_endpoints:
            # HTTP endpoints: GET /help
            return f"/{cmd_name}"

        elif self.capabilities.supports_slash_commands:
            # Slash commands: /help (default)
            return f"/{cmd_name}"

        else:
            # Plain text
            return cmd_name

    def normalize_command(self, raw_input: str) -> str:
        """
        Normalize channel-specific command syntax to canonical form.

        Args:
            raw_input: Channel-specific input (e.g., "--help", "/help", "help")

        Returns:
            Canonical command format (e.g., "/help")
        """
        raw_input = raw_input.strip()

        # CLI flags: --help → /help
        if raw_input.startswith('--'):
            return '/' + raw_input[2:]

        # Already slash command: /help → /help
        if raw_input.startswith('/'):
            return raw_input

        # Plain text: help → /help (if it matches a known command)
        if hasattr(self, 'gateway') and hasattr(self.gateway, 'commands'):
            test_cmd = '/' + raw_input
            if test_cmd in self.gateway.commands:
                return test_cmd

        # Not a command, return as-is
        return raw_input

    @abstractmethod
    async def start(self):
        """Start the channel adapter"""
        pass

    @abstractmethod
    async def stop(self):
        """Stop the channel adapter"""
        pass

    @abstractmethod
    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """
        Send a message back to a specific client through this channel.

        Args:
            reply_to: Channel-specific routing information
            message: P3394 UMF message to send
        """
        pass

    def adapt_content(self, message: P3394Message) -> P3394Message:
        """
        Adapt message content to channel capabilities.

        Transforms/downgrades content that this channel doesn't support.
        Returns adapted message with metadata about dropped content.
        """
        adapted_content = []
        dropped_content = []

        for content in message.content:
            # Check if content type is supported
            if content.type in self.capabilities.content_types:
                adapted_content.append(content)

            # Handle unsupported content types
            elif content.type == ContentType.IMAGE:
                if self.capabilities.supports_images:
                    adapted_content.append(content)
                else:
                    # Downgrade: image → text description
                    filename = content.metadata.get('filename', 'image')
                    adapted_content.append(P3394Content(
                        type=ContentType.TEXT,
                        data=f"[Image: {filename}]"
                    ))
                    dropped_content.append({
                        "type": "image",
                        "filename": filename,
                        "reason": f"{self.channel_id} does not support images"
                    })

            elif content.type == ContentType.BINARY:
                if self.capabilities.supports_attachments:
                    adapted_content.append(content)
                else:
                    # Downgrade: file → text notification
                    filename = content.metadata.get('filename', 'file')
                    size = content.metadata.get('size', 'unknown')
                    adapted_content.append(P3394Content(
                        type=ContentType.TEXT,
                        data=f"[File attachment: {filename} ({size} bytes)]"
                    ))
                    dropped_content.append({
                        "type": "file",
                        "filename": filename,
                        "reason": f"{self.channel_id} does not support file downloads",
                        "suggestion": "Use web interface to download"
                    })

            elif content.type == ContentType.HTML:
                if self.capabilities.supports_html:
                    adapted_content.append(content)
                elif self.capabilities.supports_markdown:
                    # Downgrade: HTML → Markdown (simplified)
                    adapted_content.append(P3394Content(
                        type=ContentType.MARKDOWN,
                        data=self._html_to_markdown(content.data)
                    ))
                    dropped_content.append({
                        "type": "html",
                        "reason": "HTML converted to Markdown"
                    })
                else:
                    # Downgrade: HTML → Text
                    adapted_content.append(P3394Content(
                        type=ContentType.TEXT,
                        data=self._html_to_text(content.data)
                    ))
                    dropped_content.append({
                        "type": "html",
                        "reason": "HTML converted to plain text"
                    })

            elif content.type == ContentType.MARKDOWN:
                if self.capabilities.supports_markdown:
                    adapted_content.append(content)
                else:
                    # Keep as text (Markdown is readable as plain text)
                    adapted_content.append(P3394Content(
                        type=ContentType.TEXT,
                        data=content.data
                    ))

            else:
                # Unsupported content type - use fallback if available
                if "fallback" in content.metadata:
                    fallback = P3394Content.from_dict(content.metadata["fallback"])
                    adapted_content.append(fallback)
                else:
                    # Create generic text fallback
                    adapted_content.append(P3394Content(
                        type=ContentType.TEXT,
                        data=f"[Unsupported content: {content.type.value}]"
                    ))
                dropped_content.append({
                    "type": content.type.value,
                    "reason": f"{self.channel_id} does not support this content type"
                })

        # Create adapted message
        adapted_message = P3394Message(
            id=message.id,
            type=message.type,
            timestamp=message.timestamp,
            source=message.source,
            destination=message.destination,
            reply_to=message.reply_to,
            content=adapted_content,
            session_id=message.session_id,
            conversation_id=message.conversation_id,
            metadata=message.metadata.copy() if message.metadata else {}
        )

        # Add dropped content info to metadata
        if dropped_content:
            adapted_message.metadata["dropped_content"] = dropped_content

        return adapted_message

    def _html_to_markdown(self, html: str) -> str:
        """Simple HTML to Markdown conversion"""
        # Very basic conversion - in production, use library like html2text
        import re
        md = html
        md = re.sub(r'<h1>(.*?)</h1>', r'# \1', md)
        md = re.sub(r'<h2>(.*?)</h2>', r'## \1', md)
        md = re.sub(r'<h3>(.*?)</h3>', r'### \1', md)
        md = re.sub(r'<strong>(.*?)</strong>', r'**\1**', md)
        md = re.sub(r'<b>(.*?)</b>', r'**\1**', md)
        md = re.sub(r'<em>(.*?)</em>', r'*\1*', md)
        md = re.sub(r'<i>(.*?)</i>', r'*\1*', md)
        md = re.sub(r'<code>(.*?)</code>', r'`\1`', md)
        md = re.sub(r'<[^>]+>', '', md)  # Remove remaining tags
        return md

    def _html_to_text(self, html: str) -> str:
        """Simple HTML to plain text conversion"""
        import re
        text = re.sub(r'<[^>]+>', '', html)  # Remove all tags
        return text

    def check_size_limits(self, message: P3394Message) -> tuple[bool, Optional[str]]:
        """
        Check if message fits within channel size limits.

        Returns:
            (is_valid, error_message)
        """
        total_size = 0

        for content in message.content:
            if isinstance(content.data, str):
                size = len(content.data.encode('utf-8'))
            elif isinstance(content.data, bytes):
                size = len(content.data)
            else:
                size = len(str(content.data).encode('utf-8'))

            total_size += size

            # Check attachment size limit
            if content.type in [ContentType.BINARY, ContentType.IMAGE]:
                if size > self.capabilities.max_attachment_size:
                    return False, f"Attachment too large: {size} bytes (max: {self.capabilities.max_attachment_size})"

        # Check total message size
        if total_size > self.capabilities.max_message_size:
            return False, f"Message too large: {total_size} bytes (max: {self.capabilities.max_message_size})"

        return True, None
