"""
P3394 Agent Plugins

MCP tools and hooks for the IEEE 3394 Agent.

Tool Categories:
- tools_sdk: Core SDK tools (memory, skills, ACLs)
- token_tools: KSTAR+ Control Token management
- kstar_tools: Principal, Identity, and Auth management (MCP-first architecture)
- hooks_sdk: SDK hooks for Claude Agent SDK integration
"""

from .tools_sdk import create_sdk_tools
from .token_tools import create_token_tools
from .kstar_tools import create_kstar_tools
from .hooks_sdk import create_sdk_hooks

__all__ = [
    "create_sdk_tools",
    "create_token_tools",
    "create_kstar_tools",
    "create_sdk_hooks",
]
