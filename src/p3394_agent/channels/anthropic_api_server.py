"""
Anthropic API Server Channel Adapter

Receives Anthropic API calls and translates them to P3394 UMF messages.
Makes the agent appear as an Anthropic API endpoint.
"""

import asyncio
import json
import logging
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
import uvicorn

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType
from ..core.gateway_sdk import AgentGateway

logger = logging.getLogger(__name__)


class AnthropicAPIServerAdapter:
    """
    Anthropic API Server Channel Adapter

    Transforms Anthropic API requests to P3394 UMF and back.

    Client sends Anthropic API request:
        POST /v1/messages
        {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024
        }

    Adapter transforms to UMF:
        P3394Message(type=REQUEST, content=[...])

    Gateway returns UMF:
        P3394Message(type=RESPONSE, content=[...])

    Adapter transforms back to Anthropic API format:
        {
            "id": "msg_...",
            "type": "message",
            "role": "assistant",
            "content": [{"type": "text", "text": "Response"}],
            ...
        }
    """

    def __init__(
        self,
        gateway: AgentGateway,
        host: str = "0.0.0.0",
        port: int = 8100,
        api_keys: Optional[set] = None
    ):
        self.gateway = gateway
        self.channel_id = "anthropic-api-server"
        self.host = host
        self.port = port

        # Agent-issued API keys (empty set = no auth for testing)
        self.api_keys = api_keys or set()

        self.is_active = False
        self.app = FastAPI(
            title="IEEE 3394 Agent - Anthropic API Compatible",
            description="P3394-compliant agent with Anthropic API interface",
            version=gateway.AGENT_VERSION
        )

        # Add CORS middleware to allow cross-origin requests (for GUI clients like Cherry Studio)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins
            allow_credentials=True,
            allow_methods=["*"],  # Allow all methods
            allow_headers=["*"],  # Allow all headers
        )

        self._setup_routes()

    def _setup_routes(self):
        """Setup Anthropic API-compatible routes"""

        @self.app.post("/v1/messages")
        async def create_message(
            request: Request,
            x_api_key: Optional[str] = Header(None, alias="x-api-key")
        ):
            """
            Create a message (Anthropic API /v1/messages endpoint)

            This is the main endpoint that Anthropic SDK clients use.
            """
            # Validate API key if keys are configured
            if self.api_keys and x_api_key not in self.api_keys:
                raise HTTPException(
                    status_code=401,
                    detail="Invalid API key"
                )

            # Parse request body
            try:
                body = await request.json()
            except Exception as e:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid JSON: {str(e)}"
                )

            logger.info(f"Anthropic API request: {body.get('model', 'unknown')} - {len(body.get('messages', []))} messages")

            # Check for streaming
            stream = body.get("stream", False)

            if stream:
                # Streaming response
                return StreamingResponse(
                    self._handle_streaming_request(body),
                    media_type="text/event-stream"
                )
            else:
                # Non-streaming response
                return await self._handle_request(body)

        @self.app.get("/v1/models")
        async def list_models(
            x_api_key: Optional[str] = Header(None, alias="x-api-key")
        ):
            """List available models"""
            if self.api_keys and x_api_key not in self.api_keys:
                raise HTTPException(status_code=401, detail="Invalid API key")

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

        @self.app.get("/health")
        async def health_check():
            """Health check endpoint"""
            return {
                "status": "healthy",
                "agent": self.gateway.AGENT_NAME,
                "version": self.gateway.AGENT_VERSION
            }

        @self.app.get("/chatUI")
        async def serve_chat_ui():
            """Serve web chat interface"""
            from pathlib import Path
            from fastapi.responses import HTMLResponse

            # Find web_chat.html in project root
            project_root = Path(__file__).parent.parent.parent.parent
            chat_html_path = project_root / "web_chat.html"

            if not chat_html_path.exists():
                raise HTTPException(status_code=404, detail="Web chat interface not found")

            with open(chat_html_path, 'r', encoding='utf-8') as f:
                html_content = f.read()

            return HTMLResponse(content=html_content)

    async def _handle_request(self, body: Dict[str, Any]) -> Dict[str, Any]:
        """Handle non-streaming Anthropic API request"""

        # Transform Anthropic API request to UMF
        umf_message = self._anthropic_to_umf(body)

        # Send to gateway
        umf_response = await self.gateway.handle(umf_message)

        # Transform UMF response back to Anthropic API format
        anthropic_response = self._umf_to_anthropic(umf_response, body)

        return anthropic_response

    async def _handle_streaming_request(self, body: Dict[str, Any]):
        """Handle streaming Anthropic API request"""

        # Transform Anthropic API request to UMF
        umf_message = self._anthropic_to_umf(body)

        # Send to gateway (non-streaming for now)
        umf_response = await self.gateway.handle(umf_message)

        # Transform to Anthropic streaming format
        message_id = f"msg_{uuid.uuid4().hex[:24]}"

        # Stream start event
        yield f"event: message_start\n"
        yield f"data: {json.dumps({'type': 'message_start', 'message': {'id': message_id, 'type': 'message', 'role': 'assistant'}})}\n\n"

        # Content block start
        yield f"event: content_block_start\n"
        yield f"data: {json.dumps({'type': 'content_block_start', 'index': 0, 'content_block': {'type': 'text', 'text': ''}})}\n\n"

        # Extract text from UMF response
        text = ""
        for content in umf_response.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                text += content.data

        # Stream text in chunks
        chunk_size = 20
        for i in range(0, len(text), chunk_size):
            chunk = text[i:i+chunk_size]
            yield f"event: content_block_delta\n"
            yield f"data: {json.dumps({'type': 'content_block_delta', 'index': 0, 'delta': {'type': 'text_delta', 'text': chunk}})}\n\n"
            await asyncio.sleep(0.01)  # Small delay for realistic streaming

        # Content block end
        yield f"event: content_block_stop\n"
        yield f"data: {json.dumps({'type': 'content_block_stop', 'index': 0})}\n\n"

        # Message end
        yield f"event: message_delta\n"
        yield f"data: {json.dumps({'type': 'message_delta', 'delta': {'stop_reason': 'end_turn'}, 'usage': {'output_tokens': len(text.split())}})}\n\n"

        yield f"event: message_stop\n"
        yield f"data: {json.dumps({'type': 'message_stop'})}\n\n"

    def _anthropic_to_umf(self, body: Dict[str, Any]) -> P3394Message:
        """
        Transform Anthropic API request to P3394 UMF.

        Anthropic format:
            {
                "model": "claude-3-5-sonnet-20241022",
                "messages": [
                    {"role": "user", "content": "Hello"},
                    {"role": "assistant", "content": "Hi there!"},
                    {"role": "user", "content": "How are you?"}
                ],
                "max_tokens": 1024,
                "system": "You are a helpful assistant",
                "temperature": 1.0
            }

        UMF format:
            P3394Message(
                type=REQUEST,
                content=[P3394Content(type=TEXT, data="conversation history")],
                metadata={"model": "...", "max_tokens": ...}
            )
        """
        messages = body.get("messages", [])
        system = body.get("system", "")

        # Combine system prompt and messages into conversation text
        conversation_parts = []

        if system:
            conversation_parts.append(f"System: {system}")

        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")

            # Handle both string and array content
            if isinstance(content, list):
                text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
                content = " ".join(text_parts)

            conversation_parts.append(f"{role.capitalize()}: {content}")

        # Get the last user message as the primary content
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

    def _umf_to_anthropic(
        self,
        umf_message: P3394Message,
        original_request: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Transform P3394 UMF response to Anthropic API format.

        UMF format:
            P3394Message(type=RESPONSE, content=[...])

        Anthropic format:
            {
                "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Response text"}],
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }
        """
        # Extract text from UMF content
        text_parts = []
        for content in umf_message.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                text_parts.append(content.data)

        response_text = "\n\n".join(text_parts) if text_parts else ""

        # Estimate token counts (rough approximation)
        input_tokens = len(json.dumps(original_request).split())
        output_tokens = len(response_text.split())

        return {
            "id": f"msg_{umf_message.id.replace('-', '')[:24]}",
            "type": "message",
            "role": "assistant",
            "content": [
                {
                    "type": "text",
                    "text": response_text
                }
            ],
            "model": original_request.get("model", "ieee-3394-agent"),
            "stop_reason": "end_turn",
            "stop_sequence": None,
            "usage": {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens
            }
        }

    async def start(self):
        """Start the Anthropic API server"""
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)

        logger.info(f"Anthropic API Server Adapter started on http://{self.host}:{self.port}")

        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)
        await server.serve()

    async def stop(self):
        """Stop the Anthropic API server"""
        self.is_active = False
        logger.info("Anthropic API Server Adapter stopped")
