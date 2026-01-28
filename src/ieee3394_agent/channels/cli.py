"""
CLI Channel Adapter

Transforms CLI client messages (simple text) to/from P3394 UMF messages.
Listens for CLI client connections and routes to the Agent Gateway.
"""

import asyncio
import json
import logging
from typing import Dict, Optional, Any

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType, P3394Address
from ..core.gateway_sdk import AgentGateway
from .base import ChannelAdapter, ChannelCapabilities

logger = logging.getLogger(__name__)


class CLIChannelAdapter(ChannelAdapter):
    """
    CLI Channel Adapter

    Transforms between CLI client protocol (simple text) and P3394 UMF.

    CLI Client sends:
        {"text": "Hello, world!"}

    Adapter transforms to UMF:
        P3394Message(type=REQUEST, content=[P3394Content(type=TEXT, data="Hello")])

    Gateway returns UMF:
        P3394Message(type=RESPONSE, content=[...])

    Adapter transforms back to CLI format:
        {"response": "Response text here"}
    """

    def __init__(
        self,
        gateway: AgentGateway,
        socket_path: str = "/tmp/ieee3394-agent-cli.sock"
    ):
        super().__init__(gateway, "cli")
        self.socket_path = socket_path
        self.server: Optional[asyncio.Server] = None

        # Track active CLI client connections
        self.clients: Dict[str, asyncio.StreamWriter] = {}

    @property
    def capabilities(self) -> ChannelCapabilities:
        """CLI channel capabilities"""
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.MARKDOWN],
            max_message_size=100 * 1024,  # 100 KB
            max_attachment_size=0,  # No attachments
            supports_streaming=False,
            supports_attachments=False,
            supports_images=False,
            supports_folders=False,
            supports_multipart=False,
            supports_markdown=True,  # Readable as text
            supports_html=False,
            max_concurrent_connections=10,
            rate_limit_per_minute=60
        )

    async def start(self):
        """Start the CLI channel adapter"""
        import os

        # Remove existing socket if present
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        # Create Unix domain socket server for CLI clients
        self.server = await asyncio.start_unix_server(
            self.handle_cli_client,
            path=self.socket_path
        )

        # Make socket accessible
        os.chmod(self.socket_path, 0o666)

        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)

        logger.info(f"CLI Channel Adapter started on {self.socket_path}")

        async with self.server:
            await self.server.serve_forever()

    async def stop(self):
        """Stop the CLI channel adapter"""
        self.is_active = False

        # Close all client connections
        for writer in self.clients.values():
            writer.close()
            await writer.wait_closed()
        self.clients.clear()

        # Close server
        if self.server:
            self.server.close()
            await self.server.wait_closed()

        # Clean up socket
        import os
        if os.path.exists(self.socket_path):
            os.remove(self.socket_path)

        logger.info("CLI Channel Adapter stopped")

    async def handle_cli_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter
    ):
        """
        Handle a CLI client connection.

        Protocol:
        1. Client sends: 4 bytes length + JSON {"text": "message"}
        2. Adapter transforms to UMF
        3. Adapter sends to Gateway
        4. Gateway returns UMF response
        5. Adapter transforms to JSON {"response": "text"}
        6. Adapter sends: 4 bytes length + JSON response
        """
        addr = writer.get_extra_info('peername')
        logger.info(f"CLI client connected: {addr}")

        # Create session for this client
        session = await self.gateway.session_manager.create_session(channel_id="cli")
        session_id = session.id
        self.clients[session_id] = writer

        # Send welcome message
        welcome = {
            "type": "welcome",
            "session_id": session_id,
            "agent": self.gateway.AGENT_NAME,
            "version": self.gateway.AGENT_VERSION
        }
        await self._send_cli_message(writer, welcome)

        try:
            while True:
                # Read message length (4 bytes)
                length_bytes = await reader.readexactly(4)
                if not length_bytes:
                    break

                message_length = int.from_bytes(length_bytes, 'big')

                # Read message data
                data = await reader.readexactly(message_length)
                cli_message = json.loads(data.decode('utf-8'))

                logger.debug(f"Received CLI message: {cli_message}")

                # Transform CLI message to UMF
                umf_message = self._cli_to_umf(cli_message, session_id)

                # Send to gateway
                umf_response = await self.gateway.handle(umf_message)

                # Transform UMF response back to CLI format
                cli_response = self._umf_to_cli(umf_response)

                # Send response to CLI client
                await self._send_cli_message(writer, cli_response)

        except asyncio.IncompleteReadError:
            logger.info(f"CLI client disconnected: {session_id}")
        except Exception as e:
            logger.exception(f"Error handling CLI client: {e}")
        finally:
            # Cleanup
            if session_id in self.clients:
                del self.clients[session_id]
            await self.gateway.session_manager.end_session(session_id)
            writer.close()
            await writer.wait_closed()

    def _cli_to_umf(self, cli_message: dict, session_id: str) -> P3394Message:
        """
        Transform CLI client message to P3394 UMF.

        CLI format:
            {"text": "message content"}

        UMF format:
            P3394Message(type=REQUEST, content=[...], session_id=...)
        """
        text = cli_message.get("text", "")

        return P3394Message(
            type=MessageType.REQUEST,
            content=[P3394Content(
                type=ContentType.TEXT,
                data=text
            )],
            session_id=session_id
        )

    def _umf_to_cli(self, umf_message: P3394Message) -> dict:
        """
        Transform P3394 UMF message to CLI client format.

        UMF format:
            P3394Message(type=RESPONSE, content=[...])

        CLI format:
            {"type": "response", "text": "...", "message_id": "..."}
        """
        # Adapt content to CLI capabilities (text/markdown only)
        adapted_message = self.adapt_content(umf_message)

        # Extract text from adapted content blocks
        text_parts = []
        json_parts = []

        for content in adapted_message.content:
            if content.type == ContentType.TEXT:
                text_parts.append(content.data)
            elif content.type == ContentType.MARKDOWN:
                text_parts.append(content.data)
            elif content.type == ContentType.JSON:
                json_parts.append(content.data)

        cli_response = {
            "type": "response" if adapted_message.type == MessageType.RESPONSE else "error",
            "message_id": adapted_message.id,
            "session_id": adapted_message.session_id
        }

        if text_parts:
            cli_response["text"] = "\n\n".join(text_parts)

        if json_parts:
            cli_response["data"] = json_parts

        # Notify about dropped content
        if "dropped_content" in adapted_message.metadata:
            dropped = adapted_message.metadata["dropped_content"]
            cli_response["dropped_content"] = dropped
            cli_response["text"] = cli_response.get("text", "") + f"\n\n⚠️  {len(dropped)} items not fully supported in CLI"

        return cli_response

    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """
        Send a message back to a CLI client.

        Args:
            reply_to: {"session_id": "..."}
            message: P3394 UMF message to send
        """
        session_id = reply_to.get("session_id")
        if not session_id or session_id not in self.clients:
            logger.warning(f"Cannot send to CLI client: session {session_id} not found")
            return

        writer = self.clients[session_id]
        cli_message = self._umf_to_cli(message)
        await self._send_cli_message(writer, cli_message)

    async def _send_cli_message(self, writer: asyncio.StreamWriter, message: dict):
        """Send a message to CLI client"""
        message_data = json.dumps(message).encode('utf-8')
        message_length = len(message_data).to_bytes(4, 'big')

        writer.write(message_length + message_data)
        await writer.drain()
