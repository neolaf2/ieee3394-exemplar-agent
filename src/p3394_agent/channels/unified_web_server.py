"""
Unified Web Server

Consolidates all HTTP-based channel adapters onto a single port with different routes:
- /          - Web chat UI (landing, chat page, WebSocket)
- /api/      - Web chat REST API endpoints
- /v1/       - Anthropic API compatible endpoints
- /p3394/    - P3394 native protocol endpoints

This simplifies deployment by using a single port for all HTTP traffic.
"""

import asyncio
import logging
from typing import Optional, Set, Dict, Any
from pathlib import Path

from fastapi import FastAPI, APIRouter, WebSocket, WebSocketDisconnect, Request, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
import uvicorn

from ..core.gateway_sdk import AgentGateway
from ..core.umf import P3394Message, P3394Content, ContentType, MessageType, P3394Address

logger = logging.getLogger(__name__)


class UnifiedWebServer:
    """
    Unified web server that consolidates all HTTP channels on a single port.

    Route structure:
    - GET /                  - Landing page
    - GET /chat              - Chat interface
    - WS /ws/chat            - WebSocket for chat
    - GET /api/...           - Web chat REST API
    - POST /v1/messages      - Anthropic API compatible
    - GET /v1/models         - Anthropic API models list
    - GET /p3394/manifest    - P3394 agent manifest
    - POST /p3394/messages   - P3394 UMF messages
    - WS /p3394/ws           - P3394 WebSocket
    """

    def __init__(
        self,
        gateway: AgentGateway,
        host: str = "0.0.0.0",
        port: int = 8000,
        anthropic_api_keys: Optional[Set[str]] = None,
        static_dir: Optional[str] = None
    ):
        self.gateway = gateway
        self.host = host
        self.port = port
        self.anthropic_api_keys = anthropic_api_keys or set()
        self.is_active = False

        # Find static directory
        if static_dir:
            self.static_dir = Path(static_dir)
        else:
            # Default to project root's static folder
            self.static_dir = Path(__file__).parent.parent.parent.parent / "static"

        # Active WebSocket connections by channel
        self.chat_websockets: Dict[str, WebSocket] = {}
        self.p3394_websockets: Dict[str, WebSocket] = {}

        # P3394 agent address
        self.agent_address = P3394Address(
            agent_id=gateway.AGENT_ID,
            channel_id="p3394-server"
        )

        # Create main FastAPI app
        self.app = FastAPI(
            title=f"{gateway.AGENT_NAME}",
            description="P3394-compliant agent with unified web interface",
            version=gateway.AGENT_VERSION
        )

        # Add CORS middleware
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # Create and mount routers
        self._setup_routes()

    def _setup_routes(self):
        """Setup all routes on the unified server"""

        # =====================================================================
        # ROOT ROUTES - Web Chat UI
        # =====================================================================

        @self.app.get("/", response_class=HTMLResponse)
        async def landing_page():
            """Landing page"""
            return self._render_landing_page()

        @self.app.get("/chat", response_class=HTMLResponse)
        async def chat_page():
            """Chat interface"""
            return self._render_chat_page()

        @self.app.get("/about", response_class=HTMLResponse)
        async def about_page():
            """About page"""
            return self._render_about_page()

        # =====================================================================
        # WEB CHAT WEBSOCKET
        # =====================================================================

        @self.app.websocket("/ws/chat")
        async def websocket_chat(websocket: WebSocket):
            """WebSocket endpoint for real-time chat"""
            await websocket.accept()

            # Create session
            session = await self.gateway.session_manager.create_session(channel_id="web-ws")
            self.chat_websockets[session.id] = websocket

            try:
                # Send welcome message
                welcome = P3394Message.text(
                    f"Connected to {self.gateway.AGENT_NAME}. Session: {session.id}\nType /help for commands.",
                    session_id=session.id
                )
                await websocket.send_json(welcome.to_dict())

                # Message loop
                while True:
                    data = await websocket.receive_json()

                    # Transform to P3394 message
                    if isinstance(data, str):
                        message = P3394Message.text(data, session_id=session.id)
                    else:
                        message = P3394Message.from_dict(data)
                        message.session_id = session.id

                    # Handle message
                    response = await self.gateway.handle(message)

                    # Send response
                    await websocket.send_json(response.to_dict())

            except WebSocketDisconnect:
                logger.info(f"Chat WebSocket disconnected: {session.id}")
            except Exception as e:
                logger.exception(f"Chat WebSocket error: {e}")
            finally:
                if session.id in self.chat_websockets:
                    del self.chat_websockets[session.id]
                await self.gateway.session_manager.end_session(session.id)

        # =====================================================================
        # WEB CHAT API (/api/...)
        # =====================================================================

        api_router = APIRouter(prefix="/api", tags=["Web Chat API"])

        @api_router.get("/help")
        async def api_help():
            """Get help information"""
            message = P3394Message.text("/help")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)

        @api_router.get("/about")
        async def api_about():
            """Get about information"""
            message = P3394Message.text("/about")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)

        @api_router.get("/status")
        async def api_status():
            """Get agent status"""
            message = P3394Message.text("/status")
            response = await self.gateway.handle(message)
            return self._format_api_response(response)

        @api_router.get("/version")
        async def api_version():
            """Get version"""
            return {
                "agent_id": self.gateway.AGENT_ID,
                "name": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "standard": "IEEE P3394"
            }

        @api_router.post("/message")
        async def api_send_message(request: Request):
            """Send a text message"""
            body = await request.json()
            text = body.get("text", body.get("message", ""))
            session_id = body.get("session_id")

            message = P3394Message.text(text, session_id=session_id)
            response = await self.gateway.handle(message)
            return self._format_api_response(response)

        @api_router.post("/umf")
        async def api_send_umf(request: Request):
            """Send a raw P3394 UMF message"""
            umf = await request.json()
            message = P3394Message.from_dict(umf)
            response = await self.gateway.handle(message)
            return response.to_dict()

        self.app.include_router(api_router)

        # =====================================================================
        # ANTHROPIC API (/v1/...)
        # =====================================================================

        anthropic_router = APIRouter(prefix="/v1", tags=["Anthropic API"])

        @anthropic_router.post("/messages")
        async def anthropic_create_message(
            request: Request,
            x_api_key: Optional[str] = Header(None, alias="x-api-key")
        ):
            """Create a message (Anthropic API /v1/messages endpoint)"""
            # Validate API key if configured
            if self.anthropic_api_keys and x_api_key not in self.anthropic_api_keys:
                raise HTTPException(status_code=401, detail="Invalid API key")

            body = await request.json()
            stream = body.get("stream", False)

            if stream:
                return StreamingResponse(
                    self._anthropic_streaming_response(body),
                    media_type="text/event-stream"
                )
            else:
                return await self._anthropic_non_streaming_response(body)

        @anthropic_router.get("/models")
        async def anthropic_list_models(
            x_api_key: Optional[str] = Header(None, alias="x-api-key")
        ):
            """List available models"""
            if self.anthropic_api_keys and x_api_key not in self.anthropic_api_keys:
                raise HTTPException(status_code=401, detail="Invalid API key")

            from datetime import datetime
            return {
                "object": "list",
                "data": [
                    {
                        "id": "ieee-3394-agent",
                        "object": "model",
                        "created": int(datetime.now().timestamp()),
                        "owned_by": "ieee-3394"
                    }
                ]
            }

        self.app.include_router(anthropic_router)

        # =====================================================================
        # P3394 NATIVE PROTOCOL (/p3394/...)
        # =====================================================================

        p3394_router = APIRouter(prefix="/p3394", tags=["P3394 Protocol"])

        @p3394_router.get("/manifest")
        async def p3394_manifest():
            """Agent manifest endpoint (P3394 discovery)"""
            from datetime import datetime
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
                "endpoints": {
                    "manifest": f"http://{self.host}:{self.port}/p3394/manifest",
                    "messages": f"http://{self.host}:{self.port}/p3394/messages",
                    "websocket": f"ws://{self.host}:{self.port}/p3394/ws",
                    "health": f"http://{self.host}:{self.port}/p3394/health"
                },
                "timestamp": datetime.utcnow().isoformat() + "Z"
            }

        @p3394_router.get("/channels")
        async def p3394_list_channels():
            """List available communication channels"""
            return {
                "channels": [
                    {
                        "id": channel_id,
                        "type": adapter.__class__.__name__,
                        "active": adapter.is_active
                    }
                    for channel_id, adapter in self.gateway.channels.items()
                ]
            }

        @p3394_router.post("/messages")
        async def p3394_send_message(
            request: Request,
            x_p3394_client: Optional[str] = Header(None, alias="x-p3394-client")
        ):
            """Send a P3394 UMF message"""
            umf_message = await request.json()
            message = P3394Message.from_dict(umf_message)

            # Set destination to this agent
            if not message.destination:
                message.destination = self.agent_address

            # Set source from header if provided
            if x_p3394_client and not message.source:
                message.source = P3394Address.from_uri(x_p3394_client)

            response = await self.gateway.handle(message)
            return response.to_dict()

        @p3394_router.get("/health")
        async def p3394_health():
            """P3394 health check"""
            return {
                "status": "healthy",
                "protocol": "P3394",
                "agent": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "address": self.agent_address.to_uri()
            }

        @p3394_router.websocket("/ws")
        async def p3394_websocket(websocket: WebSocket):
            """P3394 WebSocket for UMF messages"""
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

                    session = await self.gateway.session_manager.create_session(channel_id="p3394-ws")
                    session_id = session.id
                    self.p3394_websockets[session_id] = websocket

                    await websocket.send_json({
                        "action": "identified",
                        "session_id": session_id,
                        "server_address": self.agent_address.to_uri(),
                        "agent": self.gateway.AGENT_NAME,
                        "version": self.gateway.AGENT_VERSION
                    })
                else:
                    await websocket.send_json({"error": "First message must be identification"})
                    await websocket.close()
                    return

                # Message loop
                while True:
                    data = await websocket.receive_json()
                    message = P3394Message.from_dict(data)
                    message.session_id = session_id

                    if not message.source and client_address:
                        message.source = client_address
                    if not message.destination:
                        message.destination = self.agent_address

                    response = await self.gateway.handle(message)
                    await websocket.send_json(response.to_dict())

            except WebSocketDisconnect:
                logger.info(f"P3394 WebSocket disconnected: {session_id}")
            except Exception as e:
                logger.exception(f"P3394 WebSocket error: {e}")
            finally:
                if session_id:
                    if session_id in self.p3394_websockets:
                        del self.p3394_websockets[session_id]
                    await self.gateway.session_manager.end_session(session_id)

        self.app.include_router(p3394_router)

        # =====================================================================
        # HEALTH & STATUS (root level)
        # =====================================================================

        @self.app.get("/health")
        async def health_check():
            """Overall health check"""
            return {
                "status": "healthy",
                "agent": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION,
                "endpoints": {
                    "web_chat": "/",
                    "api": "/api",
                    "anthropic": "/v1",
                    "p3394": "/p3394"
                }
            }

        # Mount static files if directory exists
        if self.static_dir.exists():
            self.app.mount("/static", StaticFiles(directory=str(self.static_dir)), name="static")

    # =========================================================================
    # ANTHROPIC API HELPERS
    # =========================================================================

    async def _anthropic_non_streaming_response(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming Anthropic API request"""
        import json
        import uuid

        umf_message = self._anthropic_to_umf(body)
        umf_response = await self.gateway.handle(umf_message)

        # Extract text
        text_parts = []
        for content in umf_response.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                text_parts.append(content.data)
        response_text = "\n\n".join(text_parts) if text_parts else ""

        return {
            "id": f"msg_{umf_response.id.replace('-', '')[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": response_text}],
            "model": body.get("model", "ieee-3394-agent"),
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": len(json.dumps(body).split()),
                "output_tokens": len(response_text.split())
            }
        }

    async def _anthropic_streaming_response(self, body: Dict[str, Any]):
        """Handle streaming Anthropic API request"""
        import json
        import uuid

        umf_message = self._anthropic_to_umf(body)
        umf_response = await self.gateway.handle(umf_message)

        message_id = f"msg_{uuid.uuid4().hex[:24]}"

        # Stream start
        yield f"event: message_start\n"
        yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant'}})}\n\n"

        # Content block start
        yield f"event: content_block_start\n"
        yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

        # Extract text
        text = ""
        for content in umf_response.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                text += content.data

        # Stream in chunks
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            yield f"event: content_block_delta\n"
            yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': chunk}})}\n\n"
            await asyncio.sleep(0.01)

        # Content block end
        yield f"event: content_block_stop\n"
        yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

        # Message end
        yield f"event: message_delta\n"
        yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': len(text.split())}})}\n\n"

        yield f"event: message_stop\n"
        yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

    def _anthropic_to_umf(self, body: Dict[str, Any]) -> P3394Message:
        """Transform Anthropic API request to P3394 UMF"""
        messages = body.get("messages", [])
        system = body.get("system", "")

        # Build conversation
        conversation_parts = []
        if system:
            conversation_parts.append(f"System: {system}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                content = " ".join(text_parts)
            conversation_parts.append(f"{role.capitalize()}: {content}")

        # Get last user message
        last_user_message = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                content = msg.get("content", "")
                if isinstance(content, list):
                    text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                    last_user_message = " ".join(text_parts)
                else:
                    last_user_message = content
                break

        return P3394Message(
            type=MessageType.REQUEST,
            content=[P3394Content(
                type=ContentType.TEXT,
                data=last_user_message,
                metadata={
                    "conversation_history": "\n".join(conversation_parts),
                    "anthropic_format": True
                }
            )],
            metadata={
                "model": body.get("model"),
                "max_tokens": body.get("max_tokens"),
                "temperature": body.get("temperature"),
                "source_api": "anthropic"
            }
        )

    # =========================================================================
    # API RESPONSE HELPERS
    # =========================================================================

    def _format_api_response(self, message: P3394Message) -> dict:
        """Format P3394 message as API response"""
        content = None
        for c in message.content:
            if c.type == ContentType.TEXT:
                content = c.data
                break
            elif c.type == ContentType.JSON:
                content = c.data
                break

        return {
            "message_id": message.id,
            "type": message.type.value,
            "content": content,
            "session_id": message.session_id,
            "timestamp": message.timestamp
        }

    # =========================================================================
    # HTML RENDERING (using textContent for user-visible content)
    # =========================================================================

    def _render_landing_page(self) -> str:
        """Render the landing page HTML"""
        # Escape any user-controlled values for safe HTML output
        agent_name = self._escape_html(self.gateway.AGENT_NAME)
        agent_version = self._escape_html(self.gateway.AGENT_VERSION)
        agent_uri = self._escape_html(self.agent_address.to_uri())

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{agent_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <a href="/" class="text-xl font-bold text-blue-600">{agent_name}</a>
            <div class="space-x-4">
                <a href="/about" class="text-gray-600 hover:text-blue-600">About</a>
                <a href="/chat" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Chat</a>
            </div>
        </div>
    </nav>

    <main class="max-w-7xl mx-auto px-4 py-16">
        <div class="text-center mb-16">
            <h1 class="text-5xl font-bold text-gray-900 mb-4">IEEE P3394</h1>
            <p class="text-xl text-gray-600 mb-8">The Standard for Agent Interoperability</p>
            <div class="space-x-4">
                <a href="/chat" class="bg-blue-600 text-white px-8 py-3 rounded-lg text-lg hover:bg-blue-700">Try the Agent</a>
                <a href="/p3394/manifest" class="border border-gray-300 px-8 py-3 rounded-lg text-lg hover:border-blue-600">View Manifest</a>
            </div>
        </div>

        <div class="grid md:grid-cols-3 gap-8 mb-16">
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold mb-2">Web Chat</h3>
                <p class="text-gray-600 mb-4">Interactive chat interface at <code class="bg-gray-100 px-2 py-1 rounded">/chat</code></p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold mb-2">Anthropic API</h3>
                <p class="text-gray-600 mb-4">Compatible API at <code class="bg-gray-100 px-2 py-1 rounded">/v1/messages</code></p>
            </div>
            <div class="bg-white p-6 rounded-lg shadow">
                <h3 class="text-xl font-semibold mb-2">P3394 Protocol</h3>
                <p class="text-gray-600 mb-4">Native protocol at <code class="bg-gray-100 px-2 py-1 rounded">/p3394/</code></p>
            </div>
        </div>

        <div class="bg-blue-50 rounded-lg p-8 text-center">
            <h2 class="text-2xl font-bold mb-4">All Channels, One Port</h2>
            <p class="text-gray-700 mb-4">This agent serves all protocols on port {self.port}</p>
            <code class="bg-gray-800 text-green-400 px-4 py-2 rounded inline-block">
                {agent_uri}
            </code>
        </div>
    </main>

    <footer class="bg-gray-800 text-white py-8 mt-16">
        <div class="max-w-7xl mx-auto px-4 text-center">
            <p>IEEE P3394 Standard for Agent Interfaces</p>
            <p class="text-gray-400 text-sm mt-2">{agent_name} v{agent_version}</p>
        </div>
    </footer>
</body>
</html>
"""

    def _render_chat_page(self) -> str:
        """Render the chat interface HTML"""
        agent_name = self._escape_html(self.gateway.AGENT_NAME)

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Chat - {agent_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/dompurify@3.0.6/dist/purify.min.js"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <a href="/" class="text-xl font-bold text-blue-600">{agent_name}</a>
            <div class="space-x-4">
                <a href="/about" class="text-gray-600 hover:text-blue-600">About</a>
                <a href="/chat" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Chat</a>
            </div>
        </div>
    </nav>

    <div class="flex h-[calc(100vh-64px)]">
        <div class="w-64 bg-white border-r p-4 hidden md:block">
            <h3 class="font-semibold mb-4">Commands</h3>
            <ul class="space-y-2 text-sm">
                <li><code class="text-blue-600">/help</code> - Get help</li>
                <li><code class="text-blue-600">/about</code> - About agent</li>
                <li><code class="text-blue-600">/status</code> - Agent status</li>
                <li><code class="text-blue-600">/listSkills</code> - List skills</li>
            </ul>
        </div>

        <div class="flex-1 flex flex-col">
            <div class="flex-1 overflow-y-auto p-4 space-y-4" id="messages"></div>

            <div class="border-t p-4">
                <form id="chat-form" class="flex space-x-2">
                    <input type="text" id="message-input"
                        class="flex-1 border rounded-lg px-4 py-2 focus:outline-none focus:border-blue-600"
                        placeholder="Type a message or /command..." autocomplete="off">
                    <button type="submit" class="bg-blue-600 text-white px-6 py-2 rounded-lg hover:bg-blue-700">Send</button>
                </form>
            </div>
        </div>
    </div>

    <script>
        const messagesContainer = document.getElementById('messages');
        const chatForm = document.getElementById('chat-form');
        const messageInput = document.getElementById('message-input');

        let ws = null;
        let sessionId = null;

        function connect() {{
            const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(protocol + '//' + window.location.host + '/ws/chat');

            ws.onopen = function() {{ console.log('Connected'); }};

            ws.onmessage = function(event) {{
                const message = JSON.parse(event.data);
                displayMessage(message, 'agent');
                if (message.session_id) sessionId = message.session_id;
            }};

            ws.onclose = function() {{
                console.log('Disconnected');
                setTimeout(connect, 3000);
            }};
        }}

        function displayMessage(message, sender) {{
            const div = document.createElement('div');
            div.className = sender === 'user' ? 'flex justify-end' : 'flex justify-start';

            const content = message.content && message.content[0] ? message.content[0].data : message;
            const bubble = document.createElement('div');
            bubble.className = sender === 'user'
                ? 'bg-blue-600 text-white rounded-lg px-4 py-2 max-w-2xl'
                : 'bg-gray-100 rounded-lg px-4 py-2 max-w-2xl prose';

            if (sender === 'agent' && typeof content === 'string') {{
                // Use DOMPurify to sanitize the HTML from marked
                const rawHtml = marked.parse(content);
                const cleanHtml = DOMPurify.sanitize(rawHtml);
                bubble.innerHTML = cleanHtml;
            }} else {{
                // For user messages and non-string content, use textContent
                bubble.textContent = typeof content === 'string' ? content : JSON.stringify(content);
            }}

            div.appendChild(bubble);
            messagesContainer.appendChild(div);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }}

        chatForm.addEventListener('submit', function(e) {{
            e.preventDefault();
            const text = messageInput.value.trim();
            if (!text) return;

            displayMessage(text, 'user');

            if (ws && ws.readyState === WebSocket.OPEN) {{
                ws.send(JSON.stringify({{
                    type: 'request',
                    content: [{{ type: 'text', data: text }}],
                    session_id: sessionId
                }}));
            }}

            messageInput.value = '';
        }});

        connect();
    </script>
</body>
</html>
"""

    def _render_about_page(self) -> str:
        """Render the about page HTML"""
        agent_name = self._escape_html(self.gateway.AGENT_NAME)
        agent_version = self._escape_html(self.gateway.AGENT_VERSION)
        agent_id = self._escape_html(self.gateway.AGENT_ID)
        agent_uri = self._escape_html(self.agent_address.to_uri())

        return f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>About - {agent_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
</head>
<body class="bg-gray-50 min-h-screen">
    <nav class="bg-white shadow-sm border-b">
        <div class="max-w-7xl mx-auto px-4 py-3 flex justify-between items-center">
            <a href="/" class="text-xl font-bold text-blue-600">{agent_name}</a>
            <div class="space-x-4">
                <a href="/about" class="text-gray-600 hover:text-blue-600">About</a>
                <a href="/chat" class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700">Chat</a>
            </div>
        </div>
    </nav>

    <main class="max-w-4xl mx-auto px-4 py-16 prose">
        <h1>About {agent_name}</h1>

        <p><strong>Version:</strong> {agent_version}<br>
        <strong>Agent ID:</strong> {agent_id}<br>
        <strong>Standard:</strong> IEEE P3394 (Agent Interface Standard)</p>

        <h2>What is P3394?</h2>
        <p>IEEE P3394 defines a universal standard for agent communication, enabling:</p>
        <ul>
            <li><strong>Interoperability</strong>: Agents from different vendors can communicate</li>
            <li><strong>Universal Message Format (UMF)</strong>: Standard message structure</li>
            <li><strong>Channel Abstraction</strong>: Same agent, multiple interfaces</li>
            <li><strong>Capability Discovery</strong>: Agents can discover each other's abilities</li>
        </ul>

        <h2>Unified Endpoint</h2>
        <p>This agent serves all protocols on a single port:</p>
        <table>
            <tr><th>Path</th><th>Protocol</th><th>Description</th></tr>
            <tr><td><code>/chat</code></td><td>Web UI</td><td>Interactive chat interface</td></tr>
            <tr><td><code>/api/</code></td><td>REST</td><td>Web chat API</td></tr>
            <tr><td><code>/v1/messages</code></td><td>Anthropic</td><td>Compatible with Claude API clients</td></tr>
            <tr><td><code>/p3394/</code></td><td>P3394</td><td>Native agent protocol</td></tr>
        </table>

        <h2>P3394 Address</h2>
        <code class="bg-gray-800 text-green-400 px-4 py-2 rounded block my-4">{agent_uri}</code>
    </main>
</body>
</html>
"""

    def _escape_html(self, text: str) -> str:
        """Escape HTML special characters to prevent XSS"""
        if not isinstance(text, str):
            text = str(text)
        return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#x27;"))

    # =========================================================================
    # SERVER LIFECYCLE
    # =========================================================================

    async def start(self):
        """Start the unified web server"""
        self.is_active = True

        # Register as a channel
        self.gateway.register_channel("unified-web", self)

        logger.info(f"Unified Web Server started on http://{self.host}:{self.port}")
        logger.info(f"  Web Chat: http://{self.host}:{self.port}/chat")
        logger.info(f"  Anthropic API: http://{self.host}:{self.port}/v1/messages")
        logger.info(f"  P3394 Protocol: http://{self.host}:{self.port}/p3394/")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def stop(self):
        """Stop the unified web server"""
        self.is_active = False

        # Close all websockets
        for ws in list(self.chat_websockets.values()):
            await ws.close()
        for ws in list(self.p3394_websockets.values()):
            await ws.close()

        self.chat_websockets.clear()
        self.p3394_websockets.clear()

        logger.info("Unified Web Server stopped")
