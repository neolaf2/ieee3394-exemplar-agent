# WhatsApp Bridge for IEEE 3394 Agent

This Node.js bridge provides a connection between the IEEE 3394 Agent (Python) and WhatsApp Web using [whatsapp-web.js](https://github.com/pedroslopez/whatsapp-web.js).

## Architecture

```
┌─────────────────────┐
│  IEEE 3394 Agent    │
│    (Python)         │
└──────────┬──────────┘
           │ HTTP/WebSocket
           │
┌──────────▼──────────┐
│  WhatsApp Bridge    │
│    (Node.js)        │
└──────────┬──────────┘
           │ whatsapp-web.js
           │
┌──────────▼──────────┐
│   WhatsApp Web      │
│   (Browser/API)     │
└─────────────────────┘
```

## Installation

1. Install Node.js 18+ if not already installed

2. Install dependencies:
```bash
cd whatsapp_bridge
npm install
```

## Usage

### Start the Bridge

```bash
npm start
```

Or with auto-reload for development:
```bash
npm run dev
```

### First-Time Authentication

1. Start the bridge server
2. A QR code will be displayed in the terminal
3. Open WhatsApp on your phone
4. Go to **Settings** → **Linked Devices** → **Link a Device**
5. Scan the QR code shown in the terminal

The authentication session will be saved in `./whatsapp_auth` directory, so you won't need to scan again on subsequent runs.

## API Endpoints

### HTTP API

**Base URL:** `http://localhost:3000`

#### Status
```http
GET /status
```

Returns bridge status:
```json
{
  "status": "running",
  "ready": true,
  "authenticated": true,
  "hasQR": false
}
```

#### Authentication Status
```http
GET /auth/status
```

#### Send Message
```http
POST /send
Content-Type: application/json

{
  "chatId": "1234567890@c.us",
  "content": "Hello from IEEE 3394 Agent!",
  "quotedMessageId": "optional_message_id_to_reply_to"
}
```

#### Send Media
```http
POST /send
Content-Type: application/json

{
  "chatId": "1234567890@c.us",
  "media": {
    "url": "http://example.com/image.jpg",
    "mime_type": "image/jpeg",
    "filename": "image.jpg",
    "caption": "Check out this image!"
  }
}
```

#### Get Chats
```http
GET /chats
```

Returns list of all chats:
```json
[
  {
    "id": "1234567890@c.us",
    "name": "John Doe",
    "isGroup": false,
    "unreadCount": 2,
    "timestamp": 1706543210
  }
]
```

#### Logout
```http
POST /logout
```

### WebSocket API

**URL:** `ws://localhost:3000/ws`

The WebSocket connection provides real-time updates:

#### Incoming Events

**QR Code (for authentication)**
```json
{
  "type": "qr",
  "qr": "qr_code_string_here"
}
```

**Client Ready**
```json
{
  "type": "ready",
  "timestamp": "2026-01-29T12:00:00.000Z"
}
```

**Incoming Message**
```json
{
  "type": "message",
  "message": {
    "id": { ... },
    "body": "Hello!",
    "from": "1234567890@c.us",
    "to": "0987654321@c.us",
    "timestamp": 1706543210,
    "type": "chat",
    "isGroup": false,
    "hasMedia": false
  }
}
```

**Message Acknowledgment**
```json
{
  "type": "ack",
  "messageId": "message_id_here",
  "ack": 1
}
```

Acknowledgment levels:
- `0`: Error
- `1`: Pending
- `2`: Server received
- `3`: Delivered
- `4`: Read

**Disconnected**
```json
{
  "type": "disconnected",
  "reason": "logout"
}
```

## Chat ID Format

WhatsApp uses these ID formats:

- **Individual chats**: `phone_number@c.us` (e.g., `1234567890@c.us`)
- **Group chats**: `group_id@g.us` (e.g., `123456789@g.us`)

Phone numbers should include country code without `+` or `-`.

## Configuration

Environment variables:

- `PORT` - HTTP server port (default: 3000)

## Troubleshooting

### QR Code Not Showing

Make sure your terminal supports UTF-8 and can display QR codes. Alternatively, the QR code is also sent via WebSocket to connected clients.

### Authentication Fails

1. Delete the `./whatsapp_auth` directory
2. Restart the bridge
3. Scan the new QR code

### Connection Issues

- Make sure WhatsApp Web is not blocked by firewall
- Check that port 3000 is available
- Verify Node.js version is 18 or higher

### Client Not Ready

The bridge needs a few seconds to initialize after authentication. Wait for the "WhatsApp client is ready!" message before sending messages.

## Integration with IEEE 3394 Agent

The Python adapter (`src/ieee3394_agent/channels/whatsapp/adapter.py`) communicates with this bridge:

1. **HTTP** for sending messages and queries
2. **WebSocket** for receiving real-time messages

To start the WhatsApp channel in your agent:

```python
from ieee3394_agent.channels.whatsapp import WhatsAppChannelAdapter
from ieee3394_agent.core.gateway_sdk import AgentGateway

# Initialize gateway
gateway = AgentGateway(...)

# Create WhatsApp adapter
whatsapp = WhatsAppChannelAdapter(
    gateway=gateway,
    bridge_url="http://localhost:3000",
    bridge_ws_url="ws://localhost:3000/ws"
)

# Start adapter
await whatsapp.start()
```

## Development

### Project Structure

```
whatsapp_bridge/
├── server.js         # Main bridge server
├── package.json      # Dependencies
├── README.md         # This file
└── whatsapp_auth/    # Authentication data (auto-created)
```

### Dependencies

- **whatsapp-web.js** - WhatsApp Web interface
- **express** - HTTP server
- **ws** - WebSocket server
- **qrcode-terminal** - Terminal QR code display

## Security Notes

- The `whatsapp_auth` directory contains your WhatsApp session data. Keep it secure!
- Consider running the bridge behind a firewall or VPN for production use
- Use HTTPS and WSS in production environments
- Implement authentication/authorization for the HTTP/WebSocket APIs

## License

MIT License - See main project LICENSE file
