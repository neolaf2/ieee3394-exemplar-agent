"""
kstar_orchestrator.py
---------------------
The KSTAR Orchestrator controls the flow of state through the five
canonical transformation steps and handles:

  - Linear execution (simple tasks)
  - Recursive execution (complex tasks → sub-KSTAR loops)
  - Skill promotion (successful traces → reusable skills)
  - State persistence (checkpoint after each step)

Architecture (from the design document):

    [ CLI / API entry point ]
           ↓
    [ KSTAR Orchestrator ]   ← this module
           ↓
    [ KSTAR Steps ]          ← kstar_steps.py
           ↓
    [ Anthropic Agent SDK ]  ← claude_agent_sdk
           ↓
    [ Skill Registry ]       ← kstar_skills.py
"""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Optional

from kstar_skills import KSTARSkillRegistry
from kstar_state import (
    ComplexityLevel,
    KSTARState,
    KSTARStatus,
    StateContext,
    TaskGoal,
)
from kstar_steps import (
    action_exec,
    evaluate,
    plan_forecast,
    plan_retrieval,
    st_refine,
)

logger = logging.getLogger(__name__)

# Maximum recursion depth to prevent infinite loops
MAX_DEPTH = 4

# Minimum ΔR score to consider a run successful
SUCCESS_THRESHOLD = 0.7


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _is_complex(state: KSTARState) -> bool:
    """Return True if the task requires recursive decomposition."""
    return (
        state.T.complexity == ComplexityLevel.COMPLEX
        and state.depth < MAX_DEPTH
    )


def _create_subtask(parent: KSTARState, sub_goal: TaskGoal) -> KSTARState:
    """
    Spawn a child KSTARState for a sub-goal.

    The child inherits the parent's knowledge base and context but gets
    its own run_id and action trace.
    """
    child = KSTARState(
        raw_input=sub_goal.description,
        depth=parent.depth + 1,
        parent_run_id=parent.run_id,
        S=parent.S.model_copy(),
        K=parent.K.model_copy(),
    )
    child.T = sub_goal
    parent.sub_run_ids.append(child.run_id)
    return child


def _integrate_subtask(parent: KSTARState, child: KSTARState) -> KSTARState:
    """
    Merge the child's result back into the parent state.

    The parent's action trace is extended with the child's trace, and
    the parent's result summary is updated.
    """
    parent.action_trace.extend(child.action_trace)
    if child.result:
        if parent.result is None:
            from kstar_state import ActualResult
            parent.result = ActualResult()
        parent.result.outputs.extend(child.result.outputs)
        parent.result.summary += f"\n[Sub-task {child.run_id[:8]}]: {child.result.summary}"
        parent.result.raw_agent_output += f"\n\n--- Sub-task ---\n{child.result.raw_agent_output}"
    return parent


# ---------------------------------------------------------------------------
# Core orchestrator
# ---------------------------------------------------------------------------

class KSTAROrchestrator:
    """
    Stateful KSTAR orchestrator.

    Runs the full KSTAR pipeline for a given input and manages:
      - Step sequencing
      - Recursive sub-task spawning
      - State persistence
      - Skill promotion
    """

    def __init__(
        self,
        registry: Optional[KSTARSkillRegistry] = None,
        checkpoint_dir: Optional[str | Path] = None,
    ) -> None:
        self.registry = registry or KSTARSkillRegistry()
        self.registry.load()
        self.checkpoint_dir = Path(checkpoint_dir) if checkpoint_dir else None
        if self.checkpoint_dir:
            self.checkpoint_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run(self, prompt: str) -> KSTARState:
        """
        Execute a full KSTAR pipeline for the given prompt.

        Returns the final KSTARState after all steps have completed.
        """
        state = KSTARState(raw_input=prompt)
        logger.info("=" * 60)
        logger.info("[KSTAR] Starting run %s", state.run_id)
        logger.info("  Prompt: %s", prompt[:120])
        logger.info("=" * 60)

        try:
            state = await self._run_pipeline(state)
        except Exception as exc:
            logger.error("[KSTAR] Run %s FAILED: %s", state.run_id, exc, exc_info=True)
            state.status = KSTARStatus.FAILED
        finally:
            self._checkpoint(state)

        return state

    # ------------------------------------------------------------------
    # Internal pipeline
    # ------------------------------------------------------------------

    async def _run_pipeline(self, state: KSTARState) -> KSTARState:
        """Execute the five KSTAR steps with optional recursion."""

        # ── Step 1: ST Refine ──────────────────────────────────────────
        state = await st_refine(state)
        self._checkpoint(state)

        # Inject promoted skills into the knowledge base
        if state.T.description:
            matching = self.registry.search(state.T.description, limit=3)
            state.K.promoted_skills = [s.name for s in matching]
            logger.info(
                "[KSTAR] Injected %d promoted skill(s) into knowledge base.",
                len(matching),
            )

        # ── Step 2: Plan Retrieval ─────────────────────────────────────
        state = await plan_retrieval(state)
        self._checkpoint(state)

        # ── Step 3: Plan Forecast ──────────────────────────────────────
        state = await plan_forecast(state)
        self._checkpoint(state)

        # ── Step 4: Action Execution (with optional recursion) ─────────
        if _is_complex(state):
            logger.info(
                "[KSTAR] Task is COMPLEX (depth=%d) — spawning sub-KSTAR loops.",
                state.depth,
            )
            state = await self._recursive_exec(state)
        else:
            state = await action_exec(state)
            self._checkpoint(state)

        # ── Step 5: Evaluation ─────────────────────────────────────────
        state = await evaluate(state)
        self._checkpoint(state)

        # ── Skill Promotion ────────────────────────────────────────────
        if state.delta and state.delta.promote_to_skill:
            skill = self.registry.promote(state)
            if skill:
                logger.info(
                    "[KSTAR] New skill promoted: '%s' (id=%s)",
                    skill.name,
                    skill.skill_id,
                )

        logger.info(
            "[KSTAR] Run %s completed.  Status=%s  ΔR=%.2f",
            state.run_id,
            state.status,
            state.delta.score if state.delta else 0.0,
        )
        return state

    async def _recursive_exec(self, state: KSTARState) -> KSTARState:
        """
        Decompose a complex task into sub-goals and execute each
        recursively via a child KSTAR pipeline.
        """
        sub_goals = state.T.sub_goals or []

        if not sub_goals:
            # If no explicit sub-goals, fall back to direct execution
            logger.warning(
                "[KSTAR] Complex task has no sub-goals defined; falling back to direct execution."
            )
            return await action_exec(state)

        for sub_goal in sub_goals:
            child_state = _create_subtask(state, sub_goal)
            logger.info(
                "[KSTAR] Spawning sub-task (depth=%d): %s",
                child_state.depth,
                sub_goal.description[:80],
            )
            child_state = await self._run_pipeline(child_state)
            state = _integrate_subtask(state, child_state)
            self._checkpoint(state)

        return state

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def _checkpoint(self, state: KSTARState) -> None:
        """Save the current state to the checkpoint directory (if configured)."""
        if self.checkpoint_dir is None:
            return
        path = self.checkpoint_dir / f"{state.run_id}_{state.status}.json"
        state.save(path)
        logger.debug("[KSTAR] Checkpoint saved: %s", path)


# ---------------------------------------------------------------------------
# Convenience function
# ---------------------------------------------------------------------------

async def run_kstar(
    prompt: str,
    checkpoint_dir: Optional[str | Path] = None,
    registry_path: Optional[str | Path] = None,
) -> KSTARState:
    """
    High-level entry point: run the full KSTAR pipeline for a prompt.

    Args:
        prompt:         The raw user request.
        checkpoint_dir: Directory to save state checkpoints.  Optional.
        registry_path:  Path to the skill registry JSON file.  Optional.

    Returns:
        The final KSTARState after all steps have completed.
    """
    registry = KSTARSkillRegistry(registry_path) if registry_path else KSTARSkillRegistry()
    orchestrator = KSTAROrchestrator(
        registry=registry,
        checkpoint_dir=checkpoint_dir,
    )
    return await orchestrator.run(prompt)
