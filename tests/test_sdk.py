"""
P3394 Agent SDK Core Tests

Tests for the public SDK API: UMF messages, capabilities, sessions.
"""

import pytest
from datetime import datetime, timedelta, timezone
import json


class TestPublicAPIImports:
    """Test that all public API exports are importable."""

    def test_version_import(self):
        from p3394_agent import __version__
        assert __version__ == "0.2.0"

    def test_umf_imports(self):
        """UMF types should be importable from top level."""
        from p3394_agent import (
            P3394Message,
            P3394Content,
            P3394Address,
            P3394Error,
            MessageType,
            ContentType,
        )
        assert P3394Message is not None
        assert MessageType.REQUEST.value == "request"
        assert ContentType.TEXT.value == "text"

    def test_capability_imports(self):
        """Capability types should be importable from top level."""
        from p3394_agent import (
            AgentCapabilityDescriptor,
            CapabilityKind,
            ExecutionSubstrate,
            InvocationMode,
            ExposureScope,
            CapabilityExecution,
            CapabilityInvocation,
            CapabilityExposure,
            CapabilityPermissions,
        )
        assert CapabilityKind.ATOMIC.value == "atomic"
        assert ExecutionSubstrate.LLM.value == "llm"

    def test_session_imports(self):
        """Session types should be importable from top level."""
        from p3394_agent import (
            Session,
            SessionManager,
            ChannelRole,
            ChannelBinding,
        )
        assert ChannelRole.PRIMARY.value == "primary"

    def test_client_imports(self):
        """Client should be importable from top level."""
        from p3394_agent import AgentClient, run_client
        assert AgentClient is not None

    def test_memory_imports(self):
        """Memory types should be importable from top level."""
        from p3394_agent import (
            KStarMemory,
            ControlToken,
            TokenType,
        )
        assert KStarMemory is not None


class TestP3394Message:
    """Tests for P3394Message UMF type."""

    def test_create_text_message(self):
        """Create a simple text message."""
        from p3394_agent import P3394Message, ContentType

        msg = P3394Message.text("Hello, world!")

        assert msg.type.value == "request"
        assert len(msg.content) == 1
        assert msg.content[0].type == ContentType.TEXT
        assert msg.content[0].data == "Hello, world!"

    def test_message_has_uuid(self):
        """Messages should have auto-generated UUIDs."""
        from p3394_agent import P3394Message

        msg1 = P3394Message.text("test1")
        msg2 = P3394Message.text("test2")

        assert msg1.id is not None
        assert msg2.id is not None
        assert msg1.id != msg2.id

    def test_message_has_timestamp(self):
        """Messages should have auto-generated timestamps."""
        from p3394_agent import P3394Message

        msg = P3394Message.text("test")

        assert msg.timestamp is not None
        # Should be ISO format
        datetime.fromisoformat(msg.timestamp.replace('Z', '+00:00'))

    def test_extract_text(self):
        """Extract text content from message."""
        from p3394_agent import P3394Message

        msg = P3394Message.text("Hello, agent!")
        assert msg.extract_text() == "Hello, agent!"

    def test_extract_text_empty(self):
        """Extract text returns empty string for non-text messages."""
        from p3394_agent import P3394Message, P3394Content, ContentType

        msg = P3394Message(
            content=[P3394Content(type=ContentType.JSON, data={"key": "value"})]
        )
        assert msg.extract_text() == ""

    def test_to_dict_serialization(self):
        """Message should serialize to dict."""
        from p3394_agent import P3394Message, MessageType

        msg = P3394Message.text("Hello", session_id="sess-123")
        data = msg.to_dict()

        assert data["type"] == "request"
        assert data["session_id"] == "sess-123"
        assert len(data["content"]) == 1
        assert data["content"][0]["type"] == "text"
        assert data["content"][0]["data"] == "Hello"

    def test_from_dict_deserialization(self):
        """Message should deserialize from dict."""
        from p3394_agent import P3394Message, MessageType, ContentType

        data = {
            "id": "msg-123",
            "type": "response",
            "timestamp": "2026-02-05T10:00:00Z",
            "content": [
                {"type": "text", "data": "Response text"}
            ],
            "session_id": "sess-456"
        }

        msg = P3394Message.from_dict(data)

        assert msg.id == "msg-123"
        assert msg.type == MessageType.RESPONSE
        assert msg.session_id == "sess-456"
        assert msg.content[0].type == ContentType.TEXT
        assert msg.content[0].data == "Response text"

    def test_roundtrip_serialization(self):
        """Message should survive roundtrip serialization."""
        from p3394_agent import P3394Message, P3394Content, ContentType

        original = P3394Message(
            session_id="sess-roundtrip",
            content=[
                P3394Content(type=ContentType.TEXT, data="Hello"),
                P3394Content(
                    type=ContentType.JSON,
                    data={"nested": {"key": "value"}},
                    metadata={"priority": "high"}
                ),
            ],
            metadata={"custom": "field"}
        )

        # Serialize and deserialize
        data = original.to_dict()
        restored = P3394Message.from_dict(data)

        assert restored.session_id == original.session_id
        assert len(restored.content) == 2
        assert restored.content[0].data == "Hello"
        assert restored.content[1].data == {"nested": {"key": "value"}}

    def test_json_serialization(self):
        """Message dict should be JSON-serializable."""
        from p3394_agent import P3394Message

        msg = P3394Message.text("Test message")
        data = msg.to_dict()

        # Should not raise
        json_str = json.dumps(data)
        restored_data = json.loads(json_str)
        assert restored_data["content"][0]["data"] == "Test message"


class TestP3394Address:
    """Tests for P3394Address."""

    def test_create_address(self):
        """Create an address with all fields."""
        from p3394_agent import P3394Address

        addr = P3394Address(
            agent_id="my-agent",
            channel_id="cli",
            session_id="sess-123"
        )

        assert addr.agent_id == "my-agent"
        assert addr.channel_id == "cli"
        assert addr.session_id == "sess-123"

    def test_to_uri(self):
        """Convert address to P3394 URI."""
        from p3394_agent import P3394Address

        # Full address
        addr = P3394Address("my-agent", "cli", "sess-123")
        assert addr.to_uri() == "p3394://my-agent/cli?session=sess-123"

        # Without session
        addr2 = P3394Address("my-agent", "cli")
        assert addr2.to_uri() == "p3394://my-agent/cli"

        # Agent only
        addr3 = P3394Address("my-agent")
        assert addr3.to_uri() == "p3394://my-agent"

    def test_from_uri(self):
        """Parse address from P3394 URI."""
        from p3394_agent import P3394Address

        addr = P3394Address.from_uri("p3394://my-agent/cli?session=sess-123")

        assert addr.agent_id == "my-agent"
        assert addr.channel_id == "cli"
        assert addr.session_id == "sess-123"

    def test_from_uri_minimal(self):
        """Parse minimal URI (agent only)."""
        from p3394_agent import P3394Address

        addr = P3394Address.from_uri("p3394://my-agent")

        assert addr.agent_id == "my-agent"
        assert addr.channel_id is None
        assert addr.session_id is None

    def test_from_uri_invalid(self):
        """Invalid URIs should raise ValueError."""
        from p3394_agent import P3394Address

        with pytest.raises(ValueError):
            P3394Address.from_uri("http://not-a-p3394-uri")


class TestAgentCapabilityDescriptor:
    """Tests for capability descriptors."""

    def test_create_capability(self):
        """Create a full capability descriptor."""
        from p3394_agent import (
            AgentCapabilityDescriptor,
            CapabilityKind,
            ExecutionSubstrate,
            CapabilityExecution,
            CapabilityInvocation,
            CapabilityExposure,
            CapabilityPermissions,
            InvocationMode,
            ExposureScope,
        )

        cap = AgentCapabilityDescriptor(
            capability_id="cmd:help",
            name="Help Command",
            version="1.0.0",
            description="Show help information",
            kind=CapabilityKind.ATOMIC,
            execution=CapabilityExecution(
                substrate=ExecutionSubstrate.SYMBOLIC,
                entrypoint="gateway._cmd_help"
            ),
            invocation=CapabilityInvocation(
                modes=[InvocationMode.COMMAND],
                command_aliases=["/help", "/?"]
            ),
            exposure=CapabilityExposure(scope=ExposureScope.PUBLIC),
            permissions=CapabilityPermissions(danger_level="low")
        )

        assert cap.capability_id == "cmd:help"
        assert cap.kind == CapabilityKind.ATOMIC
        assert cap.execution.substrate == ExecutionSubstrate.SYMBOLIC
        assert "/help" in cap.invocation.command_aliases

    def test_capability_to_dict(self):
        """Capability should serialize to dict."""
        from p3394_agent import (
            AgentCapabilityDescriptor,
            CapabilityKind,
            ExecutionSubstrate,
            CapabilityExecution,
            CapabilityInvocation,
            CapabilityExposure,
            CapabilityPermissions,
        )

        cap = AgentCapabilityDescriptor(
            capability_id="test:cap",
            name="Test",
            version="1.0.0",
            description="Test capability",
            kind=CapabilityKind.ATOMIC,
            execution=CapabilityExecution(substrate=ExecutionSubstrate.SYMBOLIC),
            invocation=CapabilityInvocation(),
            exposure=CapabilityExposure(),
            permissions=CapabilityPermissions()
        )

        data = cap.to_dict()

        assert data["capability_id"] == "test:cap"
        assert data["kind"] == "atomic"
        assert data["execution"]["substrate"] == "symbolic"

    def test_capability_to_json(self):
        """Capability should serialize to JSON string."""
        from p3394_agent import (
            AgentCapabilityDescriptor,
            CapabilityKind,
            ExecutionSubstrate,
            CapabilityExecution,
            CapabilityInvocation,
            CapabilityExposure,
            CapabilityPermissions,
        )

        cap = AgentCapabilityDescriptor(
            capability_id="test:json",
            name="JSON Test",
            version="1.0.0",
            description="Test JSON serialization",
            kind=CapabilityKind.ATOMIC,
            execution=CapabilityExecution(substrate=ExecutionSubstrate.LLM),
            invocation=CapabilityInvocation(),
            exposure=CapabilityExposure(),
            permissions=CapabilityPermissions()
        )

        json_str = cap.to_json()
        data = json.loads(json_str)

        assert data["capability_id"] == "test:json"

    def test_capability_from_dict(self):
        """Capability should deserialize from dict."""
        from p3394_agent import AgentCapabilityDescriptor, CapabilityKind

        data = {
            "capability_id": "test:fromdict",
            "name": "From Dict",
            "version": "1.0.0",
            "description": "Test deserialization",
            "kind": "atomic",
            "execution": {"substrate": "llm", "runtime": "claude-sonnet"},
            "invocation": {"modes": ["command", "message"]},
            "exposure": {"scope": "public"},
            "permissions": {"danger_level": "low"}
        }

        cap = AgentCapabilityDescriptor.from_dict(data)

        assert cap.capability_id == "test:fromdict"
        assert cap.kind == CapabilityKind.ATOMIC
        assert cap.execution.runtime == "claude-sonnet"


class TestSession:
    """Tests for session management."""

    def test_create_session(self):
        """Create a session with defaults."""
        from p3394_agent import Session

        session = Session()

        assert session.id is not None
        assert session.is_authenticated is False
        assert session.client_role == "anonymous"

    def test_session_expiration(self):
        """Session should report expiration correctly."""
        from p3394_agent import Session
        from datetime import datetime, timedelta, timezone

        # Not expired
        session = Session(
            expires_at=datetime.now(timezone.utc) + timedelta(hours=1)
        )
        assert session.is_expired() is False

        # Expired
        expired_session = Session(
            expires_at=datetime.now(timezone.utc) - timedelta(hours=1)
        )
        assert expired_session.is_expired() is True

        # No expiration
        no_expire = Session()
        assert no_expire.is_expired() is False

    def test_session_permissions(self):
        """Session permission checking."""
        from p3394_agent import Session

        session = Session(
            granted_permissions=["read", "write"]
        )

        assert session.has_permission("read") is True
        assert session.has_permission("write") is True
        assert session.has_permission("admin") is False

    def test_session_wildcard_permission(self):
        """Wildcard permission grants all."""
        from p3394_agent import Session

        session = Session(
            granted_permissions=["*"]
        )

        assert session.has_permission("anything") is True
        assert session.has_permission("admin") is True

    def test_session_touch(self):
        """Touch updates last activity."""
        from p3394_agent import Session
        from datetime import datetime, timezone
        import time

        session = Session()
        original = session.last_activity

        time.sleep(0.01)  # Small delay
        session.touch()

        assert session.last_activity > original


class TestSessionManager:
    """Tests for SessionManager."""

    @pytest.mark.asyncio
    async def test_create_session(self):
        """Create a session via manager."""
        from p3394_agent import SessionManager

        manager = SessionManager()
        session = await manager.create_session(
            client_id="test-client",
            channel_id="cli"
        )

        assert session.id is not None
        assert session.client_id == "test-client"
        assert session.channel_id == "cli"
        assert session.expires_at is not None

    @pytest.mark.asyncio
    async def test_get_session(self):
        """Retrieve session by ID."""
        from p3394_agent import SessionManager

        manager = SessionManager()
        created = await manager.create_session()

        retrieved = manager.get_session(created.id)

        assert retrieved is not None
        assert retrieved.id == created.id

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self):
        """Getting nonexistent session returns None."""
        from p3394_agent import SessionManager

        manager = SessionManager()
        result = manager.get_session("nonexistent-id")

        assert result is None

    @pytest.mark.asyncio
    async def test_end_session(self):
        """End a session."""
        from p3394_agent import SessionManager

        manager = SessionManager()
        session = await manager.create_session()
        session_id = session.id

        await manager.end_session(session_id)

        assert manager.get_session(session_id) is None


class TestKStarMemory:
    """Tests for KSTAR memory."""

    @pytest.mark.asyncio
    async def test_store_trace(self):
        """Store and retrieve a trace."""
        from p3394_agent import KStarMemory

        memory = KStarMemory()
        trace_id = await memory.store_trace({
            "situation": {"domain": "test"},
            "task": {"goal": "test goal"},
            "action": {"type": "test_action"},
            "session_id": "test-session"
        })

        assert trace_id.startswith("trace_")
        stats = await memory.get_stats()
        assert stats["trace_count"] == 1

    @pytest.mark.asyncio
    async def test_store_perception(self):
        """Store a perception."""
        from p3394_agent import KStarMemory

        memory = KStarMemory()
        perception_id = await memory.store_perception({
            "content": "User prefers short responses",
            "tags": ["preference"],
            "importance": 0.8
        })

        assert perception_id.startswith("perception_")
        stats = await memory.get_stats()
        assert stats["perception_count"] == 1

    @pytest.mark.asyncio
    async def test_store_skill(self):
        """Store a skill."""
        from p3394_agent import KStarMemory

        memory = KStarMemory()
        skill_id = await memory.store_skill({
            "name": "greeting",
            "description": "Greet users warmly",
            "domain": "social"
        })

        assert skill_id.startswith("skill_")
        skills = await memory.list_skills()
        assert len(skills) == 1
        assert skills[0]["name"] == "greeting"

    @pytest.mark.asyncio
    async def test_query_traces(self):
        """Query traces by domain."""
        from p3394_agent import KStarMemory

        memory = KStarMemory()

        # Store some traces
        await memory.store_trace({
            "situation": {"domain": "support"},
            "task": {"goal": "help user"}
        })
        await memory.store_trace({
            "situation": {"domain": "sales"},
            "task": {"goal": "answer question"}
        })

        # Query for support domain
        result = await memory.query(domain="support", goal="any")

        assert result is not None
        assert result["situation"]["domain"] == "support"

    @pytest.mark.asyncio
    async def test_get_stats(self):
        """Get memory statistics."""
        from p3394_agent import KStarMemory

        memory = KStarMemory()

        await memory.store_trace({"situation": {}, "task": {}})
        await memory.store_trace({"situation": {}, "task": {}})
        await memory.store_perception({"content": "test"})
        await memory.store_skill({"name": "test"})

        stats = await memory.get_stats()

        assert stats["trace_count"] == 2
        assert stats["perception_count"] == 1
        assert stats["skill_count"] == 1
