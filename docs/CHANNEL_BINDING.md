# Channel Binding System

The IEEE 3394 Agent implements a generic **Channel Binding System** that provides a standardized process for authenticating and binding channel adapters before they launch. This ensures proper identity binding and security compliance per P3394 requirements.

## Overview

```
┌─────────────────────────────────────────────────────────┐
│                 Binding Process Flow                    │
└─────────────────────────────────────────────────────────┘

1. Check/Create Service Principal
   ↓
2. Validate Configuration
   ↓
3. Connect to Channel Bridge (if needed)
   ↓
4. Initialize Authentication (QR Code, OAuth, Token, etc.)
   ↓
5. Wait for User Authentication
   ↓
6. Verify & Test Connection
   ↓
7. Finalize & Save Session
   ↓
8. ✅ Channel Ready for Use
```

## Why Binding Before Launch?

Traditional channel adapters often handle authentication **during** runtime, which creates problems:

❌ **Problems without pre-binding:**
- No way to separate setup from runtime
- User must interact with agent during startup
- Auth failures cause runtime crashes
- Difficult to validate credentials before deployment
- No clear audit trail of who set up what

✅ **Benefits of pre-binding:**
- Setup happens **before** agent launches
- Clear separation: bind once, run many times
- Authentication can be done interactively (QR codes, OAuth)
- Credentials validated and saved for production use
- Complete audit trail with service principal identity
- Failed bindings don't crash the agent

## Architecture

### Core Components

#### 1. ChannelBindingInterface (Abstract)

Defines the contract every channel must implement:

```python
class ChannelBindingInterface(ABC):
    @property
    def channel_type(self) -> str:
        """e.g., 'whatsapp', 'telegram', 'slack'"""
        pass

    @property
    def auth_method(self) -> AuthMethod:
        """QR_CODE, OAUTH, TOKEN, etc."""
        pass

    async def initialize_auth(self, context) -> AuthPrompt:
        """Start auth and return prompt for user"""
        pass

    async def check_auth_status(self, context) -> tuple[bool, Optional[str]]:
        """Poll for auth completion"""
        pass

    async def finalize_binding(self, context) -> bool:
        """Save session and verify connection"""
        pass
```

#### 2. ChannelBindingManager

Orchestrates the multi-step binding process:

```python
manager = ChannelBindingManager(ui_callback=ui.update)
context = await manager.bind_channel(
    binding_impl=WhatsAppChannelBinding(config),
    timeout_seconds=300
)
```

Handles:
- Service principal authentication
- Status tracking and updates
- Timeout management
- Error handling and cleanup
- UI notifications

#### 3. Binding UIs

**TerminalBindingUI** - Shows status and QR codes in terminal:
```
======================================================================
Channel Binding: WHATSAPP
======================================================================

Status: 🔑 Channel Authenticating

----------------------------------------------------------------------
Authentication Required: Qr Code
----------------------------------------------------------------------

Please scan the QR code with WhatsApp to authenticate.

Instructions:
  1. Open WhatsApp on your phone
  2. Tap Menu (⋮) or Settings
  3. Tap 'Linked Devices'
  4. Tap 'Link a Device'
  5. Scan the QR code shown below

QR Code:
[QR CODE DISPLAYED HERE]
```

**WebBindingUI** - Serves a web page at http://localhost:8200:
- Real-time status updates (auto-refresh every 3 seconds)
- Visual QR code display using qrcode.js
- Progress indicators
- Error messages

#### 4. AuthMethod Enum

Supported authentication methods:

```python
class AuthMethod(str, Enum):
    QR_CODE = "qr_code"              # WhatsApp, WeChat
    OAUTH = "oauth"                   # Slack, Google Chat
    TOKEN = "token"                   # Telegram, Discord
    USERNAME_PASSWORD = "username_password"  # Traditional
    CERTIFICATE = "certificate"       # Certificate-based
    NONE = "none"                     # No auth needed
```

## Usage

### Quick Start (WhatsApp)

**Step 1: Start the WhatsApp bridge**
```bash
cd whatsapp_bridge
npm install  # First time only
npm start
```

**Step 2: Run the binding CLI**
```bash
# Terminal UI (default)
python scripts/bind_channel.py whatsapp

# Web UI (shows QR code in browser)
python scripts/bind_channel.py whatsapp --web-ui
```

**Step 3: Scan QR code with WhatsApp**

The CLI will:
1. Create/load service principal
2. Connect to bridge
3. Display QR code
4. Wait for authentication (up to 5 minutes)
5. Save authenticated session
6. ✅ Complete!

**Step 4: Use the channel**
```python
from ieee3394_agent.channels.whatsapp import WhatsAppChannelAdapter, WhatsAppChannelConfig

config = WhatsAppChannelConfig.from_file(
    Path.home() / ".ieee3394" / "whatsapp_config.json"
)

adapter = WhatsAppChannelAdapter(gateway, config)
await adapter.start()  # No QR code needed - already bound!
```

### Advanced Usage

#### Custom Configuration Path
```bash
python scripts/bind_channel.py whatsapp --config /path/to/config.json
```

#### Custom Timeout
```bash
python scripts/bind_channel.py whatsapp --timeout 600  # 10 minutes
```

#### Service Principal Expiration
```bash
python scripts/bind_channel.py whatsapp --expires-days 90  # 90 day expiry
```

#### Web UI on Custom Port
```bash
python scripts/bind_channel.py whatsapp --web-ui --web-port 9000
```

## Implementing a New Channel

To add a new channel (e.g., Telegram), implement the `ChannelBindingInterface`:

```python
# src/ieee3394_agent/channels/telegram/binding.py

from ..binding import ChannelBindingInterface, AuthMethod, AuthPrompt, BindingContext

class TelegramChannelBinding(ChannelBindingInterface):

    @property
    def channel_type(self) -> str:
        return "telegram"

    @property
    def auth_method(self) -> AuthMethod:
        return AuthMethod.TOKEN  # Telegram uses bot tokens

    async def initialize_auth(self, context: BindingContext) -> AuthPrompt:
        """Ask user to provide bot token"""
        return AuthPrompt(
            method=AuthMethod.TOKEN,
            message="Please enter your Telegram bot token from @BotFather",
            instructions=[
                "Open Telegram and find @BotFather",
                "Send /newbot to create a bot",
                "Copy the token provided",
                "Paste it when prompted"
            ]
        )

    async def check_auth_status(self, context: BindingContext) -> tuple[bool, Optional[str]]:
        """Check if token is valid"""
        token = context.auth_data.get("bot_token")
        if not token:
            return (False, None)

        # Verify token with Telegram API
        is_valid = await self._verify_token(token)
        return (is_valid, None if is_valid else "Invalid token")

    async def finalize_binding(self, context: BindingContext) -> bool:
        """Save token to config"""
        # Save config with token
        return True

    async def cleanup(self, context: BindingContext):
        """Clean up resources"""
        pass
```

Then add to the CLI:

```python
# scripts/bind_channel.py

async def bind_telegram(args):
    """Bind Telegram channel"""
    from src.ieee3394_agent.channels.telegram.binding import TelegramChannelBinding

    binding = TelegramChannelBinding(config)

    ui = TerminalBindingUI()
    manager = ChannelBindingManager(ui_callback=ui.update)

    context = await manager.bind_channel(binding, timeout_seconds=300)
    # ... rest of implementation
```

## Binding Status Flow

```python
PENDING
    ↓
SERVICE_PRINCIPAL_AUTH (verify credentials)
    ↓
AWAITING_CHANNEL_AUTH (show QR/OAuth/prompt)
    ↓
CHANNEL_AUTHENTICATING (polling for completion)
    ↓
CHANNEL_AUTHENTICATED (user scanned/authenticated)
    ↓
TESTING_CONNECTION (verify connectivity)
    ↓
COMPLETED (save session, ready to use)
```

## Security Model

### Service Principal Integration

Every channel binding **requires** a valid service principal:

1. **Before Binding** - Service principal is created or loaded
2. **During Binding** - Credentials are validated
3. **After Binding** - Principal ID is associated with the channel

The service principal provides:
- **Identity** - Who set up this channel?
- **Authorization** - What can this channel do?
- **Audit Trail** - When was it configured?
- **Expiration** - Time-limited credentials

### Secure Storage

Binding saves authentication data securely:

- **Service Principals** - `~/.ieee3394/service_principals/{client_id}.json`
- **Channel Configs** - `~/.ieee3394/{channel}_config.json`
- **Auth Sessions** - Bridge-specific (e.g., `whatsapp_bridge/whatsapp_auth/`)

All files created with secure permissions (600).

## Error Handling

### Common Errors

**Bridge Not Running**
```
❌ Cannot connect to WhatsApp bridge at http://localhost:3000
```
**Solution:** Start the bridge with `cd whatsapp_bridge && npm start`

**Authentication Timeout**
```
❌ Authentication timeout after 300 seconds
```
**Solution:** Run binding again, scan QR code faster

**Invalid Service Principal**
```
❌ Service principal has expired
```
**Solution:** Create new principal with `--expires-days` parameter

**QR Code Not Displayed**
```
QR Code: (waiting...)
```
**Solution:** Check bridge logs, ensure WebSocket is connected

## API Reference

### BindingContext

Shared state throughout the binding process:

```python
@dataclass
class BindingContext:
    channel_type: str
    status: BindingStatus
    auth_method: Optional[AuthMethod]
    auth_data: Dict[str, Any]  # Channel-specific auth data
    service_principal_id: Optional[str]
    error: Optional[str]
    started_at: str
    completed_at: Optional[str]
    metadata: Dict[str, Any]
```

### AuthPrompt

Information for displaying auth UI:

```python
@dataclass
class AuthPrompt:
    method: AuthMethod
    message: str
    data: Dict[str, Any]  # Method-specific (qr_code, url, etc.)
    instructions: list[str]  # Step-by-step instructions
```

### ChannelBindingManager

Main orchestrator:

```python
manager = ChannelBindingManager(
    gateway: Optional[AgentGateway] = None,
    ui_callback: Optional[Callable] = None
)

# Execute binding
context = await manager.bind_channel(
    binding_impl: ChannelBindingInterface,
    timeout_seconds: int = 300
)

# Get active bindings
active = manager.get_active_bindings()
```

## Testing

Test channel binding without starting the full agent:

```bash
# Test WhatsApp binding (dry run)
pytest tests/channels/test_whatsapp_binding.py

# Test binding manager
pytest tests/channels/test_binding_manager.py
```

## Troubleshooting

### QR Code Not Working

1. Check bridge logs for errors
2. Verify WebSocket connection
3. Try deleting auth session: `rm -rf whatsapp_bridge/whatsapp_auth`
4. Restart bridge and binding process

### Web UI Not Loading

1. Check port is available: `lsof -i :8200`
2. Try custom port: `--web-port 9000`
3. Check firewall settings

### Service Principal Errors

1. List principals: `ls ~/.ieee3394/service_principals/`
2. Check expiration in config file
3. Delete and recreate if corrupted

## Best Practices

1. **Bind Before Deployment** - Complete binding in development, deploy the saved config

2. **Use Expiring Credentials** - Set `--expires-days` for production security

3. **Separate Environments** - Use different service principals for dev/staging/prod

4. **Test Connection** - Verify binding with a test message before full deployment

5. **Rotate Credentials** - Re-bind periodically to rotate service principals

6. **Monitor Bindings** - Log binding events for security audit trail

## Future Enhancements

- [ ] OAuth 2.0 flow support for Slack, Google Chat
- [ ] Certificate-based authentication
- [ ] Multi-account binding (multiple WhatsApp numbers)
- [ ] Binding expiration warnings
- [ ] Auto-renewal of expiring service principals
- [ ] Binding health checks and auto-repair
- [ ] Web dashboard for managing all bindings

## Related Documentation

- [WhatsApp Channel Adapter](../src/ieee3394_agent/channels/whatsapp/README.md)
- [Service Principal Security](../docs/SECURITY.md)
- [P3394 Standard Compliance](../docs/P3394_COMPLIANCE.md)
