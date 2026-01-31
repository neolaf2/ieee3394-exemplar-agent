"""
Test Admin Access Control

Verifies that admin-only capabilities require HIGH assurance and explicit /login.
"""

import pytest
from p3394_agent.core.auth.policy import PolicyEngine, PolicyDecision, AuthorizationContext
from p3394_agent.core.auth.principal import Principal, PrincipalType, AssuranceLevel


class TestAdminAccessControl:
    """Test suite for admin access control"""

    def setup_method(self):
        """Setup for each test"""
        self.policy_engine = PolicyEngine(enforcement_enabled=True)
        self.policy_engine.enable_enforcement_for_channel("cli")

    def test_os_user_denied_admin_capability(self):
        """OS user (LOW assurance) should be denied admin capabilities"""

        # OS user principal with LOW assurance
        principal = Principal(
            principal_id="urn:principal:org:ieee:role:member:person:alice",
            org="urn:org:ieee",
            role="urn:role:member",
            person="urn:person:alice",
            principal_type=PrincipalType.HUMAN
        )

        context = AuthorizationContext(
            principal=principal,
            assurance_level=AssuranceLevel.LOW,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=AssuranceLevel.LOW,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        assert decision == PolicyDecision.DENY
        assert "HIGH" in reason or "assurance" in reason.lower()

    def test_local_socket_denied_admin_capability(self):
        """Local socket (MEDIUM assurance) should be denied admin capabilities"""

        principal = Principal(
            principal_id="urn:principal:org:ieee:role:member:person:alice",
            org="urn:org:ieee",
            role="urn:role:member",
            person="urn:person:alice",
            principal_type=PrincipalType.HUMAN
        )

        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=AssuranceLevel.MEDIUM,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        assert decision == PolicyDecision.DENY
        assert "HIGH" in reason or "assurance" in reason.lower()

    def test_admin_after_login_allowed(self):
        """Admin with HIGH assurance (after /login) should be allowed"""

        # Admin principal after /login
        admin_principal = Principal(
            principal_id="urn:principal:org:ieee3394:role:admin:person:owner",
            org="urn:org:ieee3394",
            role="urn:role:admin",
            person="urn:person:owner",
            principal_type=PrincipalType.HUMAN
        )

        decision, reason = self.policy_engine.authorize(
            principal=admin_principal,
            assurance_level=AssuranceLevel.HIGH,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=["*"],
            channel="cli"
        )

        assert decision == PolicyDecision.ALLOW
        assert "admin" in reason.lower() or "allow" in reason.lower()

    def test_anonymous_denied_admin_capability(self):
        """Anonymous users should always be denied admin capabilities"""

        anonymous = Principal.anonymous_principal()

        decision, reason = self.policy_engine.authorize(
            principal=anonymous,
            assurance_level=AssuranceLevel.NONE,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=[],
            channel="cli"
        )

        assert decision == PolicyDecision.DENY
        assert "anonymous" in reason.lower() or "privileged" in reason.lower()

    def test_os_user_allowed_read_capability(self):
        """OS user should be allowed read-only capabilities"""

        principal = Principal(
            principal_id="urn:principal:org:ieee:role:member:person:alice",
            org="urn:org:ieee",
            role="urn:role:member",
            person="urn:person:alice",
            principal_type=PrincipalType.HUMAN
        )

        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=AssuranceLevel.LOW,
            capability="help",
            requested_permissions=["read"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        assert decision == PolicyDecision.ALLOW

    def test_enforcement_disabled_allows_all(self):
        """When enforcement is disabled, all operations should be allowed"""

        # Disable enforcement
        self.policy_engine.disable_enforcement()

        anonymous = Principal.anonymous_principal()

        decision, reason = self.policy_engine.authorize(
            principal=anonymous,
            assurance_level=AssuranceLevel.NONE,
            capability="whatsapp.configure",
            requested_permissions=["admin"],
            granted_permissions=[],
            channel="cli"
        )

        assert decision == PolicyDecision.ALLOW
        assert "enforcement disabled" in reason.lower()

    def test_skill_creation_requires_admin(self):
        """Skill creation should require admin privileges"""

        # Regular user
        principal = Principal(
            principal_id="urn:principal:org:ieee:role:member:person:alice",
            org="urn:org:ieee",
            role="urn:role:member",
            person="urn:person:alice",
            principal_type=PrincipalType.HUMAN
        )

        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=AssuranceLevel.MEDIUM,
            capability="skill.create",
            requested_permissions=["admin"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        assert decision == PolicyDecision.DENY

    def test_agent_modification_requires_admin(self):
        """Agent self-modification should require admin privileges"""

        # Local socket user with MEDIUM assurance
        principal = Principal(
            principal_id="urn:principal:org:ieee:role:member:person:alice",
            org="urn:org:ieee",
            role="urn:role:member",
            person="urn:person:alice",
            principal_type=PrincipalType.HUMAN
        )

        decision, reason = self.policy_engine.authorize(
            principal=principal,
            assurance_level=AssuranceLevel.MEDIUM,
            capability="agent.modify_config",
            requested_permissions=["admin", "write"],
            granted_permissions=["chat", "query", "read"],
            channel="cli"
        )

        assert decision == PolicyDecision.DENY


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
