"""
KSTAR Memory Integration (In-Memory MVP)

KSTAR = Knowledge, Situation, Task, Action, Result
A universal representation schema for agent memory.

This MVP implementation uses in-memory storage. Can be upgraded
to SQLite or MCP server later.
"""

from typing import Any, Dict, List, Optional
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)


class KStarMemory:
    """
    KSTAR Memory for the IEEE 3394 Agent.

    Stores:
    - Traces: Complete K→S→T→A→R episodes
    - Perceptions: Facts and observations
    - Skills: Learned capabilities
    """

    def __init__(self):
        """Initialize in-memory KSTAR storage"""
        self.traces: List[Dict[str, Any]] = []
        self.perceptions: List[Dict[str, Any]] = []
        self.skills: List[Dict[str, Any]] = []

    async def store_trace(self, trace: Dict[str, Any]) -> str:
        """
        Store a KSTAR trace (episode).

        A trace represents a complete K→S→T→A→R cycle.

        Args:
            trace: Dict with keys: situation, task, action, result (optional), mode

        Returns:
            Trace ID
        """
        trace_id = f"trace_{len(self.traces)}"
        trace_entry = {
            "id": trace_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **trace
        }
        self.traces.append(trace_entry)
        logger.debug(f"Stored trace {trace_id}")
        return trace_id

    async def store_perception(self, perception: Dict[str, Any]) -> str:
        """
        Store a perception (fact/observation).

        Perceptions are declarative knowledge without action plans.

        Args:
            perception: Dict with keys: content, context, tags, importance

        Returns:
            Perception ID
        """
        perception_id = f"perception_{len(self.perceptions)}"
        perception_entry = {
            "id": perception_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **perception
        }
        self.perceptions.append(perception_entry)
        logger.debug(f"Stored perception {perception_id}")
        return perception_id

    async def store_skill(self, skill: Dict[str, Any]) -> str:
        """
        Store a skill definition.

        Args:
            skill: Dict with keys: name, description, domain, capability

        Returns:
            Skill ID
        """
        skill_id = f"skill_{len(self.skills)}"
        skill_entry = {
            "id": skill_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            **skill
        }
        self.skills.append(skill_entry)
        logger.info(f"Stored skill: {skill.get('name', skill_id)}")
        return skill_id

    async def query(self, domain: str, goal: str) -> Optional[Dict[str, Any]]:
        """
        Query KSTAR memory for matching traces.

        Simple implementation for MVP - just searches for domain match.
        """
        for trace in reversed(self.traces):
            situation = trace.get("situation", {})
            if situation.get("domain") == domain:
                return trace
        return None

    async def find_skills(self, domain: str, goal: str) -> List[Dict[str, Any]]:
        """Find skills capable of handling a task"""
        matching = []
        for skill in self.skills:
            if skill.get("domain") == domain:
                matching.append(skill)
        return matching

    async def list_skills(self) -> List[Dict[str, Any]]:
        """List all stored skills"""
        return self.skills.copy()

    async def get_stats(self) -> Dict[str, Any]:
        """Get storage statistics"""
        return {
            "trace_count": len(self.traces),
            "perception_count": len(self.perceptions),
            "skill_count": len(self.skills)
        }
