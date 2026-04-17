"""
test_kstar_interactive.py
--------------------------
Unit tests for the interactive KSTAR agent (kstar_interactive.py).

All LLM calls and SDK interactions are mocked so no API key is needed.

Run with:
    python test_kstar_interactive.py
"""

from __future__ import annotations

import asyncio
import sys
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from kstar_interactive import ClarificationHandler, InteractiveKSTARAgent
from claude_agent_sdk.types import PermissionResultAllow, PermissionResultDeny


# ---------------------------------------------------------------------------
# Helper: simulate user typing into stdin
# ---------------------------------------------------------------------------

class _FakeInput:
    """Feeds pre-set responses to input() calls one at a time."""

    def __init__(self, responses: list[str]):
        self._responses = iter(responses)

    def __call__(self, prompt: str = "") -> str:
        return next(self._responses, "")


# ===========================================================================
# Test: ClarificationHandler — AskUserQuestion
# ===========================================================================

class TestClarificationHandlerQuestions(unittest.IsolatedAsyncioTestCase):

    async def test_single_choice_question(self):
        """User picks option 2 from a single-select question."""
        handler = ClarificationHandler()
        input_data = {
            "questions": [
                {
                    "question": "Which database should I use?",
                    "header": "Database",
                    "options": [
                        {"label": "PostgreSQL", "description": "Relational, ACID"},
                        {"label": "MongoDB", "description": "Document store"},
                    ],
                    "multiSelect": False,
                }
            ]
        }

        with patch("builtins.input", _FakeInput(["2"])):
            result = await handler(
                tool_name="AskUserQuestion",
                input_data=input_data,
                context=MagicMock(),
            )

        self.assertIsInstance(result, PermissionResultAllow)
        answers = result.updated_input["answers"]
        self.assertEqual(answers["Which database should I use?"], "MongoDB")

    async def test_multi_select_question(self):
        """User picks options 1 and 3 from a multi-select question."""
        handler = ClarificationHandler()
        input_data = {
            "questions": [
                {
                    "question": "Which features do you need?",
                    "header": "Features",
                    "options": [
                        {"label": "Auth", "description": "User authentication"},
                        {"label": "Payments", "description": "Stripe integration"},
                        {"label": "Email", "description": "Transactional email"},
                    ],
                    "multiSelect": True,
                }
            ]
        }

        with patch("builtins.input", _FakeInput(["1,3"])):
            result = await handler(
                tool_name="AskUserQuestion",
                input_data=input_data,
                context=MagicMock(),
            )

        self.assertIsInstance(result, PermissionResultAllow)
        answer = result.updated_input["answers"]["Which features do you need?"]
        self.assertIn("Auth", answer)
        self.assertIn("Email", answer)
        self.assertNotIn("Payments", answer)

    async def test_free_text_question(self):
        """Question with no options → free-text answer."""
        handler = ClarificationHandler()
        input_data = {
            "questions": [
                {
                    "question": "What is the project name?",
                    "header": "Name",
                    "options": [],
                    "multiSelect": False,
                }
            ]
        }

        with patch("builtins.input", _FakeInput(["MyProject"])):
            result = await handler(
                tool_name="AskUserQuestion",
                input_data=input_data,
                context=MagicMock(),
            )

        self.assertIsInstance(result, PermissionResultAllow)
        self.assertEqual(
            result.updated_input["answers"]["What is the project name?"],
            "MyProject",
        )

    async def test_invalid_then_valid_choice(self):
        """User types invalid input first, then a valid choice."""
        handler = ClarificationHandler()
        input_data = {
            "questions": [
                {
                    "question": "Pick one",
                    "header": "Pick",
                    "options": [
                        {"label": "A", "description": "Option A"},
                        {"label": "B", "description": "Option B"},
                    ],
                    "multiSelect": False,
                }
            ]
        }

        with patch("builtins.input", _FakeInput(["99", "abc", "1"])):
            result = await handler(
                tool_name="AskUserQuestion",
                input_data=input_data,
                context=MagicMock(),
            )

        self.assertIsInstance(result, PermissionResultAllow)
        self.assertEqual(result.updated_input["answers"]["Pick one"], "A")

    async def test_clarification_log_populated(self):
        """Clarification log is updated after each question."""
        handler = ClarificationHandler()
        input_data = {
            "questions": [
                {
                    "question": "Env?",
                    "header": "Env",
                    "options": [
                        {"label": "dev", "description": "Development"},
                        {"label": "prod", "description": "Production"},
                    ],
                    "multiSelect": False,
                }
            ]
        }

        with patch("builtins.input", _FakeInput(["1"])):
            await handler("AskUserQuestion", input_data, MagicMock())

        self.assertEqual(len(handler.clarification_log), 1)
        self.assertEqual(handler.clarification_log[0]["type"], "clarification")
        self.assertEqual(
            handler.clarification_log[0]["answers"]["Env?"], "dev"
        )


# ===========================================================================
# Test: ClarificationHandler — Tool approval
# ===========================================================================

class TestClarificationHandlerApproval(unittest.IsolatedAsyncioTestCase):

    async def test_auto_approve_read_tools(self):
        """Read-only tools are auto-approved without prompting."""
        handler = ClarificationHandler()
        for tool in ("Read", "Glob", "Grep", "LS"):
            result = await handler(
                tool_name=tool,
                input_data={"file_path": "/tmp/test"},
                context=MagicMock(),
            )
            self.assertIsInstance(result, PermissionResultAllow, f"Expected auto-approve for {tool}")

    async def test_auto_approve_flag(self):
        """auto_approve=True approves everything without prompting."""
        handler = ClarificationHandler(auto_approve=True)
        result = await handler(
            tool_name="Bash",
            input_data={"command": "rm -rf /"},
            context=MagicMock(),
        )
        self.assertIsInstance(result, PermissionResultAllow)

    async def test_user_approves_bash(self):
        """User types 'y' to approve a Bash command."""
        handler = ClarificationHandler()
        with patch("builtins.input", _FakeInput(["y"])):
            result = await handler(
                tool_name="Bash",
                input_data={"command": "ls /tmp", "description": "List temp files"},
                context=MagicMock(),
            )
        self.assertIsInstance(result, PermissionResultAllow)
        log = handler.clarification_log[-1]
        self.assertEqual(log["decision"], "allow")

    async def test_user_denies_bash(self):
        """User types 'n' to deny a Bash command."""
        handler = ClarificationHandler()
        with patch("builtins.input", _FakeInput(["n", "Too dangerous"])):
            result = await handler(
                tool_name="Bash",
                input_data={"command": "rm /important.txt"},
                context=MagicMock(),
            )
        self.assertIsInstance(result, PermissionResultDeny)
        self.assertIn("Too dangerous", result.message)
        log = handler.clarification_log[-1]
        self.assertEqual(log["decision"], "deny")

    async def test_user_modifies_input(self):
        """User chooses 'm' to modify the tool input."""
        handler = ClarificationHandler()
        # Choices: 'm' → field 1 (command) → new value
        with patch("builtins.input", _FakeInput(["m", "1", "ls /safe"])):
            result = await handler(
                tool_name="Bash",
                input_data={"command": "rm /danger"},
                context=MagicMock(),
            )
        self.assertIsInstance(result, PermissionResultAllow)
        self.assertEqual(result.updated_input["command"], "ls /safe")

    async def test_invalid_then_valid_approval(self):
        """User types garbage first, then 'y'."""
        handler = ClarificationHandler()
        with patch("builtins.input", _FakeInput(["x", "q", "y"])):
            result = await handler(
                tool_name="Write",
                input_data={"file_path": "/tmp/out.txt", "content": "hello"},
                context=MagicMock(),
            )
        self.assertIsInstance(result, PermissionResultAllow)


# ===========================================================================
# Test: InteractiveKSTARAgent
# ===========================================================================

class TestInteractiveKSTARAgent(unittest.IsolatedAsyncioTestCase):

    @patch("kstar_steps.st_refine")
    @patch("kstar_steps.plan_retrieval")
    @patch("kstar_steps.plan_forecast")
    @patch("kstar_steps.evaluate")
    @patch("kstar_interactive.query")
    async def test_full_run_mocked(
        self, mock_query, mock_eval, mock_forecast, mock_retrieval, mock_st
    ):
        """Full pipeline runs without errors when all steps are mocked."""
        from kstar_state import KSTARState, KSTARStatus, ActualResult, EvaluationDelta

        async def passthrough(state):
            return state

        mock_st.side_effect = passthrough
        mock_retrieval.side_effect = passthrough
        mock_forecast.side_effect = passthrough
        mock_eval.side_effect = passthrough

        # Mock the SDK query to yield a ResultMessage
        from claude_agent_sdk import ResultMessage

        async def _fake_query(*args, **kwargs):
            msg = MagicMock(spec=ResultMessage)
            msg.subtype = "success"
            msg.result = "Task completed"
            yield msg

        mock_query.side_effect = _fake_query

        agent = InteractiveKSTARAgent(auto_approve=True)
        state = await agent.run("Write a hello world script")

        mock_st.assert_called_once()
        mock_retrieval.assert_called_once()
        mock_forecast.assert_called_once()
        mock_eval.assert_called_once()

    @patch("kstar_interactive.query")
    async def test_chat_mode(self, mock_query):
        """chat() returns the assistant's text response."""
        from claude_agent_sdk import ResultMessage

        async def _fake_query(*args, **kwargs):
            msg = MagicMock(spec=ResultMessage)
            msg.subtype = "success"
            msg.result = "Paris"
            yield msg

        mock_query.side_effect = _fake_query

        agent = InteractiveKSTARAgent(auto_approve=True)
        result = await agent.chat("What is the capital of France?")
        self.assertIsInstance(result, str)

    async def test_handler_attached_to_agent(self):
        """The agent's ClarificationHandler is wired to the stream queue."""
        agent = InteractiveKSTARAgent()
        self.assertIs(agent.handler.stream_queue, agent._stream_queue)

    async def test_redirect_injects_to_queue(self):
        """Choosing 'r' (redirect) puts a message on the stream queue."""
        queue: asyncio.Queue = asyncio.Queue()
        handler = ClarificationHandler(stream_queue=queue)

        with patch("builtins.input", _FakeInput(["r", "Use PostgreSQL instead"])):
            result = await handler(
                tool_name="Bash",
                input_data={"command": "sqlite3 db.sqlite"},
                context=MagicMock(),
            )

        self.assertIsInstance(result, PermissionResultDeny)
        self.assertFalse(queue.empty())
        msg = await queue.get()
        self.assertEqual(msg, "Use PostgreSQL instead")


# ===========================================================================
# Run all tests
# ===========================================================================

if __name__ == "__main__":
    print("Running KSTAR Interactive Agent test suite…")
    print("=" * 60)
    unittest.main(verbosity=2)
