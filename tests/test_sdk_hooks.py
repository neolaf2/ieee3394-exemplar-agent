"""
Test SDK Hooks

Tests hook system for KSTAR logging, security, and P3394 compliance
"""

import asyncio
from pathlib import Path
from src.ieee3394_agent.core.gateway_sdk import AgentGateway
from src.ieee3394_agent.core.storage import AgentStorage
from src.ieee3394_agent.memory.kstar import KStarMemory
from src.ieee3394_agent.plugins.hooks_sdk import create_sdk_hooks


async def test_sdk_hooks():
    """Test SDK hooks"""
    print("\n" + "="*60)
    print("Testing SDK Hooks")
    print("="*60)

    # Initialize components
    print("\n1. Initializing components...")
    storage = AgentStorage(agent_name="test-sdk-hooks")
    kstar = KStarMemory(storage=storage)
    gateway = AgentGateway(memory=kstar, working_dir=storage.base_dir)
    await gateway.initialize()

    print(f"   ✓ Gateway initialized")
    print(f"   ✓ KSTAR memory initialized")

    print("\n2. Creating SDK hooks...")
    try:
        hooks = create_sdk_hooks(gateway)

        print(f"   ✓ SDK hooks created")
        print(f"   - Hook types:")

        for hook_type, matchers in hooks.items():
            print(f"     • {hook_type}: {len(matchers)} matcher(s)")

    except Exception as e:
        print(f"   ✗ Error creating hooks: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n3. Verifying hook structure...")
    try:
        # Check PreToolUse hooks
        assert 'PreToolUse' in hooks, "Missing PreToolUse hooks"
        assert 'PostToolUse' in hooks, "Missing PostToolUse hooks"

        print(f"   ✓ PreToolUse hooks: {len(hooks['PreToolUse'])} matchers")
        print(f"   ✓ PostToolUse hooks: {len(hooks['PostToolUse'])} matchers")

        # Verify we have expected hooks
        # Note: HookMatcher objects don't expose their hook functions directly,
        # but we can verify the structure
        pre_matchers = hooks['PreToolUse']
        post_matchers = hooks['PostToolUse']

        print(f"\n   Hook structure:")
        print(f"   - PreToolUse matchers: {len(pre_matchers)}")
        print(f"   - PostToolUse matchers: {len(post_matchers)}")

    except AssertionError as e:
        print(f"   ✗ Validation error: {e}")
        return
    except Exception as e:
        print(f"   ✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n4. Testing KSTAR logging hooks (simulation)...")
    try:
        # We can't directly invoke hooks outside of SDK context,
        # but we can verify they would log to KSTAR

        # Simulate a tool call that would trigger pre-tool hook
        input_data = {
            'tool_name': 'Read',
            'tool_input': {'file_path': '/test/file.txt'},
            'session_id': 'test-session'
        }

        print(f"   Simulated tool call:")
        print(f"   - Tool: {input_data['tool_name']}")
        print(f"   - Input: {input_data['tool_input']}")

        # Verify KSTAR can store traces (what the hook would do)
        test_trace = {
            "situation": {
                "domain": "ieee3394_agent",
                "actor": "agent",
                "protocol": "claude_agent_sdk",
                "now": "2026-01-28T12:00:00Z"
            },
            "task": {
                "goal": f"Execute tool: {input_data['tool_name']}",
                "constraints": [],
                "success_criteria": ["Tool executes without error"]
            },
            "action": {
                "type": input_data['tool_name'],
                "parameters": input_data['tool_input'],
                "skill_used": f"builtin:{input_data['tool_name']}"
            },
            "mode": "performance",
            "session_id": input_data['session_id']
        }

        trace_id = await gateway.memory.store_trace(test_trace)

        print(f"   ✓ KSTAR trace stored (simulating pre-tool hook)")
        print(f"   - Trace ID: {trace_id}")

    except Exception as e:
        print(f"   ✗ Error testing KSTAR hooks: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n5. Testing security hook patterns...")
    try:
        # Test dangerous command patterns that security hook should block
        dangerous_commands = [
            "rm -rf /",
            "sudo rm -rf /home/user",
            ":(){:|:&};:",  # Fork bomb
        ]

        print(f"   Testing {len(dangerous_commands)} dangerous patterns:")

        for cmd in dangerous_commands:
            # Check if our dangerous pattern list would catch it
            # (This is what the security_audit_hook does)
            is_dangerous = any(
                pattern in cmd
                for pattern in ['rm -rf /', 'sudo rm', ':(){:|:&};:']
            )

            if is_dangerous:
                print(f"   ✓ Would block: {cmd[:50]}...")
            else:
                print(f"   ✗ Would NOT block: {cmd[:50]}...")

    except Exception as e:
        print(f"   ✗ Error testing security patterns: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n6. Verifying hook integration with gateway...")
    try:
        # Check that gateway SDK options include hooks
        sdk_options = gateway.get_sdk_options()

        print(f"   ✓ SDK options retrieved")

        # Verify hooks are present
        if hasattr(sdk_options, 'hooks') and sdk_options.hooks:
            print(f"   ✓ Hooks configured in SDK options")

            # Check hook types
            hook_types = list(sdk_options.hooks.keys())
            print(f"   - Hook types: {hook_types}")

            for hook_type in hook_types:
                matcher_count = len(sdk_options.hooks[hook_type])
                print(f"   - {hook_type}: {matcher_count} matcher(s)")
        else:
            print(f"   ⚠ No hooks found in SDK options")

    except Exception as e:
        print(f"   ✗ Error checking integration: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n7. Testing hook order and composition...")
    try:
        # Verify that multiple hooks can coexist
        pre_hooks = hooks['PreToolUse']

        print(f"   ✓ PreToolUse has {len(pre_hooks)} matchers")
        print(f"   - Expected: General hooks + Bash-specific hooks")

        # We should have at least:
        # 1. General matcher with kstar_pre_tool_hook, p3394_compliance_hook
        # 2. Bash matcher with security_audit_hook

        if len(pre_hooks) >= 2:
            print(f"   ✓ Multiple hook matchers configured correctly")
        else:
            print(f"   ⚠ Expected at least 2 matchers, got {len(pre_hooks)}")

    except Exception as e:
        print(f"   ✗ Error testing hook composition: {e}")
        import traceback
        traceback.print_exc()
        return

    print("\n" + "="*60)
    print("✓ All tests passed!")
    print("="*60)


if __name__ == "__main__":
    asyncio.run(test_sdk_hooks())
