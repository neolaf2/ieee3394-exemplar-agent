"""
P3394 Agent Storage Management

Manages the agent's directory structure for Short-Term Memory (STM)
and Long-Term Memory (LTM).

Directory Structure:
~/.P3394_agent_[agent_name]/
├── STM/                          # Short-Term Memory (sessions)
│   ├── server/                   # Server sessions (inbound)
│   │   └── [session_id]/
│   │       ├── trace.jsonl      # Session traces (KSTAR)
│   │       ├── context.json     # Session context
│   │       └── files/           # Session files
│   └── client/                   # Client sessions (outbound)
│       └── [session_id]/
│           ├── requests.jsonl   # Outbound requests
│           └── responses.jsonl  # Received responses
├── LTM/                          # Long-Term Memory (persistent)
│   ├── server/                   # Server capabilities
│   │   ├── plugins/             # Server plugins
│   │   ├── skills/              # Server skills (.md)
│   │   ├── agents/              # SubAgents (.md)
│   │   ├── channels/            # Channel adapter templates
│   │   ├── manifest.json        # Agent manifest (P3394)
│   │   ├── config.json          # Server configuration
│   │   └── allowlist.json       # Allowed operations/tools
│   └── client/                   # Client capabilities
│       ├── credentials/         # API keys, tokens (encrypted)
│       │   ├── anthropic.key
│       │   └── mcp_servers.json
│       ├── tools/               # Tool configurations
│       ├── agents/              # Known external agents
│       │   └── registry.json    # Agent registry
│       └── config.json          # Client configuration
└── logs/                         # Application logs
    ├── server.log
    ├── client.log
    └── audit.log                # Security audit log
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import os

logger = logging.getLogger(__name__)


class AgentStorage:
    """Manages agent storage directories and files"""

    def __init__(self, agent_name: str = "ieee3394-exemplar"):
        """
        Initialize agent storage.

        Args:
            agent_name: Name of the agent (for directory naming)
        """
        self.agent_name = agent_name
        self.base_dir = Path.home() / f".P3394_agent_{agent_name}"

        # Main directories
        self.stm_dir = self.base_dir / "STM"
        self.ltm_dir = self.base_dir / "LTM"
        self.logs_dir = self.base_dir / "logs"

        # STM subdirectories
        self.stm_server_dir = self.stm_dir / "server"
        self.stm_client_dir = self.stm_dir / "client"

        # LTM subdirectories
        self.ltm_server_dir = self.ltm_dir / "server"
        self.ltm_client_dir = self.ltm_dir / "client"

        # Initialize structure
        self._initialize_structure()

    def _initialize_structure(self):
        """Create initial directory structure"""
        logger.info(f"Initializing agent storage at {self.base_dir}")

        # Create main directories
        self.stm_dir.mkdir(parents=True, exist_ok=True)
        self.ltm_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)

        # STM directories
        self.stm_server_dir.mkdir(parents=True, exist_ok=True)
        self.stm_client_dir.mkdir(parents=True, exist_ok=True)

        # LTM server directories
        (self.ltm_server_dir / "plugins").mkdir(parents=True, exist_ok=True)
        (self.ltm_server_dir / "skills").mkdir(parents=True, exist_ok=True)
        (self.ltm_server_dir / "agents").mkdir(parents=True, exist_ok=True)
        (self.ltm_server_dir / "channels").mkdir(parents=True, exist_ok=True)

        # LTM client directories
        (self.ltm_client_dir / "credentials").mkdir(parents=True, exist_ok=True)
        (self.ltm_client_dir / "tools").mkdir(parents=True, exist_ok=True)
        (self.ltm_client_dir / "agents").mkdir(parents=True, exist_ok=True)

        # Secure credentials directory
        creds_dir = self.ltm_client_dir / "credentials"
        os.chmod(creds_dir, 0o700)  # Only owner can read/write

        # Initialize default files if they don't exist
        self._initialize_defaults()

        logger.info(f"Agent storage initialized at {self.base_dir}")

    def _initialize_defaults(self):
        """Create default configuration files if they don't exist"""

        # Server manifest
        manifest_path = self.ltm_server_dir / "manifest.json"
        if not manifest_path.exists():
            manifest = {
                "agent_id": self.agent_name,
                "version": "0.1.0",
                "standard": "IEEE P3394",
                "capabilities": {
                    "channels": ["cli", "unix-socket"],
                    "message_formats": ["P3394-UMF"],
                    "authentication": ["session-based"]
                },
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            manifest_path.write_text(json.dumps(manifest, indent=2))

        # Server config
        config_path = self.ltm_server_dir / "config.json"
        if not config_path.exists():
            config = {
                "session_ttl_hours": 24,
                "max_concurrent_sessions": 100,
                "kstar_enabled": True,
                "log_level": "INFO"
            }
            config_path.write_text(json.dumps(config, indent=2))

        # Server allowlist
        allowlist_path = self.ltm_server_dir / "allowlist.json"
        if not allowlist_path.exists():
            allowlist = {
                "allowed_tools": ["Read", "Write", "Edit", "Bash", "WebFetch"],
                "allowed_domains": ["*"],
                "blocked_operations": ["rm -rf /", "sudo rm"]
            }
            allowlist_path.write_text(json.dumps(allowlist, indent=2))

        # Client agent registry
        registry_path = self.ltm_client_dir / "agents" / "registry.json"
        if not registry_path.exists():
            registry = {
                "known_agents": [],
                "last_updated": datetime.now(timezone.utc).isoformat()
            }
            registry_path.write_text(json.dumps(registry, indent=2))

    # =========================================================================
    # STM - Server Session Management
    # =========================================================================

    def create_server_session(self, session_id: str) -> Path:
        """
        Create a new server session directory.

        Args:
            session_id: Unique session identifier

        Returns:
            Path to session directory
        """
        session_dir = self.stm_server_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)
        (session_dir / "files").mkdir(exist_ok=True)

        # Initialize session context
        context_path = session_dir / "context.json"
        if not context_path.exists():
            context = {
                "session_id": session_id,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "client_id": None,
                "metadata": {}
            }
            context_path.write_text(json.dumps(context, indent=2))

        logger.debug(f"Created server session: {session_id}")
        return session_dir

    def get_server_session_dir(self, session_id: str) -> Optional[Path]:
        """Get server session directory if it exists"""
        session_dir = self.stm_server_dir / session_id
        return session_dir if session_dir.exists() else None

    def append_trace(self, session_id: str, trace: Dict[str, Any]):
        """Append a trace to session KSTAR log (JSONL format)"""
        session_dir = self.get_server_session_dir(session_id)
        if not session_dir:
            session_dir = self.create_server_session(session_id)

        trace_path = session_dir / "trace.jsonl"
        with trace_path.open('a') as f:
            f.write(json.dumps(trace) + '\n')

    def read_session_traces(self, session_id: str) -> list[Dict[str, Any]]:
        """Read all traces for a session"""
        session_dir = self.get_server_session_dir(session_id)
        if not session_dir:
            return []

        trace_path = session_dir / "trace.jsonl"
        if not trace_path.exists():
            return []

        traces = []
        with trace_path.open('r') as f:
            for line in f:
                if line.strip():
                    traces.append(json.loads(line))
        return traces

    def cleanup_old_sessions(self, days: int = 7):
        """Remove session directories older than N days"""
        cutoff = datetime.now(timezone.utc).timestamp() - (days * 86400)

        for session_dir in self.stm_server_dir.iterdir():
            if not session_dir.is_dir():
                continue

            context_file = session_dir / "context.json"
            if not context_file.exists():
                continue

            if context_file.stat().st_mtime < cutoff:
                import shutil
                shutil.rmtree(session_dir)
                logger.info(f"Cleaned up old session: {session_dir.name}")

    # =========================================================================
    # STM - Client Session Management (Outbound)
    # =========================================================================

    def create_client_session(self, session_id: str, target_agent: str) -> Path:
        """
        Create a new client session directory (for outbound requests).

        Args:
            session_id: Unique session identifier
            target_agent: Target agent URI or ID

        Returns:
            Path to session directory
        """
        session_dir = self.stm_client_dir / session_id
        session_dir.mkdir(parents=True, exist_ok=True)

        # Initialize session context
        context_path = session_dir / "context.json"
        if not context_path.exists():
            context = {
                "session_id": session_id,
                "target_agent": target_agent,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "metadata": {}
            }
            context_path.write_text(json.dumps(context, indent=2))

        logger.debug(f"Created client session: {session_id} -> {target_agent}")
        return session_dir

    def append_client_request(self, session_id: str, request: Dict[str, Any]):
        """Log an outbound request"""
        session_dir = self.stm_client_dir / session_id
        if not session_dir.exists():
            raise ValueError(f"Client session not found: {session_id}")

        requests_path = session_dir / "requests.jsonl"
        with requests_path.open('a') as f:
            f.write(json.dumps(request) + '\n')

    def append_client_response(self, session_id: str, response: Dict[str, Any]):
        """Log a received response"""
        session_dir = self.stm_client_dir / session_id
        if not session_dir.exists():
            raise ValueError(f"Client session not found: {session_id}")

        responses_path = session_dir / "responses.jsonl"
        with responses_path.open('a') as f:
            f.write(json.dumps(response) + '\n')

    # =========================================================================
    # LTM - Server Management
    # =========================================================================

    def get_server_config(self) -> Dict[str, Any]:
        """Load server configuration"""
        config_path = self.ltm_server_dir / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {}

    def update_server_config(self, updates: Dict[str, Any]):
        """Update server configuration"""
        config = self.get_server_config()
        config.update(updates)

        config_path = self.ltm_server_dir / "config.json"
        config_path.write_text(json.dumps(config, indent=2))

    def get_manifest(self) -> Dict[str, Any]:
        """Load agent manifest"""
        manifest_path = self.ltm_server_dir / "manifest.json"
        if manifest_path.exists():
            return json.loads(manifest_path.read_text())
        return {}

    def list_skills(self) -> list[Path]:
        """List all skill files"""
        skills_dir = self.ltm_server_dir / "skills"
        return list(skills_dir.glob("*.md"))

    def list_subagents(self) -> list[Path]:
        """List all subagent definitions"""
        agents_dir = self.ltm_server_dir / "agents"
        return list(agents_dir.glob("*.md"))

    # =========================================================================
    # LTM - Client Management
    # =========================================================================

    def get_client_config(self) -> Dict[str, Any]:
        """Load client configuration"""
        config_path = self.ltm_client_dir / "config.json"
        if config_path.exists():
            return json.loads(config_path.read_text())
        return {}

    def store_credential(self, service: str, credential: str):
        """Store a credential securely"""
        creds_dir = self.ltm_client_dir / "credentials"
        cred_path = creds_dir / f"{service}.key"

        # In production, this should be encrypted
        # For now, just store with restricted permissions
        cred_path.write_text(credential)
        os.chmod(cred_path, 0o600)  # Only owner can read

        logger.info(f"Stored credential for: {service}")

    def get_credential(self, service: str) -> Optional[str]:
        """Retrieve a stored credential"""
        creds_dir = self.ltm_client_dir / "credentials"
        cred_path = creds_dir / f"{service}.key"

        if cred_path.exists():
            return cred_path.read_text().strip()
        return None

    def register_external_agent(self, agent_info: Dict[str, Any]):
        """Register an external agent in the registry"""
        registry_path = self.ltm_client_dir / "agents" / "registry.json"
        registry = json.loads(registry_path.read_text())

        # Add or update agent
        agents = registry.get("known_agents", [])
        existing = next(
            (a for a in agents if a.get("agent_id") == agent_info.get("agent_id")),
            None
        )

        if existing:
            agents.remove(existing)

        agents.append({
            **agent_info,
            "last_seen": datetime.now(timezone.utc).isoformat()
        })

        registry["known_agents"] = agents
        registry["last_updated"] = datetime.now(timezone.utc).isoformat()

        registry_path.write_text(json.dumps(registry, indent=2))

    # =========================================================================
    # Logging
    # =========================================================================

    def get_log_path(self, log_type: str = "server") -> Path:
        """Get path to log file"""
        return self.logs_dir / f"{log_type}.log"

    def __str__(self):
        return f"AgentStorage({self.agent_name}) @ {self.base_dir}"
