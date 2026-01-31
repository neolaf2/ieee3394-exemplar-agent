"""
Tests for KSTAR MCP Tools (Principal, Identity, Auth Management)

Tests the MCP-first architecture for identity management.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock, AsyncMock

from p3394_agent.plugins.kstar_tools import create_kstar_tools
from p3394_agent.core.auth.principal import Principal, PrincipalType
from p3394_agent.core.auth.credential_binding import CredentialBinding, BindingType


class MockPrincipalRegistry:
    """Mock principal registry for testing"""

    def __init__(self):
        self._principals = {}
        self._bindings = []

    def register_principal(self, principal):
        self._principals[principal.principal_id] = principal

    def get_principal(self, principal_id):
        return self._principals.get(principal_id)

    def list_principals(self, principal_type=None):
        principals = list(self._principals.values())
        if principal_type:
            principals = [p for p in principals if p.principal_type == principal_type]
        return principals

    def resolve_channel_identity(self, channel, channel_identity):
        for binding in self._bindings:
            if binding.channel == channel and binding.external_subject == channel_identity:
                return self._principals.get(binding.principal_id)
        return None

    def register_binding(self, binding):
        self._bindings.append(binding)

    def list_bindings(self, principal_id=None, channel=None):
        bindings = self._bindings
        if principal_id:
            bindings = [b for b in bindings if b.principal_id == principal_id]
        if channel:
            bindings = [b for b in bindings if b.channel == channel]
        return bindings

    def delete_binding(self, binding_id):
        self._bindings = [b for b in self._bindings if b.binding_id != binding_id]

    def get_stats(self):
        return {
            "total_principals": len(self._principals),
            "active_principals": len([p for p in self._principals.values() if p.is_active]),
            "total_bindings": len(self._bindings),
            "active_bindings": len(self._bindings),
            "principals_by_type": {},
            "bindings_by_channel": {}
        }


class MockKStarMemory:
    """Mock KSTAR memory for testing"""

    def __init__(self):
        self._principals = {}
        self._bindings = {}

    async def store_principal(self, principal_data):
        urn = principal_data.get("principal_id") or principal_data.get("urn")
        self._principals[urn] = principal_data
        return urn

    async def get_principal(self, urn):
        return self._principals.get(urn)

    async def list_principals(self):
        return list(self._principals.values())

    async def store_credential_binding(self, binding_data):
        cred_type = binding_data.get("credential_type", "unknown")
        cred_value = binding_data.get("credential_value", "unknown")
        binding_id = f"{cred_type}:{cred_value}"
        self._bindings[binding_id] = binding_data
        return binding_id

    async def get_credential_binding(self, credential_type, credential_value):
        binding_id = f"{credential_type}:{credential_value}"
        return self._bindings.get(binding_id)

    async def get_stats(self):
        return {
            "principal_count": len(self._principals),
            "binding_count": len(self._bindings),
            "trace_count": 0,
            "perception_count": 0,
            "skill_count": 0,
            "acl_count": 0,
            "capability_catalog_count": 0
        }


class MockGateway:
    """Mock gateway for testing"""

    def __init__(self):
        self.principal_registry = MockPrincipalRegistry()
        self.memory = MockKStarMemory()
        self.skills = {}
        self.AGENT_ID = "test-agent"
        self.AGENT_NAME = "Test Agent"
        self.AGENT_VERSION = "0.1.0"


@pytest.fixture
def gateway():
    """Create a mock gateway for testing"""
    return MockGateway()


@pytest.fixture
def kstar_tools(gateway):
    """Create KSTAR tools with mock gateway"""
    return create_kstar_tools(gateway)


def get_tool_by_name(tools, name):
    """Helper to find a tool by name"""
    for tool in tools:
        if tool.name == name:
            return tool
    return None


class TestKStarToolsCreation:
    """Test that KSTAR tools are created correctly"""

    def test_creates_expected_tools(self, kstar_tools):
        """Verify all expected tools are created"""
        tool_names = [t.name for t in kstar_tools]

        expected_tools = [
            "kstar_register_principal",
            "kstar_get_principal",
            "kstar_list_principals",
            "kstar_resolve_identity",
            "kstar_create_binding",
            "kstar_list_bindings",
            "kstar_delete_binding",
            "kstar_create_user",
            "kstar_authenticate_user",
            "kstar_create_session",
            "kstar_validate_session",
            "kstar_identity_stats",
        ]

        for expected in expected_tools:
            assert expected in tool_names, f"Missing tool: {expected}"

    def test_tool_count(self, kstar_tools):
        """Verify correct number of tools"""
        assert len(kstar_tools) == 12


class TestPrincipalManagement:
    """Test principal management tools"""

    @pytest.mark.asyncio
    async def test_register_principal(self, kstar_tools, gateway):
        """Test registering a new principal"""
        tool = get_tool_by_name(kstar_tools, "kstar_register_principal")

        result = await tool.handler({
            "org": "ieee",
            "role": "member",
            "person": "jsmith",
            "principal_type": "human",
            "display_name": "John Smith"
        })

        assert "content" in result
        assert "Principal registered" in result["content"][0]["text"]

        # Verify principal was stored
        principal = gateway.principal_registry.get_principal(
            "urn:principal:org:ieee:role:member:person:jsmith"
        )
        assert principal is not None
        assert principal.display_name == "John Smith"

    @pytest.mark.asyncio
    async def test_get_principal(self, kstar_tools, gateway):
        """Test getting a principal by ID"""
        # First register a principal
        principal = Principal(
            principal_id="urn:principal:org:ieee:role:admin:person:admin1",
            org="urn:org:ieee",
            role="urn:role:admin",
            person="urn:person:admin1",
            principal_type=PrincipalType.HUMAN,
            display_name="Admin User"
        )
        gateway.principal_registry.register_principal(principal)

        # Now get it
        tool = get_tool_by_name(kstar_tools, "kstar_get_principal")
        result = await tool.handler({
            "principal_id": "urn:principal:org:ieee:role:admin:person:admin1"
        })

        assert "content" in result
        assert "Principal found" in result["content"][0]["text"]
        assert "Admin User" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_get_principal_not_found(self, kstar_tools):
        """Test getting a non-existent principal"""
        tool = get_tool_by_name(kstar_tools, "kstar_get_principal")
        result = await tool.handler({
            "principal_id": "urn:principal:org:none:role:none:person:none"
        })

        assert "content" in result
        assert "not found" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_list_principals(self, kstar_tools, gateway):
        """Test listing all principals"""
        # Register some principals
        for i in range(3):
            principal = Principal(
                principal_id=f"urn:principal:org:test:role:user:person:user{i}",
                org="urn:org:test",
                role="urn:role:user",
                person=f"urn:person:user{i}",
                principal_type=PrincipalType.HUMAN,
                display_name=f"User {i}"
            )
            gateway.principal_registry.register_principal(principal)

        tool = get_tool_by_name(kstar_tools, "kstar_list_principals")
        result = await tool.handler({})

        assert "content" in result
        assert "Principals (3)" in result["content"][0]["text"]


class TestIdentityResolution:
    """Test identity resolution tools"""

    @pytest.mark.asyncio
    async def test_resolve_identity_success(self, kstar_tools, gateway):
        """Test successful identity resolution"""
        # Set up principal and binding
        principal = Principal(
            principal_id="urn:principal:org:users:role:member:person:testuser",
            org="urn:org:users",
            role="urn:role:member",
            person="urn:person:testuser",
            principal_type=PrincipalType.HUMAN,
            display_name="Test User"
        )
        gateway.principal_registry.register_principal(principal)

        binding = CredentialBinding(
            binding_id="urn:cred:whatsapp:1234567890",
            principal_id="urn:principal:org:users:role:member:person:testuser",
            channel="whatsapp",
            binding_type=BindingType.PHONE,
            external_subject="+1234567890"
        )
        gateway.principal_registry.register_binding(binding)

        # Resolve identity
        tool = get_tool_by_name(kstar_tools, "kstar_resolve_identity")
        result = await tool.handler({
            "channel": "whatsapp",
            "channel_identity": "+1234567890"
        })

        assert "content" in result
        assert "Identity resolved" in result["content"][0]["text"]
        assert "Test User" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_resolve_identity_not_found(self, kstar_tools):
        """Test identity resolution when not found"""
        tool = get_tool_by_name(kstar_tools, "kstar_resolve_identity")
        result = await tool.handler({
            "channel": "whatsapp",
            "channel_identity": "+9999999999"
        })

        assert "content" in result
        assert "No principal found" in result["content"][0]["text"]


class TestCredentialBindings:
    """Test credential binding tools"""

    @pytest.mark.asyncio
    async def test_create_binding(self, kstar_tools, gateway):
        """Test creating a credential binding"""
        # First create a principal
        principal = Principal(
            principal_id="urn:principal:org:test:role:user:person:bindtest",
            org="urn:org:test",
            role="urn:role:user",
            person="urn:person:bindtest",
            principal_type=PrincipalType.HUMAN
        )
        gateway.principal_registry.register_principal(principal)

        # Create binding
        tool = get_tool_by_name(kstar_tools, "kstar_create_binding")
        result = await tool.handler({
            "channel": "web",
            "external_subject": "test@example.com",
            "principal_id": "urn:principal:org:test:role:user:person:bindtest",
            "binding_type": "email",
            "scopes": ["read", "write"]
        })

        assert "content" in result
        assert "Credential binding created" in result["content"][0]["text"]

        # Verify binding was stored
        bindings = gateway.principal_registry.list_bindings(channel="web")
        assert len(bindings) == 1
        assert bindings[0].external_subject == "test@example.com"

    @pytest.mark.asyncio
    async def test_list_bindings(self, kstar_tools, gateway):
        """Test listing credential bindings"""
        # Create some bindings
        for i in range(2):
            binding = CredentialBinding(
                binding_id=f"urn:cred:test:binding{i}",
                principal_id="urn:principal:org:test:role:user:person:test",
                channel="test",
                binding_type=BindingType.ACCOUNT,
                external_subject=f"user{i}@test.com"
            )
            gateway.principal_registry.register_binding(binding)

        tool = get_tool_by_name(kstar_tools, "kstar_list_bindings")
        result = await tool.handler({"channel": "test"})

        assert "content" in result
        assert "Credential Bindings (2)" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_delete_binding(self, kstar_tools, gateway):
        """Test deleting a credential binding"""
        # Create a binding
        binding = CredentialBinding(
            binding_id="urn:cred:test:to_delete",
            principal_id="urn:principal:org:test:role:user:person:test",
            channel="test",
            binding_type=BindingType.ACCOUNT,
            external_subject="delete@test.com"
        )
        gateway.principal_registry.register_binding(binding)

        # Delete it
        tool = get_tool_by_name(kstar_tools, "kstar_delete_binding")
        result = await tool.handler({
            "binding_id": "urn:cred:test:to_delete"
        })

        assert "content" in result
        assert "deleted" in result["content"][0]["text"]

        # Verify it's gone
        bindings = gateway.principal_registry.list_bindings()
        assert len(bindings) == 0


class TestAuthOperations:
    """Test authentication operation tools"""

    @pytest.mark.asyncio
    async def test_create_user(self, kstar_tools, gateway):
        """Test creating a user with auto-principal registration"""
        tool = get_tool_by_name(kstar_tools, "kstar_create_user")
        result = await tool.handler({
            "email": "newuser@example.com",
            "password": "testpassword123",
            "display_name": "New User"
        })

        assert "content" in result
        assert "User created" in result["content"][0]["text"]
        assert "newuser@example.com" in result["content"][0]["text"]

        # Verify principal was created
        principals = gateway.principal_registry.list_principals()
        assert len(principals) == 1

        # Verify binding was created
        bindings = gateway.principal_registry.list_bindings(channel="web")
        assert len(bindings) == 1

    @pytest.mark.asyncio
    async def test_authenticate_user_success(self, kstar_tools, gateway):
        """Test successful user authentication"""
        # Create user first
        create_tool = get_tool_by_name(kstar_tools, "kstar_create_user")
        await create_tool.handler({
            "email": "auth@example.com",
            "password": "correctpassword",
            "display_name": "Auth User"
        })

        # Now authenticate
        auth_tool = get_tool_by_name(kstar_tools, "kstar_authenticate_user")
        result = await auth_tool.handler({
            "email": "auth@example.com",
            "password": "correctpassword"
        })

        assert "content" in result
        assert "Authentication successful" in result["content"][0]["text"]

    @pytest.mark.asyncio
    async def test_authenticate_user_wrong_password(self, kstar_tools, gateway):
        """Test authentication with wrong password"""
        # Create user first
        create_tool = get_tool_by_name(kstar_tools, "kstar_create_user")
        await create_tool.handler({
            "email": "wrongpass@example.com",
            "password": "correctpassword",
            "display_name": "Wrong Pass User"
        })

        # Try to authenticate with wrong password
        auth_tool = get_tool_by_name(kstar_tools, "kstar_authenticate_user")
        result = await auth_tool.handler({
            "email": "wrongpass@example.com",
            "password": "wrongpassword"
        })

        assert "content" in result
        assert "Invalid password" in result["content"][0]["text"]
        assert result.get("isError", False) == True

    @pytest.mark.asyncio
    async def test_create_session(self, kstar_tools, gateway):
        """Test creating a session token"""
        # Create a principal first
        principal = Principal(
            principal_id="urn:principal:org:test:role:user:person:sessiontest",
            org="urn:org:test",
            role="urn:role:user",
            person="urn:person:sessiontest",
            principal_type=PrincipalType.HUMAN
        )
        gateway.principal_registry.register_principal(principal)

        tool = get_tool_by_name(kstar_tools, "kstar_create_session")
        result = await tool.handler({
            "principal_id": "urn:principal:org:test:role:user:person:sessiontest",
            "channel": "web",
            "expires_in_hours": 24
        })

        assert "content" in result
        assert "Session created" in result["content"][0]["text"]
        assert "Token:" in result["content"][0]["text"]


class TestStatistics:
    """Test statistics tools"""

    @pytest.mark.asyncio
    async def test_identity_stats(self, kstar_tools, gateway):
        """Test getting identity registry statistics"""
        # Add some data
        for i in range(3):
            principal = Principal(
                principal_id=f"urn:principal:org:stats:role:user:person:user{i}",
                org="urn:org:stats",
                role="urn:role:user",
                person=f"urn:person:user{i}",
                principal_type=PrincipalType.HUMAN
            )
            gateway.principal_registry.register_principal(principal)

        tool = get_tool_by_name(kstar_tools, "kstar_identity_stats")
        result = await tool.handler({})

        assert "content" in result
        assert "Identity Registry Statistics" in result["content"][0]["text"]
        assert "Total Principals: 3" in result["content"][0]["text"]
