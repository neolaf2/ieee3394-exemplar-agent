# Architecture

This repo demonstrates a P3394-compliant agent implementation.

## High-level components

- **UMF messaging core**: `src/p3394_agent/core/` (message formats, routing, auth primitives)
- **Capabilities/skills system**: `src/p3394_agent/capabilities/` and `.claude/skills/`
- **Memory (KSTAR + long-term)**: `src/p3394_agent/memory/`
- **Channels/adapters**: `src/p3394_agent/channels/` (e.g., WhatsApp)
- **Examples/demos**: `examples/`, `demo_agent.py`, `serve_webchat.py`

## Repo layout (refactor)

- `plugins/ieee3394-exemplar-agent/` — marketplace/plugin wrapper (commands/manifests)
- `docs/` — documentation
- `src/` — python package
- `tests/` — pytest tests

For deep dives, see `docs/legacy/`.
