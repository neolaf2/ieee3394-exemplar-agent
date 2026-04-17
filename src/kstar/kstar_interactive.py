"""
kstar_interactive.py
--------------------
Interactive KSTAR agent that pauses mid-pipeline to ask the user
clarifying questions and to approve tool use — using the Anthropic
Claude Agent SDK's three interaction mechanisms:

  1. can_use_tool callback  — handles AskUserQuestion + tool approvals
  2. Streaming input        — lets the user inject messages mid-run
  3. PreToolUse hook        — keeps the stream open in Python while
                              waiting for can_use_tool

Usage (Python API):
    import asyncio
    from kstar_interactive import InteractiveKSTARAgent

    agent = InteractiveKSTARAgent()
    state = asyncio.run(agent.run("Build a REST API for a todo app"))

Usage (CLI):
    python kstar_interactive.py "Build a REST API for a todo app"
    python kstar_interactive.py --mode plan "Refactor the auth module"
    python kstar_interactive.py --auto-approve "List files in /tmp"
"""

from __future__ import annotations

import asyncio
import sys
import textwrap
from pathlib import Path
from typing import Any, AsyncGenerator

# ---------------------------------------------------------------------------
# SDK imports
# ---------------------------------------------------------------------------
from claude_agent_sdk import ClaudeAgentOptions, ResultMessage, query
from claude_agent_sdk.types import (
    AssistantMessage,
    HookContext,
    HookMatcher,
    PermissionResultAllow,
    PermissionResultDeny,
    SystemMessage,
    TextBlock,
    ToolPermissionContext,
    ToolUseBlock,
)

# ---------------------------------------------------------------------------
# KSTAR state
# ---------------------------------------------------------------------------
from kstar_state import KSTARState, KSTARStatus
from kstar_orchestrator import KSTAROrchestrator
from kstar_skills import KSTARSkillRegistry

# ---------------------------------------------------------------------------
# ANSI colour helpers (gracefully degrade on non-TTY)
# ---------------------------------------------------------------------------
_IS_TTY = sys.stdout.isatty()


def _c(code: str, text: str) -> str:
    return f"\033[{code}m{text}\033[0m" if _IS_TTY else text


def _header(text: str) -> str:
    return _c("1;36", f"\n{'─' * 60}\n  {text}\n{'─' * 60}")


def _question(text: str) -> str:
    return _c("1;33", text)


def _option(idx: int, label: str, desc: str) -> str:
    return f"  {_c('1;32', f'[{idx}]')} {_c('1', label)}: {desc}"


def _tool_line(label: str, value: str) -> str:
    return f"  {_c('36', label + ':')} {value}"


def _warn(text: str) -> str:
    return _c("1;31", f"  ⚠  {text}")


def _info(text: str) -> str:
    return _c("90", f"  ℹ  {text}")


# ---------------------------------------------------------------------------
# Interactive clarification handler
# ---------------------------------------------------------------------------

class ClarificationHandler:
    """
    Handles two kinds of mid-run user interaction:

    A. AskUserQuestion  — Claude generated structured multiple-choice
                          questions; we render them and collect answers.
    B. Tool approval    — Claude wants to run Bash / Write / Edit etc.;
                          we show what it plans to do and ask y/n.

    The handler is passed as `can_use_tool` in ClaudeAgentOptions.
    """

    def __init__(
        self,
        auto_approve: bool = False,
        auto_approve_tools: set[str] | None = None,
        stream_queue: asyncio.Queue | None = None,
    ):
        self.auto_approve = auto_approve
        # Tools that are always approved without prompting
        self.auto_approve_tools: set[str] = auto_approve_tools or {
            "Read", "Glob", "Grep", "LS",
        }
        self.stream_queue = stream_queue  # for streaming-input injection
        self.clarification_log: list[dict[str, Any]] = []

    # ------------------------------------------------------------------
    # Main entry point (called by SDK for every tool request)
    # ------------------------------------------------------------------

    async def __call__(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        context: ToolPermissionContext,
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Dispatch to the appropriate handler based on tool_name.
        """
        if tool_name == "AskUserQuestion":
            return await self._handle_clarifying_questions(input_data)
        else:
            return await self._handle_tool_approval(tool_name, input_data)

    # ------------------------------------------------------------------
    # A. Clarifying questions (AskUserQuestion)
    # ------------------------------------------------------------------

    async def _handle_clarifying_questions(
        self, input_data: dict[str, Any]
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Render Claude's structured questions and collect user answers.

        The SDK passes:
            input_data["questions"] = [
                {
                    "question": str,
                    "header": str,          # short chip label
                    "options": [{"label": str, "description": str}, ...],
                    "multiSelect": bool,
                }
            ]
        We must return:
            PermissionResultAllow(updated_input={
                "questions": [...],
                "answers": {"<question text>": "<answer or comma-sep answers>"}
            })
        """
        questions = input_data.get("questions", [])
        if not questions:
            return PermissionResultAllow(updated_input=input_data)

        print(_header("Claude needs clarification"))
        answers: dict[str, str] = {}

        for q_obj in questions:
            question_text = q_obj.get("question", "")
            header = q_obj.get("header", "")
            options = q_obj.get("options", [])
            multi = q_obj.get("multiSelect", False)

            print()
            if header:
                print(_c("1;35", f"  [{header}]"))
            print(_question(f"  Q: {question_text}"))
            print()

            if options:
                for idx, opt in enumerate(options, start=1):
                    print(_option(idx, opt["label"], opt["description"]))
                print()

                if multi:
                    print(_info("Multi-select: enter numbers separated by commas (e.g. 1,3)"))
                else:
                    print(_info("Enter the number of your choice"))

                while True:
                    try:
                        raw = input("  > ").strip()
                    except (EOFError, KeyboardInterrupt):
                        print()
                        return PermissionResultDeny(message="User cancelled clarification")

                    if not raw:
                        continue

                    if multi:
                        chosen_labels = []
                        valid = True
                        for part in raw.split(","):
                            part = part.strip()
                            if not part.isdigit():
                                valid = False
                                break
                            n = int(part)
                            if 1 <= n <= len(options):
                                chosen_labels.append(options[n - 1]["label"])
                            else:
                                valid = False
                                break
                        if not valid or not chosen_labels:
                            print(_warn(f"Please enter numbers between 1 and {len(options)}"))
                            continue
                        answers[question_text] = ", ".join(chosen_labels)
                        break
                    else:
                        if raw.isdigit() and 1 <= int(raw) <= len(options):
                            answers[question_text] = options[int(raw) - 1]["label"]
                            break
                        print(_warn(f"Please enter a number between 1 and {len(options)}"))
            else:
                # Free-text question (no options provided)
                print(_info("Type your answer and press Enter"))
                try:
                    raw = input("  > ").strip()
                except (EOFError, KeyboardInterrupt):
                    print()
                    return PermissionResultDeny(message="User cancelled clarification")
                answers[question_text] = raw

        # Log the exchange
        self.clarification_log.append({
            "type": "clarification",
            "questions": questions,
            "answers": answers,
        })

        print()
        print(_info("Answers recorded — resuming agent…"))

        return PermissionResultAllow(
            updated_input={**input_data, "answers": answers}
        )

    # ------------------------------------------------------------------
    # B. Tool approval
    # ------------------------------------------------------------------

    async def _handle_tool_approval(
        self,
        tool_name: str,
        input_data: dict[str, Any],
    ) -> PermissionResultAllow | PermissionResultDeny:
        """
        Show the user what Claude wants to do and ask for approval.
        Auto-approves read-only tools and when auto_approve=True.
        """
        # Always auto-approve read-only tools
        if tool_name in self.auto_approve_tools or self.auto_approve:
            return PermissionResultAllow(updated_input=input_data)

        print(_header(f"Tool request: {tool_name}"))
        self._print_tool_details(tool_name, input_data)
        print()

        while True:
            try:
                choice = input(
                    "  Allow? "
                    + _c("1;32", "[y]") + "es  "
                    + _c("1;31", "[n]") + "o  "
                    + _c("1;33", "[m]") + "odify  "
                    + _c("1;34", "[r]") + "edirect"
                    + "  > "
                ).strip().lower()
            except (EOFError, KeyboardInterrupt):
                print()
                return PermissionResultDeny(message="User cancelled")

            if choice in ("y", "yes", ""):
                self.clarification_log.append({
                    "type": "approval",
                    "tool": tool_name,
                    "decision": "allow",
                })
                return PermissionResultAllow(updated_input=input_data)

            elif choice in ("n", "no"):
                try:
                    reason = input("  Reason (optional): ").strip()
                except (EOFError, KeyboardInterrupt):
                    reason = ""
                msg = reason or f"User denied {tool_name}"
                self.clarification_log.append({
                    "type": "approval",
                    "tool": tool_name,
                    "decision": "deny",
                    "reason": msg,
                })
                return PermissionResultDeny(message=msg)

            elif choice in ("m", "modify"):
                modified = await self._modify_tool_input(tool_name, input_data)
                self.clarification_log.append({
                    "type": "approval",
                    "tool": tool_name,
                    "decision": "modify",
                    "original": input_data,
                    "modified": modified,
                })
                return PermissionResultAllow(updated_input=modified)

            elif choice in ("r", "redirect"):
                # Inject a new instruction via streaming input
                if self.stream_queue:
                    try:
                        new_instruction = input(
                            "  New instruction for Claude: "
                        ).strip()
                    except (EOFError, KeyboardInterrupt):
                        continue
                    if new_instruction:
                        await self.stream_queue.put(new_instruction)
                        print(_info("Instruction queued — Claude will receive it next turn"))
                        return PermissionResultDeny(
                            message="Redirected: see new instruction in stream"
                        )
                else:
                    print(_warn("Streaming input not enabled; cannot redirect"))
            else:
                print(_warn("Please enter y, n, m, or r"))

    def _print_tool_details(self, tool_name: str, input_data: dict[str, Any]) -> None:
        if tool_name == "Bash":
            print(_tool_line("Command", input_data.get("command", "")))
            if desc := input_data.get("description"):
                print(_tool_line("Description", desc))
        elif tool_name in ("Write", "Edit"):
            print(_tool_line("File", input_data.get("file_path", "")))
            if content := input_data.get("content", ""):
                preview = content[:200] + ("…" if len(content) > 200 else "")
                print(_tool_line("Content preview", preview))
        elif tool_name == "Read":
            print(_tool_line("File", input_data.get("file_path", "")))
        else:
            for k, v in input_data.items():
                print(_tool_line(k, str(v)[:120]))

    async def _modify_tool_input(
        self, tool_name: str, input_data: dict[str, Any]
    ) -> dict[str, Any]:
        """Let the user edit a specific field of the tool input."""
        print(_info("Which field do you want to modify?"))
        keys = list(input_data.keys())
        for idx, k in enumerate(keys, start=1):
            print(f"  {_c('1;32', f'[{idx}]')} {k}: {str(input_data[k])[:80]}")
        try:
            raw = input("  Field number: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(keys):
                field = keys[int(raw) - 1]
                new_val = input(f"  New value for '{field}': ").strip()
                return {**input_data, field: new_val}
        except (EOFError, KeyboardInterrupt):
            pass
        return input_data


# ---------------------------------------------------------------------------
# Streaming-input generator
# ---------------------------------------------------------------------------

async def _streaming_prompt_gen(
    initial_prompt: str,
    queue: asyncio.Queue,
) -> AsyncGenerator[dict[str, Any], None]:
    """
    Async generator that yields the initial prompt and then any messages
    the user injects via the queue (from the 'redirect' option).
    """
    yield {
        "type": "user",
        "message": {"role": "user", "content": initial_prompt},
    }
    while True:
        try:
            msg = await asyncio.wait_for(queue.get(), timeout=0.1)
            yield {
                "type": "user",
                "message": {"role": "user", "content": msg},
            }
        except asyncio.TimeoutError:
            # No new message yet; the generator stays alive
            continue
        except asyncio.CancelledError:
            break


# ---------------------------------------------------------------------------
# Required dummy PreToolUse hook (keeps stream open in Python)
# ---------------------------------------------------------------------------

async def _keepalive_hook(
    input_data: dict[str, Any],
    tool_use_id: str | None,
    context: HookContext,
) -> dict[str, Any]:
    """
    Python SDK requires a PreToolUse hook that returns continue_=True
    to keep the stream open while can_use_tool is waiting for input.
    """
    return {"continue_": True}


# ---------------------------------------------------------------------------
# InteractiveKSTARAgent
# ---------------------------------------------------------------------------

class InteractiveKSTARAgent:
    """
    Wraps the KSTAR orchestrator with interactive clarification support.

    The agent uses the SDK's `can_use_tool` callback to pause execution
    whenever Claude calls AskUserQuestion or requests tool approval, and
    resumes automatically once the user responds.

    Parameters
    ----------
    mode : str
        Claude permission mode.  Use "plan" to make Claude ask questions
        before proposing changes (ideal for interactive workflows).
        Other values: "default", "acceptEdits", "bypassPermissions".
    auto_approve : bool
        If True, all tool requests are auto-approved (no prompts).
    auto_approve_tools : set[str]
        Tools that are always auto-approved (default: read-only tools).
    checkpoint_dir : str | None
        Directory for saving KSTAR state checkpoints.
    registry_path : str
        Path to the skill registry JSON file.
    allowed_tools : list[str] | None
        Restrict which tools Claude may use.  None = all tools.
    """

    def __init__(
        self,
        mode: str = "default",
        auto_approve: bool = False,
        auto_approve_tools: set[str] | None = None,
        checkpoint_dir: str | None = None,
        registry_path: str = "kstar_skills_registry.json",
        allowed_tools: list[str] | None = None,
    ):
        self.mode = mode
        self.auto_approve = auto_approve
        self.auto_approve_tools = auto_approve_tools
        self.checkpoint_dir = checkpoint_dir
        self.registry = KSTARSkillRegistry(path=registry_path)
        self.allowed_tools = allowed_tools

        # Streaming input queue — shared between the prompt generator
        # and the ClarificationHandler's "redirect" option
        self._stream_queue: asyncio.Queue = asyncio.Queue()

        # Build the clarification handler
        self.handler = ClarificationHandler(
            auto_approve=auto_approve,
            auto_approve_tools=auto_approve_tools,
            stream_queue=self._stream_queue,
        )

    # ------------------------------------------------------------------
    # High-level run: full KSTAR pipeline with interactive action step
    # ------------------------------------------------------------------

    async def run(self, prompt: str) -> KSTARState:
        """
        Execute the full KSTAR pipeline.  The Action Execution step uses
        an interactive ClaudeSDKClient session with can_use_tool wired in.
        """
        from kstar_steps import st_refine, plan_retrieval, plan_forecast, evaluate
        from kstar_state import KSTARStatus

        state = KSTARState(raw_input=prompt)

        print(_header(f"KSTAR run  {state.run_id[:8]}"))
        print(_info(f"Prompt: {prompt}"))

        # Step 1 — ST Refine
        print(_c("90", "\n[1/5] ST Refine…"))
        state = await st_refine(state)

        # Step 2 — Plan Retrieval
        print(_c("90", "[2/5] Plan Retrieval…"))
        state = await plan_retrieval(state)

        # Step 3 — Plan Forecast
        print(_c("90", "[3/5] Plan Forecast…"))
        state = await plan_forecast(state)

        # Step 4 — Interactive Action Execution
        print(_c("90", "[4/5] Action Execution (interactive)…"))
        state = await self._interactive_action_exec(state)

        # Step 5 — Evaluation
        print(_c("90", "[5/5] Evaluation…"))
        state = await evaluate(state)

        # Skill promotion
        if state.delta and state.delta.promote_to_skill:
            skill = self.registry.promote(state)
            if skill:
                self.registry.save()
                print(_info(f"Skill promoted: {skill.name}"))

        # Checkpoint
        if self.checkpoint_dir:
            Path(self.checkpoint_dir).mkdir(parents=True, exist_ok=True)
            path = str(
                Path(self.checkpoint_dir) / f"{state.run_id}_{state.status.value}.json"
            )
            state.save(path)
            print(_info(f"State saved: {path}"))

        return state

    # ------------------------------------------------------------------
    # Interactive action execution step
    # ------------------------------------------------------------------

    async def _interactive_action_exec(self, state: KSTARState) -> KSTARState:
        """
        Run the action execution step using a streaming query with
        can_use_tool wired in.  Claude may pause to ask questions or
        request tool approval at any point during execution.
        """
        from kstar_state import KSTARStatus, ActualResult, ActionRecord

        if not state.plan:
            state.status = KSTARStatus.EXECUTING
            return state

        # Build the execution prompt from the plan
        plan_summary = "\n".join(
            f"  Step {s.step_id}: {s.action}" for s in state.plan.steps
        )
        exec_prompt = (
            f"Execute the following plan:\n\n"
            f"Task: {state.T.description if state.T else 'unknown'}\n\n"
            f"Plan: {state.plan.name}\n"
            f"{plan_summary}\n\n"
            f"Carry out each step carefully.  "
            f"If you need clarification at any point, use AskUserQuestion."
        )

        state.status = KSTARStatus.EXECUTING
        state.touch()

        # SDK options with can_use_tool + keepalive hook
        options = ClaudeAgentOptions(
            system_prompt=(
                "You are a KSTAR execution agent.  Execute the given plan step by step.  "
                "If you are unsure about any step, use AskUserQuestion to ask the user "
                "before proceeding.  Be precise and careful."
            ),
            permission_mode=self.mode,
            allowed_tools=self.allowed_tools,
            can_use_tool=self.handler,
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher=None, hooks=[_keepalive_hook])
                ]
            },
        )

        # Use streaming input so the user can inject messages mid-run
        prompt_stream = _streaming_prompt_gen(exec_prompt, self._stream_queue)

        raw_output_parts: list[str] = []
        tool_uses: list[dict[str, Any]] = []

        try:
            async for message in query(prompt=prompt_stream, options=options):
                if isinstance(message, AssistantMessage):
                    for block in message.content:
                        if isinstance(block, TextBlock):
                            raw_output_parts.append(block.text)
                            # Stream assistant text to the terminal
                            print(_c("97", block.text), end="", flush=True)
                        elif isinstance(block, ToolUseBlock):
                            tool_uses.append({
                                "tool": block.name,
                                "input": block.input,
                            })
                elif isinstance(message, ResultMessage):
                    if message.subtype == "success":
                        raw_output_parts.append(message.result or "")
                    break
        except Exception as exc:
            print(_warn(f"Execution error: {exc}"))
            state.status = KSTARStatus.FAILED
            return state

        # Build action trace
        state.action_trace = [
            ActionRecord(
                step_id=i,
                tool_used=t["tool"],
                input_given=t["input"],
                output_received="(see raw output)",
                success=True,
            )
            for i, t in enumerate(tool_uses)
        ]

        raw_output = "\n".join(raw_output_parts).strip()
        state.result = ActualResult(
            summary=raw_output[:500] if raw_output else "Execution completed",
            outputs=[t["tool"] for t in tool_uses],
            raw_agent_output=raw_output,
        )

        # Attach clarification log to state metadata
        if self.handler.clarification_log:
            state.metadata["clarification_log"] = self.handler.clarification_log

        return state

    # ------------------------------------------------------------------
    # Convenience: run a single-turn interactive query (no KSTAR pipeline)
    # ------------------------------------------------------------------

    async def chat(self, prompt: str) -> str:
        """
        Single-turn interactive chat with the agent.  Useful for quick
        tasks that don't need the full KSTAR pipeline.
        """
        options = ClaudeAgentOptions(
            permission_mode=self.mode,
            allowed_tools=self.allowed_tools,
            can_use_tool=self.handler,
            hooks={
                "PreToolUse": [
                    HookMatcher(matcher=None, hooks=[_keepalive_hook])
                ]
            },
        )

        prompt_stream = _streaming_prompt_gen(prompt, self._stream_queue)
        parts: list[str] = []

        async for message in query(prompt=prompt_stream, options=options):
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        parts.append(block.text)
                        print(_c("97", block.text), end="", flush=True)
            elif isinstance(message, ResultMessage):
                if message.subtype == "success":
                    parts.append(message.result or "")
                break

        print()
        return "\n".join(parts).strip()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

async def _cli_main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Interactive KSTAR agent — Claude pauses to ask you questions",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Full KSTAR pipeline (interactive)
              python kstar_interactive.py "Build a REST API for a todo app"

              # Use 'plan' mode — Claude asks questions before making changes
              python kstar_interactive.py --mode plan "Refactor the auth module"

              # Auto-approve all tools (no prompts)
              python kstar_interactive.py --auto-approve "List files in /tmp"

              # Single-turn chat (no KSTAR pipeline)
              python kstar_interactive.py --chat "What is the capital of France?"
        """),
    )
    parser.add_argument("prompt", help="Task or question for the agent")
    parser.add_argument(
        "--mode",
        default="default",
        choices=["default", "plan", "acceptEdits", "bypassPermissions"],
        help="Claude permission mode (default: default; use 'plan' for interactive planning)",
    )
    parser.add_argument(
        "--auto-approve",
        action="store_true",
        help="Auto-approve all tool requests without prompting",
    )
    parser.add_argument(
        "--checkpoints",
        default=None,
        metavar="DIR",
        help="Directory to save KSTAR state checkpoints",
    )
    parser.add_argument(
        "--chat",
        action="store_true",
        help="Run a single-turn chat instead of the full KSTAR pipeline",
    )
    parser.add_argument(
        "--output",
        default=None,
        metavar="FILE",
        help="Save the final KSTARState JSON to this file",
    )

    args = parser.parse_args()

    agent = InteractiveKSTARAgent(
        mode=args.mode,
        auto_approve=args.auto_approve,
        checkpoint_dir=args.checkpoints,
    )

    if args.chat:
        result = await agent.chat(args.prompt)
        print()
        print(_c("1;32", "Done."))
    else:
        state = await agent.run(args.prompt)
        print()
        print(_header("KSTAR run complete"))
        print(_tool_line("Status", state.status.value))
        if state.result:
            print(_tool_line("Result", state.result.summary[:200]))
        if state.delta:
            print(_tool_line("ΔR score", f"{state.delta.score:.2f}"))
        if args.output:
            state.save(args.output)
            print(_info(f"State saved to {args.output}"))


if __name__ == "__main__":
    asyncio.run(_cli_main())
