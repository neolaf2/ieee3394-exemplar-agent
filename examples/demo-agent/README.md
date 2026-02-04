# Demo Agent Example

Interactive demonstration of all P3394 agent capabilities.

## Features Demonstrated

- Symbolic commands (`/help`, `/about`, `/status`, `/version`)
- Natural language Q&A via Claude
- KSTAR memory tracking
- P3394 UMF message handling

## Usage

From the project root:

```bash
cd examples/demo-agent
uv run python demo_agent.py
```

## Prerequisites

- Anthropic API key set in environment or `.env` file
- Agent package installed (`uv sync` from project root)

## What It Shows

1. **Symbolic Commands**: Fast, deterministic responses without LLM
2. **LLM Routing**: Natural language queries processed by Claude
3. **Message Format**: P3394 Universal Message Format (UMF) in action
4. **Memory Integration**: KSTAR memory tracking all interactions
