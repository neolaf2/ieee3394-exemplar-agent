"""
Quick test of CLI client connecting to CLI channel adapter
"""

import asyncio
from src.ieee3394_agent.cli_client import CLIClient


async def test_cli():
    """Test CLI client"""
    print("\n" + "="*60)
    print("Testing CLI Client → CLI Channel Adapter → Gateway")
    print("="*60)

    # Create client
    client = CLIClient(socket_path="/tmp/ieee3394-agent-cli.sock")

    # Connect
    print("\n1. Connecting to CLI channel...")
    await client.connect()
    print(f"   ✓ Connected")
    print(f"   Session ID: {client.session_id}")
    print(f"   Agent: {client.agent_name} v{client.agent_version}")

    # Test commands
    commands = [
        "/help",
        "/about",
        "/status",
        "/version",
        "/listCommands",
        "Hello, what is P3394?"
    ]

    for i, cmd in enumerate(commands, 2):
        print(f"\n{i}. Sending: {cmd}")
        response = await client.send_message(cmd)

        print(f"   Response type: {response.get('type')}")
        print(f"   Message ID: {response.get('message_id')}")

        text = response.get('text', '')
        if text:
            # Show first 150 chars
            preview = text[:150].replace('\n', ' ')
            if len(text) > 150:
                preview += "..."
            print(f"   Text: {preview}")

    # Disconnect
    print(f"\n{len(commands) + 2}. Disconnecting...")
    await client.disconnect()
    print("   ✓ Disconnected")

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_cli())
