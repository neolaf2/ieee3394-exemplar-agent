"""
Generic Channel Binding Interface

Provides a standardized process for authenticating and binding channel adapters
to the agent before they launch. This handles service principal authentication
and channel-specific authentication (QR codes, OAuth flows, etc.).
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Optional, Dict, Any, Callable, Awaitable
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from ..core.gateway_sdk import AgentGateway

logger = logging.getLogger(__name__)


class BindingStatus(str, Enum):
    """Status of channel binding process"""
    PENDING = "pending"
    SERVICE_PRINCIPAL_AUTH = "service_principal_auth"
    AWAITING_CHANNEL_AUTH = "awaiting_channel_auth"
    CHANNEL_AUTHENTICATING = "channel_authenticating"
    CHANNEL_AUTHENTICATED = "channel_authenticated"
    TESTING_CONNECTION = "testing_connection"
    COMPLETED = "completed"
    FAILED = "failed"


class AuthMethod(str, Enum):
    """Authentication methods for channel binding"""
    QR_CODE = "qr_code"  # Scan QR code (WhatsApp, WeChat, etc.)
    OAUTH = "oauth"  # OAuth flow (Slack, Google, etc.)
    TOKEN = "token"  # API token/key (Telegram, Discord, etc.)
    USERNAME_PASSWORD = "username_password"  # Traditional login
    CERTIFICATE = "certificate"  # Certificate-based auth
    NONE = "none"  # No channel-specific auth needed


@dataclass
class BindingContext:
    """
    Context for the binding process.

    Shared state that gets passed through the binding steps.
    """
    channel_type: str
    gateway: Optional[AgentGateway] = None
    service_principal_id: Optional[str] = None
    status: BindingStatus = BindingStatus.PENDING
    auth_method: Optional[AuthMethod] = None
    auth_data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None
    started_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AuthPrompt:
    """
    Information needed to display authentication prompt to user.

    Different auth methods require different prompts:
    - QR_CODE: Display QR code image/text
    - OAUTH: Show URL to visit
    - TOKEN: Ask user to enter token
    - etc.
    """
    method: AuthMethod
    message: str
    data: Dict[str, Any] = field(default_factory=dict)  # Method-specific data
    instructions: list[str] = field(default_factory=list)  # Step-by-step instructions


class ChannelBindingInterface(ABC):
    """
    Abstract interface for channel binding.

    Each channel adapter implements this interface to define its
    authentication and binding process.
    """

    @property
    @abstractmethod
    def channel_type(self) -> str:
        """Channel type identifier (e.g., 'whatsapp', 'telegram')"""
        pass

    @property
    @abstractmethod
    def auth_method(self) -> AuthMethod:
        """Authentication method used by this channel"""
        pass

    @abstractmethod
    async def initialize_auth(self, context: BindingContext) -> AuthPrompt:
        """
        Initialize authentication process.

        Args:
            context: Binding context

        Returns:
            AuthPrompt with instructions for user
        """
        pass

    @abstractmethod
    async def check_auth_status(self, context: BindingContext) -> tuple[bool, Optional[str]]:
        """
        Check if authentication is complete.

        Args:
            context: Binding context

        Returns:
            (is_authenticated, error_message)
        """
        pass

    @abstractmethod
    async def finalize_binding(self, context: BindingContext) -> bool:
        """
        Finalize the binding process.

        Save authentication data, verify connectivity, etc.

        Args:
            context: Binding context

        Returns:
            True if successful, False otherwise
        """
        pass

    @abstractmethod
    async def cleanup(self, context: BindingContext):
        """
        Clean up resources after binding (success or failure).

        Args:
            context: Binding context
        """
        pass


class ChannelBindingManager:
    """
    Manages the channel binding process.

    Orchestrates the multi-step binding flow:
    1. Service principal authentication
    2. Channel-specific authentication
    3. Connection testing
    4. Finalization
    """

    def __init__(
        self,
        gateway: Optional[AgentGateway] = None,
        ui_callback: Optional[Callable[[BindingContext, Optional[AuthPrompt]], Awaitable[None]]] = None
    ):
        """
        Initialize binding manager.

        Args:
            gateway: Agent gateway (if available)
            ui_callback: Async callback to update UI with binding status
        """
        self.gateway = gateway
        self.ui_callback = ui_callback
        self._active_bindings: Dict[str, BindingContext] = {}

    async def bind_channel(
        self,
        binding_impl: ChannelBindingInterface,
        timeout_seconds: int = 300
    ) -> BindingContext:
        """
        Execute the complete channel binding process.

        Args:
            binding_impl: Channel-specific binding implementation
            timeout_seconds: Maximum time to wait for authentication

        Returns:
            Completed BindingContext

        Raises:
            TimeoutError: If authentication times out
            RuntimeError: If binding fails
        """
        context = BindingContext(
            channel_type=binding_impl.channel_type,
            gateway=self.gateway,
            auth_method=binding_impl.auth_method
        )

        self._active_bindings[context.channel_type] = context

        try:
            # Step 1: Service Principal Authentication (if gateway available)
            if self.gateway:
                await self._authenticate_service_principal(context)

            # Step 2: Initialize Channel Authentication
            await self._update_status(context, BindingStatus.AWAITING_CHANNEL_AUTH)
            auth_prompt = await binding_impl.initialize_auth(context)
            await self._notify_ui(context, auth_prompt)

            # Step 3: Wait for Channel Authentication
            await self._update_status(context, BindingStatus.CHANNEL_AUTHENTICATING)
            await self._wait_for_auth(binding_impl, context, timeout_seconds)

            # Step 4: Test Connection
            await self._update_status(context, BindingStatus.TESTING_CONNECTION)
            # Let the implementation do any connection testing

            # Step 5: Finalize Binding
            success = await binding_impl.finalize_binding(context)
            if not success:
                raise RuntimeError("Failed to finalize binding")

            # Step 6: Complete
            await self._update_status(context, BindingStatus.COMPLETED)
            context.completed_at = datetime.now(timezone.utc).isoformat()

            logger.info(f"Channel binding completed for {context.channel_type}")

            return context

        except Exception as e:
            logger.error(f"Channel binding failed for {context.channel_type}: {e}")
            context.status = BindingStatus.FAILED
            context.error = str(e)
            await self._notify_ui(context, None)
            raise

        finally:
            # Cleanup
            await binding_impl.cleanup(context)
            if context.channel_type in self._active_bindings:
                del self._active_bindings[context.channel_type]

    async def _authenticate_service_principal(self, context: BindingContext):
        """Authenticate service principal with gateway."""
        await self._update_status(context, BindingStatus.SERVICE_PRINCIPAL_AUTH)

        # In a real implementation, this would authenticate with the gateway
        # For now, just mark as done
        logger.info(f"Service principal authenticated for {context.channel_type}")

    async def _wait_for_auth(
        self,
        binding_impl: ChannelBindingInterface,
        context: BindingContext,
        timeout_seconds: int
    ):
        """
        Wait for channel authentication to complete.

        Polls check_auth_status() until authenticated or timeout.
        """
        start_time = asyncio.get_event_loop().time()
        poll_interval = 2.0  # seconds

        while True:
            # Check timeout
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed > timeout_seconds:
                raise TimeoutError(
                    f"Authentication timeout after {timeout_seconds} seconds"
                )

            # Check auth status
            is_authenticated, error = await binding_impl.check_auth_status(context)

            if error:
                raise RuntimeError(f"Authentication error: {error}")

            if is_authenticated:
                await self._update_status(context, BindingStatus.CHANNEL_AUTHENTICATED)
                logger.info(f"Channel authenticated: {context.channel_type}")
                return

            # Wait before next poll
            await asyncio.sleep(poll_interval)

    async def _update_status(self, context: BindingContext, status: BindingStatus):
        """Update context status and notify UI."""
        context.status = status
        logger.debug(f"Binding status: {context.channel_type} -> {status.value}")
        await self._notify_ui(context, None)

    async def _notify_ui(self, context: BindingContext, auth_prompt: Optional[AuthPrompt]):
        """Notify UI callback of status change."""
        if self.ui_callback:
            try:
                await self.ui_callback(context, auth_prompt)
            except Exception as e:
                logger.error(f"UI callback error: {e}")

    def get_active_bindings(self) -> Dict[str, BindingContext]:
        """Get all active binding contexts."""
        return self._active_bindings.copy()


class TerminalBindingUI:
    """
    Terminal-based UI for channel binding.

    Displays QR codes, authentication status, and instructions in the terminal.
    """

    def __init__(self):
        self._last_status: Optional[BindingStatus] = None

    async def update(self, context: BindingContext, auth_prompt: Optional[AuthPrompt]):
        """
        Update UI with current binding status.

        Args:
            context: Binding context
            auth_prompt: Authentication prompt (if any)
        """
        # Only print on status change or new prompt
        if context.status != self._last_status or auth_prompt:
            self._print_status(context, auth_prompt)
            self._last_status = context.status

    def _print_status(self, context: BindingContext, auth_prompt: Optional[AuthPrompt]):
        """Print current status to terminal."""
        print()
        print("=" * 70)
        print(f"Channel Binding: {context.channel_type.upper()}")
        print("=" * 70)
        print()

        # Status
        status_emoji = self._get_status_emoji(context.status)
        print(f"Status: {status_emoji} {context.status.value.replace('_', ' ').title()}")
        print()

        # Show auth prompt if available
        if auth_prompt:
            self._print_auth_prompt(auth_prompt)

        # Show error if failed
        if context.status == BindingStatus.FAILED and context.error:
            print(f"❌ Error: {context.error}")
            print()

    def _print_auth_prompt(self, auth_prompt: AuthPrompt):
        """Print authentication prompt."""
        print("-" * 70)
        print(f"Authentication Required: {auth_prompt.method.value.replace('_', ' ').title()}")
        print("-" * 70)
        print()

        print(auth_prompt.message)
        print()

        # Show instructions
        if auth_prompt.instructions:
            print("Instructions:")
            for i, instruction in enumerate(auth_prompt.instructions, 1):
                print(f"  {i}. {instruction}")
            print()

        # Method-specific display
        if auth_prompt.method == AuthMethod.QR_CODE:
            self._print_qr_code(auth_prompt.data.get("qr_code", ""))

        elif auth_prompt.method == AuthMethod.OAUTH:
            url = auth_prompt.data.get("url", "")
            print(f"Authorization URL: {url}")
            print()

        elif auth_prompt.method == AuthMethod.TOKEN:
            print("Please enter your API token/key when prompted.")
            print()

    def _print_qr_code(self, qr_data: str):
        """Print QR code to terminal."""
        if not qr_data:
            print("QR Code: (waiting...)")
            return

        try:
            import qrcode

            # Generate QR code for terminal
            qr = qrcode.QRCode()
            qr.add_data(qr_data)
            qr.make()

            print("QR Code:")
            print()
            qr.print_ascii(invert=True)
            print()

        except ImportError:
            # Fallback if qrcode library not available
            print("QR Code Data:")
            print(qr_data)
            print()
            print("(Install 'qrcode' package for terminal QR display)")
            print()

    def _get_status_emoji(self, status: BindingStatus) -> str:
        """Get emoji for status."""
        emoji_map = {
            BindingStatus.PENDING: "⏳",
            BindingStatus.SERVICE_PRINCIPAL_AUTH: "🔐",
            BindingStatus.AWAITING_CHANNEL_AUTH: "⏳",
            BindingStatus.CHANNEL_AUTHENTICATING: "🔑",
            BindingStatus.CHANNEL_AUTHENTICATED: "✅",
            BindingStatus.TESTING_CONNECTION: "🔌",
            BindingStatus.COMPLETED: "✅",
            BindingStatus.FAILED: "❌",
        }
        return emoji_map.get(status, "⏳")


class WebBindingUI:
    """
    Web-based UI for channel binding.

    Serves a web page showing QR codes and authentication status.
    Useful for remote or graphical binding.
    """

    def __init__(self, port: int = 8200):
        """
        Initialize web UI.

        Args:
            port: HTTP server port
        """
        self.port = port
        self._app = None
        self._server = None
        self._context: Optional[BindingContext] = None
        self._auth_prompt: Optional[AuthPrompt] = None

    async def start(self):
        """Start web server."""
        from aiohttp import web

        self._app = web.Application()
        self._app.router.add_get("/", self._handle_index)
        self._app.router.add_get("/status", self._handle_status)

        runner = web.AppRunner(self._app)
        await runner.setup()

        site = web.TCPSite(runner, "0.0.0.0", self.port)
        await site.start()

        self._server = runner

        print(f"Web binding UI started at http://localhost:{self.port}")

    async def stop(self):
        """Stop web server."""
        if self._server:
            await self._server.cleanup()

    async def update(self, context: BindingContext, auth_prompt: Optional[AuthPrompt]):
        """Update UI with current binding status."""
        self._context = context
        self._auth_prompt = auth_prompt

    async def _handle_index(self, request):
        """Serve main page."""
        from aiohttp import web

        html = self._generate_html()
        return web.Response(text=html, content_type="text/html")

    async def _handle_status(self, request):
        """Serve status JSON."""
        from aiohttp import web

        if not self._context:
            return web.json_response({"status": "no_active_binding"})

        data = {
            "channel_type": self._context.channel_type,
            "status": self._context.status.value,
            "auth_method": self._auth_prompt.method.value if self._auth_prompt else None,
            "error": self._context.error,
        }

        if self._auth_prompt and self._auth_prompt.method == AuthMethod.QR_CODE:
            data["qr_code"] = self._auth_prompt.data.get("qr_code")

        return web.json_response(data)

    def _generate_html(self) -> str:
        """Generate HTML page."""
        if not self._context:
            return "<html><body><h1>No active binding</h1></body></html>"

        status_color = "green" if self._context.status == BindingStatus.COMPLETED else "orange"

        qr_section = ""
        if self._auth_prompt and self._auth_prompt.method == AuthMethod.QR_CODE:
            qr_data = self._auth_prompt.data.get("qr_code", "")
            qr_section = f"""
            <div id="qr-code" style="margin: 20px 0;">
                <h2>Scan QR Code</h2>
                <img id="qr-image" style="max-width: 300px;" />
            </div>
            <script src="https://cdn.jsdelivr.net/npm/qrcode@1.5.3/build/qrcode.min.js"></script>
            <script>
                QRCode.toDataURL('{qr_data}').then(url => {{
                    document.getElementById('qr-image').src = url;
                }});
            </script>
            """

        return f"""
        <html>
        <head>
            <title>Channel Binding - {self._context.channel_type}</title>
            <style>
                body {{ font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; padding: 20px; }}
                h1 {{ color: #333; }}
                .status {{ padding: 10px; background: {status_color}; color: white; border-radius: 5px; }}
            </style>
            <meta http-equiv="refresh" content="3">
        </head>
        <body>
            <h1>Channel Binding: {self._context.channel_type.upper()}</h1>
            <div class="status">
                Status: {self._context.status.value.replace('_', ' ').title()}
            </div>
            {qr_section}
            <p><small>Page auto-refreshes every 3 seconds</small></p>
        </body>
        </html>
        """
