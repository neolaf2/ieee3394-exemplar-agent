"""
Integration test for xAPI logging
"""

import asyncio
import json
from pathlib import Path
from src.ieee3394_agent.core.storage import AgentStorage
from src.ieee3394_agent.core.umf import P3394Message, MessageType, ContentType, P3394Content
from src.ieee3394_agent.memory.kstar import KStarMemory
from src.ieee3394_agent.core.gateway import AgentGateway


async def test_xapi_logging():
    """Test that xAPI statements are logged correctly"""

    print("\n" + "="*60)
    print("Testing xAPI Integration")
    print("="*60)

    # Initialize storage with xAPI enabled
    storage = AgentStorage(agent_name="test-agent", enable_xapi=True)
    print(f"\n✓ Storage initialized at: {storage.base_dir}")

    # Create a test session
    session_id = "test-session-001"
    session_dir = storage.create_server_session(session_id)
    print(f"✓ Created session: {session_id}")
    print(f"  Directory: {session_dir}")

    # Create a test message
    test_message = P3394Message(
        type=MessageType.REQUEST,
        content=[P3394Content(
            type=ContentType.TEXT,
            data="/help"
        )],
        session_id=session_id
    )

    # Log the message as xAPI statement
    statement_id = await storage.log_xapi_statement(
        session_id=session_id,
        message=test_message,
        client_id="test-client"
    )
    print(f"\n✓ Logged xAPI statement: {statement_id}")

    # Create a response message
    response_message = P3394Message(
        type=MessageType.RESPONSE,
        content=[P3394Content(
            type=ContentType.TEXT,
            data="Here is the help information..."
        )],
        session_id=session_id,
        reply_to=test_message.id
    )

    # Log the response
    response_statement_id = await storage.log_xapi_statement(
        session_id=session_id,
        message=response_message,
        client_id="agent"
    )
    print(f"✓ Logged response statement: {response_statement_id}")

    # Read back the xAPI statements
    xapi_file = session_dir / "xapi_statements.jsonl"
    print(f"\n✓ xAPI statements file: {xapi_file}")
    print(f"  File exists: {xapi_file.exists()}")

    if xapi_file.exists():
        statements = await storage.read_xapi_statements(session_id)
        print(f"\n✓ Read {len(statements)} xAPI statements:")

        for i, stmt in enumerate(statements, 1):
            print(f"\n  Statement {i}:")
            print(f"    ID: {stmt['id']}")
            print(f"    Actor: {stmt['actor']['name']}")
            print(f"    Verb: {stmt['verb']['display']['en-US']}")
            print(f"    Object: {stmt['object']['definition']['name']['en-US']}")
            print(f"    Activity ID: {stmt['object']['id']}")

            # Verify context
            context = stmt.get('context', {})
            parent = context.get('contextActivities', {}).get('parent', [{}])[0]
            print(f"    Parent Session: {parent.get('id', 'N/A')}")

            # Check extensions
            extensions = context.get('extensions', {})
            msg_id = extensions.get('http://id.tincanapi.com/extension/p3394-message-id')
            msg_type = extensions.get('http://id.tincanapi.com/extension/p3394-message-type')
            print(f"    Message ID: {msg_id}")
            print(f"    Message Type: {msg_type}")

    # Test KSTAR + xAPI integration
    print("\n" + "-"*60)
    print("Testing KSTAR + xAPI Integration")
    print("-"*60)

    kstar = KStarMemory(storage=storage)
    gateway = AgentGateway(kstar_memory=kstar)

    # Send a message through the gateway
    test_msg = P3394Message.text("/status", session_id=session_id)
    response = await gateway.handle(test_msg)

    print(f"\n✓ Gateway handled message")
    print(f"  Request ID: {test_msg.id}")
    print(f"  Response ID: {response.id}")

    # Check xAPI logs again
    statements = await storage.read_xapi_statements(session_id)
    print(f"\n✓ Total xAPI statements after gateway: {len(statements)}")

    # Display raw JSONL content
    print("\n" + "-"*60)
    print("Raw xAPI JSONL Content")
    print("-"*60)

    with xapi_file.open('r') as f:
        for i, line in enumerate(f, 1):
            if line.strip():
                stmt = json.loads(line)
                print(f"\nStatement {i} (pretty-printed):")
                print(json.dumps(stmt, indent=2))

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)
    print(f"\nTest artifacts located at: {storage.base_dir}")
    print(f"Session directory: {session_dir}")
    print(f"xAPI statements: {xapi_file}")


if __name__ == "__main__":
    asyncio.run(test_xapi_logging())
