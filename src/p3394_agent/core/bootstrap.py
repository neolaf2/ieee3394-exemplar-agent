"""
Bootstrap Loader for P3394 Agent

Loads bootstrap configuration (ACLs, principals, credential bindings) into
the KSTAR memory server at agent startup.

Bootstrap data can come from:
1. Local JSON file (config/bootstrap_acl.json)
2. Environment variable pointing to bootstrap file
3. Remote configuration server (future)

The bootstrap process enables:
- Swappable memory servers with different capability sets
- Pre-configured access control
- Dynamic capability provisioning
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


async def load_bootstrap_config(
    config_path: Optional[Path] = None,
    memory: Optional["KStarMemory"] = None
) -> Dict[str, int]:
    """
    Load bootstrap configuration into memory.

    Args:
        config_path: Path to bootstrap JSON file
        memory: KStarMemory instance to load into

    Returns:
        Dict with counts of loaded items
    """
    from ..memory.kstar import KStarMemory

    if not memory:
        logger.warning("No memory instance provided for bootstrap")
        return {"acls": 0, "principals": 0, "credential_bindings": 0}

    # Default config path
    if config_path is None:
        config_path = Path.cwd() / "config" / "bootstrap_acl.json"

    if not config_path.exists():
        logger.info(f"No bootstrap config found at {config_path}")
        return {"acls": 0, "principals": 0, "credential_bindings": 0}

    try:
        with open(config_path) as f:
            config = json.load(f)

        logger.info(f"Loading bootstrap config from {config_path}")
        results = await memory.load_bootstrap_data(config)

        logger.info(f"Bootstrap complete: {results}")
        return results

    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in bootstrap config: {e}")
        return {"acls": 0, "principals": 0, "credential_bindings": 0}
    except Exception as e:
        logger.error(f"Failed to load bootstrap config: {e}")
        return {"acls": 0, "principals": 0, "credential_bindings": 0}


def get_default_bootstrap_config() -> Dict[str, Any]:
    """
    Get the default bootstrap configuration.

    This is used when no external config file is available.
    """
    return {
        "principals": [
            {
                "urn": "urn:principal:system:admin",
                "display_name": "System Administrator",
                "roles": ["admin", "system"],
                "organization": "system"
            },
            {
                "urn": "urn:principal:system:anonymous",
                "display_name": "Anonymous User",
                "roles": ["anonymous"],
                "organization": "public"
            },
            {
                "urn": "urn:principal:channel:cli:owner",
                "display_name": "CLI Owner",
                "roles": ["admin", "operator", "user"],
                "organization": "local"
            }
        ],
        "credential_bindings": [
            {
                "credential_type": "channel:cli:owner",
                "credential_value": "self",
                "principal_urn": "urn:principal:channel:cli:owner",
                "assurance_level": "cryptographic"
            }
        ],
        "acls": [
            # Public commands
            {
                "capability_id": "legacy.command.help",
                "visibility": "public",
                "default_permissions": ["list", "read", "execute"],
                "role_permissions": [
                    {"role": "*", "permissions": ["list", "read", "execute"], "minimum_assurance": "none"}
                ]
            },
            {
                "capability_id": "legacy.command.about",
                "visibility": "public",
                "default_permissions": ["list", "read", "execute"],
                "role_permissions": [
                    {"role": "*", "permissions": ["list", "read", "execute"], "minimum_assurance": "none"}
                ]
            },
            {
                "capability_id": "legacy.command.version",
                "visibility": "public",
                "default_permissions": ["list", "read", "execute"],
                "role_permissions": [
                    {"role": "*", "permissions": ["list", "read", "execute"], "minimum_assurance": "none"}
                ]
            },
            # Core chat
            {
                "capability_id": "core.chat",
                "visibility": "public",
                "default_permissions": ["list", "read"],
                "role_permissions": [
                    {"role": "admin", "permissions": ["list", "read", "execute", "modify", "delete"], "minimum_assurance": "none"},
                    {"role": "operator", "permissions": ["list", "read", "execute"], "minimum_assurance": "low"},
                    {"role": "user", "permissions": ["list", "read", "execute"], "minimum_assurance": "low"},
                    {"role": "anonymous", "permissions": ["list", "read"], "minimum_assurance": "none"}
                ]
            }
        ]
    }


class BootstrapManager:
    """
    Manages bootstrap data loading and synchronization.

    Supports:
    - Loading from local files
    - Loading from environment-specified paths
    - Merging multiple bootstrap sources
    - Syncing back to memory server
    """

    def __init__(self, memory: "KStarMemory", working_dir: Optional[Path] = None):
        from ..memory.kstar import KStarMemory
        self.memory = memory
        self.working_dir = working_dir or Path.cwd()
        self._loaded = False

    async def load_all(self) -> Dict[str, int]:
        """
        Load all bootstrap configurations.

        Order:
        1. Default in-code config
        2. config/bootstrap_acl.json
        3. Environment-specified config
        """
        import os

        results = {"acls": 0, "principals": 0, "credential_bindings": 0}

        # Check if memory already has data (from previous run or external preload)
        stats = await self.memory.get_stats()
        if stats.get("acl_count", 0) > 0 or stats.get("principal_count", 0) > 0:
            logger.info(
                f"Memory already has bootstrap data: "
                f"{stats.get('acl_count', 0)} ACLs, "
                f"{stats.get('principal_count', 0)} principals"
            )
            self._loaded = True
            return stats

        # Load default config
        default_config = get_default_bootstrap_config()
        default_results = await self.memory.load_bootstrap_data(default_config)
        self._merge_results(results, default_results)

        # Load from config directory
        config_path = self.working_dir / "config" / "bootstrap_acl.json"
        if config_path.exists():
            file_results = await load_bootstrap_config(config_path, self.memory)
            self._merge_results(results, file_results)

        # Load from environment-specified path
        env_path = os.environ.get("P3394_BOOTSTRAP_CONFIG")
        if env_path:
            env_config_path = Path(env_path)
            if env_config_path.exists():
                env_results = await load_bootstrap_config(env_config_path, self.memory)
                self._merge_results(results, env_results)

        self._loaded = True
        logger.info(f"Bootstrap complete: {results}")
        return results

    def _merge_results(self, target: Dict[str, int], source: Dict[str, int]) -> None:
        """Merge bootstrap result counts"""
        for key in target:
            target[key] += source.get(key, 0)

    @property
    def is_loaded(self) -> bool:
        """Check if bootstrap has been loaded"""
        return self._loaded
