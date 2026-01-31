"""
Capability Access Manager

Integrates the three-layer authorization cascade:
1. Channel Authentication → Channel Identity
2. Principal Resolution → Client Principal (org:role:person)
3. Capability Role Mapping → Access Decision

This manager:
- Computes capability access for a session based on resolved principal
- Filters capability lists based on session visibility
- Checks access before capability invocation
- Caches resolved access in session for performance
"""

import logging
from typing import Dict, List, Optional, Set, TYPE_CHECKING
from dataclasses import dataclass

from .capability_acl import (
    CapabilityACLRegistry,
    CapabilityAccessControl,
    CapabilityVisibility,
    CapabilityPermission,
    RolePermissionEntry,
    PERM_NONE,
    PERM_USE,
    PERM_FULL,
    create_builtin_acls,
)
from .auth.principal import Principal, PrincipalType, AssuranceLevel
from .session import Session

if TYPE_CHECKING:
    from .capability_registry import CapabilityRegistry
    from .capability import AgentCapabilityDescriptor

logger = logging.getLogger(__name__)


@dataclass
class AccessDecision:
    """Result of an access check"""
    allowed: bool
    permission: Optional[CapabilityPermission] = None
    reason: str = ""
    required_assurance: Optional[AssuranceLevel] = None
    current_assurance: Optional[AssuranceLevel] = None


class CapabilityAccessManager:
    """
    Manages capability access control decisions.

    This is the central point for:
    - Computing session capability access from principal
    - Filtering capability lists by visibility
    - Authorizing capability invocation
    """

    def __init__(
        self,
        acl_registry: CapabilityACLRegistry,
        capability_registry: "CapabilityRegistry"
    ):
        self.acl_registry = acl_registry
        self.capability_registry = capability_registry

        # Initialize with built-in ACLs
        self._register_builtin_acls()

    def _register_builtin_acls(self) -> None:
        """Register ACLs for built-in capabilities"""
        for acl in create_builtin_acls():
            if not self.acl_registry.get(acl.capability_id):
                self.acl_registry.register(acl)

        logger.info(f"Registered {len(create_builtin_acls())} built-in capability ACLs")

    # =========================================================================
    # Session Capability Resolution
    # =========================================================================

    def compute_session_access(
        self,
        session: Session,
        principal: Optional[Principal] = None,
        assurance: AssuranceLevel = AssuranceLevel.NONE
    ) -> None:
        """
        Compute and cache capability access for a session.

        Called after:
        - Session creation (anonymous access)
        - User authentication (upgraded access)
        - Role change (modified access)

        Args:
            session: Session to update
            principal: Resolved principal (None = anonymous)
            assurance: Current authentication assurance level
        """
        # Determine role from principal
        if principal is None:
            role = "anonymous"
            session.client_principal_id = None
        else:
            # Extract role from principal URN
            # Format: urn:principal:org:{org}:role:{role}:person:{person}
            role = self._extract_role(principal)
            session.client_principal_id = principal.principal_id

        session.client_role = role
        session.assurance_level = assurance.value

        # Compute visible and accessible capabilities
        visible: Set[str] = set()
        accessible: Set[str] = set()
        permissions: Dict[str, Set[str]] = {}

        # Get all capabilities
        all_capabilities = self.capability_registry.list_all()

        for cap in all_capabilities:
            cap_id = cap.capability_id
            acl = self.acl_registry.get_or_default(cap_id)

            # Check visibility
            if acl.is_visible_to(role, session.is_internal_session):
                visible.add(cap_id)

            # Check permissions
            cap_perms = acl.get_permissions_for_role(role, assurance)

            if cap_perms:
                # Convert CapabilityPermission enums to strings
                perm_strings = {p.value for p in cap_perms}
                permissions[cap_id] = perm_strings

                # Track if executable
                if CapabilityPermission.EXECUTE in cap_perms:
                    accessible.add(cap_id)

        # Update session cache
        session.update_capability_cache(visible, accessible, permissions)

        logger.info(
            f"Computed capability access for session {session.id}: "
            f"role={role}, visible={len(visible)}, accessible={len(accessible)}"
        )

    def _extract_role(self, principal: Principal) -> str:
        """Extract role shorthand from principal"""
        # principal.role is like "urn:role:admin" → return "admin"
        if principal.role.startswith("urn:role:"):
            return principal.role[9:]  # len("urn:role:") = 9
        return principal.role

    # =========================================================================
    # Capability Filtering
    # =========================================================================

    def filter_visible_capabilities(
        self,
        session: Session,
        capabilities: Optional[List["AgentCapabilityDescriptor"]] = None
    ) -> List["AgentCapabilityDescriptor"]:
        """
        Filter capabilities to only those visible to the session.

        Used by /listSkills, /listCommands, manifest endpoints.

        Args:
            session: Current session
            capabilities: List to filter (None = all registered)

        Returns:
            Filtered list of capabilities
        """
        if capabilities is None:
            capabilities = self.capability_registry.list_all()

        # Admin sees everything
        if session.client_role in ("admin", "urn:role:admin", "system"):
            return capabilities

        # Filter by visibility cache
        return [
            cap for cap in capabilities
            if cap.capability_id in session.visible_capabilities
        ]

    def filter_accessible_capabilities(
        self,
        session: Session,
        capabilities: Optional[List["AgentCapabilityDescriptor"]] = None
    ) -> List["AgentCapabilityDescriptor"]:
        """
        Filter capabilities to only those executable by the session.

        Args:
            session: Current session
            capabilities: List to filter (None = all registered)

        Returns:
            Filtered list of capabilities
        """
        if capabilities is None:
            capabilities = self.capability_registry.list_all()

        # Admin can execute everything
        if session.client_role in ("admin", "urn:role:admin", "system"):
            return capabilities

        # Filter by accessibility cache
        return [
            cap for cap in capabilities
            if cap.capability_id in session.accessible_capabilities
        ]

    # =========================================================================
    # Access Authorization
    # =========================================================================

    def check_access(
        self,
        session: Session,
        capability_id: str,
        permission: CapabilityPermission = CapabilityPermission.EXECUTE
    ) -> AccessDecision:
        """
        Check if session can perform an operation on a capability.

        Args:
            session: Current session
            capability_id: Capability to check
            permission: Required permission (default: EXECUTE)

        Returns:
            AccessDecision with allow/deny and reason
        """
        # Get ACL
        acl = self.acl_registry.get_or_default(capability_id)

        # Get current assurance level
        try:
            current_assurance = AssuranceLevel(session.assurance_level)
        except ValueError:
            current_assurance = AssuranceLevel.NONE

        # Admin always allowed
        if session.client_role in ("admin", "urn:role:admin"):
            return AccessDecision(
                allowed=True,
                permission=permission,
                reason="Admin role has full access"
            )

        # System principal always allowed
        if session.client_role == "system":
            return AccessDecision(
                allowed=True,
                permission=permission,
                reason="System principal has full access"
            )

        # Check explicit denial
        if session.client_role in acl.denied_roles:
            return AccessDecision(
                allowed=False,
                permission=permission,
                reason=f"Role '{session.client_role}' is explicitly denied"
            )

        # Check minimum assurance
        if self._assurance_rank(current_assurance) < self._assurance_rank(acl.minimum_assurance):
            return AccessDecision(
                allowed=False,
                permission=permission,
                reason=f"Requires {acl.minimum_assurance.value} assurance, have {current_assurance.value}",
                required_assurance=acl.minimum_assurance,
                current_assurance=current_assurance
            )

        # Check role permissions
        role_perms = acl.get_permissions_for_role(session.client_role, current_assurance)

        if permission in role_perms:
            return AccessDecision(
                allowed=True,
                permission=permission,
                reason=f"Role '{session.client_role}' has {permission.value} permission"
            )

        # Check default permissions
        if permission in acl.default_permissions:
            return AccessDecision(
                allowed=True,
                permission=permission,
                reason=f"Default permission allows {permission.value}"
            )

        # Denied
        return AccessDecision(
            allowed=False,
            permission=permission,
            reason=f"Role '{session.client_role}' lacks {permission.value} permission for {capability_id}"
        )

    def authorize_invocation(
        self,
        session: Session,
        capability_id: str
    ) -> AccessDecision:
        """
        Authorize capability invocation.

        Shorthand for check_access with EXECUTE permission.

        Args:
            session: Current session
            capability_id: Capability to invoke

        Returns:
            AccessDecision
        """
        return self.check_access(session, capability_id, CapabilityPermission.EXECUTE)

    @staticmethod
    def _assurance_rank(level: AssuranceLevel) -> int:
        """Get numeric rank for assurance level comparison"""
        ranks = {
            AssuranceLevel.NONE: 0,
            AssuranceLevel.LOW: 1,
            AssuranceLevel.MEDIUM: 2,
            AssuranceLevel.HIGH: 3,
            AssuranceLevel.CRYPTOGRAPHIC: 4,
        }
        return ranks.get(level, 0)

    # =========================================================================
    # ACL Management
    # =========================================================================

    def register_capability_acl(self, acl: CapabilityAccessControl) -> None:
        """Register or update an ACL for a capability"""
        self.acl_registry.register(acl)

    def get_capability_acl(self, capability_id: str) -> CapabilityAccessControl:
        """Get ACL for a capability (creates default if not exists)"""
        return self.acl_registry.get_or_default(capability_id)

    def create_acl_for_capability(
        self,
        capability_id: str,
        visibility: CapabilityVisibility = CapabilityVisibility.LISTED,
        allowed_roles: Optional[List[str]] = None,
        minimum_assurance: AssuranceLevel = AssuranceLevel.NONE
    ) -> CapabilityAccessControl:
        """
        Create and register an ACL for a capability.

        Convenience method for common ACL creation.

        Args:
            capability_id: Capability ID
            visibility: Visibility tier
            allowed_roles: Roles that can use the capability (default: all authenticated)
            minimum_assurance: Minimum auth level required

        Returns:
            Created ACL
        """
        if allowed_roles is None:
            allowed_roles = ["admin", "operator", "user"]

        role_permissions = []
        for role in allowed_roles:
            if role == "admin":
                role_permissions.append(RolePermissionEntry(
                    role=role,
                    permissions=PERM_FULL,
                    minimum_assurance=minimum_assurance
                ))
            else:
                role_permissions.append(RolePermissionEntry(
                    role=role,
                    permissions=PERM_USE,
                    minimum_assurance=minimum_assurance
                ))

        acl = CapabilityAccessControl(
            capability_id=capability_id,
            visibility=visibility,
            role_permissions=role_permissions,
            minimum_assurance=minimum_assurance,
            default_permissions=PERM_NONE,
        )

        self.acl_registry.register(acl)
        return acl

    # =========================================================================
    # Statistics
    # =========================================================================

    def get_stats(self) -> Dict:
        """Get access manager statistics"""
        all_acls = self.acl_registry.list_all()

        by_visibility = {}
        for vis in CapabilityVisibility:
            by_visibility[vis.value] = len([a for a in all_acls if a.visibility == vis])

        return {
            "total_acls": len(all_acls),
            "by_visibility": by_visibility,
            "builtin_acls": len(create_builtin_acls()),
        }
