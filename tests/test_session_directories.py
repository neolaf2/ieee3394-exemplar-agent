#!/usr/bin/env python3
"""
Test Session Directory Creation

Verifies that session directories are created with the correct structure:
storage_dir/stm/<session_id>/shared/{workspace, artifacts, temp, tools}
"""

import asyncio
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from ieee3394_agent.core.storage import AgentStorage
from ieee3394_agent.memory.kstar import KStarMemory
from ieee3394_agent.core.gateway_sdk import AgentGateway


async def test_session_directories():
    """Test that session directories are created correctly"""

    print("=" * 70)
    print("Testing Session Directory Creation")
    print("=" * 70)
    print()

    # Initialize storage
    print("1. Initializing agent storage...")
    storage = AgentStorage(agent_name="ieee3394-exemplar")
    print(f"   ✓ Base directory: {storage.base_dir}")
    print()

    # Initialize memory
    print("2. Initializing KSTAR memory...")
    memory = KStarMemory(storage=storage)
    print(f"   ✓ Memory initialized")
    print()

    # Initialize gateway
    print("3. Initializing agent gateway...")
    gateway = AgentGateway(memory=memory)
    print(f"   ✓ Gateway initialized")
    print()

    # Create a test session
    print("4. Creating test session...")
    session = await gateway.session_manager.create_session(
        client_id="test-client",
        channel_id="test"
    )
    print(f"   ✓ Session created: {session.id}")
    print(f"   ✓ Client ID: {session.client_id}")
    print()

    # Check if working directory was created
    if session.working_dir:
        print("5. Verifying directory structure...")
        print(f"   ✓ Working directory: {session.working_dir}")

        # Check subdirectories
        subdirs = ["workspace", "artifacts", "temp", "tools"]
        all_exist = True

        for subdir in subdirs:
            subdir_path = session.working_dir / subdir
            exists = subdir_path.exists() and subdir_path.is_dir()
            status = "✓" if exists else "✗"
            print(f"   {status} {subdir}/: {subdir_path}")
            if not exists:
                all_exist = False

        print()

        # Test helper methods
        print("6. Testing Session helper methods...")
        try:
            workspace = session.get_workspace_dir()
            print(f"   ✓ get_workspace_dir(): {workspace}")

            artifacts = session.get_artifacts_dir()
            print(f"   ✓ get_artifacts_dir(): {artifacts}")

            temp = session.get_temp_dir()
            print(f"   ✓ get_temp_dir(): {temp}")

            tools = session.get_tools_dir()
            print(f"   ✓ get_tools_dir(): {tools}")

            print()
        except Exception as e:
            print(f"   ✗ Error: {e}")
            print()
            return False

        if all_exist:
            print("=" * 70)
            print("✓ All tests passed!")
            print("=" * 70)
            print()
            print("Session directory structure created successfully:")
            print(f"  {session.working_dir.parent.parent.parent}/")
            print(f"  └── stm/")
            print(f"      └── {session.id}/")
            print(f"          └── shared/")
            print(f"              ├── workspace/")
            print(f"              ├── artifacts/")
            print(f"              ├── temp/")
            print(f"              └── tools/")
            print()
            return True
        else:
            print("=" * 70)
            print("✗ Some directories were not created")
            print("=" * 70)
            return False
    else:
        print("5. ERROR: Working directory was not set on session")
        print()
        print("   This might mean:")
        print("   - storage_dir was not passed to SessionManager")
        print("   - SessionManager initialization failed")
        print()
        return False


if __name__ == "__main__":
    try:
        success = asyncio.run(test_session_directories())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted")
        sys.exit(130)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
