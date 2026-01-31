"""
Anthropic API Client Channel Adapter

Translates P3394 UMF messages to Anthropic API format for outbound calls.
Allows the agent to call external Anthropic API.
"""

import logging
import os
from typing import Optional, Dict, Any, List
import httpx

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType

logger = logging.getLogger(__name__)


class AnthropicAPIClientAdapter:
    """
    Anthropic API Client Channel Adapter

    Transforms P3394 UMF messages to Anthropic API requests.

    Agent sends UMF:
        P3394Message(type=REQUEST, content=[...])

    Adapter transforms to Anthropic API:
        POST https://api.anthropic.com/v1/messages
        {
            "model": "claude-3-5-sonnet-20241022",
            "messages": [{"role": "user", "content": "Hello"}],
            "max_tokens": 1024
        }

    Anthropic API returns:
        {"id": "msg_...", "content": [{"text": "Response"}], ...}

    Adapter transforms back to UMF:
        P3394Message(type=RESPONSE, content=[...])
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: str = "https://api.anthropic.com",
        default_model: str = "claude-3-5-sonnet-20241022",
        default_max_tokens: int = 4096
    ):
        self.channel_id = "anthropic-api-client"
        self.api_key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        self.api_url = api_url
        self.default_model = default_model
        self.default_max_tokens = default_max_tokens

        if not self.api_key:
            logger.warning("No Anthropic API key provided - client adapter will not work")

        self.client = httpx.AsyncClient(
            base_url=api_url,
            headers={
                "x-api-key": self.api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            },
            timeout=60.0
        )

    async def send(self, umf_message: P3394Message) -> P3394Message:
        """
        Send a UMF message via Anthropic API.

        Args:
            umf_message: P3394 message to send

        Returns:
            P3394 message containing the API response
        """
        if not self.api_key:
            return P3394Message(
                type=MessageType.ERROR,
                reply_to=umf_message.id,
                content=[P3394Content(
                    type=ContentType.TEXT,
                    data="Anthropic API key not configured"
                )]
            )

        try:
            # Transform UMF to Anthropic API request
            api_request = self._umf_to_anthropic(umf_message)

            logger.info(f"Sending request to Anthropic API: {api_request.get('model')}")

            # Make API call
            response = await self.client.post(
                "/v1/messages",
                json=api_request
            )

            response.raise_for_status()
            api_response = response.json()

            logger.info(f"Received response from Anthropic API: {api_response.get('id')}")

            # Transform Anthropic API response to UMF
            umf_response = self._anthropic_to_umf(api_response, umf_message.id)

            return umf_response

        except httpx.HTTPStatusError as e:
            logger.error(f"Anthropic API HTTP error: {e.response.status_code} - {e.response.text}")
            return P3394Message(
                type=MessageType.ERROR,
                reply_to=umf_message.id,
                content=[P3394Content(
                    type=ContentType.TEXT,
                    data=f"Anthropic API error: {e.response.status_code} - {e.response.text}"
                )]
            )

        except Exception as e:
            logger.exception(f"Error calling Anthropic API: {e}")
            return P3394Message(
                type=MessageType.ERROR,
                reply_to=umf_message.id,
                content=[P3394Content(
                    type=ContentType.TEXT,
                    data=f"Error calling Anthropic API: {str(e)}"
                )]
            )

    def _umf_to_anthropic(self, umf_message: P3394Message) -> Dict[str, Any]:
        """
        Transform P3394 UMF to Anthropic API request format.

        UMF format:
            P3394Message(
                type=REQUEST,
                content=[P3394Content(type=TEXT, data="Hello")],
                metadata={"model": "...", "max_tokens": ...}
            )

        Anthropic format:
            {
                "model": "claude-3-5-sonnet-20241022",
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 1024,
                "system": "...",
                "temperature": 1.0
            }
        """
        # Extract text content
        text_parts = []
        system_prompt = None

        for content in umf_message.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                text_parts.append(content.data)

                # Check for system prompt in metadata
                if content.metadata.get("role") == "system":
                    system_prompt = content.data
                    text_parts.pop()  # Remove from user messages

        user_message = "\n\n".join(text_parts)

        # Get model and parameters from metadata
        metadata = umf_message.metadata or {}
        model = metadata.get("model", self.default_model)
        max_tokens = metadata.get("max_tokens", self.default_max_tokens)
        temperature = metadata.get("temperature", 1.0)

        # Build Anthropic API request
        api_request = {
            "model": model,
            "max_tokens": max_tokens,
            "messages": [
                {
                    "role": "user",
                    "content": user_message
                }
            ]
        }

        if system_prompt:
            api_request["system"] = system_prompt

        if temperature is not None:
            api_request["temperature"] = temperature

        return api_request

    def _anthropic_to_umf(
        self,
        api_response: Dict[str, Any],
        reply_to: str
    ) -> P3394Message:
        """
        Transform Anthropic API response to P3394 UMF.

        Anthropic format:
            {
                "id": "msg_01XFDUDYJgAACzvnptvVoYEL",
                "type": "message",
                "role": "assistant",
                "content": [{"type": "text", "text": "Hello!"}],
                "model": "claude-3-5-sonnet-20241022",
                "stop_reason": "end_turn",
                "usage": {"input_tokens": 10, "output_tokens": 20}
            }

        UMF format:
            P3394Message(
                type=RESPONSE,
                content=[P3394Content(type=TEXT, data="Hello!")],
                reply_to="original_message_id"
            )
        """
        # Extract text from content blocks
        text_parts = []
        for content_block in api_response.get("content", []):
            if content_block.get("type") == "text":
                text_parts.append(content_block.get("text", ""))

        response_text = "\n\n".join(text_parts)

        # Create UMF response
        return P3394Message(
            type=MessageType.RESPONSE,
            reply_to=reply_to,
            content=[P3394Content(
                type=ContentType.TEXT,
                data=response_text
            )],
            metadata={
                "anthropic_message_id": api_response.get("id"),
                "model": api_response.get("model"),
                "stop_reason": api_response.get("stop_reason"),
                "usage": api_response.get("usage"),
                "source_api": "anthropic"
            }
        )

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
