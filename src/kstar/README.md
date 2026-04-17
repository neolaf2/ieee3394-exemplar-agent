# KSTAR Stateful Agent

A production-grade, recursive, self-improving AI agent built on the
**Anthropic Claude Agent SDK (Python)** — implementing the KSTAR
(Knowledge, State, Task, Action, Result) execution model.

---

## Architecture

```
[ User Prompt ]
      │
      ▼
┌─────────────────────────────────────────────────────────────┐
│                    KSTAR Orchestrator                        │
│                                                              │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────┐  │
│  │ ST Refine│→ │  Plan    │→ │  Plan    │→ │  Action   │  │
│  │ Σ→(S,T) │  │ Retrieval│  │ Forecast │  │ Execution │  │
│  │          │  │(S,T)→P[] │  │(S,T,P)→  │  │ Â→(A,R)  │  │
│  └──────────┘  └──────────┘  │(Â,R̂)    │  └───────────┘  │
│                               └──────────┘         │        │
│                                                     ▼        │
│                                             ┌───────────┐   │
│                                             │ Evaluation│   │
│                                             │(R̂,R)→ΔR │   │
│                                             └───────────┘   │
│                                                     │        │
│                                                     ▼        │
│                                             ┌───────────┐   │
│                                             │  Skill    │   │
│                                             │ Promotion │   │
│                                             └───────────┘   │
└─────────────────────────────────────────────────────────────┘
      │
      ▼
[ Final KSTARState ]
```

### Layered Architecture

```
[ CLI / API entry point ]   ← kstar_cli.py
         ↓
[ KSTAR Orchestrator ]      ← kstar_orchestrator.py
         ↓
[ KSTAR Steps ]             ← kstar_steps.py
         ↓
[ Anthropic Agent SDK ]     ← claude_agent_sdk (ClaudeSDKClient)
         ↓
[ Skill Registry ]          ← kstar_skills.py  (JSON persistence)
```

---

## The KSTAR State Object

Every transformation step is a pure function `KSTARState → KSTARState`.
The state carries all information needed to resume, branch, or audit a run:

```json
{
  "run_id": "uuid",
  "raw_input": "...",
  "status": "completed",
  "S": { "description": "...", "resources": [], "constraints": [] },
  "T": { "description": "...", "success_criteria": [], "complexity": "simple" },
  "K": { "domain_facts": {}, "retrieved_plans": [], "promoted_skills": [] },
  "plan": { "name": "...", "steps": [...] },
  "expected_result": { "summary": "...", "confidence": 0.85 },
  "action_trace": [...],
  "result": { "summary": "...", "outputs": [...] },
  "delta": { "score": 0.9, "promote_to_skill": true }
}
```

---

## Canonical Step Types

| Step | Function | Type Signature |
|---|---|---|
| ST Refine | Parse raw input → (S, T) | `Σ → (S, T)` |
| Plan Retrieval | Retrieve candidate plans | `(S, T) → Plans[]` |
| Plan Forecast | Select plan + forecast result | `(S, T, P) → (Â, R̂)` |
| Action Execution | Execute plan with tools | `Â → (A, R)` |
| Evaluation | Compare expected vs actual | `(R̂, R) → ΔR` |

---

## Installation

```bash
pip install claude-agent-sdk pydantic
export ANTHROPIC_API_KEY=your-api-key
```

---

## Usage

### Python API

```python
import asyncio
from kstar_agent import run_kstar, KSTAROrchestrator

# Simple one-shot execution
state = asyncio.run(run_kstar("Research the latest advances in quantum computing"))
print(f"Status : {state.status}")
print(f"ΔR     : {state.delta.score:.2f}")
print(f"Result : {state.result.summary}")

# Full orchestrator with checkpoint persistence
orchestrator = KSTAROrchestrator(checkpoint_dir="./checkpoints")
state = asyncio.run(orchestrator.run("Write a Python web scraper for Hacker News"))
```

### CLI

```bash
# Run the full KSTAR pipeline
python kstar_cli.py run "Research quantum computing advances"

# Run with checkpoint persistence and save final state
python kstar_cli.py run "Write a Python web scraper" \
    --checkpoints ./checkpoints \
    --output final_state.json

# List all promoted skills
python kstar_cli.py skills list

# Search for a skill
python kstar_cli.py skills search "web research"

# Inspect a saved state
python kstar_cli.py state show ./checkpoints/<run_id>_completed.json
```

---

## Recursive Execution

For tasks classified as `complexity: complex`, the orchestrator spawns
sub-KSTAR loops for each sub-goal:

```python
from kstar_agent import KSTARState, TaskGoal, ComplexityLevel

# The orchestrator automatically recurses when T.complexity == "complex"
# and T.sub_goals is populated by the ST Refine step.
```

---

## Skill Promotion

After a successful run (ΔR score ≥ 0.8), the execution trace is
generalised and stored in the skill registry:

```
KSTAR trace → generalised → KSTARSkill (JSON)
```

Promoted skills are automatically injected into the knowledge base (K)
of future runs, accelerating plan retrieval.

---

## File Structure

```
kstar_agent/
├── __init__.py              # Public API
├── kstar_state.py           # KSTARState and all sub-models (Pydantic)
├── kstar_steps.py           # Five canonical transformation steps
├── kstar_orchestrator.py    # Orchestrator + recursive execution
├── kstar_skills.py          # Skill registry with JSON persistence
├── kstar_cli.py             # CLI entry point
├── kstar_skills_registry.json  # Auto-generated skill registry
└── README.md
```

---

## Key Design Decisions

**Why `ClaudeSDKClient` for action execution?**
The `ClaudeSDKClient` maintains a persistent session, allowing the agent
to use tools (Bash, Read, Write, Edit, Grep, WebSearch, etc.) and retain
context across multiple exchanges within a single execution step.

**Why `query()` for reasoning steps?**
Steps 1–3 and 5 are reasoning-only (no tool use).  The lighter `query()`
function is sufficient and avoids the overhead of a persistent session.

**Why Pydantic for the state?**
Pydantic provides type safety, JSON serialisation, and schema validation
— ensuring that every step receives and returns a well-formed state object.
