# Channel Command Routing

**Status:** ✅ Implemented
**Date:** 2026-01-28

## Overview

Different channels express commands differently, even though they conceptually do the same thing. The base adapter class now handles command syntax mapping and endpoint discovery.

## The Problem

The same "help" command expressed differently across channels:

```
Canonical P3394: /help

CLI Chat:        >>> /help
CLI Args:        $ ieee3394-agent --help
HTTP:            GET http://agent.com/help
Slack:           /help  or  @agent help
Web Form:        <button onclick="getHelp()">Help</button>
P3394 Agent:     {"content": [{"data": "/help"}]}
```

## Solution: Command Syntax Mapping

### 1. Capabilities Declaration

Each adapter declares its command syntax support:

```python
@dataclass
class ChannelCapabilities:
    # ... content capabilities ...

    # Command routing
    command_prefix: str = "/"
    supports_slash_commands: bool = True   # /command
    supports_cli_flags: bool = False       # --command
    supports_http_endpoints: bool = False  # GET /command
    supports_mentions: bool = False        # @agent command
```

### 2. Endpoint Discovery

Adapters expose their available endpoints:

```python
adapter.get_endpoints()
# Returns:
{
    "help": "/help",          # CLI chat
    "about": "/about",
    "version": "/version",
    ...
}

# or for HTTP adapter:
{
    "help": "GET /help",
    "about": "GET /about",
    "version": "GET /version",
    ...
}

# or for CLI args adapter:
{
    "help": "--help",
    "about": "--about",
    "version": "--version",
    ...
}
```

### 3. Command Normalization

Adapters normalize channel-specific input to canonical form:

```python
adapter.normalize_command("--help")  # → "/help"
adapter.normalize_command("/help")   # → "/help"
adapter.normalize_command("help")    # → "/help" (if known command)
adapter.normalize_command("GET /help")  # → "/help"
```

## Channel-Specific Examples

### CLI Chat Adapter (REPL)

```python
class CLIChannelAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            command_prefix="/",
            supports_slash_commands=True,
            supports_cli_flags=False,
            supports_http_endpoints=False,
            supports_mentions=False
        )

# Usage:
>>> /help              # ✓ Direct slash command
>>> help               # ✓ Normalized to /help
>>> --help             # ✗ Not supported in chat
```

**Endpoints:**
```python
cli_adapter.get_endpoints()
# {
#   "help": "/help",
#   "about": "/about",
#   "status": "/status",
#   "version": "/version",
#   ...
# }
```

### CLI Args Adapter (Command Line)

```python
class CLIArgsAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            command_prefix="--",
            supports_slash_commands=False,
            supports_cli_flags=True,
            supports_http_endpoints=False,
            supports_mentions=False
        )

# Usage:
$ ieee3394-agent --help       # ✓ CLI flag
$ ieee3394-agent --version    # ✓ CLI flag
$ ieee3394-agent /help        # ✗ Not standard CLI syntax
```

**Endpoints:**
```python
cli_args_adapter.get_endpoints()
# {
#   "help": "--help",
#   "about": "--about",
#   "version": "--version",
#   "status": "--status",
#   ...
# }
```

### HTTP/Web Adapter

```python
class HTTPAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            command_prefix="/",
            supports_slash_commands=False,
            supports_cli_flags=False,
            supports_http_endpoints=True,
            supports_mentions=False
        )

# HTTP Routes automatically created:
# GET  /help      → /help command
# GET  /about     → /about command
# GET  /status    → /status command
# GET  /version   → /version command
```

**Endpoints:**
```python
http_adapter.get_endpoints()
# {
#   "help": "GET /help",
#   "about": "GET /about",
#   "status": "GET /status",
#   "version": "GET /version",
#   ...
# }
```

### Slack Adapter

```python
class SlackAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            command_prefix="/",
            supports_slash_commands=True,
            supports_cli_flags=False,
            supports_http_endpoints=False,
            supports_mentions=True
        )

# Usage in Slack:
/help                  # ✓ Slack slash command
@agent help            # ✓ Mention bot
help                   # ✓ In DM with bot
```

**Endpoints:**
```python
slack_adapter.get_endpoints()
# {
#   "help": "/help or @agent help",
#   "about": "/about or @agent about",
#   ...
# }
```

### P3394 Agent Adapter

```python
class P3394ServerAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            command_prefix="/",
            supports_slash_commands=True,
            supports_cli_flags=False,
            supports_http_endpoints=True,  # Exposes HTTP + UMF
            supports_mentions=False
        )

# HTTP Endpoints:
# GET  /manifest           → Agent manifest
# POST /messages           → Send UMF message
# GET  /help, /about, etc. → Symbolic commands (HTTP)
# WS   /ws                 → WebSocket for streaming

# UMF Content:
# {"content": [{"data": "/help"}]} → Symbolic command in UMF
```

## Agent Manifest with Endpoints

When a P3394 agent publishes its manifest, it includes channel-specific endpoints:

```json
{
  "agent_id": "ieee3394-exemplar",
  "name": "IEEE 3394 Exemplar Agent",
  "version": "0.1.0",
  "protocol": "P3394",
  "address": "p3394://ieee3394-exemplar/p3394-server",

  "channels": [
    {
      "id": "cli",
      "type": "CLIChannelAdapter",
      "command_syntax": "slash",
      "endpoints": {
        "help": "/help",
        "about": "/about",
        "version": "/version"
      }
    },
    {
      "id": "http",
      "type": "HTTPAdapter",
      "command_syntax": "http",
      "endpoints": {
        "help": "GET http://agent.com/help",
        "about": "GET http://agent.com/about",
        "version": "GET http://agent.com/version"
      }
    },
    {
      "id": "p3394-server",
      "type": "P3394ServerAdapter",
      "command_syntax": "mixed",
      "endpoints": {
        "manifest": "GET http://agent.com:8101/manifest",
        "messages": "POST http://agent.com:8101/messages",
        "websocket": "WS http://agent.com:8101/ws",
        "help": "GET http://agent.com:8101/help",
        "about": "GET http://agent.com:8101/help"
      }
    }
  ],

  "commands": [
    {
      "name": "/help",
      "description": "Show available commands",
      "syntax_by_channel": {
        "cli": "/help",
        "cli-args": "--help",
        "http": "GET /help",
        "slack": "/help or @agent help",
        "p3394": "/help (in UMF content)"
      }
    },
    {
      "name": "/version",
      "description": "Get agent version",
      "syntax_by_channel": {
        "cli": "/version",
        "cli-args": "--version",
        "http": "GET /version",
        "slack": "/version",
        "p3394": "/version"
      }
    }
  ]
}
```

## Command Routing Flow

```
User Input (channel-specific)
         ↓
┌────────────────────────┐
│  Channel Adapter       │
│  .normalize_command()  │
└────────┬───────────────┘
         │
         │ Canonical command: "/help"
         ↓
┌────────────────────────┐
│  UMF Message           │
│  content: [{           │
│    type: "text",       │
│    data: "/help"       │
│  }]                    │
└────────┬───────────────┘
         │
         ↓
┌────────────────────────┐
│  Gateway               │
│  .handle()             │
│  Routes /help to       │
│  symbolic handler      │
└────────┬───────────────┘
         │
         │ Response (UMF)
         ↓
┌────────────────────────┐
│  Channel Adapter       │
│  Formats response      │
│  for channel           │
└────────┬───────────────┘
         │
         ↓
User sees channel-appropriate response
```

## Benefits

✅ **Consistent semantics**: Same command works across all channels
✅ **Channel-appropriate syntax**: Each channel uses natural syntax
✅ **Discoverability**: Clients can query available endpoints per channel
✅ **Extensibility**: Easy to add new command syntaxes
✅ **Standards compliance**: P3394 canonical form internally

## Implementation

### Base Adapter Methods

All channel adapters inherit from `ChannelAdapter` base class in `channels/base.py`:

```python
class ChannelAdapter:
    def get_endpoints(self) -> Dict[str, str]:
        """
        Get channel-specific command endpoints.

        Returns a dictionary mapping command names to channel-specific syntax.
        Automatically discovers all registered commands from the gateway.
        """
        endpoints = {}
        if hasattr(self, 'gateway') and hasattr(self.gateway, 'commands'):
            for cmd_name in set(cmd.name for cmd in self.gateway.commands.values()):
                endpoints[cmd_name.lstrip('/')] = self._map_command_syntax(cmd_name)
        return endpoints

    def _map_command_syntax(self, canonical_command: str) -> str:
        """
        Map canonical command (e.g., "/help") to channel-specific syntax.

        Uses the channel's capabilities to determine the appropriate format:
        - CLI flags: --help
        - HTTP endpoints: /help
        - Slash commands: /help (default)
        """
        cmd_name = canonical_command.lstrip('/')

        if self.capabilities.supports_cli_flags:
            return f"--{cmd_name}"
        elif self.capabilities.supports_http_endpoints:
            return f"/{cmd_name}"
        elif self.capabilities.supports_slash_commands:
            return f"/{cmd_name}"
        else:
            return cmd_name

    def normalize_command(self, raw_input: str) -> str:
        """
        Normalize channel-specific command syntax to canonical form.

        Converts:
        - --help → /help (CLI flags)
        - /help → /help (slash commands)
        - help → /help (if known command)
        """
        raw_input = raw_input.strip()

        # CLI flags: --help → /help
        if raw_input.startswith('--'):
            return '/' + raw_input[2:]

        # Already slash command
        if raw_input.startswith('/'):
            return raw_input

        # Plain text: check if it matches a known command
        if hasattr(self, 'gateway') and hasattr(self.gateway, 'commands'):
            test_cmd = '/' + raw_input
            if test_cmd in self.gateway.commands:
                return test_cmd

        return raw_input
```

### P3394 Server Manifest Methods

The P3394 Server Adapter includes methods to generate the manifest with complete channel and command information:

```python
class P3394ServerAdapter(ChannelAdapter):
    def _get_channels_with_endpoints(self) -> list:
        """
        Get list of channels with their specific command endpoints.

        Returns channel information including:
        - Channel ID and type
        - Command syntax style (cli_flags, http, slash, text)
        - All available endpoints on that channel
        """
        channels = []
        for channel_id, adapter in self.gateway.channels.items():
            caps = adapter.capabilities

            # Determine command syntax type
            if caps.supports_cli_flags:
                command_syntax = "cli_flags"
            elif caps.supports_http_endpoints:
                command_syntax = "http"
            elif caps.supports_slash_commands:
                command_syntax = "slash"
            else:
                command_syntax = "text"

            channel_info = {
                "id": channel_id,
                "type": adapter.__class__.__name__,
                "active": adapter.is_active,
                "command_syntax": command_syntax,
                "command_prefix": caps.command_prefix,
                "endpoints": adapter.get_endpoints()
            }
            channels.append(channel_info)

        return channels

    def _get_commands_with_syntax(self) -> list:
        """
        Get list of commands with syntax variations for each channel.

        Returns command information showing:
        - Command name, description, usage
        - Whether authentication is required
        - Syntax variation for each active channel
        """
        commands = []
        seen = set()

        for cmd in self.gateway.commands.values():
            if cmd.name in seen:
                continue
            seen.add(cmd.name)

            # Build syntax variations across channels
            syntax_by_channel = {}
            for channel_id, adapter in self.gateway.channels.items():
                channel_syntax = adapter._map_command_syntax(cmd.name)
                syntax_by_channel[channel_id] = channel_syntax

            command_info = {
                "name": cmd.name,
                "description": cmd.description,
                "usage": cmd.usage if cmd.usage else cmd.name,
                "requires_auth": cmd.requires_auth,
                "aliases": cmd.aliases,
                "syntax_by_channel": syntax_by_channel
            }
            commands.append(command_info)

        return commands
```

### Usage in Adapters

```python
class CLIChannelAdapter:
    async def handle_cli_client(self, reader, writer):
        # ... connection setup ...

        data = await reader.read()
        raw_input = data.decode()

        # Normalize to canonical form
        canonical = self.normalize_command(raw_input)

        # Create UMF message
        umf = P3394Message.text(canonical)

        # Gateway processes canonical command
        response = await self.gateway.handle(umf)
```

## Examples

### Discover Available Commands

```bash
# CLI
$ ieee3394-cli
>>> /listCommands

# HTTP
$ curl http://agent.com/manifest | jq '.commands'

# P3394
POST http://agent.com:8101/messages
{
  "content": [{"type": "text", "data": "/listCommands"}]
}
```

### Execute Command in Different Channels

```bash
# CLI Chat
>>> /help

# CLI Args
$ ieee3394-agent --help

# HTTP
$ curl http://agent.com/help

# Slack
/help

# P3394 UMF
POST /messages
{"content": [{"data": "/help"}]}
```

All route to the same symbolic command handler!

## Summary

Channel command routing ensures that:
1. **Commands work consistently** across all channels
2. **Syntax is natural** for each channel (CLI flags vs. HTTP vs. slash commands)
3. **Discovery is easy** (manifest shows endpoints per channel)
4. **Extension is simple** (add new channels with their own syntax)

This makes the agent truly **multi-channel while maintaining semantic consistency**! 🎯
