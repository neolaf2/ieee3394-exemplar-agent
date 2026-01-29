"""
WhatsApp Channel Adapter for IEEE 3394 Agent

Implements P3394-compliant WhatsApp integration using whatsapp-web.js bridge.
Inspired by Moltbot's multi-channel architecture.
"""

import asyncio
import json
import logging
from typing import AsyncIterator, Dict, Optional, Any
from pathlib import Path

from ..base import ChannelAdapter
from ...core.umf import P3394Message, P3394Content, ContentType, MessageType
from ...core.gateway_sdk import AgentGateway
from .normalize import normalize_whatsapp_message, normalize_umf_to_whatsapp
from .config import WhatsAppChannelConfig, ServicePrincipal

logger = logging.getLogger(__name__)


class WhatsAppChannelAdapter(ChannelAdapter):
    """
    WhatsApp channel adapter using whatsapp-web.js bridge.

    Architecture:
    - Python adapter communicates with Node.js bridge via WebSocket/HTTP
    - Node.js bridge uses whatsapp-web.js to connect to WhatsApp Web
    - Messages are normalized to/from P3394 UMF format

    Similar to Moltbot's approach:
    - Dedicated adapter per platform
    - Message normalization layer
    - WebSocket-based control plane
    - Session management
    """

    def __init__(
        self,
        gateway: AgentGateway,
        config: WhatsAppChannelConfig,
        channel_id: str = "whatsapp",
    ):
        """
        Initialize WhatsApp adapter with security binding.

        SECURITY REQUIREMENT: A valid service principal is required to establish
        channel identity and authorization. This ensures:
        - The adapter is properly authenticated to the gateway
        - Channel operations are authorized and auditable
        - Proper identity binding per P3394 security requirements

        Args:
            gateway: Agent gateway for message routing
            config: WhatsApp channel configuration with service principal (REQUIRED)
            channel_id: Channel identifier (default: "whatsapp")

        Raises:
            ValueError: If service principal is invalid or missing required permissions
        """
        super().__init__(gateway, channel_id)

        # Validate configuration and service principal (SECURITY REQUIREMENT)
        is_valid, errors = config.validate()
        if not is_valid:
            error_msg = "Invalid WhatsApp configuration:\n" + "\n".join(f"  - {e}" for e in errors)
            logger.error(error_msg)
            raise ValueError(error_msg)

        self.config = config
        self.service_principal = config.service_principal

        # Extract configuration
        self.bridge_url = config.bridge_url
        self.bridge_ws_url = config.bridge_ws_url
        self.auth_dir = config.auth_dir or Path.home() / ".ieee3394" / "whatsapp_auth"
        self.auth_dir.mkdir(parents=True, exist_ok=True)

        logger.info(
            f"WhatsApp adapter initialized with service principal: {self.service_principal.client_id}"
        )

        # Connection state
        self._ws = None
        self._http_session = None
        self._connected = False
        self._qr_code: Optional[str] = None
        self._authenticated = False

        # Message queue for incoming messages
        self._message_queue: asyncio.Queue[Dict[str, Any]] = asyncio.Queue()

        # Active chat sessions
        self._chat_sessions: Dict[str, str] = {}  # whatsapp_id -> session_id

    async def start(self):
        """
        Start the WhatsApp adapter with security binding.

        Process:
        1. Authenticate service principal with gateway (SECURITY REQUIREMENT)
        2. Connect to whatsapp-web.js bridge
        3. Authenticate with WhatsApp (QR code scan if needed)
        4. Start receiving messages
        5. Register channel with gateway
        """
        logger.info("Starting WhatsApp channel adapter...")

        try:
            # 1. Authenticate service principal with gateway (SECURITY REQUIREMENT)
            await self._authenticate_service_principal()

            # 2. Initialize HTTP session
            import aiohttp

            self._http_session = aiohttp.ClientSession()

            # 3. Check bridge status
            await self._check_bridge_status()

            # 4. Connect WebSocket for real-time messages
            await self._connect_websocket()

            # 5. Authenticate with WhatsApp
            await self._authenticate_whatsapp()

            # 6. Start message processing loop
            self._process_task = asyncio.create_task(self._process_messages())

            # 7. Register channel with gateway
            self.is_active = True
            self.gateway.register_channel(self.channel_id, self)

            logger.info(
                f"WhatsApp adapter started successfully with identity: "
                f"{self.service_principal.client_id}"
            )

        except Exception as e:
            logger.error(f"Failed to start WhatsApp adapter: {e}")
            await self.stop()
            raise

    async def stop(self):
        """Stop the WhatsApp adapter."""
        logger.info("Stopping WhatsApp channel adapter...")

        self.is_active = False

        # Cancel message processing
        if hasattr(self, "_process_task"):
            self._process_task.cancel()
            try:
                await self._process_task
            except asyncio.CancelledError:
                pass

        # Close WebSocket
        if self._ws:
            await self._ws.close()
            self._ws = None

        # Close HTTP session
        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        logger.info("WhatsApp adapter stopped")

    async def send(self, message: P3394Message) -> None:
        """
        Send a message via WhatsApp.

        Args:
            message: P3394 UMF message to send
        """
        if not self._authenticated:
            logger.warning("Cannot send message: WhatsApp not authenticated")
            return

        try:
            # Determine target WhatsApp ID
            target_chat_id = self._get_target_chat_id(message)
            if not target_chat_id:
                logger.error("No target chat ID found in message")
                return

            # Convert UMF to WhatsApp format
            whatsapp_params = normalize_umf_to_whatsapp(message, target_chat_id)

            # Send via bridge API
            await self._send_via_bridge(whatsapp_params)

            logger.debug(f"Sent message to {target_chat_id}: {message.id}")

        except Exception as e:
            logger.error(f"Error sending WhatsApp message: {e}")
            raise

    async def receive(self) -> AsyncIterator[P3394Message]:
        """
        Receive messages from WhatsApp.

        Yields:
            P3394 messages normalized from WhatsApp format
        """
        while self.is_active:
            try:
                # Wait for message from queue
                whatsapp_msg = await asyncio.wait_for(
                    self._message_queue.get(), timeout=1.0
                )

                # Get or create session for this chat
                sender_id = whatsapp_msg.get("from", "")
                session_id = self._get_or_create_session(sender_id)

                # Normalize to P3394 UMF
                umf_message = normalize_whatsapp_message(
                    whatsapp_msg, self.gateway.AGENT_ID, session_id
                )

                yield umf_message

            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error receiving WhatsApp message: {e}")

    # =========================================================================
    # BRIDGE COMMUNICATION
    # =========================================================================

    async def _check_bridge_status(self):
        """Check if the whatsapp-web.js bridge is running."""
        try:
            async with self._http_session.get(f"{self.bridge_url}/status") as resp:
                if resp.status == 200:
                    data = await resp.json()
                    logger.info(f"Bridge status: {data}")
                else:
                    raise ConnectionError(
                        f"Bridge returned status {resp.status}"
                    )
        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to WhatsApp bridge at {self.bridge_url}. "
                f"Make sure the bridge is running. Error: {e}"
            )

    async def _connect_websocket(self):
        """Connect to the bridge's WebSocket for real-time messages."""
        import aiohttp

        logger.info(f"Connecting to WebSocket: {self.bridge_ws_url}")

        try:
            self._ws = await self._http_session.ws_connect(self.bridge_ws_url)
            self._connected = True

            # Start WebSocket message listener
            asyncio.create_task(self._ws_listener())

            logger.info("WebSocket connected")

        except Exception as e:
            raise ConnectionError(f"Failed to connect WebSocket: {e}")

    async def _ws_listener(self):
        """Listen for messages from the WebSocket."""
        while self.is_active and self._ws:
            try:
                msg = await self._ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    await self._handle_ws_message(data)

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break

                elif msg.type in (
                    aiohttp.WSMsgType.CLOSED,
                    aiohttp.WSMsgType.CLOSE,
                ):
                    logger.info("WebSocket closed")
                    break

            except Exception as e:
                logger.error(f"WebSocket listener error: {e}")
                break

        self._connected = False

    async def _handle_ws_message(self, data: Dict[str, Any]):
        """
        Handle incoming WebSocket message from bridge.

        Message types:
        - qr: QR code for authentication
        - ready: WhatsApp client ready
        - message: Incoming WhatsApp message
        - ack: Message acknowledgment
        - disconnected: Client disconnected
        """
        msg_type = data.get("type")

        if msg_type == "qr":
            # QR code for authentication
            self._qr_code = data.get("qr")
            logger.info("QR Code received. Scan with WhatsApp to authenticate.")
            logger.info(f"QR Code: {self._qr_code}")
            # In a real implementation, display QR code in terminal or web UI

        elif msg_type == "ready":
            # WhatsApp client authenticated and ready
            self._authenticated = True
            logger.info("WhatsApp authenticated and ready!")

        elif msg_type == "message":
            # Incoming WhatsApp message
            whatsapp_msg = data.get("message", {})
            await self._message_queue.put(whatsapp_msg)

        elif msg_type == "ack":
            # Message acknowledgment
            msg_id = data.get("messageId")
            ack = data.get("ack")
            logger.debug(f"Message {msg_id} ack: {ack}")

        elif msg_type == "disconnected":
            # Client disconnected
            self._authenticated = False
            logger.warning("WhatsApp disconnected")

        else:
            logger.debug(f"Unknown WebSocket message type: {msg_type}")

    async def _authenticate_service_principal(self):
        """
        Authenticate service principal with the gateway.

        This establishes the adapter's identity and verifies it has
        proper authorization to operate as a channel.

        SECURITY REQUIREMENT per P3394: All channel adapters must bind
        their identity through service principal authentication before
        accepting messages.
        """
        logger.info(f"Authenticating service principal: {self.service_principal.client_id}")

        # Verify service principal is not expired
        if self.service_principal.is_expired:
            raise RuntimeError("Service principal has expired. Please renew credentials.")

        # Verify required permissions
        required_permissions = [
            "channel.whatsapp.read",
            "channel.whatsapp.write",
            "gateway.message.send",
            "gateway.message.receive",
        ]

        for perm in required_permissions:
            if not self.service_principal.has_permission(perm):
                raise RuntimeError(
                    f"Service principal missing required permission: {perm}"
                )

        # Log authentication for audit trail
        logger.info(
            f"Service principal authenticated successfully: "
            f"{self.service_principal.client_id} "
            f"(channel: {self.service_principal.channel_type}, "
            f"permissions: {len(self.service_principal.permissions)})"
        )

        # Store identity in metadata for all messages
        self._identity_metadata = {
            "channel_principal_id": self.service_principal.client_id,
            "channel_type": self.service_principal.channel_type,
            "authenticated_at": self.service_principal.created_at,
        }

    async def _authenticate_whatsapp(self):
        """
        Authenticate with WhatsApp Web.

        If not authenticated, waits for QR code scan.
        """
        # Request authentication status
        async with self._http_session.get(
            f"{self.bridge_url}/auth/status"
        ) as resp:
            if resp.status == 200:
                data = await resp.json()
                self._authenticated = data.get("authenticated", False)

        if not self._authenticated:
            logger.info(
                "Not authenticated. Please scan the QR code with WhatsApp."
            )

            # Request QR code
            async with self._http_session.post(
                f"{self.bridge_url}/auth/qr"
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError("Failed to request QR code")

            # Wait for authentication (QR code scan)
            timeout = 120  # 2 minutes
            elapsed = 0
            while not self._authenticated and elapsed < timeout:
                await asyncio.sleep(1)
                elapsed += 1

            if not self._authenticated:
                raise TimeoutError(
                    "Authentication timeout. Please scan the QR code."
                )

    async def _send_via_bridge(self, params: Dict[str, Any]):
        """
        Send message via the bridge HTTP API.

        Args:
            params: WhatsApp message parameters
        """
        async with self._http_session.post(
            f"{self.bridge_url}/send", json=params
        ) as resp:
            if resp.status != 200:
                error = await resp.text()
                raise RuntimeError(f"Failed to send message: {error}")

            result = await resp.json()
            return result

    # =========================================================================
    # SESSION MANAGEMENT
    # =========================================================================

    def _get_or_create_session(self, whatsapp_id: str) -> str:
        """
        Get or create a session for a WhatsApp chat.

        Args:
            whatsapp_id: WhatsApp chat ID

        Returns:
            Session ID
        """
        if whatsapp_id in self._chat_sessions:
            return self._chat_sessions[whatsapp_id]

        # Create new session via gateway
        session = asyncio.get_event_loop().run_until_complete(
            self.gateway.session_manager.create_session(
                client_id=whatsapp_id, channel_id=self.channel_id
            )
        )

        self._chat_sessions[whatsapp_id] = session.id
        logger.debug(f"Created session {session.id} for WhatsApp chat {whatsapp_id}")

        return session.id

    def _get_target_chat_id(self, message: P3394Message) -> Optional[str]:
        """
        Extract WhatsApp chat ID from P3394 message.

        Args:
            message: P3394 message

        Returns:
            WhatsApp chat ID or None
        """
        # Check destination address
        if message.destination and message.destination.agent_id.startswith("whatsapp:"):
            agent_id = message.destination.agent_id
            if agent_id.startswith("whatsapp:group:"):
                # Group chat
                number = agent_id.replace("whatsapp:group:", "")
                return f"{number}@g.us"
            else:
                # Individual chat
                number = agent_id.replace("whatsapp:", "")
                return f"{number}@c.us"

        # Check metadata
        target_id = message.metadata.get("whatsapp_chat_id")
        if target_id:
            return target_id

        # Check session for original sender
        if message.session_id:
            for whatsapp_id, session_id in self._chat_sessions.items():
                if session_id == message.session_id:
                    return whatsapp_id

        return None

    async def _process_messages(self):
        """
        Process incoming WhatsApp messages.

        Main message processing loop that:
        1. Receives WhatsApp messages (via receive())
        2. Normalizes to P3394 UMF
        3. Routes through gateway
        4. Sends responses back to WhatsApp
        """
        logger.info("Started WhatsApp message processing loop")

        async for umf_message in self.receive():
            try:
                # Route message through gateway
                response = await self.gateway.handle(umf_message)

                # Send response back via WhatsApp
                if response:
                    await self.send(response)

            except Exception as e:
                logger.error(f"Error processing WhatsApp message: {e}")

    # =========================================================================
    # CHANNEL-SPECIFIC METHODS
    # =========================================================================

    async def get_qr_code(self) -> Optional[str]:
        """
        Get the current QR code for authentication.

        Returns:
            QR code string or None if not available
        """
        return self._qr_code

    async def is_authenticated(self) -> bool:
        """
        Check if WhatsApp is authenticated.

        Returns:
            True if authenticated, False otherwise
        """
        return self._authenticated

    async def get_chats(self) -> list[Dict[str, Any]]:
        """
        Get list of active WhatsApp chats.

        Returns:
            List of chat information
        """
        try:
            async with self._http_session.get(
                f"{self.bridge_url}/chats"
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
                return []
        except Exception as e:
            logger.error(f"Error getting chats: {e}")
            return []
