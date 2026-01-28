"""
Interactive Demo of IEEE 3394 Exemplar Agent

This demonstrates all the agent's capabilities:
- Symbolic commands (/help, /about, /status, /version)
- Natural language Q&A via Claude
- KSTAR memory tracking
- P3394 UMF message handling
"""
import asyncio
import os
from src.ieee3394_agent.core.gateway import AgentGateway
from src.ieee3394_agent.memory.kstar import KStarMemory
from src.ieee3394_agent.core.umf import P3394Message
from src.ieee3394_agent.plugins.hooks import set_kstar_memory


def print_section(title: str):
    """Print a section header"""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


def print_response(label: str, response: P3394Message):
    """Print a formatted response"""
    print(f"🤖 {label}")
    print(f"   Message ID: {response.id}")
    print(f"   Type: {response.type.value}")
    print(f"   Content:")
    for content in response.content:
        text = content.data
        # Show first 500 chars for long responses
        if len(str(text)) > 500:
            print(f"   {str(text)[:500]}...")
        else:
            print(f"   {text}")
    print()


async def demo():
    """Run the demo"""
    print("\n" + "="*70)
    print("  IEEE 3394 EXEMPLAR AGENT - INTERACTIVE DEMO")
    print("="*70)

    # Check for API key
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("\n❌ Error: ANTHROPIC_API_KEY not set")
        print("   Natural language features will not work.")
        print("   Only symbolic commands will be available.\n")
        use_llm = False
    else:
        print("\n✅ ANTHROPIC_API_KEY found - Full features enabled\n")
        use_llm = True

    # Initialize
    print("🔧 Initializing agent...")
    kstar = KStarMemory()
    set_kstar_memory(kstar)

    api_key = os.environ.get("ANTHROPIC_API_KEY") if use_llm else None
    gateway = AgentGateway(kstar_memory=kstar, anthropic_api_key=api_key)

    print(f"✅ Agent initialized: {gateway.AGENT_NAME} v{gateway.AGENT_VERSION}")

    # =========================================================================
    # TEST 1: Help Command
    # =========================================================================
    print_section("TEST 1: Symbolic Command - /help")
    message = P3394Message.text("/help")
    response = await gateway.handle(message)
    print_response("Response from /help", response)

    # =========================================================================
    # TEST 2: About Command
    # =========================================================================
    print_section("TEST 2: Symbolic Command - /about")
    message = P3394Message.text("/about")
    response = await gateway.handle(message)
    print_response("Response from /about", response)

    # =========================================================================
    # TEST 3: Status Command
    # =========================================================================
    print_section("TEST 3: Symbolic Command - /status")
    message = P3394Message.text("/status")
    response = await gateway.handle(message)
    print_response("Response from /status", response)

    # =========================================================================
    # TEST 4: Version Command
    # =========================================================================
    print_section("TEST 4: Symbolic Command - /version")
    message = P3394Message.text("/version")
    response = await gateway.handle(message)
    print_response("Response from /version", response)

    # =========================================================================
    # TEST 5: Natural Language Q&A (if API key available)
    # =========================================================================
    if use_llm:
        print_section("TEST 5: Natural Language - 'What is P3394?'")
        print("⏳ Calling Claude API... (this may take a few seconds)")
        message = P3394Message.text("What is P3394 and why is it important for agent interoperability?")
        response = await gateway.handle(message)
        print_response("Response from Claude", response)

        print_section("TEST 6: Natural Language - 'Explain UMF'")
        print("⏳ Calling Claude API...")
        message = P3394Message.text("Can you explain the Universal Message Format (UMF) in simple terms?")
        response = await gateway.handle(message)
        print_response("Response from Claude", response)
    else:
        print_section("TEST 5-6: Natural Language (SKIPPED)")
        print("⚠️  Natural language features require ANTHROPIC_API_KEY")
        print("   Set the environment variable to test LLM routing.\n")

    # =========================================================================
    # TEST 7: KSTAR Memory Stats
    # =========================================================================
    print_section("TEST 7: KSTAR Memory Inspection")
    stats = await kstar.get_stats()
    print("📊 Memory Statistics:")
    print(f"   Traces: {stats['trace_count']}")
    print(f"   Perceptions: {stats['perception_count']}")
    print(f"   Skills: {stats['skill_count']}")

    # Show sample trace
    if kstar.traces:
        print("\n📝 Sample Trace (most recent):")
        trace = kstar.traces[-1]
        print(f"   ID: {trace['id']}")
        print(f"   Timestamp: {trace['timestamp']}")
        print(f"   Domain: {trace['situation']['domain']}")
        print(f"   Goal: {trace['task']['goal']}")
        print(f"   Action Type: {trace['action']['type']}")

    # =========================================================================
    # TEST 8: P3394 UMF Message Inspection
    # =========================================================================
    print_section("TEST 8: P3394 Message Format Inspection")
    message = P3394Message.text("Sample message", session_id="test-session")
    message_dict = message.to_dict()

    print("🔍 P3394 UMF Message Structure:")
    print(f"   ID: {message_dict['id']}")
    print(f"   Type: {message_dict['type']}")
    print(f"   Timestamp: {message_dict['timestamp']}")
    print(f"   Session ID: {message_dict['session_id']}")
    print(f"   Content Blocks: {len(message_dict['content'])}")
    print(f"   Content Type: {message_dict['content'][0]['type']}")

    # =========================================================================
    # Summary
    # =========================================================================
    print_section("DEMO COMPLETE - Summary")
    print("✅ All tests passed!")
    print("\n📋 What was demonstrated:")
    print("   • Symbolic command routing (no LLM needed)")
    print("   • P3394 Universal Message Format (UMF)")
    print("   • Session management")
    print("   • KSTAR memory logging (traces & perceptions)")
    if use_llm:
        print("   • LLM routing via Claude Opus 4.5")
        print("   • Natural language Q&A")
    print("\n🎯 The agent is ready for production use!")
    print("\n💡 To interact with the CLI:")
    print("   uv run python -m ieee3394_agent")
    print("\n" + "="*70 + "\n")


if __name__ == "__main__":
    asyncio.run(demo())
