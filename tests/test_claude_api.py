#!/usr/bin/env python3
"""
Test Claude API Channel

Quick test to verify the Claude API channel is working.
"""

import anthropic
import sys

def test_claude_api():
    """Test the Claude API channel"""

    print("🧪 Testing Claude API Channel")
    print("=" * 60)

    # Connect to local agent
    client = anthropic.Anthropic(
        api_key="test-key",
        base_url="http://localhost:8100",
        timeout=30.0
    )

    # Test 1: Basic message
    print("\n📝 Test 1: Basic Message")
    print("-" * 60)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "What skills do you have?"}
            ]
        )

        print(f"✓ Response received ({len(message.content[0].text)} chars)")
        print(f"\n{message.content[0].text[:300]}...")

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 2: IEEE WG Manager skill
    print("\n\n📊 Test 2: IEEE WG Manager Skill")
    print("-" * 60)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {
                    "role": "user",
                    "content": "Help me calculate ballot results: 30 Approve, 5 Disapprove, 10 Abstain out of 50 invitations. Did it pass?"
                }
            ]
        )

        response_text = message.content[0].text
        print(f"✓ Skill response received")

        # Check if skill provided calculation
        if "75%" in response_text or "85" in response_text:
            print("✓ Skill calculated approval rate correctly!")

        print(f"\n{response_text[:400]}...")

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: Streaming
    print("\n\n🌊 Test 3: Streaming Response")
    print("-" * 60)
    try:
        print("Response: ", end="", flush=True)

        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=512,
            messages=[
                {"role": "user", "content": "What is the P3394 Universal Message Format?"}
            ]
        ) as stream:
            char_count = 0
            for text in stream.text_stream:
                print(text, end="", flush=True)
                char_count += len(text)

        print(f"\n\n✓ Streaming works! Received {char_count} characters")

    except Exception as e:
        print(f"\n✗ Streaming failed: {e}")
        return False

    print("\n\n" + "=" * 60)
    print("🎉 All Claude API tests passed!")
    print("=" * 60)
    print("\nYour agent is accessible via:")
    print("  • HTTP API: http://localhost:8100")
    print("  • Compatible with: Anthropic Python SDK, curl, any HTTP client")
    print("  • Authentication: Disabled for testing (any API key works)")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_claude_api()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        sys.exit(1)
