"""
kstar_agent
-----------
KSTAR Stateful Agent — built on the Anthropic Claude Agent SDK (Python).

Public API::

    from kstar_agent import run_kstar, KSTARState, KSTAROrchestrator

    # Simple one-shot execution
    import asyncio
    state = asyncio.run(run_kstar("Research quantum computing advances"))

    # Full orchestrator with persistence
    from kstar_agent import KSTAROrchestrator
    orchestrator = KSTAROrchestrator(checkpoint_dir="./checkpoints")
    state = asyncio.run(orchestrator.run("Write a Python web scraper"))
"""

from kstar_orchestrator import KSTAROrchestrator, run_kstar
from kstar_skills import KSTARSkill, KSTARSkillRegistry
from kstar_state import (
    ActionRecord,
    ActualResult,
    ComplexityLevel,
    EvaluationDelta,
    ExpectedResult,
    KSTARState,
    KSTARStatus,
    KnowledgeBase,
    Plan,
    PlanStep,
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

__all__ = [
    # Orchestrator
    "KSTAROrchestrator",
    "run_kstar",
    # State
    "KSTARState",
    "KSTARStatus",
    "ComplexityLevel",
    "StateContext",
    "TaskGoal",
    "KnowledgeBase",
    "Plan",
    "PlanStep",
    "ExpectedResult",
    "ActionRecord",
    "ActualResult",
    "EvaluationDelta",
    # Skills
    "KSTARSkill",
    "KSTARSkillRegistry",
    # Steps
    "st_refine",
    "plan_retrieval",
    "plan_forecast",
    "action_exec",
    "evaluate",
]
