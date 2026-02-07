"""
Test P3394 Agent-to-Agent Communication

Tests the P3394 server and client adapters for agent-to-agent communication.
"""

import asyncio
from src.ieee3394_agent.channels.p3394_client import P3394ClientAdapter
from src.ieee3394_agent.core.gateway_sdk import AgentGateway
from src.ieee3394_agent.memory.kstar import KStarMemory
from src.ieee3394_agent.core.storage import AgentStorage
from src.ieee3394_agent.core.umf import P3394Message, P3394Content, ContentType, P3394Address


async def test_p3394_agent():
    """Test P3394 agent-to-agent communication"""
    print("\n" + "="*60)
    print("Testing P3394 Agent-to-Agent Communication (SDK)")
    print("="*60)

    # Initialize a mock gateway for the client (SDK version)
    storage = AgentStorage(agent_name="test-client-agent")
    kstar = KStarMemory(storage=storage)
    gateway = AgentGateway(memory=kstar, working_dir=storage.base_dir)
    await gateway.initialize()  # Load skills

    # Create P3394 client
    client = P3394ClientAdapter(gateway)

    # Target agent (running daemon)
    target_url = "http://localhost:8101"

    print(f"\n1. Discovering agent at {target_url}...")
    try:
        manifest = await client.discover(target_url)

        print(f"   ✓ Discovered agent:")
        print(f"   - Name: {manifest.get('name')}")
        print(f"   - Agent ID: {manifest.get('agent_id')}")
        print(f"   - Version: {manifest.get('version')}")
        print(f"   - Protocol: {manifest.get('protocol')} v{manifest.get('protocol_version')}")
        print(f"   - Address: {manifest.get('address')}")

        print(f"\n   Capabilities:")
        capabilities = manifest.get('capabilities', {})
        print(f"   - Symbolic commands: {len(capabilities.get('symbolic_commands', []))}")
        print(f"   - LLM enabled: {capabilities.get('llm_enabled')}")
        print(f"   - Streaming: {capabilities.get('streaming')}")
        print(f"   - Tools: {len(capabilities.get('tools', []))}")
        print(f"   - Subagents: {capabilities.get('subagents', [])}")

        print(f"\n   Endpoints:")
        endpoints = manifest.get('endpoints', {})
        for key, url in endpoints.items():
            print(f"   - {key}: {url}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print(f"\n2. Sending P3394 UMF message...")
    try:
        # Create a UMF message
        message = P3394Message.text("/version")
        message.source = P3394Address(
            agent_id="test-client-agent",
            channel_id="p3394-client"
        )

        # Send to target agent
        response = await client.send(message, target_url=target_url)

        print(f"   ✓ Response received:")
        print(f"   - Message ID: {response.id}")
        print(f"   - Type: {response.type.value}")
        print(f"   - Reply to: {response.reply_to}")

        # Extract text
        for content in response.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                print(f"   - Content: {content.data}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print(f"\n3. Sending text message using convenience method...")
    try:
        response = await client.send_to_agent(
            agent_id="ieee3394-exemplar",
            text="What is P3394?",
            base_url=target_url
        )

        print(f"   ✓ Response received:")
        print(f"   - Message ID: {response.id}")

        # Extract text (preview)
        for content in response.content:
            if content.type in [ContentType.TEXT, ContentType.MARKDOWN]:
                preview = content.data[:200].replace('\n', ' ')
                if len(content.data) > 200:
                    preview += "..."
                print(f"   - Content: {preview}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print(f"\n4. Getting agent capabilities...")
    try:
        capabilities = await client.get_agent_capabilities(target_url)

        print(f"   ✓ Capabilities retrieved:")
        print(f"   - Symbolic commands: {capabilities.get('symbolic_commands', [])[:5]}...")
        print(f"   - LLM enabled: {capabilities.get('llm_enabled')}")
        print(f"   - Tools: {capabilities.get('tools', [])}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print(f"\n5. Testing P3394 addressing...")
    try:
        # Test address parsing
        address_str = "p3394://ieee3394-exemplar/p3394-server?session=test-123"
        address = P3394Address.from_uri(address_str)

        print(f"   ✓ Parsed address:")
        print(f"   - Agent ID: {address.agent_id}")
        print(f"   - Channel ID: {address.channel_id}")
        print(f"   - Session ID: {address.session_id}")
        print(f"   - URI: {address.to_uri()}")

    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Cleanup
    await client.close()

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_p3394_agent())
