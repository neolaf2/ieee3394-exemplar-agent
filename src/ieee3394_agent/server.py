"""
Agent Host Server (Daemon Mode)

Runs the Agent Gateway as a background service that clients can connect to.
Uses Unix domain socket for local IPC.
"""

import asyncio
import json
import logging
import os
from pathlib import Path
from typing import Optional

from .core.gateway import AgentGateway
from .core.umf import P3394Message
from .core.storage import AgentStorage
from .memory.kstar import KStarMemory
from .plugins.hooks import set_kstar_memory
from .channels.cli import CLIChannelAdapter
from .channels.anthropic_api_server import AnthropicAPIServerAdapter
from .channels.p3394_server import P3394ServerAdapter

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
    agent_name: str = "ieee3394-exemplar",
    enable_anthropic_api: bool = False,
    anthropic_api_port: int = 8100,
    anthropic_api_keys: Optional[set] = None,
    enable_p3394_server: bool = True,
    p3394_server_port: int = 8101
):
    """Run the agent in daemon mode"""
    if debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Initialize storage
    logger.info("Initializing agent storage...")
    storage = AgentStorage(agent_name=agent_name)
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
    set_kstar_memory(kstar)

    # Initialize gateway
    logger.info("Initializing Agent Gateway...")
    gateway = AgentGateway(kstar_memory=kstar, anthropic_api_key=api_key)

    # Store agent manifest
    manifest = storage.get_manifest()
    logger.info(f"Agent Manifest: {manifest.get('agent_id')} v{manifest.get('version')}")

    # Create servers
    servers = []

    # 1. UMF Server (for direct UMF protocol clients)
    umf_server = AgentServer(gateway, socket_path="/tmp/ieee3394-agent.sock")
    servers.append(umf_server.start())

    # 2. CLI Channel Adapter (for CLI clients)
    cli_channel = CLIChannelAdapter(gateway, socket_path="/tmp/ieee3394-agent-cli.sock")
    servers.append(cli_channel.start())

    print("🚀 IEEE 3394 Agent Host starting...")
    print(f"   Agent: {gateway.AGENT_NAME} v{gateway.AGENT_VERSION}")
    print(f"   UMF Socket: /tmp/ieee3394-agent.sock")
    print(f"   CLI Channel: /tmp/ieee3394-agent-cli.sock")

    # 3. Anthropic API Server Adapter (optional)
    anthropic_server = None
    if enable_anthropic_api:
        anthropic_server = AnthropicAPIServerAdapter(
            gateway,
            host="0.0.0.0",
            port=anthropic_api_port,
            api_keys=anthropic_api_keys
        )
        servers.append(anthropic_server.start())
        print(f"   Anthropic API: http://0.0.0.0:{anthropic_api_port}")
        if anthropic_api_keys:
            print(f"   API Keys: {len(anthropic_api_keys)} configured")
        else:
            print(f"   API Keys: None (open for testing)")

    # 4. P3394 Server Adapter (for P3394 agent-to-agent)
    p3394_server = None
    if enable_p3394_server:
        p3394_server = P3394ServerAdapter(
            gateway,
            host="0.0.0.0",
            port=p3394_server_port
        )
        servers.append(p3394_server.start())
        print(f"   P3394 Agent: http://0.0.0.0:{p3394_server_port}")
        print(f"   P3394 Address: p3394://{gateway.AGENT_ID}")

    print(f"   Press Ctrl+C to stop")

    # Run all servers concurrently
    try:
        await asyncio.gather(*servers)
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down agent host...")
        await umf_server.stop()
        await cli_channel.stop()
        if anthropic_server:
            await anthropic_server.stop()
        if p3394_server:
            await p3394_server.stop()
