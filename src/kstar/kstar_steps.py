"""
kstar_steps.py
--------------
Implements the five canonical KSTAR transformation steps.

Each step is an async function with the signature:

    async def step_name(state: KSTARState) -> KSTARState

The internal structure of every step follows the four-phase pattern
described in the architecture document:

    1. Deterministic pre-processing
    2. LLM reasoning via the Anthropic Claude Agent SDK
    3. Structured output validation (Pydantic)
    4. State update

The Anthropic Claude Agent SDK (claude_agent_sdk) is used for all
LLM interactions.  The ClaudeSDKClient maintains a persistent session
across the action-execution step, while the lighter query() helper is
used for the reasoning-only steps.
"""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

from claude_agent_sdk import (
    AssistantMessage,
    ClaudeAgentOptions,
    ClaudeSDKClient,
    ResultMessage,
    TextBlock,
    query,
)

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

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

async def _llm_query(system_prompt: str, user_prompt: str) -> str:
    """
    Run a single-turn LLM query using the Agent SDK's query() function.

    Returns the concatenated text from all AssistantMessage blocks.
    """
    options = ClaudeAgentOptions(
        system_prompt=system_prompt,
        allowed_tools=[],          # reasoning-only; no tool execution
        permission_mode="default",
    )
    parts: List[str] = []
    async for message in query(prompt=user_prompt, options=options):
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    parts.append(block.text)
    return "\n".join(parts).strip()


def _extract_json(text: str) -> Dict[str, Any]:
    """
    Extract the first JSON object or array from a string.

    The LLM is instructed to return JSON, but it may wrap it in markdown
    fences.  This helper strips the fences and parses the JSON.
    """
    # Strip markdown code fences if present
    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.splitlines()
        # Remove first and last fence lines
        cleaned = "\n".join(lines[1:-1] if lines[-1].strip() == "```" else lines[1:])
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # Fall back: find the first { ... } block
        start = cleaned.find("{")
        end = cleaned.rfind("}") + 1
        if start != -1 and end > start:
            return json.loads(cleaned[start:end])
        raise ValueError(f"Could not extract JSON from LLM output:\n{text}")


# ---------------------------------------------------------------------------
# Step 1 — ST Refine   (Σ → (S, T))
# ---------------------------------------------------------------------------

SYSTEM_ST_REFINE = """
You are the ST-Refine component of a KSTAR agent pipeline.

Your job is to parse a raw user request and decompose it into two structured
components:

  S (State / Context): the situational context, available resources,
    constraints, and background knowledge relevant to the task.

  T (Task / Goal): the specific goal the agent must accomplish, including
    success criteria and a complexity estimate.

Respond ONLY with a valid JSON object matching this schema:
{
  "S": {
    "description": "<string>",
    "resources": ["<string>", ...],
    "constraints": ["<string>", ...],
    "background": {}
  },
  "T": {
    "description": "<string>",
    "success_criteria": ["<string>", ...],
    "complexity": "simple" | "moderate" | "complex"
  }
}
""".strip()


async def st_refine(state: KSTARState) -> KSTARState:
    """
    Step 1: Parse raw input into structured (S, T) components.

    Type signature:  Σ → (S, T)
    """
    logger.info("[KSTAR] Step 1 — ST Refine")
    state.status = KSTARStatus.ST_REFINING

    raw = _llm_query(
        system_prompt=SYSTEM_ST_REFINE,
        user_prompt=f"Raw user request:\n{state.raw_input}",
    )
    data = _extract_json(await raw)

    s_data = data.get("S", {})
    t_data = data.get("T", {})

    state.S = StateContext(
        description=s_data.get("description", ""),
        resources=s_data.get("resources", []),
        constraints=s_data.get("constraints", []),
        background=s_data.get("background", {}),
    )
    state.T = TaskGoal(
        description=t_data.get("description", ""),
        success_criteria=t_data.get("success_criteria", []),
        complexity=ComplexityLevel(t_data.get("complexity", "simple")),
    )

    logger.info("  S.description = %s", state.S.description)
    logger.info("  T.description = %s", state.T.description)
    logger.info("  T.complexity  = %s", state.T.complexity)

    return state.touch()


# ---------------------------------------------------------------------------
# Step 2 — Plan Retrieval   ((S, T) → Plans[])
# ---------------------------------------------------------------------------

SYSTEM_PLAN_RETRIEVAL = """
You are the Plan-Retrieval component of a KSTAR agent pipeline.

Given a structured (S, T) pair, retrieve or generate a list of candidate
execution plans.  Each plan must be a concrete, ordered sequence of tool-
backed steps that the agent can execute to achieve the goal T.

Available tools the agent can use:
  Bash, Read, Write, Edit, Glob, Grep, WebFetch, WebSearch, TodoWrite

Respond ONLY with a valid JSON object matching this schema:
{
  "plans": [
    {
      "name": "<string>",
      "description": "<string>",
      "archetype": "<string>",
      "steps": [
        {
          "step_id": <int>,
          "action": "<string>",
          "tool": "<string or null>",
          "parameters": {},
          "rationale": "<string>"
        }
      ]
    }
  ]
}

Return between 1 and 3 candidate plans.
""".strip()


async def plan_retrieval(state: KSTARState) -> KSTARState:
    """
    Step 2: Retrieve candidate plans for the given (S, T).

    Type signature:  (S, T) → Plans[]
    """
    logger.info("[KSTAR] Step 2 — Plan Retrieval")
    state.status = KSTARStatus.PLANNING

    context = json.dumps(
        {
            "S": state.S.model_dump(),
            "T": state.T.model_dump(),
            "promoted_skills": state.K.promoted_skills,
        },
        indent=2,
    )

    raw = _llm_query(
        system_prompt=SYSTEM_PLAN_RETRIEVAL,
        user_prompt=f"Context:\n{context}",
    )
    data = _extract_json(await raw)

    plans_raw = data.get("plans", [])
    state.K.retrieved_plans = plans_raw

    logger.info("  Retrieved %d candidate plan(s)", len(plans_raw))
    for p in plans_raw:
        logger.info("    - %s (%d steps)", p.get("name", "?"), len(p.get("steps", [])))

    return state.touch()


# ---------------------------------------------------------------------------
# Step 3 — Plan Forecast   ((S, T, P) → (Â, R̂))
# ---------------------------------------------------------------------------

SYSTEM_PLAN_FORECAST = """
You are the Plan-Forecast component of a KSTAR agent pipeline.

Given (S, T) and a list of candidate plans, select the BEST plan and
forecast the expected actions (Â) and expected result (R̂).

Respond ONLY with a valid JSON object matching this schema:
{
  "selected_plan": {
    "name": "<string>",
    "description": "<string>",
    "archetype": "<string>",
    "steps": [
      {
        "step_id": <int>,
        "action": "<string>",
        "tool": "<string or null>",
        "parameters": {},
        "rationale": "<string>"
      }
    ]
  },
  "expected_result": {
    "summary": "<string>",
    "expected_outputs": ["<string>", ...],
    "expected_side_effects": ["<string>", ...],
    "confidence": <float 0.0-1.0>
  }
}
""".strip()


async def plan_forecast(state: KSTARState) -> KSTARState:
    """
    Step 3: Select the best plan and forecast (Â, R̂).

    Type signature:  (S, T, P) → (Â, R̂)
    """
    logger.info("[KSTAR] Step 3 — Plan Forecast")
    state.status = KSTARStatus.FORECASTING

    context = json.dumps(
        {
            "S": state.S.model_dump(),
            "T": state.T.model_dump(),
            "candidate_plans": state.K.retrieved_plans,
        },
        indent=2,
    )

    raw = _llm_query(
        system_prompt=SYSTEM_PLAN_FORECAST,
        user_prompt=f"Context:\n{context}",
    )
    data = _extract_json(await raw)

    plan_data = data.get("selected_plan", {})
    steps = [
        PlanStep(
            step_id=s.get("step_id", i),
            action=s.get("action", ""),
            tool=s.get("tool"),
            parameters=s.get("parameters", {}),
            rationale=s.get("rationale", ""),
        )
        for i, s in enumerate(plan_data.get("steps", []))
    ]
    state.plan = Plan(
        name=plan_data.get("name", ""),
        description=plan_data.get("description", ""),
        archetype=plan_data.get("archetype", ""),
        steps=steps,
    )

    er_data = data.get("expected_result", {})
    state.expected_result = ExpectedResult(
        summary=er_data.get("summary", ""),
        expected_outputs=er_data.get("expected_outputs", []),
        expected_side_effects=er_data.get("expected_side_effects", []),
        confidence=float(er_data.get("confidence", 0.5)),
    )

    logger.info("  Selected plan: %s", state.plan.name)
    logger.info("  Expected result: %s", state.expected_result.summary)
    logger.info("  Confidence: %.2f", state.expected_result.confidence)

    return state.touch()


# ---------------------------------------------------------------------------
# Step 4 — Action Execution   (Â → (A, R))
# ---------------------------------------------------------------------------

SYSTEM_ACTION_EXEC = """
You are the Action-Execution component of a KSTAR agent pipeline.

You will be given a task description and a structured plan.  Execute the
plan step by step using the tools available to you.  After completing all
steps, provide a concise summary of what was accomplished.

Be precise, methodical, and verify each step before proceeding to the next.
""".strip()


async def action_exec(state: KSTARState) -> KSTARState:
    """
    Step 4: Execute the selected plan using the Anthropic Agent SDK.

    This step uses ClaudeSDKClient to maintain a persistent session,
    allowing the agent to use tools and maintain context across multiple
    exchanges within the same execution run.

    Type signature:  Â → (A, R)
    """
    logger.info("[KSTAR] Step 4 — Action Execution")
    state.status = KSTARStatus.EXECUTING

    if state.plan is None:
        raise ValueError("Cannot execute: no plan has been selected.")

    plan_text = json.dumps(state.plan.model_dump(), indent=2)
    execution_prompt = (
        f"Task: {state.T.description}\n\n"
        f"Plan to execute:\n{plan_text}\n\n"
        f"Expected result: {state.expected_result.summary if state.expected_result else 'N/A'}\n\n"
        "Execute the plan now.  Use the available tools as needed.  "
        "After completing all steps, summarise what was accomplished."
    )

    options = ClaudeAgentOptions(
        system_prompt=SYSTEM_ACTION_EXEC,
        allowed_tools=["Bash", "Read", "Write", "Edit", "Glob", "Grep",
                       "WebFetch", "WebSearch", "TodoWrite"],
        permission_mode="acceptEdits",
    )

    raw_output_parts: List[str] = []
    action_trace: List[ActionRecord] = []
    step_counter = 0

    async with ClaudeSDKClient(options=options) as client:
        await client.query(execution_prompt)

        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        raw_output_parts.append(block.text)
                        logger.debug("  [assistant] %s", block.text[:120])

            elif isinstance(message, ResultMessage):
                # Record the final result from the agent session
                if message.result:
                    raw_output_parts.append(str(message.result))
                logger.info("  Agent session completed (subtype=%s)", message.subtype)

    raw_output = "\n".join(raw_output_parts).strip()

    # Build a synthetic action record for the overall execution
    action_trace.append(
        ActionRecord(
            step_id=0,
            tool_used="ClaudeSDKClient",
            input_given={"plan": state.plan.model_dump()},
            output_received=raw_output[:2000],  # truncate for storage
            success=True,
        )
    )

    state.action_trace = action_trace
    state.result = ActualResult(
        summary=raw_output[:500],
        outputs=[raw_output],
        raw_agent_output=raw_output,
    )

    logger.info("  Execution complete.  Output length: %d chars", len(raw_output))
    return state.touch()


# ---------------------------------------------------------------------------
# Step 5 — Evaluation   ((R̂, R) → ΔR)
# ---------------------------------------------------------------------------

SYSTEM_EVALUATE = """
You are the Evaluation component of a KSTAR agent pipeline.

Compare the expected result (R̂) with the actual result (R) and compute
the evaluation delta (ΔR).

Respond ONLY with a valid JSON object matching this schema:
{
  "score": <float 0.0-1.0>,
  "matched_criteria": ["<string>", ...],
  "missed_criteria": ["<string>", ...],
  "unexpected_outputs": ["<string>", ...],
  "notes": "<string>",
  "promote_to_skill": <bool>
}

score: 1.0 means the actual result perfectly matches the expected result.
promote_to_skill: set to true if score >= 0.8 and the task was non-trivial.
""".strip()


async def evaluate(state: KSTARState) -> KSTARState:
    """
    Step 5: Evaluate the actual result against the expected result.

    Computes ΔR = R̂ − R and decides whether to promote the trace to a skill.

    Type signature:  (R̂, R) → ΔR
    """
    logger.info("[KSTAR] Step 5 — Evaluation")
    state.status = KSTARStatus.EVALUATING

    if state.expected_result is None or state.result is None:
        state.delta = EvaluationDelta(
            score=0.0,
            notes="Evaluation skipped: missing expected_result or result.",
        )
        state.status = KSTARStatus.COMPLETED
        return state.touch()

    context = json.dumps(
        {
            "task": state.T.model_dump(),
            "expected_result": state.expected_result.model_dump(),
            "actual_result": state.result.model_dump(),
        },
        indent=2,
    )

    raw = _llm_query(
        system_prompt=SYSTEM_EVALUATE,
        user_prompt=f"Evaluation context:\n{context}",
    )
    data = _extract_json(await raw)

    state.delta = EvaluationDelta(
        score=float(data.get("score", 0.0)),
        matched_criteria=data.get("matched_criteria", []),
        missed_criteria=data.get("missed_criteria", []),
        unexpected_outputs=data.get("unexpected_outputs", []),
        notes=data.get("notes", ""),
        promote_to_skill=bool(data.get("promote_to_skill", False)),
    )

    state.status = KSTARStatus.COMPLETED
    logger.info("  ΔR score: %.2f", state.delta.score)
    logger.info("  Promote to skill: %s", state.delta.promote_to_skill)

    return state.touch()
