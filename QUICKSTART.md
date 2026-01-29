# Quick Start Guide

## Architecture

The agent uses a **daemon/client architecture**:
- **Agent Host (Daemon)**: Runs in the background, always available
- **Agent Client (CLI)**: Connects to the running daemon for chat sessions

## Step 1: Start the Agent Host (Daemon)

In one terminal, start the agent daemon:

```bash
uv run python -m ieee3394_agent --daemon
```

You should see:
```
🚀 IEEE 3394 Agent Host running on /tmp/ieee3394-agent.sock
   Agent: IEEE 3394 Exemplar Agent v0.1.0
   Press Ctrl+C to stop
```

**Leave this running** - it's your agent server.

## Step 2: Connect a Client

In a **new terminal**, start a client session:

```bash
uv run python -m ieee3394_agent
```

This launches the interactive CLI interface where you can chat with the agent.

You can connect **multiple clients** to the same daemon!

## Your First Session

After starting, you'll see:

```
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent                        ║
║                   CLI Channel                                ║
╠══════════════════════════════════════════════════════════════╣
║  Version: 0.1.0                                         ║
║  Session: abc123...                                     ║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                     ║
║  Type 'exit' to quit                                         ║
╚══════════════════════════════════════════════════════════════╝

>>>
```

## Try These Commands

### Symbolic Commands (Instant)
```
>>> /help
>>> /about
>>> /status
>>> /version
```

### Natural Language (Uses Claude API)
```
>>> What is P3394?
>>> Explain the Universal Message Format
>>> How do channel adapters work?
>>> What makes this agent special?
```

## Exiting

To quit the CLI:
```
>>> exit
```

Or press `Ctrl+C` and then type `exit`.

## Prerequisites

Make sure you have your Anthropic API key set:

```bash
export ANTHROPIC_API_KEY='your-api-key-here'
```

Or add to `.env` file in the project root:
```
ANTHROPIC_API_KEY=your-api-key-here
```

## Troubleshooting

**"ANTHROPIC_API_KEY not set" error:**
```bash
# Check if set
echo $ANTHROPIC_API_KEY

# Set temporarily
export ANTHROPIC_API_KEY='sk-ant-...'

# Or add to your shell profile (~/.zshrc or ~/.bashrc)
echo 'export ANTHROPIC_API_KEY="sk-ant-..."' >> ~/.zshrc
source ~/.zshrc
```

**Dependencies not installed:**
```bash
uv sync
```

## What's Happening Behind the Scenes

1. **You type** → CLI adapter creates a P3394Message
2. **Gateway routes** → Determines if symbolic command or LLM
3. **Handler executes** → Runs function or calls Claude API
4. **Response returns** → Formatted and displayed
5. **KSTAR logs** → Every interaction saved to memory

Every message demonstrates the P3394 standard in action!

---

## Advanced: Multi-Channel Testing

The agent supports **multiple channel interfaces** simultaneously!

### Start with All Channels

```bash
# Start daemon with all channels enabled
uv run python -m ieee3394_agent --daemon \
  --anthropic-api --api-port 8100 \
  --p3394-server --p3394-port 8101
```

This enables:
- ✅ **CLI** (Unix socket) - Interactive REPL
- ✅ **HTTP API** (port 8100) - Anthropic-compatible API
- ✅ **P3394 Server** (port 8101) - Agent-to-agent protocol

### Test All Channels

Run the automated test suite:

```bash
python test_channels.py
```

Expected output:
```
==================================================================
TEST: Unix Socket (CLI Channel)
==================================================================
✓ Connected to /tmp/ieee3394-agent.sock
✓ Sent test message
✓ Received response

==================================================================
TEST: Anthropic API HTTP Channel
==================================================================
✓ Received response
✓ Streaming works! Received 245 characters

==================================================================
TEST: P3394 Server Channel
==================================================================
✓ Health check passed
✓ Agent ID: ieee3394-exemplar
✓ Received P3394 response

==================================================================
TEST: IEEE WG Manager Skill
==================================================================
✓ Ballot calculation response received
✓ Skill appears to be working

==================================================================
TEST SUMMARY
==================================================================
✓ Unix Socket          PASSED
✓ Anthropic API        PASSED
✓ P3394 Server         PASSED
✓ IEEE WG Skill        PASSED

Results: 4/4 tests passed
🎉 All tests passed!
```

### Test via HTTP API

```bash
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 1024,
    "messages": [{
      "role": "user",
      "content": "What is IEEE P3394?"
    }]
  }'
```

### Test via P3394 Protocol

```bash
curl -X POST http://localhost:8101/message \
  -H "Content-Type: application/json" \
  -d '{
    "type": "request",
    "content": [{
      "type": "text",
      "data": "What skills do you have?"
    }]
  }'
```

### Connect Claude Code CLI to Your Agent

Make Claude Code use your local agent instead of Anthropic's API:

```bash
# Configure environment
export ANTHROPIC_BASE_URL=http://localhost:8100
export ANTHROPIC_API_KEY=test-key

# Now use Claude Code normally - it connects to YOUR agent!
claude "What is P3394?"
claude "Help me with an IEEE ballot calculation"
```

---

## Test the IEEE WG Manager Skill

The agent includes a comprehensive IEEE Working Group management skill!

### Via CLI
```
>>> Help me prepare for an IEEE sponsor ballot
>>> Calculate ballot results: 30 Approve, 5 Disapprove, 10 Abstain
>>> Generate an IEEE meeting agenda
>>> What are the standards lifecycle milestones?
```

### Via HTTP API
```bash
curl -X POST http://localhost:8100/v1/messages \
  -H "Content-Type: application/json" \
  -H "x-api-key: test-key" \
  -d '{
    "model": "claude-sonnet-4-5-20250929",
    "max_tokens": 2048,
    "messages": [{
      "role": "user",
      "content": "Help me consolidate ballot comments and create a disposition document"
    }]
  }'
```

The skill includes:
- 📋 Ballot tracking and approval calculations
- 📝 Meeting agendas and minutes templates
- 💬 Comment consolidation tools
- 📊 Action item tracking
- 📖 Complete IEEE process documentation

---

## Next Steps

1. **Full Testing Guide**: See [TESTING_GUIDE.md](TESTING_GUIDE.md) for comprehensive channel testing
2. **Skills Documentation**: See [.claude/skills/README.md](.claude/skills/README.md) for skill details
3. **Architecture Deep Dive**: See [CLAUDE.md](CLAUDE.md) for complete system architecture
4. **Branch Status**: See [BRANCH_READY.md](BRANCH_READY.md) for merge preparation status
