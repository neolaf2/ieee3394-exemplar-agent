"""
P3394 Agent Server Channel Adapter

Implements the full P3394 agent protocol for agent-to-agent communication.
Exposes agent manifest and handles P3394 UMF message exchange.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any, Set
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn
import httpx

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType, P3394Address
from ..core.gateway import AgentGateway
from .base import ChannelAdapter, ChannelCapabilities

logger = logging.getLogger(__name__)


class P3394ServerAdapter(ChannelAdapter):
    """
    P3394 Agent Server Channel Adapter

    Implements full P3394 agent protocol for agent-to-agent communication.

    Endpoints:
    - GET /manifest - Returns agent manifest (capabilities, identity)
    - GET /channels - List available channels
    - POST /messages - Send P3394 UMF message (HTTP)
    - WS /ws - WebSocket for P3394 UMF messages (streaming)
    """

    def __init__(
        self,
        gateway: AgentGateway,
        host: str = "0.0.0.0",
        port: int = 8101
    ):
        super().__init__(gateway, "p3394-server")
        self.host = host
        self.port = port

        # Our agent's P3394 address
        self.agent_address = P3394Address(
            agent_id=gateway.AGENT_ID,
            channel_id=self.channel_id
        )

        self.app = FastAPI(
            title=f"{gateway.AGENT_NAME} - P3394 Agent Protocol",
            description="P3394-compliant agent communication endpoint",
            version=gateway.AGENT_VERSION
        )

        # Add CORS
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Active WebSocket connections
        self.websockets: Dict[str, WebSocket] = {}

        self._setup_routes()

    @property
    def capabilities(self) -> ChannelCapabilities:
        """P3394 server capabilities - supports all content types"""
        return ChannelCapabilities(
            content_types=[
                ContentType.TEXT,
                ContentType.JSON,
                ContentType.MARKDOWN,
                ContentType.HTML,
                ContentType.BINARY,
                ContentType.TOOL_CALL,
                ContentType.TOOL_RESULT
            ],
            max_message_size=100 * 1024 * 1024,  # 100 MB
            max_attachment_size=100 * 1024 * 1024,  # 100 MB
            supports_streaming=True,
            supports_attachments=True,
            supports_images=True,
            supports_folders=True,
            supports_multipart=True,
            supports_markdown=True,
            supports_html=True,
            max_concurrent_connections=1000,
            rate_limit_per_minute=1000
        )

    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """
        Send a message back to a P3394 client.

        Args:
            reply_to: {"endpoint": "http://...", "address": "p3394://..."}
            message: P3394 UMF message to send
        """
        endpoint = reply_to.get("endpoint")
        if not endpoint:
            logger.warning(f"Cannot send to P3394 client: no endpoint in reply_to")
            return

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    endpoint,
                    json=message.to_dict(),
                    headers={"x-p3394-client": self.agent_address.to_uri()}
                )
                response.raise_for_status()
        except Exception as e:
            logger.exception(f"Error sending to P3394 client: {e}")

    def _setup_routes(self):
        """Setup P3394 protocol routes"""

        @self.app.get("/manifest")
        async def get_manifest():
            """
            Agent manifest endpoint (P3394 discovery)

            Returns agent identity, capabilities, and available channels.
            """
            return {
                "agent_id": self.gateway.AGENT_ID,
                "name": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "protocol": "P3394",
                "protocol_version": "0.1.0",
                "address": self.agent_address.to_uri(),
                "description": "IEEE P3394 Exemplar Agent - Reference implementation",
                "capabilities": {
                    "symbolic_commands": list(set(cmd.name for cmd in self.gateway.commands.values())),
                    "llm_enabled": True,
                    "streaming": True,
                    "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep", "WebSearch"],
                    "skills": [],
                    "subagents": ["documentation-agent", "onboarding-agent", "demo-agent"]
                },
                "channels": self._get_channels_with_endpoints(),
                "commands": self._get_commands_with_syntax(),
                "endpoints": {
                    "manifest": f"http://{self.host}:{self.port}/manifest",
                    "messages": f"http://{self.host}:{self.port}/messages",
                    "websocket": f"ws://{self.host}:{self.port}/ws",
                    "health": f"http://{self.host}:{self.port}/health"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        @self.app.get("/channels")
        async def list_channels():
            """List available communication channels"""
            return {
                "channels": self._get_channels()
            }

        @self.app.post("/messages")
        async def send_message(
            umf_message: dict,
            x_p3394_client: Optional[str] = Header(None, alias="x-p3394-client")
        ):
            """
            Send a P3394 UMF message (HTTP POST)

            Expects:
            - Body: P3394Message as JSON
            - Header: x-p3394-client (optional) - client agent's P3394 address
            """
            try:
                # Parse UMF message
                message = P3394Message.from_dict(umf_message)

                # Set destination to this agent
                if not message.destination:
                    message.destination = self.agent_address

                # Log client agent if provided
                if x_p3394_client:
                    logger.info(f"P3394 message from: {x_p3394_client}")
                    if not message.source:
                        message.source = P3394Address.from_uri(x_p3394_client)

                # Handle message through gateway
                response = await self.gateway.handle(message)

                # Return UMF response
                return response.to_dict()

            except Exception as e:
                logger.exception(f"Error handling P3394 message: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.app.websocket("/ws")
        async def websocket_endpoint(websocket: WebSocket):
            """
            WebSocket for P3394 UMF messages

            Protocol:
            1. Client connects
            2. Client sends: {"action": "identify", "address": "p3394://client-id/channel"}
            3. Server responds: {"action": "identified", "session_id": "..."}
            4. Client sends: P3394Message as JSON
            5. Server responds: P3394Message as JSON
            """
            await websocket.accept()

            session_id = None
            client_address = None

            try:
                # Wait for identification
                data = await websocket.receive_json()

                if data.get("action") == "identify":
                    client_address_str = data.get("address")
                    if client_address_str:
                        client_address = P3394Address.from_uri(client_address_str)
                        logger.info(f"P3394 client identified: {client_address_str}")

                    # Create session
                    session = await self.gateway.session_manager.create_session(
                        channel_id="p3394-ws"
                    )
                    session_id = session.id
                    self.websockets[session_id] = websocket

                    # Send identification response
                    await websocket.send_json({
                        "action": "identified",
                        "session_id": session_id,
                        "server_address": self.agent_address.to_uri(),
                        "agent": self.gateway.AGENT_NAME,
                        "version": self.gateway.AGENT_VERSION
                    })
                else:
                    await websocket.send_json({
                        "error": "First message must be identification"
                    })
                    await websocket.close()
                    return

                # Message loop
                while True:
                    data = await websocket.receive_json()

                    # Parse as P3394 message
                    message = P3394Message.from_dict(data)
                    message.session_id = session_id

                    # Set source/destination
                    if not message.source and client_address:
                        message.source = client_address
                    if not message.destination:
                        message.destination = self.agent_address

                    # Handle message
                    response = await self.gateway.handle(message)

                    # Send response
                    await websocket.send_json(response.to_dict())

            except WebSocketDisconnect:
                logger.info(f"P3394 client disconnected: {session_id}")
            except Exception as e:
                logger.exception(f"WebSocket error: {e}")
                await websocket.send_json({"error": str(e)})
            finally:
                if session_id:
                    if session_id in self.websockets:
                        del self.websockets[session_id]
                    await self.gateway.session_manager.end_session(session_id)

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "protocol": "P3394",
                "agent": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "address": self.agent_address.to_uri()
            }

    def _get_channels(self) -> list:
        """Get list of available channels"""
        return [
            {
                "id": channel_id,
                "type": adapter.__class__.__name__,
                "active": adapter.is_active
            }
            for channel_id, adapter in self.gateway.channels.items()
        ]

    def _get_channels_with_endpoints(self) -> list:
        """
        Get list of channels with their specific command endpoints.

        Returns channel information including how to access commands on each channel.
        """
        channels = []

        for channel_id, adapter in self.gateway.channels.items():
            caps = adapter.capabilities

            # Determine command syntax type
            if caps.supports_cli_flags:
                command_syntax = "cli_flags"
            elif caps.supports_http_endpoints:
                command_syntax = "http"
            elif caps.supports_slash_commands:
                command_syntax = "slash"
            else:
                command_syntax = "text"

            channel_info = {
                "id": channel_id,
                "type": adapter.__class__.__name__,
                "active": adapter.is_active,
                "command_syntax": command_syntax,
                "command_prefix": caps.command_prefix,
                "endpoints": adapter.get_endpoints()
            }

            channels.append(channel_info)

        return channels

    def _get_commands_with_syntax(self) -> list:
        """
        Get list of commands with syntax variations for each channel.

        Returns command information showing how to invoke each command
        across different channels.
        """
        commands = []
        seen = set()

        # Get unique commands from gateway
        for cmd in self.gateway.commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            # Build syntax variations for this command across channels
            syntax_by_channel = {}

            for channel_id, adapter in self.gateway.channels.items():
                # Get the channel-specific syntax for this command
                channel_syntax = adapter._map_command_syntax(cmd.name)
                syntax_by_channel[channel_id] = channel_syntax

            command_info = {
                "name": cmd.name,
                "description": cmd.description,
                "usage": cmd.usage if cmd.usage else cmd.name,
                "requires_auth": cmd.requires_auth,
                "aliases": cmd.aliases,
                "syntax_by_channel": syntax_by_channel
            }

            commands.append(command_info)

        return commands

    async def start(self):
        """Start the P3394 server"""
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)

        logger.info(f"P3394 Server Adapter started on http://{self.host}:{self.port}")
        logger.info(f"P3394 Address: {self.agent_address.to_uri()}")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def stop(self):
        """Stop the P3394 server"""
        self.is_active = False

        # Close all websockets
        for ws in self.websockets.values():
            await ws.close()
        self.websockets.clear()

        logger.info("P3394 Server Adapter stopped")
