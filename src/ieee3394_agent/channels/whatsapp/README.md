# WhatsApp Channel Adapter for IEEE 3394 Agent

P3394-compliant WhatsApp integration with secure service principal binding.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│               IEEE 3394 Agent (Python)                      │
│                                                             │
│  ┌────────────────────────────────────────────────────┐   │
│  │         WhatsApp Channel Adapter                   │   │
│  │                                                     │   │
│  │  • Service Principal Authentication ✓              │   │
│  │  • P3394 UMF Message Normalization                 │   │
│  │  • Session Management                              │   │
│  │  • Security & Authorization                        │   │
│  └──────────────┬──────────────────────────────────────┘   │
│                 │ HTTP/WebSocket                            │
└─────────────────┼─────────────────────────────────────────┘
                  │
┌─────────────────▼─────────────────────────────────────────┐
│          WhatsApp Bridge (Node.js)                        │
│                                                            │
│  • whatsapp-web.js interface                             │
│  • QR code authentication                                 │
│  • Real-time message streaming                            │
│  • Media handling                                         │
└──────────────────┬─────────────────────────────────────────┘
                   │
┌──────────────────▼─────────────────────────────────────────┐
│              WhatsApp Web API                              │
└────────────────────────────────────────────────────────────┘
```

## Features

✅ **P3394 Compliant** - Full Universal Message Format (UMF) support
✅ **Secure Binding** - Service principal-based identity and authorization
✅ **Message Normalization** - Bidirectional conversion between WhatsApp and UMF
✅ **Media Support** - Images, videos, documents, voice notes
✅ **Group Chats** - Full support for WhatsApp groups
✅ **Real-time** - WebSocket-based instant message delivery
✅ **Session Management** - Persistent chat sessions with context
✅ **Audit Trail** - Complete message logging for compliance

## Security Model

### Service Principal Binding

Every WhatsApp adapter MUST authenticate with a **service principal** before it can send or receive messages. This implements P3394's security requirements:

1. **Identity Binding** - Each adapter instance has a unique identity (client_id)
2. **Authorization** - Fine-grained permissions control what the adapter can do
3. **Audit Trail** - All operations are logged with the principal's identity
4. **Credential Management** - Secure storage and rotation of secrets

### Required Permissions

- `channel.whatsapp.read` - Receive WhatsApp messages
- `channel.whatsapp.write` - Send WhatsApp messages
- `gateway.message.send` - Send messages to gateway
- `gateway.message.receive` - Receive messages from gateway

## Installation

### 1. Install Python Dependencies

The WhatsApp adapter is included in the IEEE 3394 agent. Install it with:

```bash
uv sync
```

### 2. Set Up WhatsApp Bridge

The adapter requires a Node.js bridge to interface with WhatsApp Web:

```bash
cd whatsapp_bridge
npm install
```

### 3. Create Service Principal

Generate a service principal with proper credentials:

```bash
python scripts/create_whatsapp_service_principal.py
```

This creates:
- Service principal credentials (client_id + client_secret)
- Configuration file at `~/.ieee3394/whatsapp_config.json`

**⚠️ IMPORTANT:** Save the client_secret securely. It won't be shown again!

## Quick Start

### 1. Start the WhatsApp Bridge

```bash
cd whatsapp_bridge
npm start
```

A QR code will be displayed. Scan it with WhatsApp to authenticate.

### 2. Use in Your Agent

```python
from pathlib import Path
from ieee3394_agent.channels.whatsapp import WhatsAppChannelAdapter
from ieee3394_agent.channels.whatsapp.config import WhatsAppChannelConfig
from ieee3394_agent.core.gateway_sdk import AgentGateway

# Load configuration (includes service principal)
config = WhatsAppChannelConfig.from_file(
    Path.home() / ".ieee3394" / "whatsapp_config.json"
)

# Create gateway
gateway = AgentGateway(...)

# Create WhatsApp adapter with security binding
whatsapp = WhatsAppChannelAdapter(
    gateway=gateway,
    config=config
)

# Start adapter (authenticates service principal)
await whatsapp.start()

# The adapter will now:
# 1. Authenticate service principal with gateway ✓
# 2. Connect to WhatsApp bridge ✓
# 3. Process messages in P3394 UMF format ✓
```

## Message Flow

### Receiving Messages (WhatsApp → Agent)

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   WhatsApp   │──1──▶│    Bridge    │──2──▶│   Normalize  │──3──▶│   Gateway    │
│     Web      │      │   (Node.js)  │      │  (to UMF)    │      │   (Route)    │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘

1. WhatsApp message received
2. Bridge sends via WebSocket
3. Normalized to P3394 UMF
4. Routed through gateway
```

### Sending Messages (Agent → WhatsApp)

```
┌──────────────┐      ┌──────────────┐      ┌──────────────┐      ┌──────────────┐
│   Gateway    │──1──▶│   Normalize  │──2──▶│    Bridge    │──3──▶│   WhatsApp   │
│   (Handle)   │      │(from UMF)    │      │   (Node.js)  │      │     Web      │
└──────────────┘      └──────────────┘      └──────────────┘      └──────────────┘

1. Agent generates response
2. Normalized to WhatsApp format
3. Bridge sends via WhatsApp Web API
4. Delivered to user
```

## Configuration

### Configuration File Format

```json
{
  "service_principal": {
    "client_id": "whatsapp-abc123...",
    "client_secret": "secret_key_here",
    "channel_type": "whatsapp",
    "permissions": [
      "channel.whatsapp.read",
      "channel.whatsapp.write",
      "gateway.message.send",
      "gateway.message.receive"
    ],
    "created_at": "2026-01-29T12:00:00Z",
    "expires_at": null
  },
  "bridge_url": "http://localhost:3000",
  "bridge_ws_url": "ws://localhost:3000/ws",
  "auth_dir": "/Users/user/.ieee3394/whatsapp_auth",
  "require_phone_verification": true,
  "enable_media_download": true,
  "enable_group_messages": true,
  "max_messages_per_minute": 20,
  "allowed_phone_numbers": [],
  "blocked_phone_numbers": [],
  "log_all_messages": true
}
```

### Environment Variables

You can override configuration with environment variables:

- `WHATSAPP_BRIDGE_URL` - Bridge HTTP URL
- `WHATSAPP_CLIENT_ID` - Service principal client ID
- `WHATSAPP_CLIENT_SECRET` - Service principal secret

## Message Examples

### Text Message (WhatsApp → UMF)

**WhatsApp Format:**
```json
{
  "from": "1234567890@c.us",
  "body": "Hello, agent!",
  "type": "chat",
  "timestamp": 1706543210
}
```

**P3394 UMF:**
```json
{
  "id": "ABC123",
  "type": "request",
  "source": {
    "agent_id": "whatsapp:1234567890",
    "channel_id": "whatsapp"
  },
  "content": [
    {
      "type": "text",
      "data": "Hello, agent!"
    }
  ],
  "metadata": {
    "platform": "whatsapp",
    "whatsapp_id": "ABC123"
  }
}
```

### Image Message (WhatsApp → UMF)

**WhatsApp Format:**
```json
{
  "from": "1234567890@c.us",
  "type": "image",
  "caption": "Check this out!",
  "hasMedia": true
}
```

**P3394 UMF:**
```json
{
  "content": [
    {
      "type": "text",
      "data": "[Image] Check this out!"
    },
    {
      "type": "file",
      "mime_type": "image/jpeg",
      "metadata": {
        "filename": "whatsapp_image_ABC123.jpg",
        "caption": "Check this out!"
      }
    }
  ]
}
```

## Advanced Usage

### Custom Permissions

Create a service principal with custom permissions:

```python
from ieee3394_agent.channels.whatsapp.config import ServicePrincipalManager

manager = ServicePrincipalManager(Path.home() / ".ieee3394" / "service_principals")

sp = manager.create_service_principal(
    channel_type="whatsapp",
    permissions=[
        "channel.whatsapp.read",
        "channel.whatsapp.write",
        "gateway.message.send",
        "gateway.message.receive",
        "admin.channel.manage",  # Additional permission
    ],
    expires_in_days=90  # Expires in 90 days
)
```

### Phone Number Filtering

Restrict which phone numbers can interact with the agent:

```python
config.allowed_phone_numbers = ["+1234567890", "+0987654321"]
config.blocked_phone_numbers = ["+1111111111"]
```

### Rate Limiting

Control message throughput:

```python
config.max_messages_per_minute = 10  # Limit to 10 messages/minute
config.max_media_size_mb = 5         # Limit media uploads to 5MB
```

## Troubleshooting

### Service Principal Authentication Fails

**Error:** `Service principal has expired` or `missing required permission`

**Solution:**
1. Check expiration: `python scripts/check_service_principal.py`
2. Renew if needed: `python scripts/create_whatsapp_service_principal.py`
3. Verify permissions in configuration file

### WhatsApp Bridge Not Connecting

**Error:** `Cannot connect to WhatsApp bridge at http://localhost:3000`

**Solution:**
1. Ensure bridge is running: `cd whatsapp_bridge && npm start`
2. Check port is not in use: `lsof -i :3000`
3. Verify `bridge_url` in configuration

### QR Code Not Working

**Solution:**
1. Stop the bridge
2. Delete authentication: `rm -rf whatsapp_bridge/whatsapp_auth`
3. Restart bridge and scan new QR code

### Messages Not Being Received

**Solution:**
1. Check service principal has `channel.whatsapp.read` permission
2. Verify WebSocket connection in logs
3. Test with `/status` to check adapter state

## API Reference

### WhatsAppChannelAdapter

Main adapter class.

```python
WhatsAppChannelAdapter(
    gateway: AgentGateway,
    config: WhatsAppChannelConfig,
    channel_id: str = "whatsapp"
)
```

**Methods:**
- `async start()` - Start adapter (authenticates service principal)
- `async stop()` - Stop adapter
- `async send(message: P3394Message)` - Send message
- `async receive() -> AsyncIterator[P3394Message]` - Receive messages
- `async get_qr_code() -> Optional[str]` - Get authentication QR code
- `async is_authenticated() -> bool` - Check authentication status

### WhatsAppChannelConfig

Configuration with service principal binding.

```python
WhatsAppChannelConfig(
    service_principal: ServicePrincipal,  # REQUIRED
    bridge_url: str = "http://localhost:3000",
    # ... other options
)
```

**Methods:**
- `validate() -> tuple[bool, list[str]]` - Validate configuration
- `from_file(path: Path) -> WhatsAppChannelConfig` - Load from JSON
- `to_file(path: Path)` - Save to JSON

### ServicePrincipal

Identity and authorization credentials.

```python
ServicePrincipal(
    client_id: str,
    client_secret: str,
    channel_type: str,
    permissions: list[str],
    expires_at: Optional[str] = None
)
```

**Methods:**
- `verify_secret(secret: str) -> bool` - Verify secret
- `has_permission(perm: str) -> bool` - Check permission
- `is_expired -> bool` - Check if expired

## Testing

Run WhatsApp adapter tests:

```bash
pytest tests/channels/test_whatsapp_adapter.py
```

## Resources

- [WhatsApp Web.js Documentation](https://wwebjs.dev/)
- [P3394 Standard](https://ieee3394.org)
- [IEEE 3394 Agent Documentation](../../README.md)

## License

MIT License - See main project LICENSE file
