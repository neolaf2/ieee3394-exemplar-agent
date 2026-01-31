"""
Agent Host Server (Daemon Mode)

Runs the Agent Gateway as a background service that clients can connect to.
Uses Unix domain socket for local IPC.

Channels are configured via agent.yaml - all enabled channels start automatically.
"""

import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Optional, Set

from .core.gateway_sdk import AgentGateway
from .core.umf import P3394Message
from .core.storage import AgentStorage
from .memory.kstar import KStarMemory
from .channels.cli import CLIChannelAdapter
from .channels.unified_web_server import UnifiedWebServer
from .data.repos.auth import AuthRepository

# Import config
try:
    from config import load_config, AgentConfig
except ImportError:
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from config import load_config, AgentConfig

logger = logging.getLogger(__name__)


class AgentServer:
    """Agent host server using Unix domain socket"""

    def __init__(
        self,
        gateway: AgentGateway,
        socket_path: str = "/tmp/ieee3394-agent.sock"
    ):
        self.gateway = gateway
        self.socket_path = socket_path
        self.server: Optional[asyncio.Server] = None

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """Handle a client connection"""
        addr = writer.get_extra_info('peername')
        logger.info(f"Client connected: {addr}")

        try:
            while True:
                # Read message length (4 bytes)
                length_bytes = await reader.readexactly(4)
                if not length_bytes:
                    break

                message_length = int.from_bytes(length_bytes, 'big')

                # Read message data
                data = await reader.readexactly(message_length)
                message_dict = json.loads(data.decode('utf-8'))

                # Convert to P3394Message
                message = P3394Message.from_dict(message_dict)

                # Ensure session directory exists
                if message.session_id:
                    session_dir = self.gateway.memory.storage.create_server_session(
                        message.session_id
                    )
                    logger.debug(f"Session directory: {session_dir}")

                    # Log incoming message as xAPI statement
                    await self.gateway.memory.storage.log_xapi_statement(
                        message.session_id,
                        message
                    )

                # Handle message
                response = await self.gateway.handle(message)

                # Log response as xAPI statement
                if message.session_id and response:
                    await self.gateway.memory.storage.log_xapi_statement(
                        message.session_id,
                        response
                    )

                # Send response
                response_data = json.dumps(response.to_dict()).encode('utf-8')
                response_length = len(response_data).to_bytes(4, 'big')

                writer.write(response_length + response_data)
                await writer.drain()

        except asyncio.IncompleteReadError:
            logger.info("Client disconnected")
        except Exception as e:
            logger.exception(f"Error handling client: {e}")
        finally:
            writer.close()
            await writer.wait_closed()

    async def start(self):
        """Start the agent server"""
        # Remove existing socket if present
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        # Create Unix domain socket server
        self.server = await asyncio.start_unix_server(
            self.handle_client,
            path=self.socket_path
        )

        # Make socket accessible
        os.chmod(self.socket_path, 0o666)

        logger.info(f"Agent server started on {self.socket_path}")
        print(f"🚀 IEEE 3394 Agent Host running on {self.socket_path}")
        print(f"   Agent: {self.gateway.AGENT_NAME} v{self.gateway.AGENT_VERSION}")
        print(f"   Press Ctrl+C to stop")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the agent server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        logger.info("Agent server stopped")


async def run_daemon(
    api_key: Optional[str] = None,
    debug: bool = False,
    config: Optional[AgentConfig] = None,
    # Legacy parameters (overridden by config if provided)
    agent_name: str = "p3394-exemplar",
    enable_anthropic_api: bool = None,
    anthropic_api_port: int = None,
    anthropic_api_keys: Optional[Set[str]] = None,
    enable_p3394_server: bool = None,
    p3394_server_port: int = None
):
    """
    Run the agent in daemon mode.

    All channels configured in agent.yaml with enabled: true will start automatically.
    Command-line arguments can override config settings.
    """
    # Load config if not provided
    if config is None:
        config = load_config()

    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get channel configurations
    cli_cfg = config.get_channel("cli")
    web_cfg = config.get_channel("web")
    anthropic_cfg = config.get_channel("anthropic_api")
    p3394_cfg = config.get_channel("p3394")

    # Apply overrides from command line (legacy support)
    if enable_anthropic_api is not None and anthropic_cfg:
        anthropic_cfg.enabled = enable_anthropic_api
    if anthropic_api_port is not None and anthropic_cfg:
        anthropic_cfg.port = anthropic_api_port
    if enable_p3394_server is not None and p3394_cfg:
        p3394_cfg.enabled = enable_p3394_server
    if p3394_server_port is not None and p3394_cfg:
        p3394_cfg.port = p3394_server_port

    # Initialize storage
    logger.info("Initializing agent storage...")
    storage = AgentStorage(agent_name=config.id)
    logger.info(f"Storage initialized at: {storage.base_dir}")

    # Configure logging to storage directory
    log_path = storage.get_log_path("server")
    file_handler = logging.FileHandler(log_path)
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    )
    logging.getLogger().addHandler(file_handler)

    # Initialize KSTAR memory with storage
    logger.info("Initializing KSTAR memory...")
    kstar = KStarMemory(storage=storage)

    # Initialize gateway with config
    logger.info("Initializing Agent Gateway (SDK)...")
    gateway = AgentGateway(memory=kstar, working_dir=storage.base_dir, config=config)

    # Load skills asynchronously
    await gateway.initialize()
    logger.info(f"Loaded {len(gateway.skills)} skills")

    # Store agent manifest
    manifest = storage.get_manifest()
    logger.info(f"Agent Manifest: {manifest.get('agent_id')} v{manifest.get('version')}")

    # Create servers based on config
    servers = []
    active_channels = []

    # Print startup banner
    print("=" * 60)
    print(f"  {config.name} v{config.version}")
    print("=" * 60)
    print(f"   Agent ID: {config.id}")

    # 1. UMF Socket Server (always enabled for local IPC)
    umf_server = AgentServer(gateway, socket_path="/tmp/p3394-agent.sock")
    servers.append(umf_server.start())
    print(f"   UMF Socket: /tmp/p3394-agent.sock")

    # 2. CLI Channel Adapter
    cli_channel = None
    if cli_cfg and cli_cfg.enabled:
        cli_channel = CLIChannelAdapter(gateway, socket_path="/tmp/p3394-agent-cli.sock")
        servers.append(cli_channel.start())
        active_channels.append("cli")
        print(f"   CLI Channel: /tmp/p3394-agent-cli.sock")

    # 3. Unified Web Server (consolidates web, anthropic_api, and p3394 channels)
    unified_web = None
    if web_cfg and web_cfg.enabled:
        # Get API keys from anthropic_api config if enabled
        api_keys = None
        if anthropic_cfg and anthropic_cfg.enabled:
            api_keys_list = anthropic_cfg.metadata.get("api_keys", [])
            api_keys = set(api_keys_list) if api_keys_list else (anthropic_api_keys or set())

        # Create auth repo with principal registry integration
        auth_repo = AuthRepository(principal_registry=gateway.principal_registry)

        unified_web = UnifiedWebServer(
            gateway,
            host=web_cfg.host,
            port=web_cfg.port,
            anthropic_api_keys=api_keys if api_keys else None,
            auth_repo=auth_repo
        )
        servers.append(unified_web.start())

        # Track active channels
        active_channels.append("web")
        print(f"\n   Unified Web Server: http://{web_cfg.host}:{web_cfg.port}")
        print(f"   ├── Web Chat:      /chat")
        print(f"   ├── Web API:       /api/")

        if anthropic_cfg and anthropic_cfg.enabled:
            active_channels.append("anthropic_api")
            print(f"   ├── Anthropic:     /v1/messages")
            if api_keys:
                print(f"   │   └── API Keys:  {len(api_keys)} configured")
            else:
                print(f"   │   └── API Keys:  None (open for testing)")

        if p3394_cfg and p3394_cfg.enabled:
            active_channels.append("p3394")
            print(f"   └── P3394:         /p3394/")
            print(f"       └── Address:   p3394://{config.id}")

    print("-" * 60)
    print(f"   Active Channels: {', '.join(active_channels)}")
    print(f"   Press Ctrl+C to stop")
    print("=" * 60)

    # Run all servers concurrently
    try:
        await asyncio.gather(*servers)
    except KeyboardInterrupt:
        print("\n\n  Shutting down agent host...")
        await umf_server.stop()
        if cli_channel:
            await cli_channel.stop()
        if unified_web:
            await unified_web.stop()
