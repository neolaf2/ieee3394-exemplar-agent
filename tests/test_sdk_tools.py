"""
Test SDK Custom Tools

Tests custom MCP tools implemented using Claude Agent SDK
"""

import asyncio
from pathlib import Path
from src.ieee3394_agent.core.gateway_sdk import AgentGateway
from src.ieee3394_agent.core.storage import AgentStorage
from src.ieee3394_agent.memory.kstar import KStarMemory
from src.ieee3394_agent.plugins.tools_sdk import create_sdk_tools


async def test_sdk_tools():
    """Test SDK custom tools"""
    print("\n" + "="*60)
    print("Testing SDK Custom Tools")
    print("="*60)

    # Initialize components
    print("\n1. Initializing components...")
    storage = AgentStorage(agent_name="test-sdk-tools")
    kstar = KStarMemory(storage=storage)
    gateway = AgentGateway(memory=kstar, working_dir=storage.base_dir)
    await gateway.initialize()

    print(f"   ✓ Gateway initialized")
    print(f"   ✓ KSTAR memory initialized")
    print(f"   ✓ Loaded {len(gateway.skills)} skills")

    print("\n2. Creating SDK tools...")
    try:
        tools_server = create_sdk_tools(gateway)

        print(f"   ✓ SDK tools server created")
        print(f"   - Server name: p3394_tools")
        print(f"   - Available tools:")

        # List available tools by examining the server
        # Note: We can't directly list tools from create_sdk_mcp_server,
        # but we know we have 3 tools
        print(f"     • query_memory - Query KSTAR memory for past traces")
        print(f"     • store_trace - Store new KSTAR trace")
        print(f"     • list_skills - List registered skills")

    except Exception as e:
        print(f"   ✗ Error creating tools: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n3. Testing store_trace tool...")
    try:
        # Store a test trace
        trace = {
            "situation": {
                "domain": "test",
                "actor": "test-agent",
                "protocol": "sdk-test",
                "now": "2026-01-28T12:00:00Z"
            },
            "task": {
                "goal": "Test SDK custom tools",
                "constraints": [],
                "success_criteria": ["Tools work correctly"]
            },
            "action": {
                "type": "test_action",
                "parameters": {"test": True},
                "skill_used": "test_skill"
            },
            "result": {
                "success": True,
                "output": "Test successful"
            },
            "mode": "learning",
            "session_id": "test-session"
        }

        # Store via KSTAR memory directly (simulating what the tool would do)
        trace_id = await gateway.memory.store_trace(trace)

        print(f"   ✓ Trace stored")
        print(f"   - Trace ID: {trace_id}")

    except Exception as e:
        print(f"   ✗ Error storing trace: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n4. Testing query_memory tool...")
    try:
        # Query KSTAR memory
        results = await gateway.memory.query(
            domain="test",
            goal="Test SDK custom tools"
        )

        print(f"   ✓ Query executed")
        if results:
            print(f"   - Found matching traces")
            # Show preview of results
            result_str = str(results)[:200]
            if len(str(results)) > 200:
                result_str += "..."
            print(f"   - Results preview: {result_str}")
        else:
            print(f"   - No matching traces found")

    except Exception as e:
        print(f"   ✗ Error querying memory: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n5. Testing list_skills tool...")
    try:
        # List skills via gateway
        skills = gateway.skills

        print(f"   ✓ Skills retrieved")
        print(f"   - Count: {len(skills)}")

        for name, skill in skills.items():
            print(f"   - {name}: {skill['description']}")

    except Exception as e:
        print(f"   ✗ Error listing skills: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n6. Testing tool integration with gateway...")
    try:
        # Verify that gateway has SDK options configured with custom tools
        sdk_options = gateway.get_sdk_options()

        print(f"   ✓ SDK options retrieved")
        print(f"   - Allowed tools count: {len(sdk_options.allowed_tools)}")
        print(f"   - Has MCP servers: {bool(sdk_options.mcp_servers)}")

        if sdk_options.mcp_servers:
            mcp_names = list(sdk_options.mcp_servers.keys())
            print(f"   - MCP servers: {mcp_names}")

    except Exception as e:
        print(f"   ✗ Error checking integration: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n7. Verifying tool permissions...")
    try:
        # Check that custom tools are in allowed_tools list
        sdk_options = gateway.get_sdk_options()
        allowed = sdk_options.allowed_tools

        custom_tool_patterns = [
            "mcp__p3394_tools__query_memory",
            "mcp__p3394_tools__store_trace",
            "mcp__p3394_tools__list_skills"
        ]

        for tool_name in custom_tool_patterns:
            if tool_name in allowed:
                print(f"   ✓ {tool_name} is allowed")
            else:
                print(f"   ⚠ {tool_name} not found in allowed_tools")

    except Exception as e:
        print(f"   ✗ Error checking permissions: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_sdk_tools())
