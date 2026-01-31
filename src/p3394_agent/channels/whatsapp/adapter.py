"""
WhatsApp Channel Adapter

Transforms WhatsApp messages to/from P3394 UMF messages.
Implements Companion Agent Mode - simple allowlist-based authentication.

Architecture:
    WhatsApp User <-> Bridge (Node.js) <-> WhatsAppChannelAdapter <-> Gateway

Companion Agent Mode:
    - Phone on allowlist → trusted with configured scopes
    - No complex credential exchange needed
    - Once authenticated via WhatsApp login (QR), user is trusted for session
"""

import asyncio
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from ..base import ChannelAdapter, ChannelCapabilities
from ...core.umf import P3394Message, P3394Content, ContentType, MessageType
from ...core.auth.principal import AssuranceLevel
from .client import WhatsAppBridgeClient, WhatsAppMessage

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppConfig:
    """
    WhatsApp channel configuration.

    Companion Agent Mode settings - allowlist-based trust.
    """
    # Bridge connection
    bridge_http_url: str = "http://localhost:3000"
    bridge_ws_url: str = "ws://localhost:3001"

    # Companion Agent Mode: allowlist = trusted
    companion_mode: bool = True

    # Allowlist behavior for unknown numbers
    # True = deny unknown, False = allow as anonymous
    deny_unknown: bool = False

    # Message settings
    text_chunk_limit: int = 4000
    send_read_receipts: bool = True

    # Acknowledgment reaction on message receive
    ack_emoji: Optional[str] = "👀"


class WhatsAppChannelAdapter(ChannelAdapter):
    """
    WhatsApp Channel Adapter for Companion Agent Mode.

    Simple allowlist-based authentication:
    - Phone on allowlist → trusted with their credential binding scopes
    - Unknown phone → anonymous or denied based on config

    The complexity of MCP tools, API keys, etc. is hidden from the user.
    They just chat with the agent via WhatsApp.
    """

    def __init__(
        self,
        gateway: "AgentGateway",
        config: Optional[WhatsAppConfig] = None
    ):
        super().__init__(gateway, "whatsapp")
        self.config = config or WhatsAppConfig()
        self.bridge_client: Optional[WhatsAppBridgeClient] = None

        # Cache credential bindings for quick lookup
        self._binding_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_loaded = False

    @property
    def capabilities(self) -> ChannelCapabilities:
        """WhatsApp channel capabilities"""
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.IMAGE],
            max_message_size=self.config.text_chunk_limit,
            max_attachment_size=50 * 1024 * 1024,  # 50 MB
            supports_streaming=False,
            supports_attachments=True,
            supports_images=True,
            supports_folders=False,
            supports_multipart=True,  # Can send multiple messages
            supports_markdown=False,  # WhatsApp has limited formatting
            supports_html=False,
            supports_mentions=True,  # @mentions in groups
            max_concurrent_connections=1,  # One WhatsApp account
            rate_limit_per_minute=30  # WhatsApp rate limits
        )

    # =========================================================================
    # COMPANION AGENT MODE AUTHENTICATION
    # =========================================================================

    def authenticate_client(self, context: Dict[str, Any]) -> "ClientPrincipalAssertion":
        """
        Authenticate WhatsApp user via Companion Agent Mode.

        Simple allowlist-based trust:
        1. Extract phone number from WhatsApp message
        2. Look up credential binding by phone
        3. If found → return principal with scopes
        4. If not found → anonymous or denied

        Args:
            context: {
                "phone": "+18625206066",  # E.164 format
                "from_jid": "18625206066@c.us",
                "contact_name": "Rich",
                "is_group": False,
                "group_id": None
            }

        Returns:
            ClientPrincipalAssertion with appropriate assurance level
        """
        phone = context.get("phone")
        from_jid = context.get("from_jid", "")
        contact_name = context.get("contact_name", "Unknown")
        is_group = context.get("is_group", False)

        if not phone:
            # Try to extract from JID
            phone = self._jid_to_phone(from_jid)

        # Load binding cache if needed
        if not self._cache_loaded:
            self._load_binding_cache()

        # Look up binding by phone number
        binding = self._find_binding_by_phone(phone)

        if binding:
            # On allowlist → trusted with their scopes
            return self.create_client_assertion(
                channel_identity=f"whatsapp:{phone}",
                assurance_level=AssuranceLevel.MEDIUM,  # WhatsApp verified phone
                authentication_method="whatsapp_allowlist",
                metadata={
                    "phone": phone,
                    "contact_name": contact_name,
                    "principal_id": binding.get("principal_id"),
                    "scopes": binding.get("scopes", []),
                    "binding_id": binding.get("binding_id"),
                    "is_group": is_group,
                    "note": "Authenticated via WhatsApp allowlist (Companion Agent Mode)"
                }
            )

        # Not on allowlist
        if self.config.deny_unknown:
            # Deny mode - return None-assurance assertion that will be rejected
            return self.create_client_assertion(
                channel_identity=f"whatsapp:{phone}:denied",
                assurance_level=AssuranceLevel.NONE,
                authentication_method="whatsapp_denied",
                metadata={
                    "phone": phone,
                    "contact_name": contact_name,
                    "is_group": is_group,
                    "denied": True,
                    "note": "Phone not on allowlist"
                }
            )
        else:
            # Allow as anonymous with discovery scopes
            return self.create_client_assertion(
                channel_identity=f"whatsapp:{phone}:anonymous",
                assurance_level=AssuranceLevel.NONE,
                authentication_method="whatsapp_anonymous",
                metadata={
                    "phone": phone,
                    "contact_name": contact_name,
                    "is_group": is_group,
                    "scopes": ["help", "about", "listCapabilities"],  # Anonymous scopes
                    "note": "Anonymous WhatsApp user (not on allowlist)"
                }
            )

    def _load_binding_cache(self):
        """Load credential bindings for WhatsApp channel."""
        try:
            from pathlib import Path
            import json

            # Try multiple locations for credential bindings
            locations = [
                Path.home() / ".P3394_agent_ieee3394-exemplar" / ".claude" / "principals" / "credential_bindings.json",
                Path(__file__).parent.parent.parent.parent.parent / ".claude" / "principals" / "credential_bindings.json",
            ]

            for path in locations:
                if path.exists():
                    with open(path) as f:
                        bindings = json.load(f)

                    # Index WhatsApp bindings by phone number
                    for binding in bindings:
                        if binding.get("channel") == "whatsapp" and binding.get("is_active", True):
                            phone = binding.get("external_subject")
                            if phone:
                                self._binding_cache[phone] = binding

                    logger.info(f"Loaded {len(self._binding_cache)} WhatsApp bindings from {path}")
                    self._cache_loaded = True
                    return

            logger.warning("No credential bindings file found")
            self._cache_loaded = True

        except Exception as e:
            logger.error(f"Failed to load credential bindings: {e}")
            self._cache_loaded = True

    def _find_binding_by_phone(self, phone: str) -> Optional[Dict[str, Any]]:
        """Find credential binding by phone number."""
        if not phone:
            return None

        # Normalize phone for lookup
        normalized = self._normalize_phone(phone)

        # Direct lookup
        if normalized in self._binding_cache:
            return self._binding_cache[normalized]

        # Try with/without + prefix
        if normalized.startswith("+"):
            if normalized[1:] in self._binding_cache:
                return self._binding_cache[normalized[1:]]
        else:
            if f"+{normalized}" in self._binding_cache:
                return self._binding_cache[f"+{normalized}"]

        return None

    def _normalize_phone(self, phone: str) -> str:
        """Normalize phone number to E.164 format."""
        if not phone:
            return ""

        # Remove non-digit characters except +
        digits = "".join(c for c in phone if c.isdigit() or c == "+")

        # Ensure + prefix
        if not digits.startswith("+") and len(digits) > 10:
            digits = "+" + digits

        return digits

    def _jid_to_phone(self, jid: str) -> str:
        """Extract phone number from WhatsApp JID."""
        if not jid:
            return ""

        # Remove @c.us or @s.whatsapp.net suffix
        phone = jid.split("@")[0]

        # Remove :0 suffix if present (device ID)
        phone = phone.split(":")[0]

        # Add + prefix
        if phone and not phone.startswith("+"):
            phone = "+" + phone

        return phone

    # =========================================================================
    # CHANNEL OPERATIONS
    # =========================================================================

    async def start(self):
        """Start the WhatsApp channel adapter."""
        logger.info("Starting WhatsApp channel adapter...")

        # Connect to bridge
        self.bridge_client = WhatsAppBridgeClient(
            http_url=self.config.bridge_http_url,
            ws_url=self.config.bridge_ws_url
        )

        try:
            await self.bridge_client.connect()

            # Check if authenticated
            if await self.bridge_client.is_ready():
                logger.info("WhatsApp bridge is ready")
            else:
                logger.warning("WhatsApp bridge connected but not authenticated")

            self.is_active = True
            await self.gateway.register_channel(self.channel_id, self)

            # Start message listener
            await self._listen_for_messages()

        except Exception as e:
            logger.error(f"Failed to start WhatsApp adapter: {e}")
            raise

    async def stop(self):
        """Stop the WhatsApp channel adapter."""
        self.is_active = False

        if self.bridge_client:
            await self.bridge_client.disconnect()
            self.bridge_client = None

        logger.info("WhatsApp channel adapter stopped")

    async def _listen_for_messages(self):
        """Listen for incoming WhatsApp messages."""
        if not self.bridge_client:
            return

        async for wa_message in self.bridge_client.listen():
            try:
                await self._handle_incoming_message(wa_message)
            except Exception as e:
                logger.exception(f"Error handling WhatsApp message: {e}")

    async def _handle_incoming_message(self, wa_message: WhatsAppMessage):
        """Handle an incoming WhatsApp message."""
        # Skip messages from self
        if wa_message.from_me:
            return

        logger.info(f"WhatsApp message from {wa_message.from_id}: {wa_message.body[:50]}...")

        # Send ack reaction if configured
        if self.config.ack_emoji:
            try:
                # Note: Reaction support depends on bridge implementation
                pass
            except Exception:
                pass

        # Build authentication context
        auth_context = {
            "phone": self._jid_to_phone(wa_message.from_id),
            "from_jid": wa_message.from_id,
            "contact_name": wa_message.contact_name or "Unknown",
            "is_group": wa_message.is_group,
            "group_id": wa_message.to_id if wa_message.is_group else None
        }

        # Authenticate client
        client_assertion = self.authenticate_client(auth_context)

        # Check if denied
        if client_assertion.metadata.get("denied"):
            logger.warning(f"Denied message from {wa_message.from_id}: not on allowlist")
            await self._send_denial_message(wa_message)
            return

        # Transform to UMF
        umf_message = self._wa_to_umf(wa_message, client_assertion)

        # Send to gateway
        umf_response = await self.gateway.handle(umf_message)

        # Transform response back to WhatsApp and send
        await self._send_umf_response(wa_message, umf_response)

    def _wa_to_umf(
        self,
        wa_message: WhatsAppMessage,
        client_assertion: "ClientPrincipalAssertion"
    ) -> P3394Message:
        """Transform WhatsApp message to P3394 UMF."""
        # Normalize command if present
        text = wa_message.body.strip()
        text = self.normalize_command(text)

        return P3394Message(
            type=MessageType.REQUEST,
            content=[P3394Content(
                type=ContentType.TEXT,
                data=text
            )],
            metadata={
                "security": {
                    "client_assertion": client_assertion.to_dict()
                },
                "channel": {
                    "channel_id": self.channel_id,
                    "whatsapp": {
                        "message_id": wa_message.id,
                        "from_jid": wa_message.from_id,
                        "to_jid": wa_message.to_id,
                        "contact_name": wa_message.contact_name,
                        "is_group": wa_message.is_group,
                        "timestamp": wa_message.timestamp
                    }
                },
                # Reply routing info
                "reply_to_whatsapp": {
                    "chat_id": wa_message.from_id if not wa_message.is_group else wa_message.to_id,
                    "message_id": wa_message.id
                }
            }
        )

    async def _send_umf_response(self, original: WhatsAppMessage, response: P3394Message):
        """Send UMF response back via WhatsApp."""
        if not self.bridge_client:
            return

        # Determine chat to reply to
        chat_id = original.from_id
        if original.is_group:
            chat_id = original.to_id  # Reply to group, not individual

        # Adapt content to WhatsApp capabilities
        adapted = self.adapt_content(response)

        # Extract text
        text_parts = []
        for content in adapted.content:
            if content.type == ContentType.TEXT:
                text_parts.append(content.data)
            elif content.type == ContentType.MARKDOWN:
                # Convert markdown to WhatsApp formatting
                text_parts.append(self._markdown_to_whatsapp(content.data))

        full_text = "\n\n".join(text_parts)

        # Chunk if needed
        chunks = self._chunk_text(full_text, self.config.text_chunk_limit)

        # Send each chunk
        for chunk in chunks:
            try:
                await self.bridge_client.send_message(chat_id, chunk)
            except Exception as e:
                logger.error(f"Failed to send WhatsApp message: {e}")

    async def _send_denial_message(self, original: WhatsAppMessage):
        """Send denial message for unauthorized users."""
        if not self.bridge_client:
            return

        denial_text = (
            "Sorry, you are not authorized to use this agent.\n\n"
            "If you believe this is an error, please contact the agent administrator."
        )

        try:
            await self.bridge_client.send_message(original.from_id, denial_text)
        except Exception as e:
            logger.error(f"Failed to send denial message: {e}")

    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """Send a message to a WhatsApp client."""
        if not self.bridge_client:
            return

        chat_id = reply_to.get("chat_id")
        if not chat_id:
            logger.warning("Cannot send to WhatsApp: no chat_id in reply_to")
            return

        # Adapt and send
        adapted = self.adapt_content(message)

        text_parts = []
        for content in adapted.content:
            if content.type == ContentType.TEXT:
                text_parts.append(content.data)

        if text_parts:
            full_text = "\n\n".join(text_parts)
            chunks = self._chunk_text(full_text, self.config.text_chunk_limit)

            for chunk in chunks:
                await self.bridge_client.send_message(chat_id, chunk)

    # =========================================================================
    # HELPERS
    # =========================================================================

    def _markdown_to_whatsapp(self, markdown: str) -> str:
        """Convert Markdown to WhatsApp formatting."""
        import re

        text = markdown

        # Use Unicode markers to avoid double-conversion
        BOLD_START = "\uFFF0"
        BOLD_END = "\uFFF1"

        # Bold: **text** or __text__ → *text* (WhatsApp bold)
        text = re.sub(r'\*\*(.+?)\*\*', BOLD_START + r'\1' + BOLD_END, text)
        text = re.sub(r'__(.+?)__', BOLD_START + r'\1' + BOLD_END, text)

        # Italic: *text* or _text_ → _text_ (WhatsApp italic)
        # Only match single asterisks (not already converted to bold)
        text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'_\1_', text)

        # Restore bold markers to WhatsApp bold (single asterisks)
        text = text.replace(BOLD_START, '*').replace(BOLD_END, '*')

        # Strikethrough: ~~text~~ → ~text~
        text = re.sub(r'~~(.+?)~~', r'~\1~', text)

        # Code: `text` → ```text```
        text = re.sub(r'`([^`]+)`', r'```\1```', text)

        # Remove headers (WhatsApp doesn't support)
        text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)

        # Convert bullet points
        text = re.sub(r'^[\*\-]\s+', '• ', text, flags=re.MULTILINE)

        return text

    def _chunk_text(self, text: str, limit: int) -> List[str]:
        """Split text into chunks that fit WhatsApp limit."""
        if len(text) <= limit:
            return [text]

        chunks = []
        current_chunk = ""

        # Try to split on paragraph boundaries
        paragraphs = text.split("\n\n")

        for para in paragraphs:
            if len(current_chunk) + len(para) + 2 <= limit:
                if current_chunk:
                    current_chunk += "\n\n"
                current_chunk += para
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                # If paragraph itself is too long, split by sentences
                if len(para) > limit:
                    sentences = para.split(". ")
                    current_chunk = ""
                    for sent in sentences:
                        if len(current_chunk) + len(sent) + 2 <= limit:
                            if current_chunk:
                                current_chunk += ". "
                            current_chunk += sent
                        else:
                            if current_chunk:
                                chunks.append(current_chunk)
                            current_chunk = sent
                else:
                    current_chunk = para

        if current_chunk:
            chunks.append(current_chunk)

        return chunks
