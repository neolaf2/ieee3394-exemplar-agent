"""
kstar_skills.py
---------------
Implements the KSTAR Skill Registry.

A "skill" is a compiled KSTAR plan — a generalised, reusable execution
template that was promoted from a successful execution trace.

Promotion rule (from the architecture document):
    After enough successful ΔR values, KSTAR traces are generalised
    and stored as skills.

The registry persists skills to a JSON file so they survive across runs.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# Default path for the skill registry file
DEFAULT_REGISTRY_PATH = Path(__file__).parent / "kstar_skills_registry.json"


# ---------------------------------------------------------------------------
# Skill model
# ---------------------------------------------------------------------------

class KSTARSkill(BaseModel):
    """
    A compiled KSTAR skill — a reusable execution template.

    Skills are promoted from successful execution traces and can be
    retrieved during the Plan Retrieval step to accelerate future runs.
    """
    skill_id: str
    name: str
    description: str
    archetype: str = ""

    # Input schema: the (S, T) signature this skill applies to
    input_schema: Dict[str, Any] = Field(default_factory=dict)

    # The compiled plan steps
    plan: List[Dict[str, Any]] = Field(default_factory=list)

    # Validation: what a successful result should look like
    expected_structure: str = ""

    # Provenance
    source_run_id: str = ""
    promotion_score: float = 0.0
    use_count: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    last_used_at: Optional[str] = None


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class KSTARSkillRegistry:
    """
    In-memory skill registry with JSON persistence.

    Usage::

        registry = KSTARSkillRegistry()
        registry.load()

        # Promote a trace to a skill
        registry.promote(state)

        # Retrieve matching skills for a task
        skills = registry.search("web_research")
    """

    def __init__(self, path: str | Path = DEFAULT_REGISTRY_PATH) -> None:
        self._path = Path(path)
        self._skills: Dict[str, KSTARSkill] = {}

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def load(self) -> None:
        """Load skills from the registry file (if it exists)."""
        if not self._path.exists():
            logger.info("[SkillRegistry] No registry file found at %s; starting empty.", self._path)
            return
        raw = json.loads(self._path.read_text(encoding="utf-8"))
        for entry in raw.get("skills", []):
            skill = KSTARSkill.model_validate(entry)
            self._skills[skill.skill_id] = skill
        logger.info("[SkillRegistry] Loaded %d skill(s) from %s", len(self._skills), self._path)

    def save(self) -> None:
        """Persist the current registry to the JSON file."""
        payload = {
            "skills": [s.model_dump() for s in self._skills.values()],
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        logger.info("[SkillRegistry] Saved %d skill(s) to %s", len(self._skills), self._path)

    # ------------------------------------------------------------------
    # Skill management
    # ------------------------------------------------------------------

    def promote(self, state: Any) -> Optional[KSTARSkill]:
        """
        Promote a successful KSTAR execution trace to a reusable skill.

        The state must have:
          - state.delta.promote_to_skill == True
          - state.plan is not None
          - state.T is not None
        """
        from kstar_state import KSTARState  # local import to avoid circular deps

        if not isinstance(state, KSTARState):
            raise TypeError("Expected a KSTARState instance.")

        if state.delta is None or not state.delta.promote_to_skill:
            logger.debug("[SkillRegistry] Promotion skipped (delta.promote_to_skill is False).")
            return None

        if state.plan is None:
            logger.warning("[SkillRegistry] Promotion skipped (no plan in state).")
            return None

        import uuid
        skill_id = str(uuid.uuid4())
        skill = KSTARSkill(
            skill_id=skill_id,
            name=state.plan.name or state.T.description[:60],
            description=state.T.description,
            archetype=state.plan.archetype,
            input_schema={
                "S": state.S.model_dump(),
                "T": {
                    "description": state.T.description,
                    "success_criteria": state.T.success_criteria,
                    "complexity": state.T.complexity,
                },
            },
            plan=[step.model_dump() for step in state.plan.steps],
            expected_structure=state.expected_result.summary if state.expected_result else "",
            source_run_id=state.run_id,
            promotion_score=state.delta.score,
        )
        self._skills[skill_id] = skill
        self.save()

        logger.info(
            "[SkillRegistry] Promoted trace %s → skill '%s' (score=%.2f)",
            state.run_id,
            skill.name,
            skill.promotion_score,
        )
        return skill

    def search(self, query: str, limit: int = 5) -> List[KSTARSkill]:
        """
        Search for skills matching a query string.

        Simple keyword search over skill name, description, and archetype.
        Returns up to `limit` results sorted by promotion_score descending.
        """
        q = query.lower()
        matches = [
            s for s in self._skills.values()
            if q in s.name.lower()
            or q in s.description.lower()
            or q in s.archetype.lower()
        ]
        matches.sort(key=lambda s: s.promotion_score, reverse=True)
        return matches[:limit]

    def get(self, skill_id: str) -> Optional[KSTARSkill]:
        """Retrieve a skill by its ID."""
        return self._skills.get(skill_id)

    def list_all(self) -> List[KSTARSkill]:
        """Return all skills sorted by creation date (newest first)."""
        return sorted(
            self._skills.values(),
            key=lambda s: s.created_at,
            reverse=True,
        )

    def record_use(self, skill_id: str) -> None:
        """Increment the use counter and update last_used_at."""
        skill = self._skills.get(skill_id)
        if skill:
            skill.use_count += 1
            skill.last_used_at = datetime.now(timezone.utc).isoformat()
            self.save()

    @property
    def count(self) -> int:
        """Number of skills in the registry."""
        return len(self._skills)
