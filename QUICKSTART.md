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
