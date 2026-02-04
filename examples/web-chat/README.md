# Web Chat Example

A standalone web chat interface for the P3394 agent.

## Files

- `web_chat.html` - Chat UI with WebSocket integration
- `serve_webchat.py` - Simple HTTP server

## Usage

1. Start the agent daemon:
   ```bash
   uv run python -m p3394_agent --daemon
   ```

2. Serve the web chat (in another terminal):
   ```bash
   cd examples/web-chat
   python serve_webchat.py
   ```

3. Open http://localhost:8080/web_chat.html

## Features

- Real-time chat via WebSocket
- Message history display
- Session management
- Responsive design
