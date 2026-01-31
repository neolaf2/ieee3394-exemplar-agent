"""
P3394 Channel Adapters

Channel adapters transform between native protocols and P3394 UMF messages.

Available adapters:
- CLIChannelAdapter: Terminal/REPL interface
- UnifiedWebServer: Consolidated HTTP server with multiple routes
  - /chat - Web chat UI
  - /api/ - REST API
  - /v1/  - Anthropic API compatible
  - /p3394/ - P3394 native protocol
- MCPServerAdapter: Inbound MCP server (exposes P3394 as MCP tools)
- MCPClientAdapter: Outbound MCP client (connects to MCP subagents)
- OutboundChannelRouter: Routes outbound messages to appropriate transport
"""

from .base import ChannelAdapter, ChannelCapabilities
from .cli import CLIChannelAdapter
from .unified_web_server import UnifiedWebServer
from .mcp import (
    MCPServerAdapter,
    MCPClientAdapter,
    OutboundChannelRouter,
    MCPToolDefinition,
    MCPToolCall,
    MCPToolResult,
)

# Legacy imports for backward compatibility
from .anthropic_api_server import AnthropicAPIServerAdapter
from .p3394_server import P3394ServerAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelCapabilities",
    "CLIChannelAdapter",
    "UnifiedWebServer",
    # MCP Channel Adapters
    "MCPServerAdapter",
    "MCPClientAdapter",
    "OutboundChannelRouter",
    "MCPToolDefinition",
    "MCPToolCall",
    "MCPToolResult",
    # Legacy
    "AnthropicAPIServerAdapter",
    "P3394ServerAdapter",
]
