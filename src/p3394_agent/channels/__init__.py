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
"""

from .base import ChannelAdapter, ChannelCapabilities
from .cli import CLIChannelAdapter
from .unified_web_server import UnifiedWebServer

# Legacy imports for backward compatibility
from .anthropic_api_server import AnthropicAPIServerAdapter
from .p3394_server import P3394ServerAdapter

__all__ = [
    "ChannelAdapter",
    "ChannelCapabilities",
    "CLIChannelAdapter",
    "UnifiedWebServer",
    # Legacy
    "AnthropicAPIServerAdapter",
    "P3394ServerAdapter",
]
