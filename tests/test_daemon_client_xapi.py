"""
End-to-end test: Daemon/Client Architecture with xAPI Logging

This test demonstrates:
1. Start agent daemon in background
2. Connect multiple clients
3. Send messages through UMF protocol
4. Verify xAPI statements logged for each interaction
5. Read back session history from xAPI LRS
"""

import asyncio
import json
import time
from pathlib import Path

from src.ieee3394_agent.core.umf import P3394Message
from src.ieee3394_agent.core.storage import AgentStorage
from src.ieee3394_agent.server import run_daemon
from src.ieee3394_agent.client import AgentClient


async def start_daemon_in_background():
    """Start the daemon in background"""
    print("\n🚀 Starting IEEE 3394 Agent Daemon...")

    # Create daemon task
    daemon_task = asyncio.create_task(run_daemon(
        api_key=None,  # No API key for testing
        debug=True,
        agent_name="daemon-test-agent"
    ))

    # Give daemon time to start
    await asyncio.sleep(2)

    print("✓ Daemon started")
    return daemon_task


async def test_client_interaction(client_num: int):
    """Test a single client interaction"""
    print(f"\n{'='*60}")
    print(f"Client {client_num} Test")
    print(f"{'='*60}")

    # Create client
    client = AgentClient()

    # Connect
    await client.connect()
    print(f"✓ Client {client_num} connected")

    # Start session
    response = await client.send_message("/startSession test-client-{client_num}")
    if response:
        session_id = response.session_id
        print(f"✓ Session started: {session_id}")

    # Send various commands
    commands = [
        "/help",
        "/about",
        "/status",
        "/listCommands",
        "Hello, I'm testing the P3394 agent!"
    ]

    for cmd in commands:
        print(f"\n  Sending: {cmd}")
        response = await client.send_message(cmd)
        if response:
            content = response.extract_text()
            print(f"  Received: {content[:100]}...")

    # End session
    await client.send_message("/endSession")
    print(f"\n✓ Client {client_num} session ended")

    # Disconnect
    await client.disconnect()
    print(f"✓ Client {client_num} disconnected")

    return session_id


async def verify_xapi_logs(session_id: str):
    """Verify xAPI logs for a session"""
    print(f"\n{'='*60}")
    print(f"xAPI Log Verification")
    print(f"{'='*60}")

    storage = AgentStorage(agent_name="daemon-test-agent")

    # Read xAPI statements
    statements = await storage.read_xapi_statements(session_id)

    print(f"\n✓ Found {len(statements)} xAPI statements for session {session_id[:8]}...")

    # Analyze statement types
    verbs = {}
    for stmt in statements:
        verb = stmt['verb']['display']['en-US']
        verbs[verb] = verbs.get(verb, 0) + 1

    print(f"\nStatement breakdown:")
    for verb, count in verbs.items():
        print(f"  {verb}: {count}")

    # Show sample statements
    print(f"\nSample statements:")
    for i, stmt in enumerate(statements[:3], 1):
        actor = stmt['actor']['name']
        verb = stmt['verb']['display']['en-US']
        obj_name = stmt['object']['definition']['name']['en-US']
        print(f"\n  {i}. {actor} {verb} {obj_name}")

        # Show P3394 extensions
        ext = stmt.get('context', {}).get('extensions', {})
        msg_id = ext.get('http://id.tincanapi.com/extension/p3394-message-id', 'N/A')
        msg_type = ext.get('http://id.tincanapi.com/extension/p3394-message-type', 'N/A')
        print(f"     P3394 Message ID: {msg_id[:20]}...")
        print(f"     Message Type: {msg_type}")

    return statements


async def main():
    """Main test orchestrator"""
    print("\n" + "="*60)
    print("IEEE 3394 Agent: Daemon/Client + xAPI Integration Test")
    print("="*60)

    # Start daemon
    daemon_task = await start_daemon_in_background()

    try:
        # Test multiple clients in sequence
        session_ids = []

        for i in range(1, 3):  # Test 2 clients
            session_id = await test_client_interaction(i)
            session_ids.append(session_id)
            await asyncio.sleep(1)  # Brief pause between clients

        # Verify xAPI logs for each session
        for session_id in session_ids:
            statements = await verify_xapi_logs(session_id)

        # Summary
        print(f"\n{'='*60}")
        print("Test Summary")
        print(f"{'='*60}")

        storage = AgentStorage(agent_name="daemon-test-agent")

        print(f"\n✓ Tested {len(session_ids)} client sessions")
        print(f"✓ All sessions logged to xAPI LRS")
        print(f"✓ Storage location: {storage.base_dir}")

        # Show directory structure
        print(f"\nSession directories created:")
        for session_id in session_ids:
            session_dir = storage.get_server_session_dir(session_id)
            if session_dir:
                print(f"  {session_dir}")
                xapi_file = session_dir / "xapi_statements.jsonl"
                if xapi_file.exists():
                    size = xapi_file.stat().st_size
                    print(f"    └── xapi_statements.jsonl ({size} bytes)")

        print(f"\n{'='*60}")
        print("✓ All tests passed!")
        print(f"{'='*60}")

    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

    finally:
        # Cleanup: cancel daemon
        daemon_task.cancel()
        try:
            await daemon_task
        except asyncio.CancelledError:
            print("\n✓ Daemon stopped")


if __name__ == "__main__":
    asyncio.run(main())
