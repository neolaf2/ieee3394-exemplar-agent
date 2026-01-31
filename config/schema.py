"""
P3394 Agent Configuration Schema

Defines the configuration structure for P3394-compliant agents.
All configuration can be specified via agent.yaml or environment variables.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from pathlib import Path


@dataclass
class ChannelConfig:
    """Configuration for a communication channel"""
    enabled: bool = True
    host: str = "0.0.0.0"
    port: int = 8000
    # Channel-specific settings stored as metadata
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMConfig:
    """Configuration for LLM provider"""
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    system_prompt: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7


@dataclass
class StorageConfig:
    """Configuration for agent storage/memory"""
    type: str = "sqlite"
    path: str = "./data/agent.db"
    # Additional storage options
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SkillConfig:
    """Configuration for a skill"""
    name: str
    enabled: bool = True
    # Skill-specific settings
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentConfig:
    """
    Central configuration for a P3394-compliant agent.

    This configuration can be loaded from:
    - agent.yaml (primary)
    - Environment variables (override)
    - Programmatic defaults

    Example agent.yaml:
    ```yaml
    agent:
      id: "my-agent"
      name: "My Custom Agent"
      version: "0.1.0"
      description: "A helpful P3394-compliant agent"

    channels:
      cli:
        enabled: true
      web:
        enabled: true
        port: 8000

    llm:
      provider: anthropic
      model: claude-sonnet-4-20250514
      system_prompt: "You are a helpful assistant."

    storage:
      type: sqlite
      path: ./data/agent.db
    ```
    """
    # Agent identity
    id: str = "p3394-agent"
    name: str = "P3394 Agent"
    version: str = "0.1.0"
    description: str = "A P3394-compliant agent"

    # Channels configuration
    channels: Dict[str, ChannelConfig] = field(default_factory=lambda: {
        "cli": ChannelConfig(enabled=True),
        "web": ChannelConfig(enabled=True, port=8000),
    })

    # LLM configuration
    llm: LLMConfig = field(default_factory=LLMConfig)

    # Storage configuration
    storage: StorageConfig = field(default_factory=StorageConfig)

    # Skills to load
    skills: List[SkillConfig] = field(default_factory=list)

    # Working directory (defaults to current directory)
    working_dir: Path = field(default_factory=Path.cwd)

    # Additional metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def get_channel(self, channel_id: str) -> Optional[ChannelConfig]:
        """Get configuration for a specific channel"""
        return self.channels.get(channel_id)

    def is_channel_enabled(self, channel_id: str) -> bool:
        """Check if a channel is enabled"""
        channel = self.get_channel(channel_id)
        return channel.enabled if channel else False

    def get_enabled_channels(self) -> List[str]:
        """Get list of enabled channel IDs"""
        return [cid for cid, cfg in self.channels.items() if cfg.enabled]

    def get_system_prompt(self) -> str:
        """Get the system prompt for LLM, with agent identity substitution"""
        if self.llm.system_prompt:
            # Substitute agent identity placeholders
            return self.llm.system_prompt.format(
                agent_id=self.id,
                agent_name=self.name,
                agent_version=self.version,
                agent_description=self.description,
            )

        # Default system prompt
        return f"""You are {self.name} (v{self.version}).

{self.description}

Your role:
- Respond helpfully and concisely
- Follow P3394 Universal Message Format standards
- Maintain context across the conversation

When responding:
1. Be helpful and accurate
2. If unsure, say so
3. Keep responses focused and relevant
"""

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create AgentConfig from dictionary (e.g., parsed YAML)"""
        # Extract agent identity
        agent_data = data.get("agent", {})

        # Parse channels
        channels = {}
        for channel_id, channel_data in data.get("channels", {}).items():
            if isinstance(channel_data, dict):
                channels[channel_id] = ChannelConfig(
                    enabled=channel_data.get("enabled", True),
                    host=channel_data.get("host", "0.0.0.0"),
                    port=channel_data.get("port", 8000),
                    metadata={k: v for k, v in channel_data.items()
                             if k not in ("enabled", "host", "port")}
                )
            elif isinstance(channel_data, bool):
                channels[channel_id] = ChannelConfig(enabled=channel_data)

        # Parse LLM config
        llm_data = data.get("llm", {})
        llm_config = LLMConfig(
            provider=llm_data.get("provider", "anthropic"),
            model=llm_data.get("model", "claude-sonnet-4-20250514"),
            system_prompt=llm_data.get("system_prompt"),
            max_tokens=llm_data.get("max_tokens", 4096),
            temperature=llm_data.get("temperature", 0.7),
        )

        # Parse storage config
        storage_data = data.get("storage", {})
        storage_config = StorageConfig(
            type=storage_data.get("type", "sqlite"),
            path=storage_data.get("path", "./data/agent.db"),
            metadata={k: v for k, v in storage_data.items()
                     if k not in ("type", "path")}
        )

        # Parse skills
        skills = []
        for skill_data in data.get("skills", []):
            if isinstance(skill_data, str):
                skills.append(SkillConfig(name=skill_data))
            elif isinstance(skill_data, dict):
                skills.append(SkillConfig(
                    name=skill_data.get("name", "unknown"),
                    enabled=skill_data.get("enabled", True),
                    metadata={k: v for k, v in skill_data.items()
                             if k not in ("name", "enabled")}
                ))

        # Create config
        return cls(
            id=agent_data.get("id", "p3394-agent"),
            name=agent_data.get("name", "P3394 Agent"),
            version=agent_data.get("version", "0.1.0"),
            description=agent_data.get("description", "A P3394-compliant agent"),
            channels=channels if channels else {
                "cli": ChannelConfig(enabled=True),
                "web": ChannelConfig(enabled=True, port=8000),
            },
            llm=llm_config,
            storage=storage_config,
            skills=skills,
            working_dir=Path(data.get("working_dir", ".")),
            metadata=data.get("metadata", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary (for serialization)"""
        return {
            "agent": {
                "id": self.id,
                "name": self.name,
                "version": self.version,
                "description": self.description,
            },
            "channels": {
                cid: {
                    "enabled": cfg.enabled,
                    "host": cfg.host,
                    "port": cfg.port,
                    **cfg.metadata,
                }
                for cid, cfg in self.channels.items()
            },
            "llm": {
                "provider": self.llm.provider,
                "model": self.llm.model,
                "system_prompt": self.llm.system_prompt,
                "max_tokens": self.llm.max_tokens,
                "temperature": self.llm.temperature,
            },
            "storage": {
                "type": self.storage.type,
                "path": self.storage.path,
                **self.storage.metadata,
            },
            "skills": [
                {"name": s.name, "enabled": s.enabled, **s.metadata}
                for s in self.skills
            ],
            "working_dir": str(self.working_dir),
            "metadata": self.metadata,
        }
