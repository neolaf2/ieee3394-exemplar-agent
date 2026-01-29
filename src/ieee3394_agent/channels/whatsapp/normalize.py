"""
WhatsApp Message Normalization

Converts between WhatsApp message formats and P3394 Universal Message Format (UMF).
Inspired by Moltbot's normalize pattern.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from ...core.umf import (
    P3394Message,
    P3394Content,
    P3394Address,
    ContentType,
    MessageType,
)


def normalize_whatsapp_message(
    whatsapp_msg: Dict[str, Any],
    agent_id: str,
    session_id: Optional[str] = None,
) -> P3394Message:
    """
    Convert a WhatsApp message to P3394 UMF format.

    WhatsApp message structure (from whatsapp-web.js):
    {
        "id": {"fromMe": false, "remote": "1234567890@c.us", "id": "ABC123", "_serialized": "..."},
        "ack": 1,
        "hasMedia": false,
        "body": "Hello, agent!",
        "type": "chat",
        "timestamp": 1706543210,
        "from": "1234567890@c.us",
        "to": "0987654321@c.us",
        "author": "1234567890@c.us",
        "isForwarded": false,
        "broadcast": false,
        "isStatus": false,
        "isGroup": false,
        "hasQuotedMsg": false
    }

    Args:
        whatsapp_msg: Raw WhatsApp message object
        agent_id: This agent's identifier
        session_id: Optional session ID to associate

    Returns:
        P3394Message with normalized content
    """
    # Extract sender information
    sender_id = whatsapp_msg.get("from", "unknown")
    message_id = whatsapp_msg.get("id", {}).get("_serialized", "unknown")

    # Create P3394 address for sender
    source_address = P3394Address(
        agent_id=_normalize_whatsapp_id(sender_id),
        channel_id="whatsapp",
        session_id=session_id,
    )

    # Create P3394 address for this agent
    dest_address = P3394Address(
        agent_id=agent_id,
        channel_id="whatsapp",
        session_id=session_id,
    )

    # Convert timestamp
    timestamp = datetime.fromtimestamp(
        whatsapp_msg.get("timestamp", 0), tz=timezone.utc
    ).isoformat()

    # Determine content type and extract content
    content_blocks = []
    msg_type = whatsapp_msg.get("type", "chat")

    if msg_type == "chat" or msg_type == "text":
        # Text message
        text = whatsapp_msg.get("body", "")
        content_blocks.append(P3394Content(type=ContentType.TEXT, data=text))

    elif msg_type == "image":
        # Image message - include caption if available
        caption = whatsapp_msg.get("caption", "")
        if caption:
            content_blocks.append(
                P3394Content(type=ContentType.TEXT, data=f"[Image] {caption}")
            )

        # Add file reference if media is available
        if whatsapp_msg.get("hasMedia"):
            content_blocks.append(
                P3394Content(
                    type=ContentType.FILE,
                    mime_type="image/jpeg",  # WhatsApp typically uses JPEG
                    metadata={
                        "filename": f"whatsapp_image_{message_id}.jpg",
                        "media_key": whatsapp_msg.get("mediaKey"),
                        "caption": caption,
                    },
                )
            )

    elif msg_type == "document":
        # Document attachment
        filename = whatsapp_msg.get("filename", "document")
        mime_type = whatsapp_msg.get("mimetype", "application/octet-stream")

        content_blocks.append(
            P3394Content(
                type=ContentType.FILE,
                mime_type=mime_type,
                metadata={
                    "filename": filename,
                    "media_key": whatsapp_msg.get("mediaKey"),
                    "size": whatsapp_msg.get("filesize", 0),
                },
            )
        )

        # Include caption as text if present
        caption = whatsapp_msg.get("caption", "")
        if caption:
            content_blocks.append(P3394Content(type=ContentType.TEXT, data=caption))

    elif msg_type == "audio" or msg_type == "ptt":  # ptt = push-to-talk voice note
        content_blocks.append(
            P3394Content(
                type=ContentType.FILE,
                mime_type="audio/ogg",
                metadata={
                    "filename": f"whatsapp_audio_{message_id}.ogg",
                    "media_key": whatsapp_msg.get("mediaKey"),
                    "is_voice_note": msg_type == "ptt",
                },
            )
        )

    elif msg_type == "video":
        caption = whatsapp_msg.get("caption", "")
        if caption:
            content_blocks.append(
                P3394Content(type=ContentType.TEXT, data=f"[Video] {caption}")
            )

        content_blocks.append(
            P3394Content(
                type=ContentType.FILE,
                mime_type="video/mp4",
                metadata={
                    "filename": f"whatsapp_video_{message_id}.mp4",
                    "media_key": whatsapp_msg.get("mediaKey"),
                    "caption": caption,
                },
            )
        )

    elif msg_type == "location":
        # Location message
        latitude = whatsapp_msg.get("latitude", 0)
        longitude = whatsapp_msg.get("longitude", 0)
        location_name = whatsapp_msg.get("location", {}).get("name", "")

        location_text = f"📍 Location: {location_name}\n" if location_name else "📍 Location\n"
        location_text += f"Lat: {latitude}, Lon: {longitude}"

        content_blocks.append(P3394Content(type=ContentType.TEXT, data=location_text))

    else:
        # Fallback for unknown message types
        content_blocks.append(
            P3394Content(
                type=ContentType.TEXT,
                data=f"[Unsupported message type: {msg_type}]",
            )
        )

    # Add metadata about the WhatsApp message
    metadata = {
        "platform": "whatsapp",
        "whatsapp_id": message_id,
        "is_forwarded": whatsapp_msg.get("isForwarded", False),
        "is_group": whatsapp_msg.get("isGroup", False),
        "ack_status": whatsapp_msg.get("ack", 0),
    }

    # If it's a group message, add group info
    if whatsapp_msg.get("isGroup"):
        metadata["group_id"] = whatsapp_msg.get("from")
        metadata["author"] = whatsapp_msg.get("author")

    # If it's a quoted/reply message, add reply info
    if whatsapp_msg.get("hasQuotedMsg"):
        quoted_msg = whatsapp_msg.get("quotedMsg", {})
        metadata["reply_to"] = quoted_msg.get("id", {}).get("_serialized")

    return P3394Message(
        id=message_id,
        type=MessageType.REQUEST,
        timestamp=timestamp,
        source=source_address,
        destination=dest_address,
        content=content_blocks,
        session_id=session_id,
        metadata=metadata,
    )


def normalize_umf_to_whatsapp(
    umf_message: P3394Message,
    target_chat_id: str,
) -> Dict[str, Any]:
    """
    Convert a P3394 UMF message to WhatsApp send format.

    Args:
        umf_message: P3394 message to convert
        target_chat_id: WhatsApp chat ID (e.g., "1234567890@c.us")

    Returns:
        Dictionary with WhatsApp send parameters
    """
    whatsapp_params = {"chatId": target_chat_id}

    # Extract text content
    text_parts = []
    media_content = None

    for content_block in umf_message.content:
        if content_block.type == ContentType.TEXT:
            text_parts.append(content_block.data)

        elif content_block.type == ContentType.MARKDOWN:
            # Convert markdown to WhatsApp formatted text
            formatted = _convert_markdown_to_whatsapp(content_block.data)
            text_parts.append(formatted)

        elif content_block.type == ContentType.FILE:
            # Handle file attachments
            media_content = {
                "mime_type": content_block.mime_type,
                "filename": content_block.metadata.get("filename", "file"),
                "url": content_block.metadata.get("url") or content_block.metadata.get("path"),
                "caption": content_block.metadata.get("caption", ""),
            }

    # Combine text content
    if text_parts:
        whatsapp_params["content"] = "\n\n".join(text_parts)

    # Add media if present
    if media_content:
        whatsapp_params["media"] = media_content
        if media_content["caption"]:
            whatsapp_params["caption"] = media_content["caption"]

    # Add reply reference if present
    if umf_message.reply_to:
        whatsapp_params["quotedMessageId"] = umf_message.reply_to

    # Add metadata
    whatsapp_params["messageMetadata"] = {
        "umf_id": umf_message.id,
        "timestamp": umf_message.timestamp,
    }

    return whatsapp_params


def _normalize_whatsapp_id(whatsapp_id: str) -> str:
    """
    Convert WhatsApp ID to agent-friendly format.

    Examples:
        "1234567890@c.us" -> "whatsapp:1234567890"
        "123456789@g.us" -> "whatsapp:group:123456789"
    """
    if "@g.us" in whatsapp_id:
        # Group chat
        number = whatsapp_id.split("@")[0]
        return f"whatsapp:group:{number}"
    elif "@c.us" in whatsapp_id:
        # Individual chat
        number = whatsapp_id.split("@")[0]
        return f"whatsapp:{number}"
    else:
        return f"whatsapp:{whatsapp_id}"


def _convert_markdown_to_whatsapp(markdown: str) -> str:
    """
    Convert markdown to WhatsApp formatting.

    WhatsApp supports:
    - *bold*
    - _italic_
    - ~strikethrough~
    - ```monospace```

    Args:
        markdown: Markdown text

    Returns:
        WhatsApp-formatted text
    """
    import re

    text = markdown

    # Bold: **text** or __text__ -> *text*
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    text = re.sub(r"__(.+?)__", r"*\1*", text)

    # Italic: *text* or _text_ -> _text_
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"_\1_", text)

    # Strikethrough: ~~text~~ -> ~text~
    text = re.sub(r"~~(.+?)~~", r"~\1~", text)

    # Code: `text` -> ```text```
    text = re.sub(r"`(.+?)`", r"```\1```", text)

    # Remove unsupported markdown
    text = re.sub(r"^#+\s+", "", text, flags=re.MULTILINE)  # Headers

    return text
