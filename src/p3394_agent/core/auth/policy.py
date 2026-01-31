"""
Authorization Policy Engine

Implements capability-level authorization with:
- Policy rules (allowlist, assurance, scopes)
- Policy evaluation (Policy Decision Point)
- Default policies for system/anonymous/admin
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any, Callable

from .principal import Principal, PrincipalType, AssuranceLevel

logger = logging.getLogger(__name__)


class PolicyDecision(str, Enum):
    """Authorization decision"""
    ALLOW = "allow"
    DENY = "deny"


@dataclass
class AuthorizationContext:
    """Context for authorization decisions"""
    principal: Principal
    assurance_level: AssuranceLevel
    capability: str
    requested_permissions: List[str]
    granted_permissions: List[str] = field(default_factory=list)
    channel: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PolicyRule:
    """
    A single policy rule.

    Rules are evaluated in order. First matching rule wins.
    """
    rule_id: str
    description: str
    condition: Callable[[AuthorizationContext], bool]  # Predicate function
    decision: PolicyDecision
    reason: str = ""
    priority: int = 100  # Lower = higher priority

    def evaluate(self, context: AuthorizationContext) -> Optional[tuple[PolicyDecision, str]]:
        """
        Evaluate this rule against the context.

        Returns:
            (decision, reason) if rule matches, None otherwise
        """
        try:
            if self.condition(context):
                reason = self.reason or self.description
                logger.debug(f"Rule {self.rule_id} matched: {reason}")
                return (self.decision, reason)
        except Exception as e:
            logger.error(f"Error evaluating rule {self.rule_id}: {e}")

        return None


@dataclass
class Policy:
    """
    Collection of policy rules.

    Rules are evaluated in priority order (lower priority value = higher priority).
    First matching rule determines the decision.
    """
    policy_id: str
    name: str
    description: str = ""
    rules: List[PolicyRule] = field(default_factory=list)
    is_active: bool = True

    def add_rule(self, rule: PolicyRule) -> None:
        """Add a rule to this policy"""
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def evaluate(self, context: AuthorizationContext) -> tuple[PolicyDecision, str]:
        """
        Evaluate this policy against the context.

        Returns:
            (decision, reason) tuple
        """
        if not self.is_active:
            return (PolicyDecision.DENY, "Policy is inactive")

        # Evaluate rules in priority order
        for rule in self.rules:
            result = rule.evaluate(context)
            if result:
                decision, reason = result
                logger.info(f"Policy {self.policy_id}: {decision.value} - {reason}")
                return (decision, f"{self.policy_id}:{rule.rule_id} - {reason}")

        # Default deny if no rules matched
        return (PolicyDecision.DENY, f"No matching rule in policy {self.policy_id}")


class PolicyEngine:
    """
    Policy Decision Point (PDP) for authorization.

    Evaluates policies to make allow/deny decisions for capability access.
    """

    def __init__(self, enforcement_enabled: bool = False):
        """
        Initialize policy engine.

        Args:
            enforcement_enabled: Whether to enforce authorization (default: False for Phase 1)
        """
        self.enforcement_enabled = enforcement_enabled
        self.channel_enforcement: Dict[str, bool] = {}
        self.policies: List[Policy] = []

        # Create default policy
        self._create_default_policy()

    def _create_default_policy(self) -> None:
        """Create the default authorization policy"""
        policy = Policy(
            policy_id="default",
            name="Default Authorization Policy",
            description="P3394 default authorization rules",
            is_active=True
        )

        # Rule 1: System principal always allowed (highest priority)
        policy.add_rule(PolicyRule(
            rule_id="allow-system",
            description="System principal has all permissions",
            condition=lambda ctx: ctx.principal.principal_type == PrincipalType.SYSTEM,
            decision=PolicyDecision.ALLOW,
            reason="System principal",
            priority=1
        ))

        # Rule 2: Admin role always allowed
        policy.add_rule(PolicyRule(
            rule_id="allow-admin",
            description="Admin role has all permissions",
            condition=lambda ctx: ctx.principal.role == "urn:role:admin",
            decision=PolicyDecision.ALLOW,
            reason="Admin role",
            priority=2
        ))

        # Rule 3: Allow anonymous for login and help commands (Phase 3)
        policy.add_rule(PolicyRule(
            rule_id="allow-anonymous-login-help",
            description="Anonymous users can access login and help",
            condition=lambda ctx: (
                ctx.principal.principal_type == PrincipalType.ANONYMOUS
                and ctx.capability in ["login", "help", "about", "version",
                                      "legacy.command.login", "legacy.command.help",
                                      "legacy.command.about", "legacy.command.version"]
            ),
            decision=PolicyDecision.ALLOW,
            reason="Public command accessible without authentication",
            priority=3
        ))

        # Rule 4: Deny anonymous for privileged capabilities
        policy.add_rule(PolicyRule(
            rule_id="deny-anonymous-privileged",
            description="Anonymous principal denied for privileged capabilities",
            condition=lambda ctx: (
                ctx.principal.principal_type == PrincipalType.ANONYMOUS
                and any(perm in ["admin", "write", "execute"] for perm in ctx.requested_permissions)
            ),
            decision=PolicyDecision.DENY,
            reason="Anonymous principal cannot access privileged capabilities",
            priority=10
        ))

        # Rule 5: HIGH assurance for admin capabilities
        policy.add_rule(PolicyRule(
            rule_id="require-high-assurance-admin",
            description="Admin capabilities require HIGH assurance",
            condition=lambda ctx: (
                "admin" in ctx.requested_permissions
                and ctx.assurance_level not in [AssuranceLevel.HIGH, AssuranceLevel.CRYPTOGRAPHIC]
            ),
            decision=PolicyDecision.DENY,
            reason="Admin capabilities require HIGH or CRYPTOGRAPHIC assurance",
            priority=20
        ))

        # Rule 6: MEDIUM assurance for write capabilities
        policy.add_rule(PolicyRule(
            rule_id="require-medium-assurance-write",
            description="Write capabilities require at least MEDIUM assurance",
            condition=lambda ctx: (
                "write" in ctx.requested_permissions
                and ctx.assurance_level in [AssuranceLevel.NONE, AssuranceLevel.LOW]
            ),
            decision=PolicyDecision.DENY,
            reason="Write capabilities require at least MEDIUM assurance",
            priority=30
        ))

        # Rule 7: Check granted permissions
        policy.add_rule(PolicyRule(
            rule_id="check-granted-permissions",
            description="Allow if all requested permissions are granted",
            condition=lambda ctx: (
                "*" in ctx.granted_permissions
                or all(perm in ctx.granted_permissions for perm in ctx.requested_permissions)
            ),
            decision=PolicyDecision.ALLOW,
            reason="All requested permissions are granted",
            priority=40
        ))

        # Rule 8: Allow read-only for any authenticated user
        policy.add_rule(PolicyRule(
            rule_id="allow-read-authenticated",
            description="Allow read-only for authenticated users",
            condition=lambda ctx: (
                ctx.principal.principal_type != PrincipalType.ANONYMOUS
                and all(perm in ["read", "query", "chat"] for perm in ctx.requested_permissions)
            ),
            decision=PolicyDecision.ALLOW,
            reason="Read-only access for authenticated user",
            priority=50
        ))

        # Rule 9: Default deny (lowest priority)
        policy.add_rule(PolicyRule(
            rule_id="default-deny",
            description="Default deny if no other rule matched",
            condition=lambda ctx: True,  # Always matches
            decision=PolicyDecision.DENY,
            reason="No authorization rule matched",
            priority=999
        ))

        self.policies.append(policy)
        logger.info("Created default authorization policy")

    def enable_enforcement(self) -> None:
        """Enable global enforcement"""
        self.enforcement_enabled = True
        logger.info("Authorization enforcement enabled globally")

    def disable_enforcement(self) -> None:
        """Disable global enforcement"""
        self.enforcement_enabled = False
        logger.warning("Authorization enforcement disabled globally")

    def enable_enforcement_for_channel(self, channel: str) -> None:
        """Enable enforcement for a specific channel"""
        self.channel_enforcement[channel] = True
        logger.info(f"Authorization enforcement enabled for channel: {channel}")

    def disable_enforcement_for_channel(self, channel: str) -> None:
        """Disable enforcement for a specific channel"""
        self.channel_enforcement[channel] = False
        logger.info(f"Authorization enforcement disabled for channel: {channel}")

    def is_enforcement_enabled_for_channel(self, channel: Optional[str]) -> bool:
        """Check if enforcement is enabled for a channel"""
        if not self.enforcement_enabled:
            return False
        if channel is None:
            return True
        return self.channel_enforcement.get(channel, False)

    def add_policy(self, policy: Policy) -> None:
        """Add a custom policy"""
        self.policies.append(policy)
        logger.info(f"Added policy: {policy.policy_id}")

    def authorize(
        self,
        principal: Principal,
        assurance_level: AssuranceLevel,
        capability: str,
        requested_permissions: List[str],
        granted_permissions: List[str] = None,
        channel: Optional[str] = None,
        metadata: Dict[str, Any] = None
    ) -> tuple[PolicyDecision, str]:
        """
        Make an authorization decision.

        Args:
            principal: The principal requesting access
            assurance_level: Authentication assurance level
            capability: Capability being accessed
            requested_permissions: Permissions required for capability
            granted_permissions: Permissions already granted to principal
            channel: Channel making the request
            metadata: Additional context

        Returns:
            (decision, reason) tuple
        """
        if granted_permissions is None:
            granted_permissions = []
        if metadata is None:
            metadata = {}

        # Check if enforcement is enabled for this channel
        if not self.is_enforcement_enabled_for_channel(channel):
            logger.debug(f"Authorization check (enforcement disabled): capability={capability}, principal={principal.principal_id}")
            return (PolicyDecision.ALLOW, "Authorization enforcement disabled")

        # Build context
        context = AuthorizationContext(
            principal=principal,
            assurance_level=assurance_level,
            capability=capability,
            requested_permissions=requested_permissions,
            granted_permissions=granted_permissions,
            channel=channel,
            metadata=metadata
        )

        # Evaluate policies
        for policy in self.policies:
            if policy.is_active:
                decision, reason = policy.evaluate(context)
                if decision == PolicyDecision.ALLOW:
                    logger.info(f"Authorization ALLOW: {capability} for {principal.principal_id} - {reason}")
                    return (decision, reason)
                elif decision == PolicyDecision.DENY:
                    logger.warning(f"Authorization DENY: {capability} for {principal.principal_id} - {reason}")
                    return (decision, reason)

        # Should never reach here (default policy has catch-all deny)
        return (PolicyDecision.DENY, "No active policy evaluated")

    def get_stats(self) -> Dict[str, Any]:
        """Get policy engine statistics"""
        return {
            "enforcement_enabled": self.enforcement_enabled,
            "total_policies": len(self.policies),
            "active_policies": len([p for p in self.policies if p.is_active]),
            "channel_enforcement": self.channel_enforcement.copy(),
            "policies": [
                {
                    "policy_id": p.policy_id,
                    "name": p.name,
                    "is_active": p.is_active,
                    "rule_count": len(p.rules)
                }
                for p in self.policies
            ]
        }
