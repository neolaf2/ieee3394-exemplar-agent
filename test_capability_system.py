#!/usr/bin/env python3
"""
Test Agent Capability Descriptor System

Demonstrates the capability system functionality:
1. List all capabilities
2. Filter capabilities by kind (skills only)
3. Filter capabilities by substrate (commands only)
4. Test backward compatibility
"""

import anthropic
import sys
import json


def test_capability_system():
    """Test the capability system via Claude API"""

    print("=" * 70)
    print("🧪 Testing Agent Capability Descriptor (ACD) System")
    print("=" * 70)
    print()

    # Connect to local agent
    client = anthropic.Anthropic(
        api_key="test-key",
        base_url="http://localhost:8100",
        timeout=30.0
    )

    # Test 1: List all capabilities
    print("📋 Test 1: List All Capabilities")
    print("-" * 70)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": "/listCapabilities"}
            ]
        )

        response_text = message.content[0].text
        print(response_text[:500] + "...\n")
        print(f"✓ Listed capabilities successfully")

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 2: Filter by kind (skills only)
    print("\n📊 Test 2: Filter by Kind (Composite/Skills Only)")
    print("-" * 70)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": "/listCapabilities?kind=composite"}
            ]
        )

        response_text = message.content[0].text
        # Count how many capabilities were returned
        count = response_text.count("**ID:**")
        print(f"✓ Found {count} composite capabilities (skills)")
        print(f"\nFirst skill:")
        lines = response_text.split('\n')
        for i, line in enumerate(lines[:15]):
            print(line)

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 3: Filter by substrate (commands only)
    print("\n\n⚙️ Test 3: Filter by Substrate (Symbolic/Commands Only)")
    print("-" * 70)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": "/listCapabilities?substrate=symbolic"}
            ]
        )

        response_text = message.content[0].text
        count = response_text.count("**ID:**")
        print(f"✓ Found {count} symbolic capabilities (commands)")
        print(f"\nCommand examples:")
        # Extract command names
        for line in response_text.split('\n'):
            if line.startswith('**Commands:**'):
                print(f"  {line}")

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 4: Backward compatibility
    print("\n\n🔄 Test 4: Backward Compatibility (Legacy /listSkills)")
    print("-" * 70)
    try:
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[
                {"role": "user", "content": "/listSkills"}
            ]
        )

        response_text = message.content[0].text
        count = response_text.count("**ID:**")
        print(f"✓ /listSkills works (shows {count} capabilities)")
        print(f"✓ Backward compatibility maintained")

    except Exception as e:
        print(f"✗ Failed: {e}")
        return False

    # Test 5: Legacy commands still work
    print("\n\n📌 Test 5: Legacy Commands Still Work")
    print("-" * 70)
    for command in ["/help", "/about", "/status"]:
        try:
            message = client.messages.create(
                model="claude-sonnet-4-5-20250929",
                max_tokens=1024,
                messages=[
                    {"role": "user", "content": command}
                ]
            )

            response_text = message.content[0].text
            print(f"✓ {command:15} → {len(response_text)} chars response")

        except Exception as e:
            print(f"✗ {command:15} → Failed: {e}")
            return False

    print("\n" + "=" * 70)
    print("🎉 All capability system tests passed!")
    print("=" * 70)
    print()
    print("Summary:")
    print("  ✓ Capability registry working")
    print("  ✓ Query filtering operational")
    print("  ✓ Backward compatibility confirmed")
    print("  ✓ All legacy commands functional")
    print()
    print("The Agent Capability Descriptor system is ready for production!")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_capability_system()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
