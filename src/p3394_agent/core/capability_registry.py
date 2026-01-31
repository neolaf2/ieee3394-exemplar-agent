"""
Unified Capability Registry

Single registry for all agent capabilities (replaces separate command/skill/channel registries).
Provides CRUD operations and query interface.
"""

from typing import Dict, List, Optional, Callable, Any
import logging
from pathlib import Path
import json
import yaml

from .capability import (
    AgentCapabilityDescriptor,
    CapabilityKind,
    ExecutionSubstrate,
    InvocationMode,
    ExposureScope
)

logger = logging.getLogger(__name__)


class CapabilityRegistry:
    """
    Unified registry for all agent capabilities.

    Replaces:
    - Command registry (dict[str, SymbolicCommand])
    - Skill registry (dict[str, skill_def])
    - Channel registry (dict[str, adapter])
    """

    def __init__(self, persistence_path: Optional[Path] = None):
        self._capabilities: Dict[str, AgentCapabilityDescriptor] = {}
        self._persistence_path = persistence_path

        # Indexes for fast queries
        self._by_kind: Dict[CapabilityKind, List[str]] = {}
        self._by_substrate: Dict[ExecutionSubstrate, List[str]] = {}
        self._by_command_alias: Dict[str, str] = {}  # alias → capability_id
        self._by_trigger: Dict[str, str] = {}        # trigger → capability_id

    # CRUD Operations

    def register(self, capability: AgentCapabilityDescriptor) -> None:
        """Register a capability"""
        cap_id = capability.capability_id

        if cap_id in self._capabilities:
            if capability.status and not capability.status.mutable:
                raise ValueError(f"Capability {cap_id} is immutable")

        self._capabilities[cap_id] = capability
        self._update_indexes(capability)

        logger.info(f"Registered capability: {cap_id} ({capability.kind.value}/{capability.execution.substrate.value})")

    def unregister(self, capability_id: str) -> None:
        """Remove a capability"""
        if capability_id not in self._capabilities:
            raise KeyError(f"Capability not found: {capability_id}")

        cap = self._capabilities[capability_id]
        if cap.status and not cap.status.mutable:
            raise ValueError(f"Cannot remove immutable capability: {capability_id}")

        del self._capabilities[capability_id]
        self._rebuild_indexes()

        logger.info(f"Unregistered capability: {capability_id}")

    def get(self, capability_id: str) -> Optional[AgentCapabilityDescriptor]:
        """Get a capability by ID"""
        return self._capabilities.get(capability_id)

    def update(self, capability: AgentCapabilityDescriptor) -> None:
        """Update an existing capability"""
        if capability.capability_id not in self._capabilities:
            raise KeyError(f"Capability not found: {capability.capability_id}")

        self.register(capability)  # Handles mutability check

    # Query Operations

    def list_all(self) -> List[AgentCapabilityDescriptor]:
        """List all capabilities"""
        return list(self._capabilities.values())

    def query(
        self,
        kind: Optional[CapabilityKind] = None,
        substrate: Optional[ExecutionSubstrate] = None,
        scope: Optional[ExposureScope] = None,
        enabled_only: bool = True,
        **filters
    ) -> List[AgentCapabilityDescriptor]:
        """Query capabilities by criteria"""
        results = list(self._capabilities.values())

        if kind:
            results = [c for c in results if c.kind == kind]

        if substrate:
            results = [c for c in results if c.execution.substrate == substrate]

        if scope:
            results = [c for c in results if c.exposure.scope == scope]

        if enabled_only:
            results = [c for c in results if not c.status or c.status.enabled]

        # Additional filters
        for key, value in filters.items():
            results = [c for c in results if getattr(c, key, None) == value]

        return results

    def find_by_command(self, command: str) -> Optional[AgentCapabilityDescriptor]:
        """Find capability by command alias"""
        # Strip query parameters (everything after ? or &)
        command_base = command.split('?')[0].split('&')[0].strip()

        # Normalize command (remove leading / or --)
        normalized = command_base.lstrip('/').lstrip('-')

        # Check direct match
        if command_base in self._by_command_alias:
            cap_id = self._by_command_alias[command_base]
            return self._capabilities.get(cap_id)

        # Check normalized match
        if normalized in self._by_command_alias:
            cap_id = self._by_command_alias[normalized]
            return self._capabilities.get(cap_id)

        return None

    def find_by_trigger(self, text: str) -> Optional[AgentCapabilityDescriptor]:
        """Find capability by message trigger"""
        text_lower = text.lower()

        # Sort triggers by length (longest first) for better matching
        sorted_triggers = sorted(self._by_trigger.keys(), key=len, reverse=True)

        for trigger in sorted_triggers:
            if trigger in text_lower:
                cap_id = self._by_trigger[trigger]
                return self._capabilities.get(cap_id)

        return None

    def has_capability(self, capability_id: str) -> bool:
        """Check if capability is registered"""
        return capability_id in self._capabilities

    def count(self) -> int:
        """Get total count of registered capabilities"""
        return len(self._capabilities)

    def count_by_kind(self, kind: CapabilityKind) -> int:
        """Count capabilities by kind"""
        return len(self._by_kind.get(kind, []))

    def count_by_substrate(self, substrate: ExecutionSubstrate) -> int:
        """Count capabilities by substrate"""
        return len(self._by_substrate.get(substrate, []))

    # Index Management

    def _update_indexes(self, capability: AgentCapabilityDescriptor):
        """Update indexes after capability registration"""
        cap_id = capability.capability_id

        # Index by kind
        if capability.kind not in self._by_kind:
            self._by_kind[capability.kind] = []
        if cap_id not in self._by_kind[capability.kind]:
            self._by_kind[capability.kind].append(cap_id)

        # Index by substrate
        substrate = capability.execution.substrate
        if substrate not in self._by_substrate:
            self._by_substrate[substrate] = []
        if cap_id not in self._by_substrate[substrate]:
            self._by_substrate[substrate].append(cap_id)

        # Index command aliases
        for alias in capability.invocation.command_aliases:
            self._by_command_alias[alias] = cap_id
            # Also index without leading /
            self._by_command_alias[alias.lstrip('/')] = cap_id

        # Index message triggers
        for trigger in capability.invocation.message_triggers:
            self._by_trigger[trigger.lower()] = cap_id

    def _rebuild_indexes(self):
        """Rebuild all indexes from scratch"""
        self._by_kind.clear()
        self._by_substrate.clear()
        self._by_command_alias.clear()
        self._by_trigger.clear()

        for cap in self._capabilities.values():
            self._update_indexes(cap)

    # Persistence

    async def save(self):
        """Save registry to disk (if persistence enabled)"""
        if not self._persistence_path:
            return

        try:
            # Serialize all capabilities
            data = {
                "capabilities": [cap.to_dict() for cap in self._capabilities.values()]
            }

            # Write to file
            with open(self._persistence_path, 'w') as f:
                json.dump(data, f, indent=2)

            logger.info(f"Saved {len(self._capabilities)} capabilities to {self._persistence_path}")

        except Exception as e:
            logger.error(f"Failed to save capability registry: {e}")

    async def load(self):
        """Load registry from disk"""
        if not self._persistence_path or not self._persistence_path.exists():
            return

        try:
            with open(self._persistence_path, 'r') as f:
                data = json.load(f)

            # Deserialize capabilities
            for cap_data in data.get('capabilities', []):
                try:
                    cap = AgentCapabilityDescriptor.from_dict(cap_data)
                    self.register(cap)
                except Exception as e:
                    logger.error(f"Failed to load capability {cap_data.get('capability_id')}: {e}")

            logger.info(f"Loaded {len(self._capabilities)} capabilities from {self._persistence_path}")

        except Exception as e:
            logger.error(f"Failed to load capability registry: {e}")

    # Bulk operations

    def register_many(self, capabilities: List[AgentCapabilityDescriptor]) -> int:
        """Register multiple capabilities at once"""
        count = 0
        for cap in capabilities:
            try:
                self.register(cap)
                count += 1
            except Exception as e:
                logger.error(f"Failed to register capability {cap.capability_id}: {e}")

        return count

    def load_from_yaml(self, yaml_path: Path) -> Optional[AgentCapabilityDescriptor]:
        """Load a capability from YAML file"""
        try:
            with open(yaml_path, 'r') as f:
                data = yaml.safe_load(f)

            capability = AgentCapabilityDescriptor.from_dict(data)
            self.register(capability)

            logger.info(f"Loaded capability from {yaml_path}: {capability.capability_id}")
            return capability

        except Exception as e:
            logger.error(f"Failed to load capability from {yaml_path}: {e}")
            return None

    def load_from_directory(self, directory: Path) -> int:
        """Load all capabilities from a directory (YAML files)"""
        if not directory.exists() or not directory.is_dir():
            logger.warning(f"Capability directory does not exist: {directory}")
            return 0

        count = 0
        for yaml_file in directory.rglob("*.yaml"):
            if self.load_from_yaml(yaml_file):
                count += 1

        for yml_file in directory.rglob("*.yml"):
            if self.load_from_yaml(yml_file):
                count += 1

        logger.info(f"Loaded {count} capabilities from {directory}")
        return count

    # Debug utilities

    def dump_registry(self) -> str:
        """Dump registry contents for debugging"""
        lines = [
            f"Capability Registry Summary",
            f"===========================",
            f"Total capabilities: {self.count()}",
            f"",
            f"By Kind:",
        ]

        for kind in CapabilityKind:
            count = self.count_by_kind(kind)
            if count > 0:
                lines.append(f"  {kind.value}: {count}")

        lines.append("")
        lines.append("By Substrate:")

        for substrate in ExecutionSubstrate:
            count = self.count_by_substrate(substrate)
            if count > 0:
                lines.append(f"  {substrate.value}: {count}")

        lines.append("")
        lines.append("All Capabilities:")

        for cap in sorted(self._capabilities.values(), key=lambda c: c.capability_id):
            status = "✓" if not cap.status or cap.status.enabled else "✗"
            lines.append(f"  {status} {cap.capability_id} ({cap.kind.value}/{cap.execution.substrate.value})")
            if cap.invocation.command_aliases:
                lines.append(f"     Commands: {', '.join(cap.invocation.command_aliases)}")

        return "\n".join(lines)
