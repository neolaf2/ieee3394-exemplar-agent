"""
Principal Registry

Central registry for principals and credential bindings.
Handles:
- Principal storage and retrieval
- Channel identity resolution
- Credential binding management
"""

import json
import logging
from pathlib import Path
from typing import Optional, List, Dict, Any

from .principal import Principal, PrincipalType, ClientPrincipalAssertion
from .credential_binding import CredentialBinding

logger = logging.getLogger(__name__)


class PrincipalRegistry:
    """
    Registry for principals and credential bindings.

    Storage:
        .claude/principals/principals.json
        .claude/principals/credential_bindings.json
    """

    def __init__(self, storage_dir: Optional[Path] = None):
        """
        Initialize registry.

        Args:
            storage_dir: Directory for principal storage (default: .claude/principals)
        """
        if storage_dir is None:
            storage_dir = Path.home() / ".claude" / "principals"

        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.principals_file = self.storage_dir / "principals.json"
        self.bindings_file = self.storage_dir / "credential_bindings.json"

        # In-memory caches
        self._principals: Dict[str, Principal] = {}
        self._bindings: List[CredentialBinding] = []

        # Load from disk
        self._load()

        # Ensure system and anonymous principals exist
        self._ensure_builtin_principals()

    def _load(self) -> None:
        """Load principals and bindings from disk"""
        # Load principals
        if self.principals_file.exists():
            try:
                with open(self.principals_file) as f:
                    data = json.load(f)
                    for principal_data in data:
                        principal = Principal.from_dict(principal_data)
                        self._principals[principal.principal_id] = principal
                logger.info(f"Loaded {len(self._principals)} principals")
            except Exception as e:
                logger.error(f"Failed to load principals: {e}")
                self._principals = {}

        # Load bindings
        if self.bindings_file.exists():
            try:
                with open(self.bindings_file) as f:
                    data = json.load(f)
                    for binding_data in data:
                        binding = CredentialBinding.from_dict(binding_data)
                        self._bindings.append(binding)
                logger.info(f"Loaded {len(self._bindings)} credential bindings")
            except Exception as e:
                logger.error(f"Failed to load credential bindings: {e}")
                self._bindings = []

    def _save(self) -> None:
        """Save principals and bindings to disk"""
        # Save principals
        try:
            with open(self.principals_file, "w") as f:
                data = [p.to_dict() for p in self._principals.values()]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save principals: {e}")

        # Save bindings
        try:
            with open(self.bindings_file, "w") as f:
                data = [b.to_dict() for b in self._bindings]
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save credential bindings: {e}")

    def _ensure_builtin_principals(self) -> None:
        """Ensure system and anonymous principals exist"""
        system = Principal.system_principal()
        if system.principal_id not in self._principals:
            self._principals[system.principal_id] = system
            logger.info("Created system principal")

        anonymous = Principal.anonymous_principal()
        if anonymous.principal_id not in self._principals:
            self._principals[anonymous.principal_id] = anonymous
            logger.info("Created anonymous principal")

        # Ensure CLI admin principal exists
        cli_admin_id = "urn:principal:org:ieee3394:role:admin:person:owner"
        if cli_admin_id not in self._principals:
            cli_admin = Principal(
                principal_id=cli_admin_id,
                org="urn:org:ieee3394",
                role="urn:role:admin",
                person="urn:person:owner",
                principal_type=PrincipalType.HUMAN,
                display_name="Agent Owner (CLI)",
                is_active=True
            )
            self._principals[cli_admin_id] = cli_admin
            logger.info("Created CLI admin principal")

            # Ensure CLI admin binding exists
            cli_binding = CredentialBinding.create_cli_admin_binding()
            if not any(b.binding_id == cli_binding.binding_id for b in self._bindings):
                self._bindings.append(cli_binding)
                logger.info("Created CLI admin credential binding")

        self._save()

    # =========================================================================
    # PRINCIPAL MANAGEMENT
    # =========================================================================

    def register_principal(self, principal: Principal) -> None:
        """Register a new principal"""
        self._principals[principal.principal_id] = principal
        self._save()
        logger.info(f"Registered principal: {principal.principal_id}")

    def get_principal(self, principal_id: str) -> Optional[Principal]:
        """Get a principal by ID"""
        return self._principals.get(principal_id)

    def list_principals(self, principal_type: Optional[PrincipalType] = None) -> List[Principal]:
        """List all principals, optionally filtered by type"""
        principals = list(self._principals.values())
        if principal_type:
            principals = [p for p in principals if p.principal_type == principal_type]
        return principals

    def update_principal(self, principal: Principal) -> None:
        """Update an existing principal"""
        if principal.principal_id not in self._principals:
            raise ValueError(f"Principal not found: {principal.principal_id}")
        self._principals[principal.principal_id] = principal
        self._save()
        logger.info(f"Updated principal: {principal.principal_id}")

    def delete_principal(self, principal_id: str) -> None:
        """Delete a principal"""
        if principal_id in self._principals:
            del self._principals[principal_id]
            self._save()
            logger.info(f"Deleted principal: {principal_id}")

    # =========================================================================
    # CREDENTIAL BINDING MANAGEMENT
    # =========================================================================

    def register_binding(self, binding: CredentialBinding) -> None:
        """Register a new credential binding"""
        self._bindings.append(binding)
        self._save()
        logger.info(f"Registered credential binding: {binding.binding_id}")

    def get_binding(self, binding_id: str) -> Optional[CredentialBinding]:
        """Get a binding by ID"""
        for binding in self._bindings:
            if binding.binding_id == binding_id:
                return binding
        return None

    def list_bindings(
        self,
        principal_id: Optional[str] = None,
        channel: Optional[str] = None
    ) -> List[CredentialBinding]:
        """List bindings, optionally filtered by principal or channel"""
        bindings = self._bindings
        if principal_id:
            bindings = [b for b in bindings if b.principal_id == principal_id]
        if channel:
            bindings = [b for b in bindings if b.channel == channel]
        return bindings

    def update_binding(self, binding: CredentialBinding) -> None:
        """Update an existing binding"""
        for i, b in enumerate(self._bindings):
            if b.binding_id == binding.binding_id:
                self._bindings[i] = binding
                self._save()
                logger.info(f"Updated credential binding: {binding.binding_id}")
                return
        raise ValueError(f"Binding not found: {binding.binding_id}")

    def delete_binding(self, binding_id: str) -> None:
        """Delete a credential binding"""
        self._bindings = [b for b in self._bindings if b.binding_id != binding_id]
        self._save()
        logger.info(f"Deleted credential binding: {binding_id}")

    # =========================================================================
    # IDENTITY RESOLUTION (Core P3394 requirement)
    # =========================================================================

    def resolve_channel_identity(
        self,
        channel: str,
        channel_identity: str
    ) -> Optional[Principal]:
        """
        Resolve a channel-specific identity to a semantic principal.

        This is the core P3394 requirement: map channel identities to principals.

        Args:
            channel: Channel ID (cli, whatsapp, p3394, etc.)
            channel_identity: Channel-specific identity (phone, email, etc.)

        Returns:
            Principal if found, None otherwise
        """
        # Find matching credential binding
        for binding in self._bindings:
            if binding.matches(channel, channel_identity):
                binding.touch()
                principal = self.get_principal(binding.principal_id)
                if principal and principal.is_active:
                    logger.info(f"Resolved {channel}:{channel_identity} → {principal.principal_id}")
                    return principal

        logger.warning(f"No principal found for {channel}:{channel_identity}")
        return None

    def resolve_assertion(self, assertion: ClientPrincipalAssertion) -> Optional[Principal]:
        """
        Resolve a client principal assertion to a semantic principal.

        Args:
            assertion: Client principal assertion from channel adapter

        Returns:
            Principal if resolved, None otherwise
        """
        principal = self.resolve_channel_identity(
            assertion.channel_id,
            assertion.channel_identity
        )

        if principal:
            assertion.is_resolved = True
            assertion.resolved_principal_id = principal.principal_id

        return principal

    def get_system_principal(self) -> Principal:
        """Get the system principal"""
        return self._principals[Principal.system_principal().principal_id]

    def get_anonymous_principal(self) -> Principal:
        """Get the anonymous principal"""
        return self._principals[Principal.anonymous_principal().principal_id]

    # =========================================================================
    # UTILITY
    # =========================================================================

    def get_stats(self) -> Dict[str, Any]:
        """Get registry statistics"""
        return {
            "total_principals": len(self._principals),
            "total_bindings": len(self._bindings),
            "active_principals": len([p for p in self._principals.values() if p.is_active]),
            "active_bindings": len([b for b in self._bindings if b.is_active and not b.is_expired()]),
            "principals_by_type": {
                ptype.value: len([p for p in self._principals.values() if p.principal_type == ptype])
                for ptype in PrincipalType
            },
            "bindings_by_channel": {
                channel: len([b for b in self._bindings if b.channel == channel])
                for channel in set(b.channel for b in self._bindings)
            }
        }
