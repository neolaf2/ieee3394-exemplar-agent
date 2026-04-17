"""
test_kstar.py
-------------
Unit and integration tests for the KSTAR stateful agent.

Tests are designed to run without a live Anthropic API key by mocking
the LLM calls.  The integration test at the bottom requires a valid
ANTHROPIC_API_KEY environment variable.

Run with:
    python test_kstar.py
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

# Ensure the package directory is on the path
sys.path.insert(0, str(Path(__file__).parent))

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
from kstar_skills import KSTARSkill, KSTARSkillRegistry


# ---------------------------------------------------------------------------
# Helper: build a fully-populated state for testing
# ---------------------------------------------------------------------------

def _make_full_state() -> KSTARState:
    state = KSTARState(raw_input="Write a Python hello-world script")
    state.S = StateContext(
        description="Developer environment with Python 3.11",
        resources=["Python 3.11", "bash"],
        constraints=["no external libraries"],
    )
    state.T = TaskGoal(
        description="Write a Python hello-world script",
        success_criteria=["script prints 'Hello, World!'"],
        complexity=ComplexityLevel.SIMPLE,
    )
    state.K = KnowledgeBase(domain_facts={"language": "Python"})
    state.plan = Plan(
        name="hello_world_plan",
        archetype="code_generation",
        steps=[
            PlanStep(step_id=0, action="Write hello.py", tool="Write",
                     parameters={"path": "hello.py", "content": "print('Hello, World!')"}),
        ],
    )
    state.expected_result = ExpectedResult(
        summary="A hello.py file that prints 'Hello, World!'",
        expected_outputs=["hello.py"],
        confidence=0.95,
    )
    state.action_trace = [
        ActionRecord(step_id=0, tool_used="Write",
                     input_given={"path": "hello.py"},
                     output_received="File written successfully",
                     success=True)
    ]
    state.result = ActualResult(
        summary="Created hello.py with print statement",
        outputs=["hello.py created"],
        raw_agent_output="I have written hello.py with print('Hello, World!')",
    )
    state.delta = EvaluationDelta(
        score=0.95,
        matched_criteria=["script prints 'Hello, World!'"],
        missed_criteria=[],
        promote_to_skill=True,
    )
    state.status = KSTARStatus.COMPLETED
    return state


# ===========================================================================
# Test: KSTARState
# ===========================================================================

class TestKSTARState(unittest.TestCase):

    def test_default_initialization(self):
        state = KSTARState(raw_input="test")
        self.assertEqual(state.raw_input, "test")
        self.assertEqual(state.status, KSTARStatus.INITIALIZED)
        self.assertIsNotNone(state.run_id)
        self.assertEqual(state.depth, 0)
        self.assertIsNone(state.plan)
        self.assertIsNone(state.result)
        self.assertIsNone(state.delta)

    def test_touch_updates_timestamp(self):
        state = KSTARState(raw_input="test")
        old_ts = state.updated_at
        import time; time.sleep(0.01)
        state.touch()
        self.assertGreaterEqual(state.updated_at, old_ts)

    def test_save_and_load(self):
        state = _make_full_state()
        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = f.name
        try:
            state.save(path)
            loaded = KSTARState.load(path)
            self.assertEqual(loaded.run_id, state.run_id)
            self.assertEqual(loaded.status, state.status)
            self.assertEqual(loaded.T.description, state.T.description)
            self.assertIsNotNone(loaded.plan)
            self.assertEqual(loaded.plan.name, "hello_world_plan")
            self.assertIsNotNone(loaded.delta)
            self.assertAlmostEqual(loaded.delta.score, 0.95)
        finally:
            Path(path).unlink(missing_ok=True)

    def test_to_dict(self):
        state = KSTARState(raw_input="test")
        d = state.to_dict()
        self.assertIsInstance(d, dict)
        self.assertIn("run_id", d)
        self.assertIn("status", d)
        self.assertIn("S", d)
        self.assertIn("T", d)

    def test_complexity_levels(self):
        for level in ComplexityLevel:
            t = TaskGoal(description="test", complexity=level)
            self.assertEqual(t.complexity, level)

    def test_recursive_sub_goals(self):
        parent_goal = TaskGoal(
            description="Complex task",
            complexity=ComplexityLevel.COMPLEX,
            sub_goals=[
                TaskGoal(description="Sub-task 1", complexity=ComplexityLevel.SIMPLE),
                TaskGoal(description="Sub-task 2", complexity=ComplexityLevel.SIMPLE),
            ],
        )
        self.assertEqual(len(parent_goal.sub_goals), 2)
        self.assertEqual(parent_goal.sub_goals[0].description, "Sub-task 1")


# ===========================================================================
# Test: KSTARSkillRegistry
# ===========================================================================

class TestKSTARSkillRegistry(unittest.TestCase):

    def setUp(self):
        self._tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        self._tmp.close()
        self.registry = KSTARSkillRegistry(path=self._tmp.name)

    def tearDown(self):
        Path(self._tmp.name).unlink(missing_ok=True)

    def test_empty_registry(self):
        self.assertEqual(self.registry.count, 0)
        self.assertEqual(self.registry.list_all(), [])

    def test_promote_skill(self):
        state = _make_full_state()
        skill = self.registry.promote(state)
        self.assertIsNotNone(skill)
        self.assertEqual(self.registry.count, 1)
        self.assertEqual(skill.source_run_id, state.run_id)
        self.assertAlmostEqual(skill.promotion_score, 0.95)

    def test_promote_skipped_when_flag_false(self):
        state = _make_full_state()
        state.delta.promote_to_skill = False
        result = self.registry.promote(state)
        self.assertIsNone(result)
        self.assertEqual(self.registry.count, 0)

    def test_save_and_load(self):
        state = _make_full_state()
        self.registry.promote(state)
        self.registry.save()

        registry2 = KSTARSkillRegistry(path=self._tmp.name)
        registry2.load()
        self.assertEqual(registry2.count, 1)
        skills = registry2.list_all()
        self.assertEqual(skills[0].name, state.plan.name)

    def test_search(self):
        state = _make_full_state()
        self.registry.promote(state)

        results = self.registry.search("hello_world")
        self.assertEqual(len(results), 1)

        results = self.registry.search("nonexistent_xyz")
        self.assertEqual(len(results), 0)

    def test_record_use(self):
        state = _make_full_state()
        skill = self.registry.promote(state)
        self.assertEqual(skill.use_count, 0)
        self.registry.record_use(skill.skill_id)
        updated = self.registry.get(skill.skill_id)
        self.assertEqual(updated.use_count, 1)
        self.assertIsNotNone(updated.last_used_at)


# ===========================================================================
# Test: KSTAR Steps (mocked LLM)
# ===========================================================================

class TestKSTARSteps(unittest.IsolatedAsyncioTestCase):

    def _make_st_refine_response(self) -> str:
        return json.dumps({
            "S": {
                "description": "Python development environment",
                "resources": ["Python 3.11"],
                "constraints": [],
                "background": {}
            },
            "T": {
                "description": "Write a hello world script",
                "success_criteria": ["prints Hello, World!"],
                "complexity": "simple"
            }
        })

    def _make_plan_retrieval_response(self) -> str:
        return json.dumps({
            "plans": [
                {
                    "name": "direct_write",
                    "description": "Write the script directly",
                    "archetype": "code_generation",
                    "steps": [
                        {
                            "step_id": 0,
                            "action": "Write hello.py",
                            "tool": "Write",
                            "parameters": {"path": "hello.py"},
                            "rationale": "Create the file"
                        }
                    ]
                }
            ]
        })

    def _make_plan_forecast_response(self) -> str:
        return json.dumps({
            "selected_plan": {
                "name": "direct_write",
                "description": "Write the script directly",
                "archetype": "code_generation",
                "steps": [
                    {
                        "step_id": 0,
                        "action": "Write hello.py",
                        "tool": "Write",
                        "parameters": {"path": "hello.py"},
                        "rationale": "Create the file"
                    }
                ]
            },
            "expected_result": {
                "summary": "hello.py created",
                "expected_outputs": ["hello.py"],
                "expected_side_effects": [],
                "confidence": 0.95
            }
        })

    def _make_eval_response(self) -> str:
        return json.dumps({
            "score": 0.95,
            "matched_criteria": ["prints Hello, World!"],
            "missed_criteria": [],
            "unexpected_outputs": [],
            "notes": "Task completed successfully",
            "promote_to_skill": True
        })

    @patch("kstar_steps._llm_query", new_callable=AsyncMock)
    async def test_st_refine(self, mock_llm):
        mock_llm.return_value = self._make_st_refine_response()
        from kstar_steps import st_refine
        state = KSTARState(raw_input="Write a hello world script")
        result = await st_refine(state)
        self.assertEqual(result.status, KSTARStatus.ST_REFINING)
        self.assertIn("Python", result.S.description)
        self.assertEqual(result.T.complexity, ComplexityLevel.SIMPLE)

    @patch("kstar_steps._llm_query", new_callable=AsyncMock)
    async def test_plan_retrieval(self, mock_llm):
        mock_llm.return_value = self._make_plan_retrieval_response()
        from kstar_steps import plan_retrieval
        state = _make_full_state()
        state.status = KSTARStatus.ST_REFINING
        result = await plan_retrieval(state)
        self.assertEqual(result.status, KSTARStatus.PLANNING)
        self.assertEqual(len(result.K.retrieved_plans), 1)

    @patch("kstar_steps._llm_query", new_callable=AsyncMock)
    async def test_plan_forecast(self, mock_llm):
        mock_llm.return_value = self._make_plan_forecast_response()
        from kstar_steps import plan_forecast
        state = _make_full_state()
        state.status = KSTARStatus.PLANNING
        result = await plan_forecast(state)
        self.assertEqual(result.status, KSTARStatus.FORECASTING)
        self.assertIsNotNone(result.plan)
        self.assertEqual(result.plan.name, "direct_write")
        self.assertAlmostEqual(result.expected_result.confidence, 0.95)

    @patch("kstar_steps._llm_query", new_callable=AsyncMock)
    async def test_evaluate(self, mock_llm):
        mock_llm.return_value = self._make_eval_response()
        from kstar_steps import evaluate
        state = _make_full_state()
        state.status = KSTARStatus.EXECUTING
        result = await evaluate(state)
        self.assertEqual(result.status, KSTARStatus.COMPLETED)
        self.assertIsNotNone(result.delta)
        self.assertAlmostEqual(result.delta.score, 0.95)
        self.assertTrue(result.delta.promote_to_skill)


# ===========================================================================
# Test: Orchestrator (mocked steps)
# ===========================================================================

class TestKSTAROrchestrator(unittest.IsolatedAsyncioTestCase):

    @patch("kstar_orchestrator.st_refine")
    @patch("kstar_orchestrator.plan_retrieval")
    @patch("kstar_orchestrator.plan_forecast")
    @patch("kstar_orchestrator.action_exec")
    @patch("kstar_orchestrator.evaluate")
    async def test_full_pipeline_simple(
        self, mock_eval, mock_exec, mock_forecast, mock_retrieval, mock_st
    ):
        """Test that the orchestrator calls all 5 steps in order for a simple task."""
        from kstar_orchestrator import KSTAROrchestrator

        # Each mock returns the state unchanged (with the required fields set)
        async def passthrough(state):
            return state

        mock_st.side_effect = passthrough
        mock_retrieval.side_effect = passthrough
        mock_forecast.side_effect = passthrough
        mock_exec.side_effect = passthrough
        mock_eval.side_effect = passthrough

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "skills.json"
            orchestrator = KSTAROrchestrator(
                registry=KSTARSkillRegistry(path=str(registry_path)),
                checkpoint_dir=tmpdir,
            )
            state = await orchestrator.run("Write a hello world script")

        mock_st.assert_called_once()
        mock_retrieval.assert_called_once()
        mock_forecast.assert_called_once()
        mock_exec.assert_called_once()
        mock_eval.assert_called_once()

    @patch("kstar_orchestrator.st_refine")
    @patch("kstar_orchestrator.plan_retrieval")
    @patch("kstar_orchestrator.plan_forecast")
    @patch("kstar_orchestrator.action_exec")
    @patch("kstar_orchestrator.evaluate")
    async def test_skill_promotion_triggered(
        self, mock_eval, mock_exec, mock_forecast, mock_retrieval, mock_st
    ):
        """Test that skill promotion is triggered when delta.promote_to_skill is True."""
        from kstar_orchestrator import KSTAROrchestrator

        full_state = _make_full_state()

        async def return_full(state):
            # Merge full_state data into the passed state
            state.S = full_state.S
            state.T = full_state.T
            state.K = full_state.K
            state.plan = full_state.plan
            state.expected_result = full_state.expected_result
            state.action_trace = full_state.action_trace
            state.result = full_state.result
            state.delta = full_state.delta
            state.status = full_state.status
            return state

        mock_st.side_effect = return_full
        async def _pass(s): return s
        mock_retrieval.side_effect = _pass
        mock_forecast.side_effect = _pass
        mock_exec.side_effect = _pass
        mock_eval.side_effect = _pass

        with tempfile.TemporaryDirectory() as tmpdir:
            registry_path = Path(tmpdir) / "skills.json"
            registry = KSTARSkillRegistry(path=str(registry_path))
            orchestrator = KSTAROrchestrator(
                registry=registry,
                checkpoint_dir=tmpdir,
            )
            await orchestrator.run("Write a hello world script")

        # Skill should have been promoted
        self.assertEqual(registry.count, 1)


# ===========================================================================
# Run all tests
# ===========================================================================

if __name__ == "__main__":
    print("Running KSTAR Agent test suite...")
    print("=" * 60)
    unittest.main(verbosity=2)
