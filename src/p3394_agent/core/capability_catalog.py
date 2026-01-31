"""
Capability Catalog System

Provides a unified view of all agent capabilities by:
1. Discovering capabilities from system sources (top-down inspection)
2. Synchronizing with long-term memory (what agent knows)
3. Detecting changes and maintaining consistency

Sources of System Truth:
- SDK configuration (allowed_tools, hooks, etc.)
- .claude/skills/ directory (skill definitions)
- .claude/agents/ directory (subagent definitions)
- .claude/commands/ directory (command extensions)
- MCP server configurations
- Plugin registry
- Hook definitions
- agent.yaml configuration

Memory Truth:
- KSTAR long-term memory
- Capability catalog entries
- ACL definitions
- Learned/evolved capabilities
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, TYPE_CHECKING
import logging
import json
import yaml

if TYPE_CHECKING:
    from ..memory.kstar import KStarMemory
    from .gateway_sdk import AgentGateway

logger = logging.getLogger(__name__)


class CapabilitySource(str, Enum):
    """Where a capability comes from"""
    BUILTIN = "builtin"           # Hardcoded in agent code
    SDK = "sdk"                   # From Claude Agent SDK
    SKILL = "skill"               # From .claude/skills/
    SUBAGENT = "subagent"         # From .claude/agents/
    COMMAND = "command"           # From .claude/commands/ or registered
    MCP_SERVER = "mcp_server"     # From MCP server configuration
    PLUGIN = "plugin"             # From plugin system
    HOOK = "hook"                 # Hook definitions
    CONFIG = "config"             # From agent.yaml
    LEARNED = "learned"           # Agent learned/created this
    EXTERNAL = "external"         # From external source


class CapabilityType(str, Enum):
    """Type of capability"""
    COMMAND = "command"           # Symbolic command (/help, /status)
    SKILL = "skill"               # LLM-guided skill
    SUBAGENT = "subagent"         # Delegated subagent
    TOOL = "tool"                 # SDK tool (Read, Write, Bash, etc.)
    MCP_TOOL = "mcp_tool"         # MCP server tool
    HOOK = "hook"                 # Pre/Post hook
    CHANNEL = "channel"           # Channel adapter
    CORE = "core"                 # Core internal capability


class CapabilityPowerLevel(str, Enum):
    """
    Power level taxonomy for capabilities.

    This distinguishes capabilities by their potential impact on the agent:
    - STANDARD: Isolated task execution, safe for all users
    - META: Can invoke other capabilities recursively
    - SELF_MODIFYING: Can modify agent state, memory, or capabilities
    - BOOTSTRAP: Essential for agent factory/replication

    Security implications:
    - Anonymous users: STANDARD only (public capabilities)
    - Client principals: STANDARD only (no agent mutation)
    - Service principal: STANDARD + META + controlled SELF_MODIFYING
    - Admin/System: All levels
    """
    STANDARD = "standard"           # Level 0: Task-specific, isolated
    META = "meta"                   # Level 1: Can invoke other skills/capabilities
    SELF_MODIFYING = "self_modifying"  # Level 2: Can modify agent state/memory/skills
    BOOTSTRAP = "bootstrap"         # Level 3: Factory-essential, system-level


# Classification of known capabilities by power level
POWER_LEVEL_CLASSIFICATIONS = {
    # BOOTSTRAP level - SDK and factory essentials
    CapabilityPowerLevel.BOOTSTRAP: {
        "tool.sdk.read", "tool.sdk.write", "tool.sdk.edit", "tool.sdk.bash",
        "tool.sdk.glob", "tool.sdk.grep", "tool.sdk.task",
        "core.llm.invoke", "core.session.create", "core.session.destroy",
    },
    # SELF_MODIFYING level - Can mutate agent
    CapabilityPowerLevel.SELF_MODIFYING: {
        "skill.skill-creator", "skill.skill-creation-guide", "skill.skill-evolution",
        "skill.skill-management", "skill.skill-transfer",
        "skill.control-tokens",  # KSTAR+ control tokens
        "skill.agent-development", "skill.Hook Development",
        "command.configure",
        "admin.principal_manage", "admin.acl_manage", "admin.channel_manage",
    },
    # META level - Can invoke other capabilities
    CapabilityPowerLevel.META: {
        "tool.sdk.task",  # Subagent delegation
        "skill.skill-discovery",
        "skill.agent-sdk-basics", "skill.agent-sdk-advanced",
        "skill.research-lookup", "skill.scientific-writing", "skill.scientific-brainstorming",
        "skill.ieee-wg-manager",
        "core.chat.with_tools", "core.skill_dispatch", "core.subagent_dispatch",
    },
    # STANDARD is the default for everything else
}


def classify_power_level(capability_id: str) -> CapabilityPowerLevel:
    """
    Classify a capability's power level based on its ID.

    Checks against known classifications, defaults to STANDARD.
    """
    for level, ids in POWER_LEVEL_CLASSIFICATIONS.items():
        if capability_id in ids:
            return level

    # Check patterns
    if capability_id.startswith("admin."):
        return CapabilityPowerLevel.SELF_MODIFYING
    if "skill-creator" in capability_id or "skill-evolution" in capability_id:
        return CapabilityPowerLevel.SELF_MODIFYING
    if "control-token" in capability_id:
        return CapabilityPowerLevel.SELF_MODIFYING

    return CapabilityPowerLevel.STANDARD


@dataclass
class CatalogEntry:
    """Entry in the capability catalog"""
    id: str                                    # Unique identifier
    name: str                                  # Display name
    type: CapabilityType                       # Type of capability
    source: CapabilitySource                   # Where it comes from
    description: str = ""                      # Description
    version: str = "1.0.0"                     # Version
    enabled: bool = True                       # Is it enabled?

    # Power level classification
    power_level: CapabilityPowerLevel = CapabilityPowerLevel.STANDARD

    # Source location
    source_path: Optional[str] = None          # File path if applicable
    source_module: Optional[str] = None        # Python module if applicable

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    # Timestamps
    discovered_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_verified_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    # Sync state
    in_memory: bool = False                    # Is it in long-term memory?
    in_system: bool = True                     # Is it in the system?

    def __post_init__(self):
        """Auto-classify power level if not explicitly set"""
        if self.power_level == CapabilityPowerLevel.STANDARD:
            # Check if this capability should have a higher power level
            self.power_level = classify_power_level(self.id)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type.value,
            "source": self.source.value,
            "description": self.description,
            "version": self.version,
            "enabled": self.enabled,
            "power_level": self.power_level.value,
            "source_path": self.source_path,
            "source_module": self.source_module,
            "metadata": self.metadata,
            "discovered_at": self.discovered_at.isoformat(),
            "last_verified_at": self.last_verified_at.isoformat(),
            "in_memory": self.in_memory,
            "in_system": self.in_system,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CatalogEntry":
        """Deserialize from dictionary"""
        # Parse power level, defaulting to STANDARD
        power_level = CapabilityPowerLevel.STANDARD
        if data.get("power_level"):
            try:
                power_level = CapabilityPowerLevel(data["power_level"])
            except ValueError:
                pass

        return cls(
            id=data["id"],
            name=data["name"],
            type=CapabilityType(data["type"]),
            source=CapabilitySource(data["source"]),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            enabled=data.get("enabled", True),
            power_level=power_level,
            source_path=data.get("source_path"),
            source_module=data.get("source_module"),
            metadata=data.get("metadata", {}),
            discovered_at=datetime.fromisoformat(data["discovered_at"]) if data.get("discovered_at") else datetime.now(timezone.utc),
            last_verified_at=datetime.fromisoformat(data["last_verified_at"]) if data.get("last_verified_at") else datetime.now(timezone.utc),
            in_memory=data.get("in_memory", False),
            in_system=data.get("in_system", True),
        )


class CapabilityCatalog:
    """
    Unified capability catalog that synchronizes system truth with memory truth.

    This is the single source of truth for what the agent can do.
    """

    def __init__(
        self,
        memory: "KStarMemory",
        working_dir: Path,
        gateway: Optional["AgentGateway"] = None
    ):
        self.memory = memory
        self.working_dir = working_dir
        self.gateway = gateway

        # Catalog entries indexed by ID
        self._entries: Dict[str, CatalogEntry] = {}

        # Discovery state
        self._last_discovery: Optional[datetime] = None
        self._last_sync: Optional[datetime] = None

    # =========================================================================
    # DISCOVERY (Top-Down Inspection)
    # =========================================================================

    async def discover_all(self) -> Dict[str, int]:
        """
        Discover all capabilities from system sources.

        Returns counts of discovered capabilities by type.
        """
        counts = {
            "commands": 0,
            "skills": 0,
            "subagents": 0,
            "tools": 0,
            "mcp_tools": 0,
            "hooks": 0,
            "channels": 0,
            "core": 0,
        }

        # Discover from each source
        counts["commands"] = await self._discover_commands()
        counts["skills"] = await self._discover_skills()
        counts["subagents"] = await self._discover_subagents()
        counts["tools"] = await self._discover_sdk_tools()
        counts["mcp_tools"] = await self._discover_mcp_tools()
        counts["hooks"] = await self._discover_hooks()
        counts["channels"] = await self._discover_channels()
        counts["core"] = await self._discover_core_capabilities()

        self._last_discovery = datetime.now(timezone.utc)

        total = sum(counts.values())
        logger.info(f"Discovered {total} capabilities: {counts}")

        return counts

    async def _discover_commands(self) -> int:
        """Discover symbolic commands"""
        count = 0

        if self.gateway:
            seen = set()
            for name, cmd in self.gateway.commands.items():
                if cmd.name in seen:
                    continue
                seen.add(cmd.name)

                entry = CatalogEntry(
                    id=f"command.{cmd.name.lstrip('/')}",
                    name=cmd.name,
                    type=CapabilityType.COMMAND,
                    source=CapabilitySource.BUILTIN,
                    description=cmd.description,
                    metadata={
                        "usage": cmd.usage,
                        "requires_auth": cmd.requires_auth,
                        "aliases": cmd.aliases,
                    }
                )
                self._entries[entry.id] = entry
                count += 1

        # Also check .claude/commands/ directory
        commands_dir = self.working_dir / ".claude" / "commands"
        if commands_dir.exists():
            for cmd_file in commands_dir.glob("*.md"):
                cmd_name = cmd_file.stem
                entry_id = f"command.{cmd_name}"

                if entry_id not in self._entries:
                    entry = CatalogEntry(
                        id=entry_id,
                        name=f"/{cmd_name}",
                        type=CapabilityType.COMMAND,
                        source=CapabilitySource.COMMAND,
                        source_path=str(cmd_file),
                        description=f"Custom command from {cmd_file.name}",
                    )
                    self._entries[entry.id] = entry
                    count += 1

        return count

    async def _discover_skills(self) -> int:
        """Discover skills from .claude/skills/"""
        count = 0

        # Check multiple skill directories
        skill_dirs = [
            self.working_dir / ".claude" / "skills",
            Path.home() / ".claude" / "skills",
        ]

        for skills_dir in skill_dirs:
            if not skills_dir.exists():
                continue

            for skill_path in skills_dir.iterdir():
                if not skill_path.is_dir():
                    continue

                skill_file = skill_path / "SKILL.md"
                if not skill_file.exists():
                    continue

                skill_name = skill_path.name
                entry_id = f"skill.{skill_name}"

                # Parse skill metadata
                metadata = await self._parse_skill_frontmatter(skill_file)

                entry = CatalogEntry(
                    id=entry_id,
                    name=metadata.get("name", skill_name),
                    type=CapabilityType.SKILL,
                    source=CapabilitySource.SKILL,
                    source_path=str(skill_file),
                    description=metadata.get("description", ""),
                    metadata=metadata,
                )
                self._entries[entry.id] = entry
                count += 1

        return count

    async def _discover_subagents(self) -> int:
        """Discover subagents from .claude/agents/"""
        count = 0

        agents_dir = self.working_dir / ".claude" / "agents"
        if not agents_dir.exists():
            return 0

        for agent_file in agents_dir.glob("*.md"):
            agent_name = agent_file.stem
            entry_id = f"subagent.{agent_name}"

            # Try to parse description from file
            description = ""
            try:
                content = agent_file.read_text()
                # Extract first heading or first paragraph
                lines = content.strip().split('\n')
                for line in lines:
                    if line.startswith('# '):
                        description = line[2:].strip()
                        break
                    elif line.strip() and not line.startswith('#'):
                        description = line.strip()
                        break
            except Exception:
                pass

            entry = CatalogEntry(
                id=entry_id,
                name=agent_name,
                type=CapabilityType.SUBAGENT,
                source=CapabilitySource.SUBAGENT,
                source_path=str(agent_file),
                description=description,
            )
            self._entries[entry.id] = entry
            count += 1

        return count

    async def _discover_sdk_tools(self) -> int:
        """Discover SDK tools (built-in)"""
        count = 0

        # Built-in SDK tools
        sdk_tools = [
            ("Read", "Read files from the filesystem"),
            ("Write", "Write files to the filesystem"),
            ("Edit", "Edit existing files"),
            ("Bash", "Execute shell commands"),
            ("Glob", "Find files by pattern"),
            ("Grep", "Search file contents"),
            ("WebSearch", "Search the web"),
            ("WebFetch", "Fetch web pages"),
            ("Task", "Spawn subagent tasks"),
        ]

        for tool_name, description in sdk_tools:
            entry = CatalogEntry(
                id=f"tool.sdk.{tool_name.lower()}",
                name=tool_name,
                type=CapabilityType.TOOL,
                source=CapabilitySource.SDK,
                description=description,
            )
            self._entries[entry.id] = entry
            count += 1

        return count

    async def _discover_mcp_tools(self) -> int:
        """Discover MCP server tools"""
        count = 0

        # Check agent.yaml for MCP server configurations
        agent_yaml = self.working_dir / "agent.yaml"
        if agent_yaml.exists():
            try:
                with open(agent_yaml) as f:
                    config = yaml.safe_load(f)

                mcp_servers = config.get("mcp_servers", {})
                for server_name, server_config in mcp_servers.items():
                    entry = CatalogEntry(
                        id=f"mcp.{server_name}",
                        name=server_name,
                        type=CapabilityType.MCP_TOOL,
                        source=CapabilitySource.MCP_SERVER,
                        description=f"MCP server: {server_name}",
                        metadata=server_config,
                    )
                    self._entries[entry.id] = entry
                    count += 1
            except Exception as e:
                logger.warning(f"Failed to parse agent.yaml for MCP servers: {e}")

        # Also check settings.json
        settings_json = self.working_dir / ".claude" / "settings.json"
        if settings_json.exists():
            try:
                with open(settings_json) as f:
                    settings = json.load(f)

                mcp_servers = settings.get("mcpServers", {})
                for server_name, server_config in mcp_servers.items():
                    entry_id = f"mcp.{server_name}"
                    if entry_id not in self._entries:
                        entry = CatalogEntry(
                            id=entry_id,
                            name=server_name,
                            type=CapabilityType.MCP_TOOL,
                            source=CapabilitySource.MCP_SERVER,
                            source_path=str(settings_json),
                            description=f"MCP server: {server_name}",
                            metadata=server_config,
                        )
                        self._entries[entry.id] = entry
                        count += 1
            except Exception as e:
                logger.warning(f"Failed to parse settings.json for MCP servers: {e}")

        return count

    async def _discover_hooks(self) -> int:
        """Discover hook definitions"""
        count = 0

        # Check settings.json for hooks
        settings_json = self.working_dir / ".claude" / "settings.json"
        if settings_json.exists():
            try:
                with open(settings_json) as f:
                    settings = json.load(f)

                hooks = settings.get("hooks", {})
                for hook_event, hook_configs in hooks.items():
                    if isinstance(hook_configs, list):
                        for i, hook_config in enumerate(hook_configs):
                            entry = CatalogEntry(
                                id=f"hook.{hook_event}.{i}",
                                name=f"{hook_event}[{i}]",
                                type=CapabilityType.HOOK,
                                source=CapabilitySource.HOOK,
                                source_path=str(settings_json),
                                description=f"Hook for {hook_event}",
                                metadata=hook_config if isinstance(hook_config, dict) else {"command": hook_config},
                            )
                            self._entries[entry.id] = entry
                            count += 1
            except Exception as e:
                logger.warning(f"Failed to parse settings.json for hooks: {e}")

        return count

    async def _discover_channels(self) -> int:
        """Discover channel adapters"""
        count = 0

        if self.gateway:
            for channel_id, adapter in self.gateway.channels.items():
                entry = CatalogEntry(
                    id=f"channel.{channel_id}",
                    name=channel_id,
                    type=CapabilityType.CHANNEL,
                    source=CapabilitySource.BUILTIN,
                    description=f"Channel adapter: {adapter.__class__.__name__}",
                    enabled=adapter.is_active,
                    metadata={
                        "adapter_class": adapter.__class__.__name__,
                    }
                )
                self._entries[entry.id] = entry
                count += 1

        return count

    async def _discover_core_capabilities(self) -> int:
        """Discover core internal capabilities"""
        count = 0

        # Core capabilities that are always present
        core_caps = [
            ("core.message.handle", "Message routing and handling"),
            ("core.llm.invoke", "LLM invocation via Claude API"),
            ("core.session.create", "Create new sessions"),
            ("core.session.destroy", "End sessions"),
            ("core.chat", "Basic chat capability"),
            ("core.chat.with_tools", "Chat with tool access"),
        ]

        for cap_id, description in core_caps:
            entry = CatalogEntry(
                id=cap_id,
                name=cap_id,
                type=CapabilityType.CORE,
                source=CapabilitySource.BUILTIN,
                description=description,
            )
            self._entries[entry.id] = entry
            count += 1

        return count

    async def _parse_skill_frontmatter(self, skill_file: Path) -> Dict[str, Any]:
        """Parse YAML frontmatter from skill file"""
        try:
            content = skill_file.read_text()

            # Check for YAML frontmatter
            if content.startswith('---'):
                parts = content.split('---', 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    return frontmatter if isinstance(frontmatter, dict) else {}

            return {}
        except Exception as e:
            logger.debug(f"Failed to parse skill frontmatter: {e}")
            return {}

    # =========================================================================
    # MEMORY SYNCHRONIZATION
    # =========================================================================

    async def sync_to_memory(self) -> Dict[str, int]:
        """
        Synchronize catalog to long-term memory.

        Returns counts of synced items.
        """
        results = {"added": 0, "updated": 0, "unchanged": 0}

        for entry in self._entries.values():
            # Check if already in memory
            existing = await self.memory.get_capability_catalog_entry(entry.id)

            if existing is None:
                # Add to memory
                await self.memory.store_capability_catalog_entry(entry.to_dict())
                entry.in_memory = True
                results["added"] += 1
            elif self._entry_changed(entry, existing):
                # Update in memory
                await self.memory.store_capability_catalog_entry(entry.to_dict())
                entry.in_memory = True
                results["updated"] += 1
            else:
                entry.in_memory = True
                results["unchanged"] += 1

        self._last_sync = datetime.now(timezone.utc)
        logger.info(f"Synced catalog to memory: {results}")

        return results

    async def load_from_memory(self) -> int:
        """
        Load catalog entries from long-term memory.

        Returns count of loaded entries.
        """
        entries = await self.memory.list_capability_catalog_entries()
        count = 0

        for entry_dict in entries:
            entry = CatalogEntry.from_dict(entry_dict)
            entry.in_memory = True
            entry.in_system = entry.id in self._entries

            if entry.id not in self._entries:
                # Entry exists in memory but not in system
                entry.in_system = False
                self._entries[entry.id] = entry
            else:
                # Merge memory state with system state
                self._entries[entry.id].in_memory = True

            count += 1

        logger.info(f"Loaded {count} catalog entries from memory")
        return count

    def _entry_changed(self, entry: CatalogEntry, existing: Dict[str, Any]) -> bool:
        """Check if an entry has changed from what's in memory"""
        # Compare key fields
        if entry.name != existing.get("name"):
            return True
        if entry.description != existing.get("description"):
            return True
        if entry.enabled != existing.get("enabled"):
            return True
        if entry.version != existing.get("version"):
            return True
        return False

    # =========================================================================
    # QUERY API
    # =========================================================================

    def get(self, entry_id: str) -> Optional[CatalogEntry]:
        """Get a catalog entry by ID"""
        return self._entries.get(entry_id)

    def list_all(self) -> List[CatalogEntry]:
        """List all catalog entries"""
        return list(self._entries.values())

    def list_by_type(self, cap_type: CapabilityType) -> List[CatalogEntry]:
        """List entries by type"""
        return [e for e in self._entries.values() if e.type == cap_type]

    def list_by_source(self, source: CapabilitySource) -> List[CatalogEntry]:
        """List entries by source"""
        return [e for e in self._entries.values() if e.source == source]

    def list_enabled(self) -> List[CatalogEntry]:
        """List only enabled entries"""
        return [e for e in self._entries.values() if e.enabled]

    def list_out_of_sync(self) -> List[CatalogEntry]:
        """List entries that are out of sync between system and memory"""
        return [e for e in self._entries.values() if e.in_memory != e.in_system]

    def list_by_power_level(self, power_level: CapabilityPowerLevel) -> List[CatalogEntry]:
        """
        List entries by power level.

        Power levels:
        - STANDARD: Safe for all users, isolated task execution
        - META: Can invoke other capabilities, requires auth
        - SELF_MODIFYING: Can modify agent state, service principal/admin only
        - BOOTSTRAP: Factory essentials, system-level only
        """
        return [e for e in self._entries.values() if e.power_level == power_level]

    def list_safe_for_client(self) -> List[CatalogEntry]:
        """
        List capabilities safe for client principals (external users).

        These are STANDARD level capabilities that cannot modify agent state.
        """
        return [
            e for e in self._entries.values()
            if e.power_level == CapabilityPowerLevel.STANDARD and e.enabled
        ]

    def list_meta_skills(self) -> List[CatalogEntry]:
        """List meta-skills that can invoke other capabilities"""
        return self.list_by_power_level(CapabilityPowerLevel.META)

    def list_self_modifying(self) -> List[CatalogEntry]:
        """List self-modifying capabilities (can mutate agent state)"""
        return self.list_by_power_level(CapabilityPowerLevel.SELF_MODIFYING)

    def list_bootstrap_essential(self) -> List[CatalogEntry]:
        """List bootstrap-essential capabilities for agent factory"""
        return self.list_by_power_level(CapabilityPowerLevel.BOOTSTRAP)

    def get_stats(self) -> Dict[str, Any]:
        """Get catalog statistics"""
        by_type = {}
        by_source = {}
        by_power_level = {}

        for entry in self._entries.values():
            by_type[entry.type.value] = by_type.get(entry.type.value, 0) + 1
            by_source[entry.source.value] = by_source.get(entry.source.value, 0) + 1
            by_power_level[entry.power_level.value] = by_power_level.get(entry.power_level.value, 0) + 1

        in_both = sum(1 for e in self._entries.values() if e.in_memory and e.in_system)
        only_system = sum(1 for e in self._entries.values() if e.in_system and not e.in_memory)
        only_memory = sum(1 for e in self._entries.values() if e.in_memory and not e.in_system)

        return {
            "total": len(self._entries),
            "by_type": by_type,
            "by_source": by_source,
            "by_power_level": by_power_level,
            "enabled": sum(1 for e in self._entries.values() if e.enabled),
            "sync_status": {
                "in_both": in_both,
                "only_system": only_system,
                "only_memory": only_memory,
            },
            "last_discovery": self._last_discovery.isoformat() if self._last_discovery else None,
            "last_sync": self._last_sync.isoformat() if self._last_sync else None,
        }

    def to_manifest(self) -> Dict[str, Any]:
        """
        Export catalog as a manifest document.

        This can be used for agent configuration, sharing, or factory processes.
        """
        return {
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "stats": self.get_stats(),
            "capabilities": {
                entry.id: entry.to_dict()
                for entry in self._entries.values()
            }
        }

    # =========================================================================
    # INCREMENTAL UPDATES
    # =========================================================================

    async def refresh_channels(self) -> int:
        """
        Refresh channel discovery and sync to memory.

        Call this after channels are registered (which happens after initialize()).
        Returns count of channels discovered.
        """
        count = await self._discover_channels()

        if count > 0:
            # Sync new channel entries to memory
            for entry_id, entry in self._entries.items():
                if entry.type == CapabilityType.CHANNEL and not entry.in_memory:
                    await self.memory.store_capability_catalog_entry(entry.to_dict())
                    entry.in_memory = True

            logger.info(f"Refreshed {count} channel(s) in catalog")

        return count

    async def add_capability(self, entry: CatalogEntry, sync_to_memory: bool = True) -> str:
        """
        Add a single capability to the catalog.

        Use this for dynamic capability registration (e.g., learned capabilities).

        Args:
            entry: The catalog entry to add
            sync_to_memory: Whether to immediately sync to memory

        Returns:
            The entry ID
        """
        self._entries[entry.id] = entry

        if sync_to_memory:
            await self.memory.store_capability_catalog_entry(entry.to_dict())
            entry.in_memory = True

        logger.debug(f"Added capability to catalog: {entry.id}")
        return entry.id

    async def remove_capability(self, entry_id: str, sync_to_memory: bool = True) -> bool:
        """
        Remove a capability from the catalog.

        Args:
            entry_id: The ID of the capability to remove
            sync_to_memory: Whether to immediately sync to memory

        Returns:
            True if removed, False if not found
        """
        if entry_id not in self._entries:
            return False

        del self._entries[entry_id]

        if sync_to_memory:
            await self.memory.delete_capability_catalog_entry(entry_id)

        logger.debug(f"Removed capability from catalog: {entry_id}")
        return True
