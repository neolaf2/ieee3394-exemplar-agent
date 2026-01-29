"""
WhatsApp Channel Binding Implementation

Implements the channel binding interface for WhatsApp,
handling QR code authentication and session management.
"""

import asyncio
import logging
from typing import Optional
from pathlib import Path

from ..binding import (
    ChannelBindingInterface,
    BindingContext,
    AuthPrompt,
    AuthMethod,
)
from .config import WhatsAppChannelConfig, ServicePrincipal

logger = logging.getLogger(__name__)


class WhatsAppChannelBinding(ChannelBindingInterface):
    """
    WhatsApp channel binding implementation.

    Handles:
    1. Service principal verification
    2. WhatsApp bridge connection
    3. QR code authentication
    4. Session persistence
    """

    def __init__(
        self,
        config: WhatsAppChannelConfig,
        bridge_url: str = "http://localhost:3000",
        bridge_ws_url: str = "ws://localhost:3000/ws"
    ):
        """
        Initialize WhatsApp binding.

        Args:
            config: WhatsApp channel configuration with service principal
            bridge_url: URL of WhatsApp bridge HTTP API
            bridge_ws_url: URL of WhatsApp bridge WebSocket
        """
        self.config = config
        self.bridge_url = bridge_url
        self.bridge_ws_url = bridge_ws_url

        self._http_session = None
        self._ws = None
        self._qr_code: Optional[str] = None
        self._authenticated = False
        self._ws_listener_task: Optional[asyncio.Task] = None

    @property
    def channel_type(self) -> str:
        return "whatsapp"

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.QR_CODE

    async def initialize_auth(self, context: BindingContext) -> AuthPrompt:
        """
        Initialize WhatsApp authentication.

        Steps:
        1. Connect to WhatsApp bridge
        2. Request QR code
        3. Start listening for authentication events

        Returns:
            AuthPrompt with QR code for user to scan
        """
        logger.info("Initializing WhatsApp authentication")

        try:
            # Initialize HTTP session
            import aiohttp
            self._http_session = aiohttp.ClientSession()

            # Check bridge status
            await self._check_bridge_status()

            # Connect WebSocket
            await self._connect_websocket()

            # Request QR code
            await self._request_qr_code()

            # Wait for QR code to be received (up to 10 seconds)
            for _ in range(50):  # 50 * 0.2s = 10s
                if self._qr_code:
                    break
                await asyncio.sleep(0.2)

            if not self._qr_code:
                raise RuntimeError("Failed to receive QR code from bridge")

            # Store QR in context
            context.auth_data["qr_code"] = self._qr_code

            # Create auth prompt
            return AuthPrompt(
                method=AuthMethod.QR_CODE,
                message="Please scan the QR code with WhatsApp to authenticate.",
                data={"qr_code": self._qr_code},
                instructions=[
                    "Open WhatsApp on your phone",
                    "Tap Menu (⋮) or Settings",
                    "Tap 'Linked Devices'",
                    "Tap 'Link a Device'",
                    "Scan the QR code shown below"
                ]
            )

        except Exception as e:
            logger.error(f"Failed to initialize WhatsApp auth: {e}")
            raise

    async def check_auth_status(self, context: BindingContext) -> tuple[bool, Optional[str]]:
        """
        Check if WhatsApp authentication is complete.

        Returns:
            (is_authenticated, error_message)
        """
        return (self._authenticated, None)

    async def finalize_binding(self, context: BindingContext) -> bool:
        """
        Finalize WhatsApp binding.

        Saves authentication session and verifies connectivity.

        Returns:
            True if successful
        """
        logger.info("Finalizing WhatsApp binding")

        try:
            # Verify connection
            async with self._http_session.get(f"{self.bridge_url}/auth/status") as resp:
                if resp.status != 200:
                    raise RuntimeError("Failed to verify authentication status")

                data = await resp.json()
                if not data.get("authenticated"):
                    raise RuntimeError("Authentication verification failed")

            # Save metadata
            context.metadata["whatsapp_authenticated"] = True
            context.metadata["bridge_url"] = self.bridge_url

            logger.info("WhatsApp binding finalized successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to finalize WhatsApp binding: {e}")
            context.error = str(e)
            return False

    async def cleanup(self, context: BindingContext):
        """Clean up resources."""
        logger.info("Cleaning up WhatsApp binding resources")

        # Stop WebSocket listener
        if self._ws_listener_task:
            self._ws_listener_task.cancel()
            try:
                await self._ws_listener_task
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

    # =========================================================================
    # BRIDGE COMMUNICATION
    # =========================================================================

    async def _check_bridge_status(self):
        """Check if WhatsApp bridge is running."""
        try:
            async with self._http_session.get(
                f"{self.bridge_url}/status",
                timeout=5
            ) as resp:
                if resp.status != 200:
                    raise ConnectionError(f"Bridge returned status {resp.status}")

                data = await resp.json()
                logger.info(f"Bridge status: {data}")

        except Exception as e:
            raise ConnectionError(
                f"Cannot connect to WhatsApp bridge at {self.bridge_url}. "
                f"Make sure the bridge is running with 'npm start'. Error: {e}"
            )

    async def _connect_websocket(self):
        """Connect to bridge WebSocket."""
        import aiohttp

        logger.info(f"Connecting to WebSocket: {self.bridge_ws_url}")

        try:
            self._ws = await self._http_session.ws_connect(self.bridge_ws_url)

            # Start WebSocket listener
            self._ws_listener_task = asyncio.create_task(self._ws_listener())

            logger.info("WebSocket connected")

        except Exception as e:
            raise ConnectionError(f"Failed to connect WebSocket: {e}")

    async def _ws_listener(self):
        """Listen for messages from WebSocket."""
        import aiohttp

        while self._ws:
            try:
                msg = await self._ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    import json
                    data = json.loads(msg.data)
                    await self._handle_ws_message(data)

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.CLOSE):
                    logger.info("WebSocket closed")
                    break

                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self._ws.exception()}")
                    break

            except Exception as e:
                logger.error(f"WebSocket listener error: {e}")
                break

    async def _handle_ws_message(self, data: dict):
        """Handle WebSocket message from bridge."""
        msg_type = data.get("type")

        if msg_type == "qr":
            # QR code received
            self._qr_code = data.get("qr")
            logger.info("QR code received from bridge")

        elif msg_type == "ready":
            # WhatsApp authenticated
            self._authenticated = True
            logger.info("WhatsApp authentication complete!")

        elif msg_type == "auth_failure":
            # Authentication failed
            logger.error(f"WhatsApp authentication failed: {data.get('message')}")

        elif msg_type == "disconnected":
            # Client disconnected
            self._authenticated = False
            logger.warning("WhatsApp disconnected")

    async def _request_qr_code(self):
        """Request QR code from bridge."""
        try:
            async with self._http_session.post(
                f"{self.bridge_url}/auth/qr"
            ) as resp:
                if resp.status != 200:
                    raise RuntimeError(f"Failed to request QR code: {resp.status}")

        except Exception as e:
            raise RuntimeError(f"Failed to request QR code: {e}")
