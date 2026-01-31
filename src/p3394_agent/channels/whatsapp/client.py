"""
WhatsApp Bridge Client

Connects to the Node.js WhatsApp bridge (bridge/whatsapp-bridge/).
Based on ClaudBot's proven whatsapp-web.js integration.
"""

import asyncio
import json
import logging
from typing import Any, Callable, Dict, Optional
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class WhatsAppMessage:
    """Incoming WhatsApp message from the bridge."""
    id: str
    from_id: str
    to_id: str
    body: str
    timestamp: int
    type: str = "chat"
    has_media: bool = False
    is_forwarded: bool = False
    from_me: bool = False
    contact_name: Optional[str] = None
    chat_name: Optional[str] = None
    is_group: bool = False

    @classmethod
    def from_bridge(cls, data: Dict[str, Any]) -> "WhatsAppMessage":
        """Create from bridge message format."""
        contact = data.get("contact", {})
        chat = data.get("chat", {})

        return cls(
            id=data.get("id", ""),
            from_id=data.get("from", ""),
            to_id=data.get("to", ""),
            body=data.get("body", ""),
            timestamp=data.get("timestamp", 0),
            type=data.get("type", "chat"),
            has_media=data.get("hasMedia", False),
            is_forwarded=data.get("isForwarded", False),
            from_me=data.get("fromMe", False),
            contact_name=contact.get("name") or contact.get("pushname"),
            chat_name=chat.get("name"),
            is_group=chat.get("isGroup", False),
        )


class WhatsAppBridgeClient:
    """
    Client for the Node.js WhatsApp bridge.

    The bridge must be running at bridge/whatsapp-bridge/:
        cd bridge/whatsapp-bridge && npm start

    Architecture:
        Python Agent <-> WhatsAppBridgeClient <-> Bridge (Node.js) <-> WhatsApp Web

    Example:
        async with WhatsAppBridgeClient() as client:
            # Check status
            status = await client.get_status()
            print(f"Ready: {status['whatsapp']['ready']}")

            # Send message
            await client.send_message("1234567890@c.us", "Hello!")

            # Listen for messages
            async for msg in client.listen():
                print(f"From {msg.from_id}: {msg.body}")
                await client.send_message(msg.from_id, f"Echo: {msg.body}")
    """

    def __init__(
        self,
        http_url: str = "http://localhost:3000",
        ws_url: str = "ws://localhost:3001",
    ):
        self.http_url = http_url
        self.ws_url = ws_url
        self._http_session = None
        self._ws = None
        self._connected = False
        self._message_handlers: list[Callable] = []

    async def __aenter__(self):
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.disconnect()

    async def connect(self):
        """Connect to the bridge HTTP and WebSocket."""
        import aiohttp

        self._http_session = aiohttp.ClientSession()

        # Check bridge is running
        try:
            status = await self.get_status()
            logger.info(f"Bridge status: {status}")
        except Exception as e:
            await self._http_session.close()
            raise ConnectionError(
                f"Cannot connect to WhatsApp bridge at {self.http_url}. "
                f"Make sure the bridge is running: cd bridge/whatsapp-bridge && npm start"
            ) from e

        # Connect WebSocket
        try:
            self._ws = await self._http_session.ws_connect(self.ws_url)
            self._connected = True
            logger.info(f"Connected to WhatsApp bridge WebSocket: {self.ws_url}")
        except Exception as e:
            await self._http_session.close()
            raise ConnectionError(
                f"Cannot connect to WebSocket at {self.ws_url}"
            ) from e

    async def disconnect(self):
        """Disconnect from the bridge."""
        self._connected = False

        if self._ws:
            await self._ws.close()
            self._ws = None

        if self._http_session:
            await self._http_session.close()
            self._http_session = None

        logger.info("Disconnected from WhatsApp bridge")

    # =========================================================================
    # HTTP API
    # =========================================================================

    async def get_status(self) -> Dict[str, Any]:
        """Get bridge and WhatsApp status."""
        async with self._http_session.get(f"{self.http_url}/status") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_auth_status(self) -> Dict[str, Any]:
        """Get authentication status."""
        async with self._http_session.get(f"{self.http_url}/auth/status") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_qr_code(self) -> Optional[str]:
        """Get current QR code for authentication."""
        async with self._http_session.get(f"{self.http_url}/auth/qr") as resp:
            if resp.status == 404:
                return None
            resp.raise_for_status()
            data = await resp.json()
            return data.get("qr")

    async def is_ready(self) -> bool:
        """Check if WhatsApp is authenticated and ready."""
        status = await self.get_status()
        return status.get("whatsapp", {}).get("ready", False)

    async def send_message(self, chat_id: str, message: str) -> Dict[str, Any]:
        """
        Send a message to a WhatsApp chat.

        Args:
            chat_id: WhatsApp chat ID (e.g., "1234567890@c.us" or "group_id@g.us")
            message: Text message to send

        Returns:
            Response with messageId and timestamp
        """
        payload = {"chatId": chat_id, "message": message}

        async with self._http_session.post(
            f"{self.http_url}/send",
            json=payload
        ) as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_chats(self) -> list[Dict[str, Any]]:
        """Get list of all WhatsApp chats."""
        async with self._http_session.get(f"{self.http_url}/chats") as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("chats", [])

    async def get_chat(self, chat_id: str) -> Dict[str, Any]:
        """Get specific chat by ID."""
        async with self._http_session.get(f"{self.http_url}/chats/{chat_id}") as resp:
            resp.raise_for_status()
            return await resp.json()

    async def get_messages(self, chat_id: str, limit: int = 50) -> list[Dict[str, Any]]:
        """Get messages from a chat."""
        async with self._http_session.get(
            f"{self.http_url}/chats/{chat_id}/messages",
            params={"limit": limit}
        ) as resp:
            resp.raise_for_status()
            data = await resp.json()
            return data.get("messages", [])

    async def logout(self):
        """Logout from WhatsApp (clears session)."""
        async with self._http_session.post(f"{self.http_url}/auth/logout") as resp:
            resp.raise_for_status()
            return await resp.json()

    # =========================================================================
    # WEBSOCKET EVENTS
    # =========================================================================

    async def listen(self):
        """
        Listen for incoming WhatsApp messages.

        Yields:
            WhatsAppMessage objects for each incoming message
        """
        import aiohttp

        if not self._ws:
            raise RuntimeError("Not connected. Call connect() first.")

        while self._connected:
            try:
                msg = await self._ws.receive()

                if msg.type == aiohttp.WSMsgType.TEXT:
                    data = json.loads(msg.data)
                    event_type = data.get("type")

                    if event_type == "message":
                        message_data = data.get("message", {})
                        yield WhatsAppMessage.from_bridge(message_data)

                    elif event_type == "ready":
                        logger.info("WhatsApp is ready")

                    elif event_type == "qr":
                        logger.info("QR code received - scan with WhatsApp")

                    elif event_type == "disconnected":
                        logger.warning(f"WhatsApp disconnected: {data.get('reason')}")
                        break

                elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                    logger.warning("WebSocket closed")
                    break

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in WebSocket listener: {e}")
                break

        self._connected = False

    def on_message(self, handler: Callable[[WhatsAppMessage], None]):
        """Register a message handler callback."""
        self._message_handlers.append(handler)

    async def run_handlers(self):
        """Run registered message handlers (alternative to listen() generator)."""
        async for msg in self.listen():
            for handler in self._message_handlers:
                try:
                    result = handler(msg)
                    if asyncio.iscoroutine(result):
                        await result
                except Exception as e:
                    logger.error(f"Error in message handler: {e}")
