# Development

## Setup

```bash
uv sync
```

## Tests

### Smoke tests (default CI)

CI runs **smoke tests only** by default to avoid requiring API keys or local services.

```bash
uv run pytest -q tests/smoke
```

### Full test suite (local)

Some tests require optional dependencies (e.g., `anthropic`) and/or running local services.
Run locally when you have the environment configured:

```bash
uv run pytest
```

## Lint (optional)

If you use ruff:

```bash
uv run ruff check .
```
