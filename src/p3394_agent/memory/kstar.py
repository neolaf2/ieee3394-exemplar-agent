"""
KSTAR Memory Integration

KSTAR = Knowledge, Situation, Task, Action, Result
A universal representation schema for agent memory.

This implementation persists to the agent's STM directories.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class KStarMemory:
    """
    KSTAR Memory for the IEEE 3394 Agent.

    Stores:
    - Traces: Complete K→S→T→A→R episodes (persisted to STM)
    - Perceptions: Facts and observations
    - Skills: Learned capabilities
    - ACLs: Capability Access Control Lists (bootstrap data)
    - Principals: Principal definitions (bootstrap data)
    """

    def __init__(self, storage=None):
        """
        Initialize KSTAR storage.

        Args:
            storage: AgentStorage instance for persistence
        """
        self.storage = storage
        self.traces: List[Dict[str, Any]] = []
        self.perceptions: List[Dict[str, Any]] = []
        self.skills: List[Dict[str, Any]] = []
        # Bootstrap data - loaded from configuration/memory server
        self.capability_acls: Dict[str, Dict[str, Any]] = {}
        self.principals: Dict[str, Dict[str, Any]] = {}
        self.credential_bindings: Dict[str, Dict[str, Any]] = {}

    async def store_trace(self, trace: Dict[str, Any]) -> str:
        """
        Store a KSTAR trace (episode).

        A trace represents a complete K→S→T→A→R cycle.

        Args:
            trace: Dict with keys: situation, task, action, result (optional), mode

        Returns:
            Trace ID
        """
        trace_id = f"trace_{len(self.traces)}"
        trace_entry = {
            "id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **trace
        }
        self.traces.append(trace_entry)

        # Persist to storage if available
        if self.storage and trace.get("session_id"):
            try:
                self.storage.append_trace(trace["session_id"], trace_entry)
            except Exception as e:
                logger.warning(f"Failed to persist trace to storage: {e}")

        logger.debug(f"Stored trace {trace_id}")
        return trace_id

    async def store_perception(self, perception: Dict[str, Any]) -> str:
        """
        Store a perception (fact/observation).

        Perceptions are declarative knowledge without action plans.

        Args:
            perception: Dict with keys: content, context, tags, importance

        Returns:
            Perception ID
        """
        perception_id = f"perception_{len(self.perceptions)}"
        perception_entry = {
            "id": perception_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **perception
        }
        self.perceptions.append(perception_entry)
        logger.debug(f"Stored perception {perception_id}")
        return perception_id

    async def store_skill(self, skill: Dict[str, Any]) -> str:
        """
        Store a skill definition.

        Args:
            skill: Dict with keys: name, description, domain, capability

        Returns:
            Skill ID
        """
        skill_id = f"skill_{len(self.skills)}"
        skill_entry = {
            "id": skill_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **skill
        }
        self.skills.append(skill_entry)
        logger.info(f"Stored skill: {skill.get('name', skill_id)}")
        return skill_id

    async def query(self, domain: str, goal: str) -> Optional[Dict[str, Any]]:
        """
        Query KSTAR memory for matching traces.

        Simple implementation for MVP - just searches for domain match.
        """
        for trace in reversed(self.traces):
            situation = trace.get("situation", {})
            if situation.get("domain") == domain:
                return trace
        return None

    async def find_skills(self, domain: str, goal: str) -> List[Dict[str, Any]]:
        """Find skills capable of handling a task"""
        matching = []
        for skill in self.skills:
            if skill.get("domain") == domain:
                matching.append(skill)
        return matching

    async def list_skills(self) -> List[Dict[str, Any]]:
        """List all stored skills"""
        return self.skills.copy()

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "trace_count": len(self.traces),
            "perception_count": len(self.perceptions),
            "skill_count": len(self.skills),
            "acl_count": len(self.capability_acls),
            "principal_count": len(self.principals),
            "binding_count": len(self.credential_bindings)
        }

    # =========================================================================
    # ACL Storage (Bootstrap Data)
    # =========================================================================

    async def store_acl(self, acl: Dict[str, Any]) -> str:
        """
        Store a capability ACL definition.

        Args:
            acl: Dict with keys: capability_id, visibility, default_permissions, role_permissions

        Returns:
            ACL ID (same as capability_id)
        """
        capability_id = acl.get("capability_id")
        if not capability_id:
            raise ValueError("ACL must have capability_id")

        self.capability_acls[capability_id] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **acl
        }
        logger.debug(f"Stored ACL for capability: {capability_id}")
        return capability_id

    async def get_acl(self, capability_id: str) -> Optional[Dict[str, Any]]:
        """Get ACL for a specific capability"""
        return self.capability_acls.get(capability_id)

    async def list_acls(self) -> List[Dict[str, Any]]:
        """List all stored ACLs"""
        return list(self.capability_acls.values())

    async def delete_acl(self, capability_id: str) -> bool:
        """Delete an ACL"""
        if capability_id in self.capability_acls:
            del self.capability_acls[capability_id]
            logger.debug(f"Deleted ACL for capability: {capability_id}")
            return True
        return False

    async def bulk_store_acls(self, acls: List[Dict[str, Any]]) -> int:
        """
        Bulk store multiple ACLs (for bootstrap).

        Args:
            acls: List of ACL definitions

        Returns:
            Number of ACLs stored
        """
        count = 0
        for acl in acls:
            try:
                await self.store_acl(acl)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store ACL: {e}")
        logger.info(f"Bulk stored {count} ACLs")
        return count

    # =========================================================================
    # Principal Storage (Bootstrap Data)
    # =========================================================================

    async def store_principal(self, principal: Dict[str, Any]) -> str:
        """
        Store a principal definition.

        Args:
            principal: Dict with keys: urn, display_name, roles, organization, metadata

        Returns:
            Principal URN
        """
        urn = principal.get("urn")
        if not urn:
            raise ValueError("Principal must have urn")

        self.principals[urn] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **principal
        }
        logger.debug(f"Stored principal: {urn}")
        return urn

    async def get_principal(self, urn: str) -> Optional[Dict[str, Any]]:
        """Get principal by URN"""
        return self.principals.get(urn)

    async def list_principals(self) -> List[Dict[str, Any]]:
        """List all stored principals"""
        return list(self.principals.values())

    async def bulk_store_principals(self, principals: List[Dict[str, Any]]) -> int:
        """
        Bulk store multiple principals (for bootstrap).

        Args:
            principals: List of principal definitions

        Returns:
            Number of principals stored
        """
        count = 0
        for principal in principals:
            try:
                await self.store_principal(principal)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store principal: {e}")
        logger.info(f"Bulk stored {count} principals")
        return count

    # =========================================================================
    # Credential Binding Storage (Bootstrap Data)
    # =========================================================================

    async def store_credential_binding(self, binding: Dict[str, Any]) -> str:
        """
        Store a credential→principal binding.

        Args:
            binding: Dict with keys: credential_type, credential_value, principal_urn, assurance_level

        Returns:
            Binding ID
        """
        # Create binding key from credential type and value
        cred_type = binding.get("credential_type", "unknown")
        cred_value = binding.get("credential_value", "unknown")
        binding_id = f"{cred_type}:{cred_value}"

        self.credential_bindings[binding_id] = {
            "id": binding_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **binding
        }
        logger.debug(f"Stored credential binding: {binding_id}")
        return binding_id

    async def get_credential_binding(self, credential_type: str, credential_value: str) -> Optional[Dict[str, Any]]:
        """Get binding for a specific credential"""
        binding_id = f"{credential_type}:{credential_value}"
        return self.credential_bindings.get(binding_id)

    async def list_credential_bindings(self) -> List[Dict[str, Any]]:
        """List all credential bindings"""
        return list(self.credential_bindings.values())

    async def bulk_store_credential_bindings(self, bindings: List[Dict[str, Any]]) -> int:
        """
        Bulk store multiple credential bindings (for bootstrap).

        Args:
            bindings: List of binding definitions

        Returns:
            Number of bindings stored
        """
        count = 0
        for binding in bindings:
            try:
                await self.store_credential_binding(binding)
                count += 1
            except Exception as e:
                logger.warning(f"Failed to store credential binding: {e}")
        logger.info(f"Bulk stored {count} credential bindings")
        return count

    # =========================================================================
    # Bootstrap Loading
    # =========================================================================

    async def load_bootstrap_data(self, bootstrap_config: Dict[str, Any]) -> Dict[str, int]:
        """
        Load bootstrap data from configuration.

        This is called at startup to preload ACLs, principals, and bindings.

        Args:
            bootstrap_config: Dict with keys: acls, principals, credential_bindings

        Returns:
            Dict with counts of loaded items
        """
        results = {
            "acls": 0,
            "principals": 0,
            "credential_bindings": 0
        }

        # Load ACLs
        if "acls" in bootstrap_config:
            results["acls"] = await self.bulk_store_acls(bootstrap_config["acls"])

        # Load principals
        if "principals" in bootstrap_config:
            results["principals"] = await self.bulk_store_principals(bootstrap_config["principals"])

        # Load credential bindings
        if "credential_bindings" in bootstrap_config:
            results["credential_bindings"] = await self.bulk_store_credential_bindings(
                bootstrap_config["credential_bindings"]
            )

        logger.info(f"Loaded bootstrap data: {results}")
        return results
