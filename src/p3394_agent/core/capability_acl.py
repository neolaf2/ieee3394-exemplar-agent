"""
Capability Access Control List (CACL)

Implements three-layer authorization cascade:
1. Channel Authentication → Channel Identity
2. Principal Resolution → Client Principal (org:role:person)
3. Capability Role Mapping → Access Decision

Each capability declares:
- Visibility: Who can see it exists (PUBLIC, LISTED, PROTECTED, PRIVATE, ADMIN)
- Access: Who can invoke it (role-based with assurance requirements)
- Permissions: Fine-grained LRXMD (List, Read, Execute, Modify, Delete)
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Set, Any, TYPE_CHECKING
from datetime import datetime
import logging
import json
from pathlib import Path

from .auth.principal import AssuranceLevel

if TYPE_CHECKING:
    from ..memory.kstar import KStarMemory

logger = logging.getLogger(__name__)


class CapabilityVisibility(str, Enum):
    """
    Visibility tiers for capabilities.

    Controls whether a capability appears in listings/manifests.
    """
    PUBLIC = "public"        # Listed in manifest, accessible by anyone
    LISTED = "listed"        # Listed in manifest, requires auth to access
    PROTECTED = "protected"  # Not listed, but accessible if you know it exists
    PRIVATE = "private"      # Not listed, internal agent↔subagent only
    ADMIN = "admin"          # Only visible and accessible to admin role


class CapabilityPermission(str, Enum):
    """
    Fine-grained permissions for capabilities.

    LRXMD model (like file permissions but for capabilities):
    - List: Can see the capability exists
    - Read: Can get capability details/description
    - Execute: Can invoke the capability
    - Modify: Can change capability configuration
    - Delete: Can remove the capability
    """
    LIST = "list"
    READ = "read"
    EXECUTE = "execute"
    MODIFY = "modify"
    DELETE = "delete"


# Convenience sets for common permission combinations
PERM_NONE = set()
PERM_LIST_ONLY = {CapabilityPermission.LIST}
PERM_READ_ONLY = {CapabilityPermission.LIST, CapabilityPermission.READ}
PERM_USE = {CapabilityPermission.LIST, CapabilityPermission.READ, CapabilityPermission.EXECUTE}
PERM_MANAGE = {CapabilityPermission.LIST, CapabilityPermission.READ, CapabilityPermission.EXECUTE, CapabilityPermission.MODIFY}
PERM_FULL = {CapabilityPermission.LIST, CapabilityPermission.READ, CapabilityPermission.EXECUTE, CapabilityPermission.MODIFY, CapabilityPermission.DELETE}


@dataclass
class RolePermissionEntry:
    """
    Permission entry for a specific role.
    """
    role: str                                    # Role URN or shorthand (e.g., "admin", "user")
    permissions: Set[CapabilityPermission]       # Granted permissions
    minimum_assurance: AssuranceLevel = AssuranceLevel.NONE  # Minimum auth confidence


@dataclass
class CapabilityAccessControl:
    """
    Access control entry for a single capability.

    Controls both visibility (can you see it?) and access (can you use it?).
    """
    capability_id: str

    # Visibility tier
    visibility: CapabilityVisibility = CapabilityVisibility.LISTED

    # Role-based permissions
    role_permissions: List[RolePermissionEntry] = field(default_factory=list)

    # Explicit denials (override allows)
    denied_roles: List[str] = field(default_factory=list)

    # Minimum assurance for any access
    minimum_assurance: AssuranceLevel = AssuranceLevel.NONE

    # Default for unlisted roles
    default_permissions: Set[CapabilityPermission] = field(default_factory=set)

    # Metadata
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)

    def get_permissions_for_role(
        self,
        role: str,
        assurance: AssuranceLevel = AssuranceLevel.NONE
    ) -> Set[CapabilityPermission]:
        """
        Get permissions for a specific role.

        Args:
            role: Role URN or shorthand
            assurance: Current authentication assurance level

        Returns:
            Set of granted permissions
        """
        # Check explicit denial
        if role in self.denied_roles:
            return set()

        # Check minimum assurance
        if self._assurance_rank(assurance) < self._assurance_rank(self.minimum_assurance):
            return set()

        # Find role entry
        for entry in self.role_permissions:
            if entry.role == role or entry.role == "*":
                # Check role-specific assurance requirement
                if self._assurance_rank(assurance) >= self._assurance_rank(entry.minimum_assurance):
                    return entry.permissions

        # Return default if no specific entry
        return self.default_permissions

    def can_list(self, role: str, assurance: AssuranceLevel = AssuranceLevel.NONE) -> bool:
        """Check if role can list this capability"""
        return CapabilityPermission.LIST in self.get_permissions_for_role(role, assurance)

    def can_read(self, role: str, assurance: AssuranceLevel = AssuranceLevel.NONE) -> bool:
        """Check if role can read this capability's details"""
        return CapabilityPermission.READ in self.get_permissions_for_role(role, assurance)

    def can_execute(self, role: str, assurance: AssuranceLevel = AssuranceLevel.NONE) -> bool:
        """Check if role can execute this capability"""
        return CapabilityPermission.EXECUTE in self.get_permissions_for_role(role, assurance)

    def can_modify(self, role: str, assurance: AssuranceLevel = AssuranceLevel.NONE) -> bool:
        """Check if role can modify this capability"""
        return CapabilityPermission.MODIFY in self.get_permissions_for_role(role, assurance)

    def can_delete(self, role: str, assurance: AssuranceLevel = AssuranceLevel.NONE) -> bool:
        """Check if role can delete this capability"""
        return CapabilityPermission.DELETE in self.get_permissions_for_role(role, assurance)

    def is_visible_to(self, role: str, is_internal: bool = False) -> bool:
        """
        Check if capability is visible to a role based on visibility tier.

        Args:
            role: Role to check
            is_internal: Whether this is an internal (subagent) request
        """
        if self.visibility == CapabilityVisibility.PUBLIC:
            return True
        elif self.visibility == CapabilityVisibility.LISTED:
            # Listed capabilities visible to any non-anonymous role
            return role != "anonymous"
        elif self.visibility == CapabilityVisibility.ADMIN:
            return role == "admin" or role == "urn:role:admin"
        elif self.visibility == CapabilityVisibility.PRIVATE:
            # Private only visible to internal/admin
            return is_internal or role == "admin" or role == "urn:role:admin"
        elif self.visibility == CapabilityVisibility.PROTECTED:
            # Protected never listed, but accessible if known
            return False

        return False

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

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "capability_id": self.capability_id,
            "visibility": self.visibility.value,
            "role_permissions": [
                {
                    "role": rp.role,
                    "permissions": [p.value for p in rp.permissions],
                    "minimum_assurance": rp.minimum_assurance.value,
                }
                for rp in self.role_permissions
            ],
            "denied_roles": self.denied_roles,
            "minimum_assurance": self.minimum_assurance.value,
            "default_permissions": [p.value for p in self.default_permissions],
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CapabilityAccessControl":
        """Deserialize from dictionary"""
        role_permissions = []
        for rp_data in data.get("role_permissions", []):
            role_permissions.append(RolePermissionEntry(
                role=rp_data["role"],
                permissions={CapabilityPermission(p) for p in rp_data["permissions"]},
                minimum_assurance=AssuranceLevel(rp_data.get("minimum_assurance", "none")),
            ))

        return cls(
            capability_id=data["capability_id"],
            visibility=CapabilityVisibility(data.get("visibility", "listed")),
            role_permissions=role_permissions,
            denied_roles=data.get("denied_roles", []),
            minimum_assurance=AssuranceLevel(data.get("minimum_assurance", "none")),
            default_permissions={CapabilityPermission(p) for p in data.get("default_permissions", [])},
            created_at=datetime.fromisoformat(data["created_at"]) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data["updated_at"]) if data.get("updated_at") else datetime.utcnow(),
        )


class CapabilityACLRegistry:
    """
    Registry for Capability Access Control Lists.

    Manages ACL storage, lookup, and default ACL generation.

    Supports two storage backends:
    1. Memory server (KStarMemory) - primary, swappable, for dynamic configs
    2. Local JSON file - fallback for persistence
    """

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        memory: Optional["KStarMemory"] = None
    ):
        """
        Initialize ACL registry.

        Args:
            storage_path: Path to ACL storage file (JSON) - fallback storage
            memory: KStarMemory instance for primary storage
        """
        self._acls: Dict[str, CapabilityAccessControl] = {}
        self._storage_path = storage_path
        self._memory = memory
        self._initialized = False

    def set_memory(self, memory: "KStarMemory") -> None:
        """Set the memory backend (for delayed initialization)"""
        self._memory = memory

    async def initialize(self) -> None:
        """
        Initialize ACLs from storage.

        Loads from memory server first, then falls back to local file.
        """
        if self._initialized:
            return

        # Try loading from memory server first
        if self._memory:
            await self._load_from_memory()

        # If no ACLs from memory, try local file
        if not self._acls and self._storage_path and self._storage_path.exists():
            self._load_from_file()

        self._initialized = True

    async def _load_from_memory(self) -> None:
        """Load ACLs from memory server"""
        try:
            acl_dicts = await self._memory.list_acls()

            for acl_data in acl_dicts:
                acl = CapabilityAccessControl.from_dict(acl_data)
                self._acls[acl.capability_id] = acl

            if self._acls:
                logger.info(f"Loaded {len(self._acls)} capability ACLs from memory server")
        except Exception as e:
            logger.warning(f"Failed to load ACLs from memory server: {e}")

    def _load_from_file(self) -> None:
        """Load ACLs from local JSON file (fallback)"""
        if not self._storage_path or not self._storage_path.exists():
            return

        try:
            with open(self._storage_path) as f:
                data = json.load(f)

            for acl_data in data.get("acls", []):
                acl = CapabilityAccessControl.from_dict(acl_data)
                self._acls[acl.capability_id] = acl

            logger.info(f"Loaded {len(self._acls)} capability ACLs from file")
        except Exception as e:
            logger.error(f"Failed to load capability ACLs from file: {e}")

    async def _save_to_memory(self, acl: CapabilityAccessControl) -> None:
        """Save ACL to memory server"""
        if not self._memory:
            return

        try:
            await self._memory.store_acl(acl.to_dict())
        except Exception as e:
            logger.warning(f"Failed to save ACL to memory server: {e}")

    def _save_to_file(self) -> None:
        """Save ACLs to local JSON file (fallback)"""
        if not self._storage_path:
            return

        try:
            self._storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "acls": [acl.to_dict() for acl in self._acls.values()]
            }

            with open(self._storage_path, "w") as f:
                json.dump(data, f, indent=2)

            logger.debug(f"Saved {len(self._acls)} capability ACLs to file")
        except Exception as e:
            logger.error(f"Failed to save capability ACLs to file: {e}")

    async def sync_to_memory(self) -> int:
        """
        Sync all local ACLs to memory server.

        Useful for bootstrapping or migration.

        Returns:
            Number of ACLs synced
        """
        if not self._memory:
            logger.warning("No memory server configured for ACL sync")
            return 0

        count = 0
        for acl in self._acls.values():
            try:
                await self._memory.store_acl(acl.to_dict())
                count += 1
            except Exception as e:
                logger.warning(f"Failed to sync ACL {acl.capability_id}: {e}")

        logger.info(f"Synced {count} ACLs to memory server")
        return count

    def register(self, acl: CapabilityAccessControl) -> None:
        """
        Register or update an ACL (sync version for initialization).

        Use register_async() for runtime updates.
        """
        acl.updated_at = datetime.utcnow()
        self._acls[acl.capability_id] = acl
        self._save_to_file()
        logger.debug(f"Registered ACL for capability: {acl.capability_id}")

    async def register_async(self, acl: CapabilityAccessControl) -> None:
        """Register or update an ACL with memory server sync"""
        acl.updated_at = datetime.utcnow()
        self._acls[acl.capability_id] = acl

        # Save to both memory and file
        await self._save_to_memory(acl)
        self._save_to_file()
        logger.debug(f"Registered ACL for capability: {acl.capability_id}")

    def get(self, capability_id: str) -> Optional[CapabilityAccessControl]:
        """Get ACL for a capability"""
        return self._acls.get(capability_id)

    def get_or_default(self, capability_id: str) -> CapabilityAccessControl:
        """Get ACL or create a default one"""
        if capability_id in self._acls:
            return self._acls[capability_id]

        # Create default ACL based on capability_id pattern
        return self._create_default_acl(capability_id)

    def delete(self, capability_id: str) -> None:
        """Delete an ACL (sync version)"""
        if capability_id in self._acls:
            del self._acls[capability_id]
            self._save_to_file()

    async def delete_async(self, capability_id: str) -> None:
        """Delete an ACL with memory server sync"""
        if capability_id in self._acls:
            del self._acls[capability_id]
            self._save_to_file()

            # Also delete from memory if available
            if self._memory:
                try:
                    await self._memory.delete_acl(capability_id)
                except Exception as e:
                    logger.warning(f"Failed to delete ACL from memory: {e}")

    def list_all(self) -> List[CapabilityAccessControl]:
        """List all ACLs"""
        return list(self._acls.values())

    def _create_default_acl(self, capability_id: str) -> CapabilityAccessControl:
        """
        Create a default ACL based on capability_id pattern.

        Patterns:
        - core.* → PRIVATE, admin only
        - internal.* → PRIVATE, admin only
        - legacy.command.* → Based on command type
        - * → LISTED, authenticated users
        """
        # Default visibility and permissions based on naming convention
        if capability_id.startswith("core.") or capability_id.startswith("internal."):
            # Internal capabilities
            return CapabilityAccessControl(
                capability_id=capability_id,
                visibility=CapabilityVisibility.PRIVATE,
                role_permissions=[
                    RolePermissionEntry(role="admin", permissions=PERM_FULL),
                    RolePermissionEntry(role="system", permissions=PERM_FULL),
                ],
                minimum_assurance=AssuranceLevel.HIGH,
            )

        elif capability_id.startswith("legacy.command."):
            # Legacy commands - map to appropriate visibility
            cmd_name = capability_id.split(".")[-1]

            if cmd_name in ["help", "about", "version"]:
                # Public commands
                return CapabilityAccessControl(
                    capability_id=capability_id,
                    visibility=CapabilityVisibility.PUBLIC,
                    role_permissions=[
                        RolePermissionEntry(role="*", permissions=PERM_USE),
                    ],
                    default_permissions=PERM_USE,
                )

            elif cmd_name in ["login", "startSession"]:
                # Session commands - public but limited
                return CapabilityAccessControl(
                    capability_id=capability_id,
                    visibility=CapabilityVisibility.PUBLIC,
                    role_permissions=[
                        RolePermissionEntry(role="*", permissions=PERM_USE),
                    ],
                    default_permissions=PERM_USE,
                )

            elif cmd_name in ["configure", "shutdown", "restart"]:
                # Admin commands
                return CapabilityAccessControl(
                    capability_id=capability_id,
                    visibility=CapabilityVisibility.ADMIN,
                    role_permissions=[
                        RolePermissionEntry(role="admin", permissions=PERM_FULL, minimum_assurance=AssuranceLevel.HIGH),
                    ],
                    minimum_assurance=AssuranceLevel.HIGH,
                )

            else:
                # Other commands - listed for authenticated
                return CapabilityAccessControl(
                    capability_id=capability_id,
                    visibility=CapabilityVisibility.LISTED,
                    role_permissions=[
                        RolePermissionEntry(role="admin", permissions=PERM_FULL),
                        RolePermissionEntry(role="operator", permissions=PERM_USE),
                        RolePermissionEntry(role="user", permissions=PERM_USE),
                    ],
                    default_permissions=PERM_READ_ONLY,
                )

        else:
            # Default: listed, authenticated users can use
            return CapabilityAccessControl(
                capability_id=capability_id,
                visibility=CapabilityVisibility.LISTED,
                role_permissions=[
                    RolePermissionEntry(role="admin", permissions=PERM_FULL),
                    RolePermissionEntry(role="operator", permissions=PERM_USE),
                    RolePermissionEntry(role="user", permissions=PERM_USE),
                ],
                default_permissions=PERM_READ_ONLY,
            )


# ============================================================================
# Built-in Capability ACLs
# ============================================================================

def create_builtin_acls() -> List[CapabilityAccessControl]:
    """
    Create ACLs for built-in/implied capabilities.

    These are the core capabilities that every agent has.
    """
    return [
        # Public commands (anyone can use)
        CapabilityAccessControl(
            capability_id="legacy.command.help",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="*", permissions=PERM_USE),
            ],
            default_permissions=PERM_USE,
        ),
        CapabilityAccessControl(
            capability_id="legacy.command.about",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="*", permissions=PERM_USE),
            ],
            default_permissions=PERM_USE,
        ),
        CapabilityAccessControl(
            capability_id="legacy.command.version",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="*", permissions=PERM_USE),
            ],
            default_permissions=PERM_USE,
        ),
        CapabilityAccessControl(
            capability_id="legacy.command.login",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="*", permissions=PERM_USE),
            ],
            default_permissions=PERM_USE,
        ),

        # Listed commands (visible to authenticated, need perms to use)
        CapabilityAccessControl(
            capability_id="legacy.command.status",
            visibility=CapabilityVisibility.LISTED,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="user", permissions=PERM_READ_ONLY),
            ],
            default_permissions=PERM_LIST_ONLY,
        ),
        CapabilityAccessControl(
            capability_id="legacy.command.listSkills",
            visibility=CapabilityVisibility.LISTED,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="user", permissions=PERM_USE),
            ],
            default_permissions=PERM_LIST_ONLY,
        ),
        CapabilityAccessControl(
            capability_id="legacy.command.endpoints",
            visibility=CapabilityVisibility.LISTED,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="user", permissions=PERM_READ_ONLY),
            ],
            default_permissions=PERM_LIST_ONLY,
        ),

        # Admin commands
        CapabilityAccessControl(
            capability_id="legacy.command.configure",
            visibility=CapabilityVisibility.ADMIN,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL, minimum_assurance=AssuranceLevel.HIGH),
            ],
            minimum_assurance=AssuranceLevel.HIGH,
        ),

        # Core internal capabilities
        CapabilityAccessControl(
            capability_id="core.message.handle",
            visibility=CapabilityVisibility.PRIVATE,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="system", permissions=PERM_FULL),
            ],
            minimum_assurance=AssuranceLevel.HIGH,
        ),
        CapabilityAccessControl(
            capability_id="core.llm.invoke",
            visibility=CapabilityVisibility.PRIVATE,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="system", permissions=PERM_FULL),
            ],
            minimum_assurance=AssuranceLevel.MEDIUM,
        ),
        CapabilityAccessControl(
            capability_id="core.tool.execute",
            visibility=CapabilityVisibility.PRIVATE,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
            ],
            minimum_assurance=AssuranceLevel.MEDIUM,
        ),
        CapabilityAccessControl(
            capability_id="core.subagent.delegate",
            visibility=CapabilityVisibility.PRIVATE,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="system", permissions=PERM_FULL),
            ],
            minimum_assurance=AssuranceLevel.HIGH,
        ),

        # Session management
        CapabilityAccessControl(
            capability_id="core.session.create",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="*", permissions=PERM_USE),
            ],
            default_permissions=PERM_USE,
        ),
        CapabilityAccessControl(
            capability_id="core.session.destroy",
            visibility=CapabilityVisibility.LISTED,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="user", permissions=PERM_USE),
            ],
            default_permissions=PERM_NONE,
        ),

        # Chat capability
        CapabilityAccessControl(
            capability_id="core.chat",
            visibility=CapabilityVisibility.PUBLIC,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE),
                RolePermissionEntry(role="user", permissions=PERM_USE),
                RolePermissionEntry(role="anonymous", permissions=PERM_READ_ONLY),
            ],
            default_permissions=PERM_READ_ONLY,
        ),
        CapabilityAccessControl(
            capability_id="core.chat.with_tools",
            visibility=CapabilityVisibility.PROTECTED,
            role_permissions=[
                RolePermissionEntry(role="admin", permissions=PERM_FULL),
                RolePermissionEntry(role="operator", permissions=PERM_USE, minimum_assurance=AssuranceLevel.MEDIUM),
            ],
            minimum_assurance=AssuranceLevel.MEDIUM,
        ),
    ]
