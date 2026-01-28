# Content Negotiation and Channel Capabilities

**Status:** ✅ Implemented
**Date:** 2026-01-28

## Overview

Implemented a comprehensive content negotiation system that allows channel adapters to:
1. Declare their capabilities (supported content types, size limits, features)
2. Automatically adapt UMF messages to channel limitations
3. Provide fallback representations for unsupported content
4. Notify clients about dropped/downgraded content

## Problem Statement

P3394 UMF supports rich content:
- Text, Markdown, HTML
- Images, binary files
- Folder structures (zip files)
- Tool calls and results

But different channels have different capabilities:
- **CLI**: Text/Markdown only
- **Slack**: Text, images, file attachments
- **HTTP API**: Full support
- **SMS**: Text only, very limited size

## Solution: Channel Capabilities + Content Adaptation

### 1. Channel Capabilities Declaration

Each adapter declares what it supports:

```python
@dataclass
class ChannelCapabilities:
    # Supported content types
    content_types: List[ContentType]

    # Size limits
    max_message_size: int
    max_attachment_size: int

    # Feature support
    supports_streaming: bool
    supports_attachments: bool
    supports_images: bool
    supports_folders: bool
    supports_multipart: bool
    supports_markdown: bool
    supports_html: bool

    # Rate limits
    max_concurrent_connections: int
    rate_limit_per_minute: int
```

### 2. Base Adapter Class

All adapters inherit from `ChannelAdapter` base class:

```python
class ChannelAdapter(ABC):
    @property
    @abstractmethod
    def capabilities(self) -> ChannelCapabilities:
        """Declare channel capabilities"""
        pass

    def adapt_content(self, message: P3394Message) -> P3394Message:
        """Adapt message to channel capabilities"""
        # Transforms unsupported content types
        # Adds metadata about dropped content
        pass

    @abstractmethod
    async def send_to_client(self, reply_to: Dict, message: P3394Message):
        """Send message back to client"""
        pass
```

### 3. Content Downgrading Rules

When content type is not supported, adapters automatically downgrade:

| Original | Channel Support | Downgrade To |
|----------|----------------|--------------|
| Image | No images | `[Image: filename.png]` (text) |
| Binary file | No attachments | `[File: document.pdf (1.2 MB)]` (text) |
| HTML | Markdown support | Convert HTML → Markdown |
| HTML | Text only | Strip HTML tags → Plain text |
| Folder (zip) | No folders | List filenames (text) |

### 4. Metadata About Dropped Content

Adapted messages include information about what was dropped:

```json
{
  "type": "response",
  "content": [...],
  "metadata": {
    "dropped_content": [
      {
        "type": "image",
        "filename": "chart.png",
        "reason": "CLI does not support images"
      },
      {
        "type": "file",
        "filename": "report.pdf",
        "reason": "CLI does not support file downloads",
        "suggestion": "Use web interface to download"
      }
    ]
  }
}
```

## Implementation

### Files Created/Modified

**New Files:**
- `src/ieee3394_agent/channels/base.py` - Base adapter class with capabilities

**Modified Files:**
- `src/ieee3394_agent/channels/cli.py` - Added capabilities, content adaptation
- `src/ieee3394_agent/channels/p3394_server.py` - Added capabilities
- `src/ieee3394_agent/channels/anthropic_api_server.py` - (TODO: add capabilities)

### Example: CLI Channel Capabilities

```python
class CLIChannelAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            content_types=[ContentType.TEXT, ContentType.MARKDOWN],
            max_message_size=100 * 1024,  # 100 KB
            max_attachment_size=0,  # No attachments
            supports_streaming=False,
            supports_attachments=False,
            supports_images=False,
            supports_folders=False,
            supports_multipart=False,
            supports_markdown=True,
            supports_html=False
        )
```

### Example: P3394 Server Capabilities

```python
class P3394ServerAdapter(ChannelAdapter):
    @property
    def capabilities(self) -> ChannelCapabilities:
        return ChannelCapabilities(
            content_types=[
                ContentType.TEXT,
                ContentType.JSON,
                ContentType.MARKDOWN,
                ContentType.HTML,
                ContentType.BINARY,
                ContentType.TOOL_CALL,
                ContentType.TOOL_RESULT
            ],
            max_message_size=100 * 1024 * 1024,  # 100 MB
            supports_streaming=True,
            supports_attachments=True,
            supports_images=True,
            supports_folders=True,
            supports_multipart=True
        )
```

## Content Adaptation Flow

```
┌──────────────────┐
│  Gateway         │
│  (Generates      │
│   rich UMF)      │
└────────┬─────────┘
         │
         │ P3394Message with:
         │ - Text content
         │ - Image attachment
         │ - Binary file
         │
         ↓
┌────────────────────┐
│  CLI Adapter       │
│  .adapt_content()  │
└────────┬───────────┘
         │
         │ Adapted P3394Message:
         │ - Text content ✓
         │ - [Image: chart.png] (text) ✓
         │ - [File: data.csv (2.1 KB)] (text) ✓
         │ - metadata.dropped_content = [...]
         │
         ↓
┌────────────────────┐
│  CLI Client        │
│  (Displays text)   │
└────────────────────┘

Output:
  "Here is the analysis:

  [Image: chart.png]
  [File: data.csv (2.1 KB)]

  ⚠️  2 items not fully supported in CLI"
```

## Return Addressing

Each adapter implements `send_to_client()` to route responses back:

```python
class CLIChannelAdapter:
    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """Send message back to CLI client"""
        session_id = reply_to.get("session_id")
        writer = self.clients[session_id]

        # Adapt content to CLI capabilities
        cli_message = self._umf_to_cli(message)

        # Send back through Unix socket
        await self._send_cli_message(writer, cli_message)
```

```python
class SlackChannelAdapter:
    async def send_to_client(self, reply_to: Dict[str, Any], message: P3394Message):
        """Send message back to Slack channel"""
        workspace_id = reply_to.get("workspace_id")
        channel_id = reply_to.get("channel_id")
        thread_ts = reply_to.get("thread_ts")

        # Slack supports images and files - send as multipart
        for content in message.content:
            if content.type == ContentType.TEXT:
                await self.slack_client.chat_postMessage(
                    channel=channel_id,
                    thread_ts=thread_ts,
                    text=content.data
                )
            elif content.type == ContentType.IMAGE:
                await self.slack_client.files_upload(
                    channels=channel_id,
                    file=content.data,
                    thread_ts=thread_ts
                )
```

## Future Enhancements

### 1. Client-Requested Capabilities

Allow clients to specify what they support:

```json
{
  "text": "Send me the report",
  "client_capabilities": {
    "supports_images": true,
    "max_size": 10485760,
    "preferred_format": "markdown"
  }
}
```

### 2. Content Fallback in UMF

Add fallback content directly in UMF messages:

```python
message.add_content_with_fallback(
    primary=P3394Content(
        type=ContentType.IMAGE,
        data=image_bytes,
        metadata={"filename": "chart.png"}
    ),
    fallback=P3394Content(
        type=ContentType.TEXT,
        data="[Chart showing Q4 revenue: +15% growth]"
    )
)
```

### 3. Progressive Enhancement

Send minimal content first, then enhancements:

```python
# Send text immediately
await adapter.send_to_client(reply_to, text_message)

# Then send image if supported
if adapter.capabilities.supports_images:
    await adapter.send_to_client(reply_to, image_message)
```

### 4. Transcoding Services

Add automatic transcoding:
- PDF → Images (for image-only channels)
- Video → Audio (for audio-only channels)
- Large files → Links to download

## Benefits

✅ **Universal Compatibility**: Rich UMF works with limited channels
✅ **Graceful Degradation**: Unsupported content becomes readable text
✅ **Transparency**: Clients know what was dropped/downgraded
✅ **Extensibility**: Easy to add new content types and channels
✅ **User Experience**: Clear feedback about limitations

## Testing

Test content adaptation:

```bash
# Start daemon
uv run ieee3394-agent --daemon

# Terminal 2: Connect CLI client
uv run ieee3394-cli

# Send command that generates rich content
>>> "Create a chart of sales data"

# CLI receives:
# [Text content]
# [Image: sales_chart.png]
# ⚠️  1 item not fully supported in CLI
```

## Summary

The content negotiation system ensures that **P3394's rich message format works seamlessly across channels with different capabilities**, providing automatic adaptation, clear feedback, and graceful degradation when content types are not supported.

This makes the agent truly multi-channel while maintaining the expressiveness of P3394 UMF! 🚀
