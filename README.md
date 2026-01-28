# IEEE 3394 Exemplar Agent

A reference implementation of the IEEE P3394 Standard for Agent Interfaces, demonstrating:

- **Universal Message Format (UMF)** - Standard message structure for agent communication
- **Multi-Channel Architecture** - Web, CLI, and MCP channels with unified routing
- **KSTAR Memory Integration** - Episodic memory and skill learning
- **Self-Documenting Agent** - The agent IS the documentation

## Architecture

This agent serves dual purposes:
1. **Reference Implementation** - Demonstrates P3394 compliance patterns
2. **Public Agent** - Powers ieee3394.org for standard education and adoption

Built on the Claude Agent SDK with:
- Two-tier message routing (symbolic commands + LLM intelligence)
- Channel adapters transforming protocols to/from P3394 UMF
- Hook-based extensibility for compliance and logging
- Agent skills and subagents for specialized capabilities

## Quick Start

```bash
# Install dependencies
uv sync

# Run CLI channel
uv run python -m ieee3394_agent --channel cli

# Run web channel
uv run python -m ieee3394_agent --channel web --port 8000

# Run both channels
uv run python -m ieee3394_agent --channel cli --channel web
```

## Project Status

🚧 **In Development** - MVP implementation in progress

Current phase: CLI + Claude SDK Integration MVP

## Documentation

See [CLAUDE.md](./CLAUDE.md) for complete architecture specification and implementation instructions.

## License

MIT License - See LICENSE file for details

## IEEE P3394 Standard

Learn more about the IEEE P3394 Agent Interface Standard:
- **Website:** ieee3394.org (powered by this agent)
- **Working Group:** IEEE Standards Association
- **Purpose:** Enable agent interoperability across vendors and platforms
