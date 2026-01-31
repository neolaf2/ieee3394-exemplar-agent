"""
P3394 Agent Client Channel Adapter

Makes outbound calls to other P3394-compliant agents.
Discovers agent manifests and formats messages with proper P3394 addressing.
"""

import logging
from typing import Optional, Dict, Any
import httpx

from ..core.umf import P3394Message, P3394Content, ContentType, MessageType, P3394Address
from ..core.gateway_sdk import AgentGateway

logger = logging.getLogger(__name__)


class P3394ClientAdapter:
    """
    P3394 Agent Client Channel Adapter

    Makes outbound calls to other P3394-compliant agents.

    Usage:
        client = P3394ClientAdapter(gateway)

        # Discover agent
        manifest = await client.discover("http://other-agent:8101")

        # Send message
        response = await client.send(umf_message, target_address="p3394://other-agent/channel")
    """

    def __init__(self, gateway: AgentGateway):
        self.gateway = gateway
        self.channel_id = "p3394-client"

        # Our agent's P3394 address
        self.agent_address = P3394Address(
            agent_id=gateway.AGENT_ID,
            channel_id=self.channel_id
        )

        # HTTP client for P3394 requests
        self.client = httpx.AsyncClient(
            timeout=60.0,
            headers={
                "Content-Type": "application/json",
                "x-p3394-client": self.agent_address.to_uri()
            }
        )

        # Cache of discovered agent manifests
        self.manifests: Dict[str, Dict[str, Any]] = {}

    async def discover(self, base_url: str) -> Dict[str, Any]:
        """
        Discover a P3394 agent by fetching its manifest.

        Args:
            base_url: Base URL of the target agent (e.g., "http://agent:8101")

        Returns:
            Agent manifest dictionary
        """
        try:
            manifest_url = f"{base_url.rstrip('/')}/manifest"
            logger.info(f"Discovering P3394 agent at: {manifest_url}")

            response = await self.client.get(manifest_url)
            response.raise_for_status()

            manifest = response.json()

            # Cache manifest by agent_id
            agent_id = manifest.get("agent_id")
            if agent_id:
                self.manifests[agent_id] = manifest
                logger.info(f"Discovered agent: {manifest.get('name')} ({agent_id})")

            return manifest

        except Exception as e:
            logger.exception(f"Error discovering P3394 agent at {base_url}: {e}")
            raise

    async def send(
        self,
        message: P3394Message,
        target_address: Optional[str] = None,
        target_url: Optional[str] = None
    ) -> P3394Message:
        """
        Send a P3394 UMF message to another agent.

        Args:
            message: P3394 UMF message to send
            target_address: P3394 address (e.g., "p3394://agent-id/channel")
            target_url: Base URL if manifest not cached (e.g., "http://agent:8101")

        Returns:
            P3394 UMF response message
        """
        # Set source address
        if not message.source:
            message.source = self.agent_address

        # Parse target address
        if target_address:
            target_addr = P3394Address.from_uri(target_address)
            message.destination = target_addr

            # Get manifest if not cached
            if target_addr.agent_id not in self.manifests and target_url:
                await self.discover(target_url)

            # Get endpoint from manifest
            manifest = self.manifests.get(target_addr.agent_id)
            if manifest:
                endpoint = manifest.get("endpoints", {}).get("messages")
                if not endpoint:
                    raise ValueError(f"No messages endpoint in manifest for {target_addr.agent_id}")
            else:
                if not target_url:
                    raise ValueError(f"No manifest cached for {target_addr.agent_id} and no target_url provided")
                endpoint = f"{target_url.rstrip('/')}/messages"

        elif target_url:
            # Use target_url directly
            endpoint = f"{target_url.rstrip('/')}/messages"
        else:
            raise ValueError("Either target_address or target_url must be provided")

        try:
            logger.info(f"Sending P3394 message to: {endpoint}")

            # Send UMF message
            response = await self.client.post(
                endpoint,
                json=message.to_dict()
            )

            response.raise_for_status()
            response_data = response.json()

            # Parse response as UMF
            umf_response = P3394Message.from_dict(response_data)

            logger.info(f"Received P3394 response: {umf_response.id}")

            return umf_response

        except httpx.HTTPStatusError as e:
            logger.error(f"P3394 HTTP error: {e.response.status_code} - {e.response.text}")
            return P3394Message(
                type=MessageType.ERROR,
                reply_to=message.id,
                content=[P3394Content(
                    type=ContentType.TEXT,
                    data=f"P3394 error: {e.response.status_code} - {e.response.text}"
                )]
            )

        except Exception as e:
            logger.exception(f"Error sending P3394 message: {e}")
            return P3394Message(
                type=MessageType.ERROR,
                reply_to=message.id,
                content=[P3394Content(
                    type=ContentType.TEXT,
                    data=f"Error sending P3394 message: {str(e)}"
                )]
            )

    async def send_to_agent(
        self,
        agent_id: str,
        text: str,
        base_url: Optional[str] = None
    ) -> P3394Message:
        """
        Convenience method to send a text message to another agent.

        Args:
            agent_id: Target agent ID
            text: Text message to send
            base_url: Base URL if manifest not cached

        Returns:
            P3394 UMF response
        """
        # Create UMF message
        message = P3394Message.text(text)

        # Build target address
        target_address = f"p3394://{agent_id}"

        return await self.send(
            message,
            target_address=target_address,
            target_url=base_url
        )

    async def get_agent_capabilities(
        self,
        base_url: str
    ) -> Dict[str, Any]:
        """
        Get an agent's capabilities from its manifest.

        Args:
            base_url: Base URL of the target agent

        Returns:
            Capabilities dictionary
        """
        manifest = await self.discover(base_url)
        return manifest.get("capabilities", {})

    async def close(self):
        """Close the HTTP client"""
        await self.client.aclose()
