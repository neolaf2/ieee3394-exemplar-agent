"""
MCP Channel Adapter

Provides bidirectional MCP (Model Context Protocol) integration:

1. **Inbound (MCPServerAdapter)** - Runs as an MCP server, exposing P3394
   capabilities as MCP tools. MCP clients (like Claude Code) call tools,
   which are transformed to P3394 UMF and routed through the gateway.

2. **Outbound (MCPClientAdapter)** - Connects to MCP subagents (like KSTAR
   memory server). P3394 UMF messages destined for subagents are transformed
   to MCP tool calls and sent via the appropriate transport.

The key insight: Inbound calls automatically require response handling
(request/response pattern), while outbound can be either request/response
or fire-and-forget notifications.
"""

import asyncio
import json
import logging
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional, Awaitable
from uuid import uuid4

from ..core.umf import (
    P3394Message, P3394Content, ContentType, MessageType, P3394Address
)
from .base import ChannelAdapter, ChannelCapabilities

logger = logging.getLogger(__name__)


# =============================================================================
# MCP PROTOCOL TYPES
# =============================================================================

@dataclass
class MCPToolDefinition:
    """MCP Tool definition for capability exposure."""
    name: str
    description: str
    input_schema: Dict[str, Any]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.input_schema
        }


@dataclass
class MCPToolCall:
    """Incoming MCP tool call."""
    id: str
    name: str
    arguments: Dict[str, Any]

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MCPToolCall":
        return cls(
            id=data.get("id", str(uuid4())),
            name=data["name"],
            arguments=data.get("arguments", data.get("params", {}))
        )


@dataclass
class MCPToolResult:
    """MCP tool call result."""
    call_id: str
    content: List[Dict[str, Any]]
    is_error: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool_result",
            "tool_use_id": self.call_id,
            "content": self.content,
            "is_error": self.is_error
        }


# =============================================================================
# INBOUND MCP CHANNEL ADAPTER (SERVER)
# =============================================================================

class MCPServerAdapter(ChannelAdapter):
    """
    Inbound MCP Channel Adapter - Runs as an MCP server.

    Exposes P3394 capabilities as MCP tools. When an MCP client (like Claude
    Code or another LLM) calls a tool:

    1. MCPToolCall received via stdio/SSE
    2. Transform to P3394Message (REQUEST type)
    3. Route through AgentGateway
    4. Transform P3394Message response to MCPToolResult
    5. Return to MCP client

    This enables any MCP-compatible client to interact with the P3394 agent.
    """

    def __init__(
        self,
        gateway: "AgentGateway",
        transport: str = "stdio",  # "stdio" or "sse"
        sse_port: int = 8002
    ):
        super().__init__(gateway, "mcp")
        self.transport = transport
        self.sse_port = sse_port

        # Registered MCP tools (generated from P3394 capabilities)
        self._tools: Dict[str, MCPToolDefinition] = {}

        # Pending requests waiting for responses
        self._pending_requests: Dict[str, asyncio.Future] = {}

        # stdio streams
        self._reader: Optional[asyncio.StreamReader] = None
        self._writer: Optional[asyncio.StreamWriter] = None

        # Session tracking
        self._session_id: Optional[str] = None

    @property
    def capabilities(self) -> ChannelCapabilities:
        """MCP channel capabilities."""
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.JSON, ContentType.TOOL_CALL, ContentType.TOOL_RESULT],
            max_message_size=1024 * 1024,  # 1 MB
            supports_streaming=False,
            supports_attachments=False,
            supports_images=False,
            supports_markdown=True,
            supports_html=False,
            supports_slash_commands=False,  # MCP uses tool calls, not slash commands
            supports_cli_flags=False,
            supports_http_endpoints=False,
            command_prefix=""  # No command prefix in MCP
        )

    def authenticate_client(self, context: Dict[str, Any]) -> "ClientPrincipalAssertion":
        """
        Authenticate MCP client.

        MCP clients are typically other agents or tools. Authentication
        is based on the transport:
        - stdio: Local process (MEDIUM assurance)
        - SSE: HTTP with optional auth headers (varies)
        """
        from ..core.auth.principal import AssuranceLevel

        transport = context.get("transport", self.transport)
        client_info = context.get("client_info", {})

        if transport == "stdio":
            # Local process connection - MEDIUM assurance
            import os
            import getpass

            username = getpass.getuser()
            channel_identity = f"mcp:stdio:{username}:{os.getpid()}"

            return self.create_client_assertion(
                channel_identity=channel_identity,
                assurance_level=AssuranceLevel.MEDIUM,
                authentication_method="mcp_stdio",
                metadata={
                    "transport": "stdio",
                    "os_user": username,
                    "pid": os.getpid(),
                    "client_info": client_info
                }
            )

        elif transport == "sse":
            # HTTP SSE connection - check for auth headers
            auth_header = context.get("authorization")

            if auth_header and auth_header.startswith("Bearer "):
                # Bearer token provided - could validate against token store
                token = auth_header[7:]
                channel_identity = f"mcp:sse:bearer:{token[:8]}..."

                return self.create_client_assertion(
                    channel_identity=channel_identity,
                    assurance_level=AssuranceLevel.MEDIUM,
                    authentication_method="mcp_bearer_token",
                    metadata={
                        "transport": "sse",
                        "token_prefix": token[:8],
                        "client_info": client_info
                    }
                )
            else:
                # No auth - LOW assurance
                client_ip = context.get("client_ip", "unknown")
                channel_identity = f"mcp:sse:anonymous:{client_ip}"

                return self.create_client_assertion(
                    channel_identity=channel_identity,
                    assurance_level=AssuranceLevel.LOW,
                    authentication_method="mcp_anonymous",
                    metadata={
                        "transport": "sse",
                        "client_ip": client_ip,
                        "client_info": client_info
                    }
                )

        # Unknown transport - NONE assurance
        return self.create_client_assertion(
            channel_identity="mcp:unknown",
            assurance_level=AssuranceLevel.NONE,
            authentication_method="mcp_unknown",
            metadata={"transport": transport}
        )

    async def start(self):
        """Start the MCP server."""
        self.is_active = True

        # Register tools from P3394 capabilities
        await self._register_tools_from_capabilities()

        # Register with gateway
        await self.gateway.register_channel(self.channel_id, self)

        if self.transport == "stdio":
            await self._start_stdio_server()
        elif self.transport == "sse":
            await self._start_sse_server()
        else:
            raise ValueError(f"Unknown MCP transport: {self.transport}")

    async def stop(self):
        """Stop the MCP server."""
        self.is_active = False

        # Cancel pending requests
        for future in self._pending_requests.values():
            if not future.done():
                future.cancel()
        self._pending_requests.clear()

        if self._writer:
            self._writer.close()
            await self._writer.wait_closed()

        logger.info("MCP Server Adapter stopped")

    async def _register_tools_from_capabilities(self):
        """Generate MCP tools from P3394 capabilities."""

        # Register capability-based tools
        if hasattr(self.gateway, 'capability_registry'):
            for cap_id, capability in self.gateway.capability_registry._capabilities.items():
                tool_name = f"p3394_{cap_id.replace(':', '_').replace('.', '_')}"

                self._tools[tool_name] = MCPToolDefinition(
                    name=tool_name,
                    description=f"P3394 Capability: {capability.description}",
                    input_schema=capability.input_schema or {
                        "type": "object",
                        "properties": {},
                        "required": []
                    }
                )

        # Register symbolic commands as tools
        if hasattr(self.gateway, 'commands'):
            for cmd_name, cmd in self.gateway.commands.items():
                if cmd_name.startswith('/'):
                    tool_name = f"p3394_cmd{cmd_name.replace('/', '_')}"

                    self._tools[tool_name] = MCPToolDefinition(
                        name=tool_name,
                        description=cmd.description,
                        input_schema={
                            "type": "object",
                            "properties": {
                                "args": {
                                    "type": "string",
                                    "description": "Command arguments"
                                }
                            },
                            "required": []
                        }
                    )

        # Always register a generic message tool
        self._tools["p3394_send_message"] = MCPToolDefinition(
            name="p3394_send_message",
            description="Send a P3394 message to the agent",
            input_schema={
                "type": "object",
                "properties": {
                    "text": {
                        "type": "string",
                        "description": "Message text"
                    },
                    "content_type": {
                        "type": "string",
                        "description": "Content type (text, json, markdown)",
                        "enum": ["text", "json", "markdown"],
                        "default": "text"
                    },
                    "metadata": {
                        "type": "object",
                        "description": "Additional message metadata"
                    }
                },
                "required": ["text"]
            }
        )

        # Register UMF passthrough tool
        self._tools["p3394_umf"] = MCPToolDefinition(
            name="p3394_umf",
            description="Send a raw P3394 UMF message",
            input_schema={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "object",
                        "description": "Full P3394 UMF message"
                    }
                },
                "required": ["message"]
            }
        )

        logger.info(f"Registered {len(self._tools)} MCP tools from P3394 capabilities")

    async def _start_stdio_server(self):
        """Start MCP server over stdio."""
        logger.info("Starting MCP Server over stdio")

        # Use asyncio's stdin/stdout
        loop = asyncio.get_event_loop()

        # Create stream reader for stdin
        self._reader = asyncio.StreamReader()
        protocol = asyncio.StreamReaderProtocol(self._reader)
        await loop.connect_read_pipe(lambda: protocol, sys.stdin)

        # Create stream writer for stdout
        write_transport, write_protocol = await loop.connect_write_pipe(
            asyncio.streams.FlowControlMixin, sys.stdout
        )
        self._writer = asyncio.StreamWriter(write_transport, write_protocol, None, loop)

        # Create session
        self._session_id = str(uuid4())

        # Send initialization message
        await self._send_mcp_message({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": self.gateway.AGENT_NAME,
                    "version": self.gateway.AGENT_VERSION
                },
                "capabilities": {
                    "tools": {}
                }
            }
        })

        # Message loop
        await self._mcp_message_loop()

    async def _start_sse_server(self):
        """Start MCP server over SSE (HTTP)."""
        logger.info(f"Starting MCP Server over SSE on port {self.sse_port}")

        # Import FastAPI components
        from fastapi import FastAPI, Request
        from fastapi.responses import StreamingResponse
        import uvicorn

        app = FastAPI(title="P3394 MCP Server")

        @app.get("/mcp")
        async def mcp_sse(request: Request):
            """SSE endpoint for MCP communication."""

            async def event_generator():
                # Send tools list
                tools_event = {
                    "type": "tools",
                    "tools": [t.to_dict() for t in self._tools.values()]
                }
                yield f"data: {json.dumps(tools_event)}\n\n"

                # Keep connection alive
                while True:
                    await asyncio.sleep(30)
                    yield f"data: {json.dumps({'type': 'ping'})}\n\n"

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream"
            )

        @app.post("/mcp/tools/{tool_name}")
        async def call_tool(tool_name: str, request: Request):
            """Handle MCP tool call via HTTP POST."""
            body = await request.json()

            tool_call = MCPToolCall(
                id=body.get("id", str(uuid4())),
                name=tool_name,
                arguments=body.get("arguments", {})
            )

            # Build auth context from request
            auth_context = {
                "transport": "sse",
                "authorization": request.headers.get("Authorization"),
                "client_ip": request.client.host if request.client else "unknown",
                "client_info": {
                    "user_agent": request.headers.get("User-Agent")
                }
            }

            result = await self._handle_tool_call(tool_call, auth_context)
            return result.to_dict()

        config = uvicorn.Config(app, host="0.0.0.0", port=self.sse_port, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    async def _mcp_message_loop(self):
        """Main message loop for stdio MCP server."""
        while self.is_active:
            try:
                # Read line from stdin
                line = await self._reader.readline()
                if not line:
                    break

                # Parse JSON-RPC message
                message = json.loads(line.decode('utf-8').strip())

                # Handle different message types
                if "method" in message:
                    await self._handle_mcp_request(message)
                elif "result" in message or "error" in message:
                    await self._handle_mcp_response(message)

            except asyncio.CancelledError:
                break
            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON received: {e}")
            except Exception as e:
                logger.exception(f"Error in MCP message loop: {e}")

    async def _handle_mcp_request(self, message: Dict[str, Any]):
        """Handle incoming MCP JSON-RPC request."""
        method = message.get("method")
        params = message.get("params", {})
        msg_id = message.get("id")

        if method == "initialize":
            # Client initialization
            await self._send_mcp_response(msg_id, {
                "protocolVersion": "2024-11-05",
                "serverInfo": {
                    "name": self.gateway.AGENT_NAME,
                    "version": self.gateway.AGENT_VERSION
                },
                "capabilities": {
                    "tools": {}
                }
            })

        elif method == "tools/list":
            # Return available tools
            tools_list = [t.to_dict() for t in self._tools.values()]
            await self._send_mcp_response(msg_id, {"tools": tools_list})

        elif method == "tools/call":
            # Handle tool call
            tool_name = params.get("name")
            tool_args = params.get("arguments", {})

            tool_call = MCPToolCall(
                id=msg_id or str(uuid4()),
                name=tool_name,
                arguments=tool_args
            )

            auth_context = {"transport": "stdio"}
            result = await self._handle_tool_call(tool_call, auth_context)

            await self._send_mcp_response(msg_id, {
                "content": result.content,
                "isError": result.is_error
            })

        elif method == "ping":
            await self._send_mcp_response(msg_id, {"pong": True})

        else:
            # Unknown method
            await self._send_mcp_error(msg_id, -32601, f"Method not found: {method}")

    async def _handle_mcp_response(self, message: Dict[str, Any]):
        """Handle MCP JSON-RPC response (for outbound calls)."""
        msg_id = message.get("id")

        if msg_id and msg_id in self._pending_requests:
            future = self._pending_requests.pop(msg_id)

            if "error" in message:
                future.set_exception(Exception(message["error"].get("message", "Unknown error")))
            else:
                future.set_result(message.get("result"))

    async def _handle_tool_call(
        self,
        tool_call: MCPToolCall,
        auth_context: Dict[str, Any]
    ) -> MCPToolResult:
        """
        Handle an MCP tool call by transforming to P3394 and routing.

        This is the core inbound transformation:
        MCPToolCall → P3394Message → Gateway → P3394Message → MCPToolResult
        """
        try:
            # Transform MCP tool call to P3394 UMF message
            umf_message = self._mcp_to_umf(tool_call, auth_context)

            # Route through gateway
            umf_response = await self.gateway.handle(umf_message)

            # Transform P3394 response to MCP result
            result = self._umf_to_mcp_result(tool_call.id, umf_response)

            return result

        except Exception as e:
            logger.exception(f"Error handling MCP tool call: {e}")
            return MCPToolResult(
                call_id=tool_call.id,
                content=[{"type": "text", "text": f"Error: {str(e)}"}],
                is_error=True
            )

    def _mcp_to_umf(
        self,
        tool_call: MCPToolCall,
        auth_context: Dict[str, Any]
    ) -> P3394Message:
        """
        Transform MCP tool call to P3394 UMF message.

        MCP tool calls become P3394 REQUEST messages with:
        - TOOL_CALL content type for capability invocations
        - TEXT content type for simple messages
        - Security metadata with client assertion
        """
        tool_name = tool_call.name
        args = tool_call.arguments

        # Authenticate client
        client_assertion = self.authenticate_client(auth_context)

        # Determine content based on tool type
        if tool_name == "p3394_send_message":
            # Simple text message
            content = [P3394Content(
                type=ContentType(args.get("content_type", "text")),
                data=args.get("text", "")
            )]

        elif tool_name == "p3394_umf":
            # Raw UMF passthrough
            umf_data = args.get("message", {})
            return P3394Message.from_dict(umf_data)

        elif tool_name.startswith("p3394_cmd_"):
            # Symbolic command
            cmd_name = "/" + tool_name.replace("p3394_cmd_", "")
            cmd_args = args.get("args", "")
            full_cmd = f"{cmd_name} {cmd_args}".strip()

            content = [P3394Content(
                type=ContentType.TEXT,
                data=full_cmd
            )]

        else:
            # Capability invocation
            capability_id = tool_name.replace("p3394_", "").replace("_", ":")

            content = [P3394Content(
                type=ContentType.TOOL_CALL,
                data={
                    "capability_id": capability_id,
                    "arguments": args
                },
                metadata={"mcp_tool": tool_name}
            )]

        # Build P3394 message
        return P3394Message(
            id=tool_call.id,
            type=MessageType.REQUEST,
            source=P3394Address(agent_id="mcp-client", channel_id="mcp"),
            destination=P3394Address(agent_id=self.gateway.AGENT_ID, channel_id="mcp"),
            content=content,
            session_id=self._session_id,
            metadata={
                "security": {
                    "client_assertion": client_assertion.to_dict()
                },
                "channel": {
                    "channel_id": "mcp",
                    "transport": auth_context.get("transport", "unknown"),
                    "mcp_tool": tool_name
                }
            }
        )

    def _umf_to_mcp_result(
        self,
        call_id: str,
        umf_message: P3394Message
    ) -> MCPToolResult:
        """
        Transform P3394 UMF response to MCP tool result.

        P3394 content blocks are converted to MCP content blocks.
        """
        mcp_content = []
        is_error = umf_message.type == MessageType.ERROR

        for content in umf_message.content:
            if content.type == ContentType.TEXT:
                mcp_content.append({
                    "type": "text",
                    "text": content.data
                })

            elif content.type == ContentType.MARKDOWN:
                mcp_content.append({
                    "type": "text",
                    "text": content.data
                })

            elif content.type == ContentType.JSON:
                mcp_content.append({
                    "type": "text",
                    "text": json.dumps(content.data, indent=2)
                })

            elif content.type == ContentType.TOOL_RESULT:
                # Nested tool result
                mcp_content.append({
                    "type": "tool_result",
                    "tool_use_id": content.data.get("tool_id"),
                    "content": content.data.get("result")
                })

            else:
                # Other content types - convert to text representation
                mcp_content.append({
                    "type": "text",
                    "text": f"[{content.type.value}]: {str(content.data)[:500]}"
                })

        # If no content, add a default message
        if not mcp_content:
            mcp_content.append({
                "type": "text",
                "text": "Operation completed successfully" if not is_error else "Operation failed"
            })

        return MCPToolResult(
            call_id=call_id,
            content=mcp_content,
            is_error=is_error
        )

    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """
        Send a message back to an MCP client.

        For MCP, this is typically handled as part of the tool call response.
        This method is used for push notifications (if supported).
        """
        # MCP is primarily request/response, but we can send notifications
        notification = {
            "jsonrpc": "2.0",
            "method": "notification",
            "params": {
                "message_id": message.id,
                "type": message.type.value,
                "content": [
                    {"type": c.type.value, "data": c.data}
                    for c in message.content
                ]
            }
        }

        await self._send_mcp_message(notification)

    async def _send_mcp_message(self, message: Dict[str, Any]):
        """Send a JSON-RPC message over stdio."""
        if self._writer:
            line = json.dumps(message) + "\n"
            self._writer.write(line.encode('utf-8'))
            await self._writer.drain()

    async def _send_mcp_response(self, msg_id: Any, result: Any):
        """Send a JSON-RPC response."""
        await self._send_mcp_message({
            "jsonrpc": "2.0",
            "id": msg_id,
            "result": result
        })

    async def _send_mcp_error(self, msg_id: Any, code: int, message: str):
        """Send a JSON-RPC error response."""
        await self._send_mcp_message({
            "jsonrpc": "2.0",
            "id": msg_id,
            "error": {
                "code": code,
                "message": message
            }
        })


# =============================================================================
# OUTBOUND MCP CHANNEL ADAPTER (CLIENT)
# =============================================================================

@dataclass
class MCPSubagentConnection:
    """Connection to an MCP subagent."""
    agent_id: str
    transport: str  # "stdio" or "http"
    process: Optional[asyncio.subprocess.Process] = None
    reader: Optional[asyncio.StreamReader] = None
    writer: Optional[asyncio.StreamWriter] = None
    http_endpoint: Optional[str] = None
    pending_requests: Dict[str, asyncio.Future] = field(default_factory=dict)
    is_connected: bool = False


class MCPClientAdapter:
    """
    Outbound MCP Channel Adapter - Connects to MCP subagents.

    Used when the P3394 gateway needs to send messages to MCP-based
    subagents (like KSTAR memory server). Transforms P3394 UMF messages
    to MCP tool calls.

    Unlike the inbound adapter (which responds to calls), this adapter
    initiates calls to subagents.
    """

    def __init__(self, gateway: "AgentGateway"):
        self.gateway = gateway

        # Connected subagents
        self._connections: Dict[str, MCPSubagentConnection] = {}

        # Message ID counter
        self._message_id = 0

    async def connect_stdio(
        self,
        agent_id: str,
        command: str,
        args: List[str] = None
    ) -> bool:
        """
        Connect to an MCP subagent via stdio.

        Args:
            agent_id: Subagent identifier
            command: Command to run the MCP server
            args: Command arguments

        Returns:
            True if connection successful
        """
        try:
            # Start the subprocess using create_subprocess_exec (safe, no shell)
            process = await asyncio.create_subprocess_exec(
                command,
                *(args or []),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # Create connection record
            conn = MCPSubagentConnection(
                agent_id=agent_id,
                transport="stdio",
                process=process,
                reader=process.stdout,
                writer=process.stdin,
                is_connected=True
            )

            self._connections[agent_id] = conn

            # Start response reader
            asyncio.create_task(self._read_responses(agent_id))

            # Initialize connection
            await self._initialize_connection(agent_id)

            logger.info(f"Connected to MCP subagent: {agent_id}")
            return True

        except Exception as e:
            logger.exception(f"Failed to connect to MCP subagent {agent_id}: {e}")
            return False

    async def connect_http(self, agent_id: str, endpoint: str) -> bool:
        """
        Connect to an MCP subagent via HTTP.

        Args:
            agent_id: Subagent identifier
            endpoint: HTTP endpoint URL

        Returns:
            True if connection successful
        """
        conn = MCPSubagentConnection(
            agent_id=agent_id,
            transport="http",
            http_endpoint=endpoint,
            is_connected=True
        )

        self._connections[agent_id] = conn
        logger.info(f"Connected to MCP subagent via HTTP: {agent_id} at {endpoint}")
        return True

    async def disconnect(self, agent_id: str):
        """Disconnect from an MCP subagent."""
        conn = self._connections.get(agent_id)
        if not conn:
            return

        conn.is_connected = False

        # Cancel pending requests
        for future in conn.pending_requests.values():
            if not future.done():
                future.cancel()

        # Close stdio connection
        if conn.transport == "stdio" and conn.process:
            conn.process.terminate()
            await conn.process.wait()

        del self._connections[agent_id]
        logger.info(f"Disconnected from MCP subagent: {agent_id}")

    async def send(self, agent_id: str, message: P3394Message) -> P3394Message:
        """
        Send a P3394 message to an MCP subagent.

        Transforms the P3394 UMF message to an MCP tool call,
        sends it, and transforms the response back to UMF.

        Args:
            agent_id: Target subagent ID
            message: P3394 UMF message

        Returns:
            P3394 UMF response message
        """
        conn = self._connections.get(agent_id)
        if not conn or not conn.is_connected:
            return self._create_error_response(
                message, f"Not connected to subagent: {agent_id}"
            )

        try:
            # Transform P3394 to MCP tool call
            tool_call = self._umf_to_mcp_call(message)

            # Send based on transport
            if conn.transport == "stdio":
                result = await self._send_stdio(conn, tool_call)
            else:
                result = await self._send_http(conn, tool_call)

            # Transform MCP result to P3394 response
            response = self._mcp_result_to_umf(message, result)
            return response

        except Exception as e:
            logger.exception(f"Error sending to MCP subagent {agent_id}: {e}")
            return self._create_error_response(message, str(e))

    def _umf_to_mcp_call(self, message: P3394Message) -> Dict[str, Any]:
        """Transform P3394 UMF message to MCP tool call."""
        self._message_id += 1

        # Extract capability/tool info from message
        tool_name = "p3394_message"
        arguments = {}

        for content in message.content:
            if content.type == ContentType.TOOL_CALL:
                # Direct tool call
                tool_name = content.data.get("capability_id", "").replace(":", "_")
                arguments = content.data.get("arguments", {})
                break

            elif content.type == ContentType.TEXT:
                # Text message - use generic handler
                tool_name = "p3394_send_message"
                arguments = {"text": content.data}
                break

            elif content.type == ContentType.JSON:
                # JSON data
                tool_name = "p3394_json"
                arguments = content.data
                break

        return {
            "jsonrpc": "2.0",
            "id": self._message_id,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }

    def _mcp_result_to_umf(
        self,
        original: P3394Message,
        result: Dict[str, Any]
    ) -> P3394Message:
        """Transform MCP result to P3394 UMF response."""
        content = []
        is_error = result.get("isError", False)

        mcp_content = result.get("content", [])
        for item in mcp_content:
            item_type = item.get("type", "text")

            if item_type == "text":
                content.append(P3394Content(
                    type=ContentType.TEXT,
                    data=item.get("text", "")
                ))
            else:
                content.append(P3394Content(
                    type=ContentType.JSON,
                    data=item
                ))

        return P3394Message(
            type=MessageType.ERROR if is_error else MessageType.RESPONSE,
            reply_to=original.id,
            source=original.destination,
            destination=original.source,
            content=content,
            session_id=original.session_id
        )

    async def _send_stdio(
        self,
        conn: MCPSubagentConnection,
        call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send MCP call over stdio."""
        msg_id = call["id"]

        # Create future for response
        future = asyncio.get_event_loop().create_future()
        conn.pending_requests[msg_id] = future

        try:
            # Send message
            line = json.dumps(call) + "\n"
            conn.writer.write(line.encode('utf-8'))
            await conn.writer.drain()

            # Wait for response (with timeout)
            result = await asyncio.wait_for(future, timeout=30.0)
            return result

        except asyncio.TimeoutError:
            raise Exception("MCP call timed out")
        finally:
            conn.pending_requests.pop(msg_id, None)

    async def _send_http(
        self,
        conn: MCPSubagentConnection,
        call: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send MCP call over HTTP."""
        import httpx

        tool_name = call["params"]["name"]
        url = f"{conn.http_endpoint}/mcp/tools/{tool_name}"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                url,
                json={
                    "id": call["id"],
                    "arguments": call["params"]["arguments"]
                },
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()

    async def _read_responses(self, agent_id: str):
        """Background task to read responses from stdio connection."""
        conn = self._connections.get(agent_id)
        if not conn or not conn.reader:
            return

        while conn.is_connected:
            try:
                line = await conn.reader.readline()
                if not line:
                    break

                message = json.loads(line.decode('utf-8').strip())

                # Match response to pending request
                msg_id = message.get("id")
                if msg_id and msg_id in conn.pending_requests:
                    future = conn.pending_requests[msg_id]

                    if "error" in message:
                        future.set_exception(Exception(
                            message["error"].get("message", "Unknown error")
                        ))
                    else:
                        future.set_result(message.get("result", {}))

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning(f"Error reading MCP response: {e}")

    async def _initialize_connection(self, agent_id: str):
        """Send initialization message to MCP subagent."""
        conn = self._connections.get(agent_id)
        if not conn:
            return

        init_msg = {
            "jsonrpc": "2.0",
            "id": 0,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "clientInfo": {
                    "name": self.gateway.AGENT_NAME,
                    "version": self.gateway.AGENT_VERSION
                },
                "capabilities": {}
            }
        }

        if conn.transport == "stdio":
            line = json.dumps(init_msg) + "\n"
            conn.writer.write(line.encode('utf-8'))
            await conn.writer.drain()

    def _create_error_response(
        self,
        original: P3394Message,
        error_message: str
    ) -> P3394Message:
        """Create an error response message."""
        return P3394Message(
            type=MessageType.ERROR,
            reply_to=original.id,
            source=original.destination,
            destination=original.source,
            content=[P3394Content(
                type=ContentType.JSON,
                data={"code": "MCP_ERROR", "message": error_message}
            )],
            session_id=original.session_id
        )

    def get_connected_subagents(self) -> List[str]:
        """Get list of connected subagent IDs."""
        return [
            agent_id
            for agent_id, conn in self._connections.items()
            if conn.is_connected
        ]

    def is_connected(self, agent_id: str) -> bool:
        """Check if connected to a subagent."""
        conn = self._connections.get(agent_id)
        return conn is not None and conn.is_connected


# =============================================================================
# OUTBOUND CHANNEL ROUTER
# =============================================================================

class OutboundChannelRouter:
    """
    Routes outbound P3394 messages to the appropriate transport.

    This is the unified outbound adapter that:
    1. Looks up the destination agent in the session registry
    2. Selects the best available transport
    3. Transforms and sends the message
    4. Returns the response
    """

    def __init__(self, gateway: "AgentGateway"):
        self.gateway = gateway
        self.mcp_client = MCPClientAdapter(gateway)

        # Transport handlers
        self._transports: Dict[str, Callable] = {
            "mcp_stdio": self._send_via_mcp,
            "mcp_http": self._send_via_mcp,
            "http": self._send_via_http,
            "direct": self._send_via_direct,
        }

    async def send(self, message: P3394Message) -> P3394Message:
        """
        Send a P3394 message to its destination.

        Routes based on destination agent's registered transport.
        """
        if not message.destination:
            raise ValueError("Message has no destination")

        agent_id = message.destination.agent_id

        # Look up transport for destination
        transport = await self._get_transport(agent_id)

        if transport in self._transports:
            return await self._transports[transport](agent_id, message)
        else:
            raise ValueError(f"Unknown transport for {agent_id}: {transport}")

    async def _get_transport(self, agent_id: str) -> str:
        """Get the transport type for a destination agent."""
        # Check if already connected via MCP
        if self.mcp_client.is_connected(agent_id):
            conn = self.mcp_client._connections[agent_id]
            return f"mcp_{conn.transport}"

        # Look up in session registry (if available)
        # For now, default to direct for in-process subagents
        if agent_id == "kstar-memory":
            return "direct"

        return "http"

    async def _send_via_mcp(
        self,
        agent_id: str,
        message: P3394Message
    ) -> P3394Message:
        """Send via MCP client."""
        return await self.mcp_client.send(agent_id, message)

    async def _send_via_http(
        self,
        agent_id: str,
        message: P3394Message
    ) -> P3394Message:
        """Send via HTTP POST."""
        import httpx

        # TODO: Look up endpoint from registry
        endpoint = f"http://localhost:8001/api/p3394"

        async with httpx.AsyncClient() as client:
            response = await client.post(
                endpoint,
                json=message.to_dict(),
                headers={"Content-Type": "application/json"},
                timeout=30.0
            )
            response.raise_for_status()
            return P3394Message.from_dict(response.json())

    async def _send_via_direct(
        self,
        agent_id: str,
        message: P3394Message
    ) -> P3394Message:
        """Send via direct in-process call."""
        # For in-process subagents, we can call methods directly
        # This is the fastest path for same-process communication

        if agent_id == "kstar-memory" and self.gateway.memory:
            # Route KSTAR memory operations directly
            return await self._handle_kstar_direct(message)

        raise ValueError(f"No direct handler for: {agent_id}")

    async def _handle_kstar_direct(self, message: P3394Message) -> P3394Message:
        """Handle KSTAR memory operations directly."""
        # Extract operation from message
        for content in message.content:
            if content.type == ContentType.TOOL_CALL:
                capability_id = content.data.get("capability_id", "")
                args = content.data.get("arguments", {})

                # Map capability to memory method
                result = await self._invoke_kstar_method(capability_id, args)

                return P3394Message(
                    type=MessageType.RESPONSE,
                    reply_to=message.id,
                    source=message.destination,
                    destination=message.source,
                    content=[P3394Content(
                        type=ContentType.JSON,
                        data=result
                    )],
                    session_id=message.session_id
                )

        # Default response for non-tool messages
        return P3394Message(
            type=MessageType.RESPONSE,
            reply_to=message.id,
            source=message.destination,
            destination=message.source,
            content=[P3394Content(
                type=ContentType.TEXT,
                data="Message received by KSTAR memory"
            )],
            session_id=message.session_id
        )

    async def _invoke_kstar_method(
        self,
        capability_id: str,
        args: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Invoke KSTAR memory method based on capability ID."""
        memory = self.gateway.memory

        method_map = {
            "kstar:store_trace": memory.store_trace,
            "kstar:query_traces": memory.query_traces,
            "kstar:store_perception": memory.store_perception,
            "kstar:store_skill": memory.store_skill,
            "kstar:get_skill": memory.get_skill,
            "kstar:list_skills": memory.list_skills,
            "kstar:get_stats": memory.get_stats,
        }

        method = method_map.get(capability_id)
        if method:
            result = await method(**args) if asyncio.iscoroutinefunction(method) else method(**args)
            return {"success": True, "result": result}

        return {"success": False, "error": f"Unknown capability: {capability_id}"}
