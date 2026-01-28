#!/usr/bin/env python3
"""
Test Command Discovery via P3394 Manifest

Demonstrates how a client agent can discover command syntax across channels.
"""

import asyncio
import httpx
import json


async def discover_commands():
    """Fetch and display command syntax from P3394 manifest"""

    base_url = "http://localhost:8101"

    async with httpx.AsyncClient() as client:
        print("🔍 Discovering IEEE 3394 Exemplar Agent...\n")

        # Fetch manifest
        response = await client.get(f"{base_url}/manifest")
        manifest = response.json()

        # Display agent identity
        print(f"📋 Agent: {manifest['name']}")
        print(f"   Version: {manifest['version']}")
        print(f"   P3394 Address: {manifest['address']}")
        print(f"   Protocol: {manifest['protocol']} v{manifest['protocol_version']}\n")

        # Display available channels
        print("📡 Available Channels:")
        for channel in manifest.get('channels', []):
            status = "🟢 Active" if channel['active'] else "🔴 Inactive"
            print(f"   {channel['id']:15} {status:12} {channel['command_syntax']}")
        print()

        # Display commands with syntax variations
        print("🎯 Available Commands:\n")
        for cmd in manifest.get('commands', []):
            print(f"   {cmd['name']}")
            print(f"      {cmd['description']}")

            if cmd.get('requires_auth'):
                print(f"      🔒 Authentication required")

            print(f"      Syntax by channel:")
            for channel_id, syntax in cmd.get('syntax_by_channel', {}).items():
                print(f"         {channel_id:15} → {syntax}")

            if cmd.get('aliases'):
                print(f"      Aliases: {', '.join(cmd['aliases'])}")

            print()

        # Test command execution via different channels
        print("\n🧪 Testing command execution:")

        # Test 1: HTTP-style via P3394 messages endpoint
        print("\n   Test 1: /version via P3394 UMF")
        umf_message = {
            "type": "request",
            "content": [{"type": "text", "data": "/version"}]
        }
        response = await client.post(f"{base_url}/messages", json=umf_message)
        result = response.json()

        if result.get('content'):
            version_text = result['content'][0].get('data', '')
            print(f"   Response: {version_text}")

        # Test 2: /listChannels
        print("\n   Test 2: /listChannels via P3394 UMF")
        umf_message = {
            "type": "request",
            "content": [{"type": "text", "data": "/listChannels"}]
        }
        response = await client.post(f"{base_url}/messages", json=umf_message)
        result = response.json()

        if result.get('content'):
            channels_text = result['content'][0].get('data', '')
            print(f"   Response:\n{channels_text}")


if __name__ == '__main__':
    print("""
╔══════════════════════════════════════════════════════════════╗
║          P3394 Command Discovery Test                        ║
║     Testing channel-aware command routing                    ║
╚══════════════════════════════════════════════════════════════╝
""")

    try:
        asyncio.run(discover_commands())
    except httpx.ConnectError:
        print("❌ Error: Could not connect to P3394 server")
        print("   Make sure the daemon is running:")
        print("   $ uv run ieee3394-agent --daemon --p3394-server")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
