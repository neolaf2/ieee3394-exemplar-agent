"""
kstar_cli.py
------------
Command-line interface for the KSTAR stateful agent.

Usage examples:

    # Run the full KSTAR pipeline
    python kstar_cli.py run "Research the latest advances in quantum computing"

    # Run with checkpoint persistence
    python kstar_cli.py run "Write a Python web scraper" --checkpoints ./checkpoints

    # List all promoted skills
    python kstar_cli.py skills list

    # Search for a skill
    python kstar_cli.py skills search "web research"

    # Show a saved state
    python kstar_cli.py state show ./checkpoints/<run_id>_completed.json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import sys
from pathlib import Path

from kstar_orchestrator import run_kstar
from kstar_skills import KSTARSkillRegistry
from kstar_state import KSTARState


# ---------------------------------------------------------------------------
# Logging setup
# ---------------------------------------------------------------------------

def _configure_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
        datefmt="%H:%M:%S",
    )


# ---------------------------------------------------------------------------
# Sub-commands
# ---------------------------------------------------------------------------

async def cmd_run(args: argparse.Namespace) -> None:
    """Execute the full KSTAR pipeline for a given prompt."""
    state = await run_kstar(
        prompt=args.prompt,
        checkpoint_dir=args.checkpoints,
    )

    print("\n" + "=" * 60)
    print("KSTAR Run Complete")
    print("=" * 60)
    print(f"  Run ID  : {state.run_id}")
    print(f"  Status  : {state.status}")
    print(f"  Task    : {state.T.description}")
    print(f"  Plan    : {state.plan.name if state.plan else 'N/A'}")
    if state.delta:
        print(f"  ΔR Score: {state.delta.score:.2f}")
        print(f"  Promoted: {state.delta.promote_to_skill}")
    if state.result:
        print(f"\nResult Summary:\n{state.result.summary}")
    print("=" * 60)

    if args.output:
        out_path = Path(args.output)
        state.save(out_path)
        print(f"\nState saved to: {out_path}")


def cmd_skills_list(args: argparse.Namespace) -> None:
    """List all promoted skills in the registry."""
    registry = KSTARSkillRegistry()
    registry.load()
    skills = registry.list_all()

    if not skills:
        print("No skills in registry.")
        return

    print(f"\n{'ID':<36}  {'Name':<40}  {'Score':>6}  {'Uses':>5}")
    print("-" * 95)
    for s in skills:
        print(f"{s.skill_id:<36}  {s.name:<40}  {s.promotion_score:>6.2f}  {s.use_count:>5}")


def cmd_skills_search(args: argparse.Namespace) -> None:
    """Search for skills matching a query."""
    registry = KSTARSkillRegistry()
    registry.load()
    results = registry.search(args.query)

    if not results:
        print(f"No skills found matching '{args.query}'.")
        return

    for skill in results:
        print(f"\n{'─' * 60}")
        print(f"  ID       : {skill.skill_id}")
        print(f"  Name     : {skill.name}")
        print(f"  Archetype: {skill.archetype}")
        print(f"  Score    : {skill.promotion_score:.2f}")
        print(f"  Uses     : {skill.use_count}")
        print(f"  Steps    : {len(skill.plan)}")
        print(f"  Desc     : {skill.description[:120]}")


def cmd_state_show(args: argparse.Namespace) -> None:
    """Display a saved KSTAR state from a checkpoint file."""
    path = Path(args.path)
    if not path.exists():
        print(f"File not found: {path}", file=sys.stderr)
        sys.exit(1)

    state = KSTARState.load(path)
    print(json.dumps(state.to_dict(), indent=2))


# ---------------------------------------------------------------------------
# Argument parser
# ---------------------------------------------------------------------------

def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="kstar",
        description="KSTAR Stateful Agent — Anthropic Claude Agent SDK",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Enable debug logging"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    # ── run ────────────────────────────────────────────────────────────
    run_p = sub.add_parser("run", help="Execute the KSTAR pipeline for a prompt")
    run_p.add_argument("prompt", help="The task prompt to execute")
    run_p.add_argument(
        "--checkpoints",
        metavar="DIR",
        help="Directory to save state checkpoints",
    )
    run_p.add_argument(
        "--output",
        metavar="FILE",
        help="Save the final state to this JSON file",
    )

    # ── skills ─────────────────────────────────────────────────────────
    skills_p = sub.add_parser("skills", help="Manage the skill registry")
    skills_sub = skills_p.add_subparsers(dest="skills_command", required=True)

    skills_sub.add_parser("list", help="List all promoted skills")

    search_p = skills_sub.add_parser("search", help="Search for skills")
    search_p.add_argument("query", help="Search query")

    # ── state ──────────────────────────────────────────────────────────
    state_p = sub.add_parser("state", help="Inspect saved state files")
    state_sub = state_p.add_subparsers(dest="state_command", required=True)

    show_p = state_sub.add_parser("show", help="Display a saved state")
    show_p.add_argument("path", help="Path to the state JSON file")

    return parser


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = _build_parser()
    args = parser.parse_args()
    _configure_logging(args.verbose)

    if args.command == "run":
        asyncio.run(cmd_run(args))

    elif args.command == "skills":
        if args.skills_command == "list":
            cmd_skills_list(args)
        elif args.skills_command == "search":
            cmd_skills_search(args)

    elif args.command == "state":
        if args.state_command == "show":
            cmd_state_show(args)


if __name__ == "__main__":
    main()
