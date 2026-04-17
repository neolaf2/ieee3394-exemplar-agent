"""
kstar_state.py
--------------
Defines the canonical KSTAR state object and all supporting data models.

The KSTAR state is the single source of truth passed between every transformation
step in the pipeline.  Each step is a pure function:

    KSTARState -> KSTARState

This file also provides persistence helpers (save / load JSON) so that the
orchestrator can resume a run from any checkpoint.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------

class KSTARStatus(str, Enum):
    """Lifecycle status of a KSTAR execution run."""
    INITIALIZED  = "initialized"
    ST_REFINING  = "st_refining"
    PLANNING     = "planning"
    FORECASTING  = "forecasting"
    EXECUTING    = "executing"
    EVALUATING   = "evaluating"
    COMPLETED    = "completed"
    FAILED       = "failed"


class ComplexityLevel(str, Enum):
    """Task complexity classification used to decide whether to recurse."""
    SIMPLE   = "simple"
    MODERATE = "moderate"
    COMPLEX  = "complex"


# ---------------------------------------------------------------------------
# Sub-models
# ---------------------------------------------------------------------------

class StateContext(BaseModel):
    """
    S — the situational context in which the task is being performed.

    Captures background knowledge, available resources, constraints, and
    any prior results that are relevant to the current task.
    """
    description: str = ""
    resources: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    background: Dict[str, Any] = Field(default_factory=dict)


class TaskGoal(BaseModel):
    """
    T — the task / goal the agent must accomplish.

    Includes a natural-language description, success criteria, and a
    complexity estimate used by the orchestrator for recursion decisions.
    """
    description: str = ""
    success_criteria: List[str] = Field(default_factory=list)
    complexity: ComplexityLevel = ComplexityLevel.SIMPLE
    sub_goals: List["TaskGoal"] = Field(default_factory=list)


class KnowledgeBase(BaseModel):
    """
    K — the knowledge / skills available to the agent.

    Includes retrieved plans (archetypes), domain facts, and promoted
    skills that were learned from prior successful KSTAR traces.
    """
    domain_facts: Dict[str, Any] = Field(default_factory=dict)
    retrieved_plans: List[Dict[str, Any]] = Field(default_factory=list)
    promoted_skills: List[str] = Field(default_factory=list)


class PlanStep(BaseModel):
    """A single step within a KSTAR execution plan."""
    step_id: int
    action: str
    tool: Optional[str] = None
    parameters: Dict[str, Any] = Field(default_factory=dict)
    rationale: str = ""


class Plan(BaseModel):
    """A fully structured KSTAR execution plan."""
    plan_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    steps: List[PlanStep] = Field(default_factory=list)
    archetype: str = ""


class ExpectedResult(BaseModel):
    """
    R̂ — the forecast of what the agent expects to achieve.

    Generated during the Plan Forecast step and compared against the
    actual result in the Evaluation step to compute ΔR.
    """
    summary: str = ""
    expected_outputs: List[str] = Field(default_factory=list)
    expected_side_effects: List[str] = Field(default_factory=list)
    confidence: float = 0.0


class ActionRecord(BaseModel):
    """A single entry in the action trace, recording what was actually done."""
    step_id: int
    tool_used: str = ""
    input_given: Dict[str, Any] = Field(default_factory=dict)
    output_received: str = ""
    success: bool = True
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


class ActualResult(BaseModel):
    """R — the actual result produced by action execution."""
    summary: str = ""
    outputs: List[str] = Field(default_factory=list)
    side_effects: List[str] = Field(default_factory=list)
    raw_agent_output: str = ""


class EvaluationDelta(BaseModel):
    """
    ΔR — the delta between the expected and actual result.

    A positive delta (score close to 1.0) indicates the agent performed
    well and the trace is a candidate for skill promotion.
    """
    score: float = 0.0          # 0.0 = total failure, 1.0 = perfect match
    matched_criteria: List[str] = Field(default_factory=list)
    missed_criteria: List[str] = Field(default_factory=list)
    unexpected_outputs: List[str] = Field(default_factory=list)
    notes: str = ""
    promote_to_skill: bool = False


# ---------------------------------------------------------------------------
# Root state object
# ---------------------------------------------------------------------------

class KSTARState(BaseModel):
    """
    The canonical KSTAR state object.

    Every transformation step in the pipeline receives this object and
    returns an updated copy.  The state is serialisable to / from JSON
    so that it can be persisted between runs or passed to sub-agents.
    """

    # Unique identifier for this execution run
    run_id: str = Field(default_factory=lambda: str(uuid.uuid4()))

    # Raw user input that initiated this run
    raw_input: str = ""

    # Lifecycle status
    status: KSTARStatus = KSTARStatus.INITIALIZED

    # Core KSTAR components
    S: StateContext = Field(default_factory=StateContext)
    T: TaskGoal = Field(default_factory=TaskGoal)
    K: KnowledgeBase = Field(default_factory=KnowledgeBase)

    # Pipeline outputs
    plan: Optional[Plan] = None
    expected_result: Optional[ExpectedResult] = None
    action_trace: List[ActionRecord] = Field(default_factory=list)
    result: Optional[ActualResult] = None
    delta: Optional[EvaluationDelta] = None

    # Recursion tracking
    depth: int = 0
    parent_run_id: Optional[str] = None
    sub_run_ids: List[str] = Field(default_factory=list)

    # Timestamps
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # ---------------------------------------------------------------------------
    # Helpers
    # ---------------------------------------------------------------------------

    def touch(self) -> "KSTARState":
        """Update the `updated_at` timestamp and return self for chaining."""
        self.updated_at = datetime.now(timezone.utc).isoformat()
        return self

    def save(self, path: str | Path) -> None:
        """Persist the state to a JSON file."""
        Path(path).write_text(
            self.model_dump_json(indent=2), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: str | Path) -> "KSTARState":
        """Load a previously persisted state from a JSON file."""
        raw = Path(path).read_text(encoding="utf-8")
        return cls.model_validate_json(raw)

    def to_dict(self) -> Dict[str, Any]:
        """Return the state as a plain Python dictionary."""
        return json.loads(self.model_dump_json())


# Allow forward references in TaskGoal.sub_goals
TaskGoal.model_rebuild()
