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
    agent_name: str = "ieee3394-exemplar"
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

    # Create and start server
    server = AgentServer(gateway)

    try:
        await server.start()
    except KeyboardInterrupt:
        print("\n\n👋 Shutting down agent host...")
        await server.stop()
