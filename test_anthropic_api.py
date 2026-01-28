"""
Test Anthropic API Server Adapter

Tests the Anthropic API server adapter using the Anthropic SDK client.
"""

import asyncio
from anthropic import AsyncAnthropic


async def test_anthropic_api():
    """Test Anthropic API server adapter"""
    print("\n" + "="*60)
    print("Testing Anthropic API Server Adapter")
    print("="*60)

    # Create client pointing to our agent (not real Anthropic API)
    # Use empty API key for testing
    client = AsyncAnthropic(
        api_key="test-key-12345",  # Agent-issued key (or blank for testing)
        base_url="http://localhost:8100"  # Our agent's Anthropic API endpoint
    )

    print("\n1. Testing non-streaming message...")
    try:
        message = await client.messages.create(
            model="ieee-3394-agent",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "Hello, what is P3394?"}
            ]
        )

        print(f"   ✓ Response received")
        print(f"   Message ID: {message.id}")
        print(f"   Model: {message.model}")
        print(f"   Stop Reason: {message.stop_reason}")
        print(f"   Usage: {message.usage.input_tokens} in, {message.usage.output_tokens} out")
        print(f"\n   Response:")
        for block in message.content:
            if hasattr(block, 'text'):
                preview = block.text[:200].replace('\n', ' ')
                if len(block.text) > 200:
                    preview += "..."
                print(f"   {preview}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print("\n2. Testing streaming message...")
    try:
        stream = await client.messages.create(
            model="ieee-3394-agent",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "What are the main components of P3394?"}
            ],
            stream=True
        )

        print("   ✓ Streaming response:")
        print("   ", end="")
        async for event in stream:
            if event.type == "content_block_delta":
                if hasattr(event.delta, 'text'):
                    print(event.delta.text, end="", flush=True)
        print("\n")

    except Exception as e:
        print(f"   ✗ Streaming error: {e}")
        return

    print("\n3. Testing multiple messages (conversation)...")
    try:
        message = await client.messages.create(
            model="ieee-3394-agent",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "What is UMF?"},
                {"role": "assistant", "content": "UMF stands for Universal Message Format."},
                {"role": "user", "content": "What are its main components?"}
            ]
        )

        print(f"   ✓ Response received")
        print(f"   Response:")
        for block in message.content:
            if hasattr(block, 'text'):
                preview = block.text[:200].replace('\n', ' ')
                if len(block.text) > 200:
                    preview += "..."
                print(f"   {preview}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print("\n4. Testing system prompt...")
    try:
        message = await client.messages.create(
            model="ieee-3394-agent",
            max_tokens=1024,
            system="You are an expert on agent interoperability standards.",
            messages=[
                {"role": "user", "content": "Why is P3394 important?"}
            ]
        )

        print(f"   ✓ Response received")
        print(f"   Response:")
        for block in message.content:
            if hasattr(block, 'text'):
                preview = block.text[:200].replace('\n', ' ')
                if len(block.text) > 200:
                    preview += "..."
                print(f"   {preview}")

    except Exception as e:
        print(f"   ✗ Error: {e}")
        return

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_anthropic_api())
