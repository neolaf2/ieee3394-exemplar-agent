"""
P3394 Agent Configuration Loader

Loads configuration from YAML files with environment variable interpolation.

Environment Variable Interpolation:
- ${VAR_NAME} - Required variable, raises error if not set
- ${VAR_NAME:-default} - Optional variable with default value

Example:
```yaml
channels:
  whatsapp:
    enabled: true
    service_phone: "${WHATSAPP_SERVICE_PHONE}"
    gateway_url: "${GATEWAY_URL:-http://localhost:8000/api/umf}"
```
"""

import os
import re
from pathlib import Path
from typing import Any, Dict, Optional, Union
import logging

import yaml

from .schema import AgentConfig

logger = logging.getLogger(__name__)

# Pattern for environment variable substitution: ${VAR} or ${VAR:-default}
ENV_VAR_PATTERN = re.compile(r'\$\{([^}:]+)(?::-([^}]*))?\}')


def interpolate_env_vars(value: Any) -> Any:
    """
    Recursively interpolate environment variables in configuration values.

    Supports:
    - ${VAR_NAME} - Required, raises KeyError if not set
    - ${VAR_NAME:-default} - Optional with default value

    Args:
        value: Configuration value (string, dict, list, or primitive)

    Returns:
        Value with environment variables interpolated
    """
    if isinstance(value, str):
        def replace_env_var(match):
            var_name = match.group(1)
            default_value = match.group(2)

            env_value = os.environ.get(var_name)

            if env_value is not None:
                return env_value
            elif default_value is not None:
                return default_value
            else:
                raise KeyError(
                    f"Environment variable '{var_name}' is required but not set. "
                    f"Set it or provide a default: ${{{var_name}:-default}}"
                )

        return ENV_VAR_PATTERN.sub(replace_env_var, value)

    elif isinstance(value, dict):
        return {k: interpolate_env_vars(v) for k, v in value.items()}

    elif isinstance(value, list):
        return [interpolate_env_vars(item) for item in value]

    else:
        return value


def load_config_from_file(
    config_path: Union[str, Path],
    interpolate: bool = True
) -> AgentConfig:
    """
    Load agent configuration from a YAML file.

    Args:
        config_path: Path to agent.yaml configuration file
        interpolate: Whether to interpolate environment variables (default: True)

    Returns:
        AgentConfig instance

    Raises:
        FileNotFoundError: If config file doesn't exist
        KeyError: If required environment variable is not set
        yaml.YAMLError: If YAML is malformed
    """
    config_path = Path(config_path)

    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")

    logger.info(f"Loading configuration from {config_path}")

    with open(config_path, 'r') as f:
        raw_config = yaml.safe_load(f)

    if raw_config is None:
        raw_config = {}

    # Interpolate environment variables
    if interpolate:
        try:
            raw_config = interpolate_env_vars(raw_config)
        except KeyError as e:
            logger.error(f"Configuration error: {e}")
            raise

    # Set working directory to config file's directory if not specified
    if "working_dir" not in raw_config:
        raw_config["working_dir"] = str(config_path.parent.absolute())

    return AgentConfig.from_dict(raw_config)


def load_config(
    config_path: Optional[Union[str, Path]] = None,
    working_dir: Optional[Union[str, Path]] = None,
) -> AgentConfig:
    """
    Load agent configuration with sensible defaults.

    Search order for configuration:
    1. Explicit config_path if provided
    2. agent.yaml in working_dir
    3. agent.yaml in current directory
    4. Default configuration

    Args:
        config_path: Explicit path to configuration file
        working_dir: Working directory to search for agent.yaml

    Returns:
        AgentConfig instance
    """
    # If explicit path provided, use it
    if config_path:
        return load_config_from_file(config_path)

    # Search for agent.yaml
    search_paths = []

    if working_dir:
        working_dir = Path(working_dir)
        search_paths.append(working_dir / "agent.yaml")
        search_paths.append(working_dir / "config" / "agent.yaml")

    # Current directory
    cwd = Path.cwd()
    search_paths.append(cwd / "agent.yaml")
    search_paths.append(cwd / "config" / "agent.yaml")

    # Try each path
    for path in search_paths:
        if path.exists():
            logger.info(f"Found configuration at {path}")
            return load_config_from_file(path)

    # No config file found - return defaults
    logger.info("No agent.yaml found, using default configuration")
    return AgentConfig(
        working_dir=Path(working_dir) if working_dir else cwd
    )


def create_default_config(
    output_path: Optional[Union[str, Path]] = None,
    agent_id: str = "my-agent",
    agent_name: str = "My P3394 Agent",
) -> Path:
    """
    Create a default agent.yaml configuration file.

    Useful for initializing new projects.

    Args:
        output_path: Where to write the config (default: ./agent.yaml)
        agent_id: Agent identifier
        agent_name: Human-readable agent name

    Returns:
        Path to created configuration file
    """
    output_path = Path(output_path) if output_path else Path("agent.yaml")

    default_config = f"""# P3394 Agent Configuration
# This file configures your P3394-compliant agent.
# Environment variables can be used: ${{VAR_NAME}} or ${{VAR_NAME:-default}}

agent:
  id: "{agent_id}"
  name: "{agent_name}"
  version: "0.1.0"
  description: "A P3394-compliant agent built from the starter kit"

# Channel configuration
channels:
  cli:
    enabled: true

  web:
    enabled: true
    host: "0.0.0.0"
    port: 8000

  # WhatsApp channel (disabled by default)
  # whatsapp:
  #   enabled: false
  #   service_phone: "${{WHATSAPP_SERVICE_PHONE}}"
  #   gateway_url: "${{GATEWAY_URL:-http://localhost:8000/api/umf}}"

# Skills to load
skills:
  - name: "echo"
    enabled: true
  - name: "help"
    enabled: true

# LLM configuration
llm:
  provider: "anthropic"
  model: "claude-sonnet-4-20250514"
  # Custom system prompt (optional)
  # system_prompt: |
  #   You are {{agent_name}}, a helpful assistant.
  #   Respond concisely and helpfully.

# Storage configuration
storage:
  type: "sqlite"
  path: "./data/agent.db"
"""

    with open(output_path, 'w') as f:
        f.write(default_config)

    logger.info(f"Created default configuration at {output_path}")
    return output_path
