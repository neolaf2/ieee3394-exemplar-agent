#!/usr/bin/env python3
"""
IEEE 3394 Exemplar Agent - Multi-Channel Test Script

Tests all channel interfaces to verify the agent is working correctly.
Run this after starting the agent daemon.
"""

import asyncio
import json
import socket
import sys
from pathlib import Path

try:
    import anthropic
    import httpx
except ImportError:
    print("⚠️  Optional dependencies not installed. Some tests will be skipped.")
    print("Install with: uv add anthropic httpx")
    anthropic = None
    httpx = None


class Colors:
    """Terminal colors for pretty output"""
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKCYAN = '\033[96m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'


def print_test(name: str):
    """Print test header"""
    print(f"\n{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}TEST: {name}{Colors.ENDC}")
    print(f"{Colors.BOLD}{Colors.OKBLUE}{'='*70}{Colors.ENDC}\n")


def print_success(msg: str):
    """Print success message"""
    print(f"{Colors.OKGREEN}✓ {msg}{Colors.ENDC}")


def print_error(msg: str):
    """Print error message"""
    print(f"{Colors.FAIL}✗ {msg}{Colors.ENDC}")


def print_info(msg: str):
    """Print info message"""
    print(f"{Colors.OKCYAN}ℹ {msg}{Colors.ENDC}")


def print_warning(msg: str):
    """Print warning message"""
    print(f"{Colors.WARNING}⚠ {msg}{Colors.ENDC}")


# ============================================================================
# TEST 1: Unix Socket (CLI Channel)
# ============================================================================

def test_unix_socket(socket_path: str = "/tmp/ieee3394-agent.sock"):
    """Test Unix socket connection"""
    print_test("Unix Socket (CLI Channel)")

    if not Path(socket_path).exists():
        print_error(f"Socket not found at {socket_path}")
        print_info("Start daemon first: uv run python -m ieee3394_agent --daemon")
        return False

    try:
        # Connect to socket
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.connect(socket_path)
        print_success(f"Connected to {socket_path}")

        # Send test message
        test_msg = json.dumps({
            "type": "request",
            "content": [{"type": "text", "data": "What is IEEE P3394?"}]
        }) + "\n"

        sock.sendall(test_msg.encode())
        print_success("Sent test message")

        # Receive response
        response_data = b""
        while True:
            chunk = sock.recv(4096)
            if not chunk:
                break
            response_data += chunk
            if b"\n" in response_data:
                break

        response = json.loads(response_data.decode())
        print_success("Received response")

        # Display response
        if response.get("content"):
            content = response["content"][0].get("data", "")
            print_info(f"Response preview: {content[:200]}...")

        sock.close()
        return True

    except Exception as e:
        print_error(f"Socket test failed: {e}")
        return False


# ============================================================================
# TEST 2: Anthropic API HTTP Channel
# ============================================================================

async def test_anthropic_api(
    base_url: str = "http://localhost:8100",
    api_key: str = "test-key"
):
    """Test Anthropic API HTTP channel"""
    print_test("Anthropic API HTTP Channel")

    if anthropic is None:
        print_warning("anthropic package not installed, skipping")
        return False

    try:
        # Test basic connection
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=30.0
        )

        # Send message
        print_info("Sending message to agent...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=1024,
            messages=[
                {"role": "user", "content": "What skills do you have?"}
            ]
        )

        print_success("Received response")
        print_info(f"Response: {message.content[0].text[:200]}...")

        # Test streaming
        print_info("\nTesting streaming response...")
        with client.messages.stream(
            model="claude-sonnet-4-5-20250929",
            max_tokens=512,
            messages=[
                {"role": "user", "content": "What is P3394?"}
            ]
        ) as stream:
            text_chunks = []
            for text in stream.text_stream:
                text_chunks.append(text)

        full_text = "".join(text_chunks)
        print_success(f"Streaming works! Received {len(full_text)} characters")
        print_info(f"Preview: {full_text[:100]}...")

        return True

    except anthropic.APIConnectionError as e:
        print_error(f"Could not connect to {base_url}")
        print_info("Start daemon with: uv run python -m ieee3394_agent --daemon --anthropic-api")
        return False
    except Exception as e:
        print_error(f"API test failed: {e}")
        return False


# ============================================================================
# TEST 3: P3394 Server Channel
# ============================================================================

async def test_p3394_server(base_url: str = "http://localhost:8101"):
    """Test P3394 agent-to-agent channel"""
    print_test("P3394 Server Channel")

    if httpx is None:
        print_warning("httpx package not installed, skipping")
        return False

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            # Test health endpoint
            print_info("Checking health endpoint...")
            response = await client.get(f"{base_url}/health")
            if response.status_code == 200:
                print_success("Health check passed")
            else:
                print_error(f"Health check failed: {response.status_code}")
                return False

            # Test capabilities endpoint
            print_info("Checking capabilities...")
            response = await client.get(f"{base_url}/capabilities")
            if response.status_code == 200:
                caps = response.json()
                print_success(f"Agent ID: {caps.get('agent_id')}")
                print_info(f"Skills: {len(caps.get('skills', []))}")
            else:
                print_warning("Capabilities endpoint not available")

            # Send P3394 message
            print_info("Sending P3394 UMF message...")
            p3394_message = {
                "type": "request",
                "source": {
                    "agent_id": "test-client",
                    "channel_id": "http"
                },
                "destination": {
                    "agent_id": "ieee3394-exemplar"
                },
                "content": [
                    {
                        "type": "text",
                        "data": "What is the IEEE 3394 standard?"
                    }
                ],
                "session_id": "test-session-p3394"
            }

            response = await client.post(
                f"{base_url}/message",
                json=p3394_message,
                headers={"Content-Type": "application/json"}
            )

            if response.status_code == 200:
                result = response.json()
                print_success("Received P3394 response")

                if result.get("content"):
                    content = result["content"][0].get("data", "")
                    print_info(f"Response preview: {content[:200]}...")
                return True
            else:
                print_error(f"P3394 message failed: {response.status_code}")
                return False

        except httpx.ConnectError:
            print_error(f"Could not connect to {base_url}")
            print_info("Start daemon with: uv run python -m ieee3394_agent --daemon --p3394-server")
            return False
        except Exception as e:
            print_error(f"P3394 test failed: {e}")
            return False


# ============================================================================
# TEST 4: IEEE WG Manager Skill
# ============================================================================

async def test_ieee_wg_skill(
    base_url: str = "http://localhost:8100",
    api_key: str = "test-key"
):
    """Test IEEE WG Manager skill via API"""
    print_test("IEEE WG Manager Skill")

    if anthropic is None:
        print_warning("anthropic package not installed, skipping")
        return False

    try:
        client = anthropic.Anthropic(
            api_key=api_key,
            base_url=base_url,
            timeout=60.0
        )

        # Test ballot calculation
        print_info("Testing ballot approval calculation...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": "Help me calculate ballot results. We got 30 Approve, 5 Disapprove, 10 Abstain out of 50 invitations. Did it pass?"
            }]
        )

        response_text = message.content[0].text
        print_success("Ballot calculation response received")

        # Check if skill was used
        if "75%" in response_text or "approval" in response_text.lower():
            print_success("Skill appears to be working (mentions approval threshold)")
        else:
            print_warning("Response doesn't mention ballot approval - skill may not have loaded")

        print_info(f"Response preview: {response_text[:300]}...")

        # Test meeting agenda generation
        print_info("\nTesting meeting agenda generation...")
        message = client.messages.create(
            model="claude-sonnet-4-5-20250929",
            max_tokens=2048,
            messages=[{
                "role": "user",
                "content": "Generate an IEEE working group meeting agenda for tomorrow's meeting"
            }]
        )

        response_text = message.content[0].text
        print_success("Meeting agenda response received")

        if "agenda" in response_text.lower() and "meeting" in response_text.lower():
            print_success("Skill appears to be generating meeting documents")

        print_info(f"Response preview: {response_text[:300]}...")

        return True

    except Exception as e:
        print_error(f"IEEE WG skill test failed: {e}")
        return False


# ============================================================================
# MAIN TEST RUNNER
# ============================================================================

async def run_all_tests():
    """Run all channel tests"""
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("IEEE 3394 Exemplar Agent - Multi-Channel Test Suite")
    print("=" * 70)
    print(f"{Colors.ENDC}\n")

    results = {
        "Unix Socket": False,
        "Anthropic API": False,
        "P3394 Server": False,
        "IEEE WG Skill": False
    }

    # Test 1: Unix Socket
    results["Unix Socket"] = test_unix_socket()
    await asyncio.sleep(1)

    # Test 2: Anthropic API
    results["Anthropic API"] = await test_anthropic_api()
    await asyncio.sleep(1)

    # Test 3: P3394 Server
    results["P3394 Server"] = await test_p3394_server()
    await asyncio.sleep(1)

    # Test 4: IEEE WG Manager Skill
    results["IEEE WG Skill"] = await test_ieee_wg_skill()

    # Summary
    print(f"\n{Colors.BOLD}{Colors.HEADER}")
    print("=" * 70)
    print("TEST SUMMARY")
    print("=" * 70)
    print(f"{Colors.ENDC}\n")

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for name, result in results.items():
        if result:
            print_success(f"{name:20} PASSED")
        else:
            print_error(f"{name:20} FAILED")

    print(f"\n{Colors.BOLD}Results: {passed}/{total} tests passed{Colors.ENDC}\n")

    if passed == total:
        print(f"{Colors.OKGREEN}{Colors.BOLD}🎉 All tests passed!{Colors.ENDC}\n")
        return 0
    else:
        print(f"{Colors.WARNING}{Colors.BOLD}⚠️  Some tests failed{Colors.ENDC}\n")
        print("Make sure the agent daemon is running:")
        print("  uv run python -m ieee3394_agent --daemon --anthropic-api --p3394-server")
        print()
        return 1


def main():
    """Entry point"""
    try:
        exit_code = asyncio.run(run_all_tests())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n{Colors.WARNING}Tests interrupted by user{Colors.ENDC}\n")
        sys.exit(130)


if __name__ == "__main__":
    main()
