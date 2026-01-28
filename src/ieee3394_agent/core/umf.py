"""
P3394 Universal Message Format (UMF)

This module implements the IEEE P3394 Universal Message Format,
the canonical message structure for all agent communication.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
from uuid import uuid4
from enum import Enum


class MessageType(str, Enum):
    """P3394 message types"""
    REQUEST = "request"
    RESPONSE = "response"
    NOTIFICATION = "notification"
    ERROR = "error"


class ContentType(str, Enum):
    """P3394 content types"""
    TEXT = "text"
    JSON = "json"
    MARKDOWN = "markdown"
    HTML = "html"
    BINARY = "binary"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"


@dataclass
class P3394Address:
    """
    Agent addressing per P3394.

    Format: p3394://{agent_id}/{channel_id}?session={session_id}
    """
    agent_id: str
    channel_id: Optional[str] = None
    session_id: Optional[str] = None

    def to_uri(self) -> str:
        """Convert to P3394 URI format"""
        uri = f"p3394://{self.agent_id}"
        if self.channel_id:
            uri += f"/{self.channel_id}"
        if self.session_id:
            uri += f"?session={self.session_id}"
        return uri

    @classmethod
    def from_uri(cls, uri: str) -> "P3394Address":
        """Parse P3394 URI"""
        if not uri.startswith("p3394://"):
            raise ValueError(f"Invalid P3394 URI: {uri}")

        # Remove protocol
        path = uri[8:]  # len("p3394://") = 8

        # Extract session if present
        session_id = None
        if "?session=" in path:
            path, session_part = path.split("?session=", 1)
            session_id = session_part

        # Extract agent_id and channel_id
        parts = path.split("/")
        agent_id = parts[0]
        channel_id = parts[1] if len(parts) > 1 else None

        return cls(agent_id=agent_id, channel_id=channel_id, session_id=session_id)


@dataclass
class P3394Content:
    """Message content block"""
    type: ContentType
    data: Any
    mime_type: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class P3394Message:
    """
    IEEE P3394 Universal Message Format

    This is the canonical message structure for all agent communication.
    All channel adapters transform their native formats to/from this structure.
    """
    # Header
    id: str = field(default_factory=lambda: str(uuid4()))
    type: MessageType = MessageType.REQUEST
    timestamp: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Addressing
    source: Optional[P3394Address] = None
    destination: Optional[P3394Address] = None
    reply_to: Optional[str] = None  # Message ID for threading

    # Content
    content: List[P3394Content] = field(default_factory=list)

    # Context
    session_id: Optional[str] = None
    conversation_id: Optional[str] = None

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary"""
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp,
            "source": self.source.to_uri() if self.source else None,
            "destination": self.destination.to_uri() if self.destination else None,
            "reply_to": self.reply_to,
            "content": [
                {
                    "type": c.type.value,
                    "data": c.data,
                    "mime_type": c.mime_type,
                    "metadata": c.metadata
                }
                for c in self.content
            ],
            "session_id": self.session_id,
            "conversation_id": self.conversation_id,
            "metadata": self.metadata
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "P3394Message":
        """Deserialize from dictionary"""
        # Parse addresses
        source = P3394Address.from_uri(data["source"]) if data.get("source") else None
        destination = (
            P3394Address.from_uri(data["destination"]) if data.get("destination") else None
        )

        # Parse content blocks
        content = [
            P3394Content(
                type=ContentType(c["type"]),
                data=c["data"],
                mime_type=c.get("mime_type"),
                metadata=c.get("metadata", {})
            )
            for c in data.get("content", [])
        ]

        return cls(
            id=data.get("id", str(uuid4())),
            type=MessageType(data.get("type", "request")),
            timestamp=data.get("timestamp", datetime.now(timezone.utc).isoformat()),
            source=source,
            destination=destination,
            reply_to=data.get("reply_to"),
            content=content,
            session_id=data.get("session_id"),
            conversation_id=data.get("conversation_id"),
            metadata=data.get("metadata", {})
        )

    @classmethod
    def text(cls, text: str, **kwargs) -> "P3394Message":
        """Convenience constructor for text messages"""
        return cls(
            content=[P3394Content(type=ContentType.TEXT, data=text)],
            **kwargs
        )

    def extract_text(self) -> str:
        """Extract first text content from message"""
        for c in self.content:
            if c.type == ContentType.TEXT:
                return c.data
        return ""


@dataclass
class P3394Error:
    """Standard error format"""
    code: str
    message: str
    details: Optional[Dict[str, Any]] = None
