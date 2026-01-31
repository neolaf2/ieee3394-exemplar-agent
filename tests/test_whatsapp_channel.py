"""
Test WhatsApp Channel Adapter

Tests for the WhatsApp channel adapter, bridge client, and companion mode authentication.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import asdict

from p3394_agent.channels.whatsapp.client import WhatsAppMessage, WhatsAppBridgeClient
from p3394_agent.channels.whatsapp.adapter import WhatsAppChannelAdapter, WhatsAppConfig
from p3394_agent.core.umf import P3394Message, ContentType, MessageType
from p3394_agent.core.auth.principal import AssuranceLevel


class TestWhatsAppMessage:
    """Tests for WhatsAppMessage dataclass"""

    def test_from_bridge_basic(self):
        """Test parsing a basic message from bridge format"""
        bridge_data = {
            "id": "msg123",
            "from": "18625206066@c.us",
            "to": "agent@c.us",
            "body": "Hello agent!",
            "timestamp": 1706745600,
            "type": "chat",
            "hasMedia": False,
            "isForwarded": False,
            "fromMe": False,
            "contact": {
                "name": "Rich",
                "pushname": "Richard"
            },
            "chat": {
                "name": "Rich",
                "isGroup": False
            }
        }

        msg = WhatsAppMessage.from_bridge(bridge_data)

        assert msg.id == "msg123"
        assert msg.from_id == "18625206066@c.us"
        assert msg.to_id == "agent@c.us"
        assert msg.body == "Hello agent!"
        assert msg.timestamp == 1706745600
        assert msg.type == "chat"
        assert msg.has_media is False
        assert msg.from_me is False
        assert msg.contact_name == "Rich"
        assert msg.is_group is False

    def test_from_bridge_group_message(self):
        """Test parsing a group message"""
        bridge_data = {
            "id": "msg456",
            "from": "18625206066@c.us",
            "to": "120363123456789@g.us",
            "body": "Hello group!",
            "timestamp": 1706745700,
            "type": "chat",
            "hasMedia": False,
            "isForwarded": False,
            "fromMe": False,
            "contact": {
                "name": "Rich",
                "pushname": "Richard"
            },
            "chat": {
                "name": "IEEE 3394 Working Group",
                "isGroup": True
            }
        }

        msg = WhatsAppMessage.from_bridge(bridge_data)

        assert msg.is_group is True
        assert msg.chat_name == "IEEE 3394 Working Group"

    def test_from_bridge_minimal(self):
        """Test parsing with minimal data"""
        bridge_data = {
            "id": "msg789",
            "from": "12345@c.us",
            "to": "agent@c.us",
            "body": "Hi",
            "timestamp": 0
        }

        msg = WhatsAppMessage.from_bridge(bridge_data)

        assert msg.id == "msg789"
        assert msg.body == "Hi"
        assert msg.contact_name is None
        assert msg.is_group is False

    def test_from_bridge_with_media(self):
        """Test parsing a message with media"""
        bridge_data = {
            "id": "msg_media",
            "from": "12345@c.us",
            "to": "agent@c.us",
            "body": "",
            "timestamp": 1706745800,
            "type": "image",
            "hasMedia": True,
            "isForwarded": True,
            "fromMe": False,
            "contact": {},
            "chat": {"isGroup": False}
        }

        msg = WhatsAppMessage.from_bridge(bridge_data)

        assert msg.has_media is True
        assert msg.is_forwarded is True
        assert msg.type == "image"


class TestWhatsAppAdapter:
    """Tests for WhatsAppChannelAdapter"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_gateway = MagicMock()
        self.mock_gateway.commands = {}
        self.config = WhatsAppConfig(
            bridge_http_url="http://localhost:3000",
            bridge_ws_url="ws://localhost:3001",
            companion_mode=True,
            deny_unknown=False,
            text_chunk_limit=4000,
            ack_emoji="👀"
        )
        self.adapter = WhatsAppChannelAdapter(
            gateway=self.mock_gateway,
            config=self.config
        )

    def test_jid_to_phone_basic(self):
        """Test extracting phone from JID"""
        assert self.adapter._jid_to_phone("18625206066@c.us") == "+18625206066"
        assert self.adapter._jid_to_phone("447700900123@c.us") == "+447700900123"

    def test_jid_to_phone_with_device(self):
        """Test JID with device suffix"""
        assert self.adapter._jid_to_phone("18625206066:0@c.us") == "+18625206066"

    def test_jid_to_phone_empty(self):
        """Test empty JID"""
        assert self.adapter._jid_to_phone("") == ""
        assert self.adapter._jid_to_phone(None) == ""

    def test_normalize_phone_with_plus(self):
        """Test phone normalization with + prefix"""
        assert self.adapter._normalize_phone("+18625206066") == "+18625206066"

    def test_normalize_phone_without_plus(self):
        """Test phone normalization without + prefix"""
        assert self.adapter._normalize_phone("18625206066") == "+18625206066"

    def test_normalize_phone_with_formatting(self):
        """Test phone normalization with formatting characters"""
        assert self.adapter._normalize_phone("+1-862-520-6066") == "+18625206066"
        assert self.adapter._normalize_phone("+1 (862) 520-6066") == "+18625206066"

    def test_normalize_phone_short(self):
        """Test short phone numbers (local)"""
        # Short numbers shouldn't get + prefix
        assert self.adapter._normalize_phone("5551234") == "5551234"

    def test_capabilities(self):
        """Test channel capabilities"""
        caps = self.adapter.capabilities

        assert ContentType.TEXT in caps.content_types
        assert ContentType.IMAGE in caps.content_types
        assert caps.max_message_size == 4000
        assert caps.supports_streaming is False
        assert caps.supports_markdown is False
        assert caps.rate_limit_per_minute == 30

    def test_markdown_to_whatsapp_bold(self):
        """Test markdown bold conversion"""
        assert self.adapter._markdown_to_whatsapp("**bold text**") == "*bold text*"
        assert self.adapter._markdown_to_whatsapp("__also bold__") == "*also bold*"

    def test_markdown_to_whatsapp_strikethrough(self):
        """Test markdown strikethrough conversion"""
        assert self.adapter._markdown_to_whatsapp("~~strike~~") == "~strike~"

    def test_markdown_to_whatsapp_code(self):
        """Test markdown code conversion"""
        assert self.adapter._markdown_to_whatsapp("`code`") == "```code```"

    def test_markdown_to_whatsapp_headers(self):
        """Test markdown header removal"""
        assert self.adapter._markdown_to_whatsapp("# Header") == "Header"
        assert self.adapter._markdown_to_whatsapp("## Subheader") == "Subheader"
        assert self.adapter._markdown_to_whatsapp("### Sub-subheader") == "Sub-subheader"

    def test_markdown_to_whatsapp_bullets(self):
        """Test markdown bullet conversion"""
        text = "* Item 1\n- Item 2"
        result = self.adapter._markdown_to_whatsapp(text)
        assert "• Item 1" in result
        assert "• Item 2" in result

    def test_chunk_text_short(self):
        """Test text chunking - short text"""
        text = "Short message"
        chunks = self.adapter._chunk_text(text, 4000)

        assert len(chunks) == 1
        assert chunks[0] == text

    def test_chunk_text_long(self):
        """Test text chunking - long text"""
        # Create text longer than limit
        paragraph1 = "A" * 2000
        paragraph2 = "B" * 2000
        paragraph3 = "C" * 2000
        text = f"{paragraph1}\n\n{paragraph2}\n\n{paragraph3}"

        chunks = self.adapter._chunk_text(text, 4000)

        assert len(chunks) >= 2
        for chunk in chunks:
            assert len(chunk) <= 4000

    def test_chunk_text_preserves_paragraphs(self):
        """Test that chunking tries to preserve paragraph boundaries"""
        # Create paragraphs that need to be split
        para1 = "First paragraph with some content. " * 3
        para2 = "Second paragraph with more content. " * 3
        para3 = "Third paragraph with even more. " * 3
        text = f"{para1}\n\n{para2}\n\n{para3}"

        # Use a limit that forces splitting but allows full paragraphs
        chunks = self.adapter._chunk_text(text, 150)

        # Should have multiple chunks
        assert len(chunks) >= 2

        # Verify chunks respect size limit
        for chunk in chunks:
            assert len(chunk) <= 150


class TestWhatsAppAuthentication:
    """Tests for companion mode authentication"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_gateway = MagicMock()
        self.mock_gateway.commands = {}
        self.config = WhatsAppConfig(
            companion_mode=True,
            deny_unknown=False
        )
        self.adapter = WhatsAppChannelAdapter(
            gateway=self.mock_gateway,
            config=self.config
        )

    def test_authenticate_unknown_anonymous_mode(self):
        """Test authentication for unknown user in anonymous mode"""
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {}  # Empty allowlist

        context = {
            "phone": "+15551234567",
            "from_jid": "15551234567@c.us",
            "contact_name": "Unknown User",
            "is_group": False
        }

        assertion = self.adapter.authenticate_client(context)

        assert assertion.assurance_level == AssuranceLevel.NONE
        assert assertion.authentication_method == "whatsapp_anonymous"
        assert "anonymous" in assertion.metadata.get("note", "").lower()
        # Should get discovery scopes
        assert "help" in assertion.metadata.get("scopes", [])

    def test_authenticate_unknown_deny_mode(self):
        """Test authentication for unknown user in deny mode"""
        self.adapter.config.deny_unknown = True
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {}  # Empty allowlist

        context = {
            "phone": "+15551234567",
            "from_jid": "15551234567@c.us",
            "contact_name": "Unknown User",
            "is_group": False
        }

        assertion = self.adapter.authenticate_client(context)

        assert assertion.assurance_level == AssuranceLevel.NONE
        assert assertion.authentication_method == "whatsapp_denied"
        assert assertion.metadata.get("denied") is True

    def test_authenticate_allowlisted_user(self):
        """Test authentication for user on allowlist"""
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {
            "+18625206066": {
                "binding_id": "urn:cred:whatsapp:18625206066",
                "principal_id": "urn:principal:org:ieee:role:chair:person:rtong",
                "scopes": ["chat", "query", "admin"],
                "is_active": True
            }
        }

        context = {
            "phone": "+18625206066",
            "from_jid": "18625206066@c.us",
            "contact_name": "Rich",
            "is_group": False
        }

        assertion = self.adapter.authenticate_client(context)

        assert assertion.assurance_level == AssuranceLevel.MEDIUM
        assert assertion.authentication_method == "whatsapp_allowlist"
        assert assertion.metadata.get("principal_id") == "urn:principal:org:ieee:role:chair:person:rtong"
        assert "admin" in assertion.metadata.get("scopes", [])

    def test_authenticate_phone_normalization(self):
        """Test that phone lookup works with different formats"""
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {
            "+18625206066": {
                "binding_id": "urn:cred:whatsapp:18625206066",
                "principal_id": "urn:principal:org:ieee:role:chair:person:rtong",
                "scopes": ["chat"],
                "is_active": True
            }
        }

        # Without + prefix in context
        context = {
            "phone": "18625206066",
            "from_jid": "18625206066@c.us",
            "contact_name": "Rich",
            "is_group": False
        }

        assertion = self.adapter.authenticate_client(context)

        # Should still find the binding
        assert assertion.assurance_level == AssuranceLevel.MEDIUM

    def test_authenticate_extracts_phone_from_jid(self):
        """Test that phone is extracted from JID if not provided"""
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {
            "+18625206066": {
                "binding_id": "urn:cred:whatsapp:18625206066",
                "principal_id": "urn:principal:org:ieee:role:chair:person:rtong",
                "scopes": ["chat"],
                "is_active": True
            }
        }

        context = {
            "phone": None,  # No phone provided
            "from_jid": "18625206066@c.us",
            "contact_name": "Rich",
            "is_group": False
        }

        assertion = self.adapter.authenticate_client(context)

        # Should extract from JID and find binding
        assert assertion.assurance_level == AssuranceLevel.MEDIUM


class TestWhatsAppUMFTransformation:
    """Tests for P3394 UMF transformation"""

    def setup_method(self):
        """Setup for each test"""
        self.mock_gateway = MagicMock()
        self.mock_gateway.commands = {"/help": MagicMock()}
        self.adapter = WhatsAppChannelAdapter(
            gateway=self.mock_gateway,
            config=WhatsAppConfig()
        )
        self.adapter._cache_loaded = True
        self.adapter._binding_cache = {}

    def test_wa_to_umf_basic(self):
        """Test basic WhatsApp to UMF conversion"""
        wa_msg = WhatsAppMessage(
            id="msg123",
            from_id="18625206066@c.us",
            to_id="agent@c.us",
            body="Hello agent!",
            timestamp=1706745600,
            contact_name="Rich",
            is_group=False
        )

        assertion = self.adapter.authenticate_client({
            "phone": "+18625206066",
            "from_jid": wa_msg.from_id,
            "contact_name": wa_msg.contact_name,
            "is_group": wa_msg.is_group
        })

        umf = self.adapter._wa_to_umf(wa_msg, assertion)

        assert umf.type == MessageType.REQUEST
        assert len(umf.content) == 1
        assert umf.content[0].type == ContentType.TEXT
        assert umf.content[0].data == "Hello agent!"

        # Check metadata
        assert "security" in umf.metadata
        assert "channel" in umf.metadata
        assert umf.metadata["channel"]["whatsapp"]["from_jid"] == "18625206066@c.us"

    def test_wa_to_umf_command_normalization(self):
        """Test that commands are normalized in UMF"""
        wa_msg = WhatsAppMessage(
            id="msg123",
            from_id="18625206066@c.us",
            to_id="agent@c.us",
            body="/help",
            timestamp=1706745600,
            is_group=False
        )

        assertion = self.adapter.authenticate_client({
            "phone": "+18625206066",
            "from_jid": wa_msg.from_id,
            "is_group": False
        })

        umf = self.adapter._wa_to_umf(wa_msg, assertion)

        # Command should be normalized
        assert umf.content[0].data == "/help"

    def test_wa_to_umf_group_message(self):
        """Test UMF conversion for group messages"""
        wa_msg = WhatsAppMessage(
            id="msg123",
            from_id="18625206066@c.us",
            to_id="120363123456789@g.us",
            body="Hello group!",
            timestamp=1706745600,
            contact_name="Rich",
            chat_name="IEEE 3394 WG",
            is_group=True
        )

        assertion = self.adapter.authenticate_client({
            "phone": "+18625206066",
            "from_jid": wa_msg.from_id,
            "contact_name": wa_msg.contact_name,
            "is_group": True
        })

        umf = self.adapter._wa_to_umf(wa_msg, assertion)

        assert umf.metadata["channel"]["whatsapp"]["is_group"] is True
        # Reply should go to group
        assert umf.metadata["reply_to_whatsapp"]["chat_id"] == "120363123456789@g.us"


class TestWhatsAppBridgeClient:
    """Tests for WhatsAppBridgeClient"""

    @pytest.mark.asyncio
    async def test_send_message(self):
        """Test sending a message through the bridge"""
        client = WhatsAppBridgeClient()

        # Mock the HTTP session
        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "success": True,
            "messageId": "msg123",
            "timestamp": 1706745600
        })

        mock_session = MagicMock()
        mock_session.post = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        client._http_session = mock_session

        result = await client.send_message("18625206066@c.us", "Hello!")

        assert result["success"] is True
        assert result["messageId"] == "msg123"

    @pytest.mark.asyncio
    async def test_get_status(self):
        """Test getting bridge status"""
        client = WhatsAppBridgeClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "status": "running",
            "whatsapp": {
                "ready": True,
                "authenticating": False
            }
        })

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        client._http_session = mock_session

        status = await client.get_status()

        assert status["status"] == "running"
        assert status["whatsapp"]["ready"] is True

    @pytest.mark.asyncio
    async def test_is_ready(self):
        """Test checking if WhatsApp is ready"""
        client = WhatsAppBridgeClient()

        mock_response = AsyncMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={
            "status": "running",
            "whatsapp": {"ready": True}
        })

        mock_session = MagicMock()
        mock_session.get = MagicMock(return_value=AsyncMock(__aenter__=AsyncMock(return_value=mock_response)))

        client._http_session = mock_session

        assert await client.is_ready() is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
