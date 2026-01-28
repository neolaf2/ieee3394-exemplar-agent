"""
P3394 Hooks for KSTAR Integration

Hooks that log agent operations to KSTAR memory for learning and debugging.

Note: For MVP, these are simplified. Full implementation would integrate
with Claude Agent SDK's hook system.
"""

from typing import Any, Dict
from datetime import datetime, timezone
import logging

logger = logging.getLogger(__name__)

# Global reference to KSTAR memory (set during initialization)
_kstar_memory = None


def set_kstar_memory(memory):
    """Set the KSTAR memory instance for hooks"""
    global _kstar_memory
    _kstar_memory = memory


async def log_tool_use(tool_name: str, tool_input: Dict[str, Any], session_id: str = "unknown"):
    """
    Log tool use to KSTAR memory.

    This implements the T→A transition in the KSTAR cognitive cycle:
    - Task has been determined
    - Action is about to be executed
    """
    if not _kstar_memory:
        return

    try:
        await _kstar_memory.store_trace({
            "situation": {
                "domain": "ieee3394_agent",
                "actor": "agent",
                "protocol": "direct",
                "now": datetime.now(timezone.utc).isoformat()
            },
            "task": {
                "goal": f"Execute tool: {tool_name}",
                "constraints": [],
                "success_criteria": ["Tool executes without error"]
            },
            "action": {
                "type": tool_name,
                "parameters": tool_input,
                "skill_used": f"builtin:{tool_name}"
            },
            "mode": "performance",
            "session_id": session_id,
            "tags": ["tool_use", tool_name]
        })
    except Exception as e:
        logger.warning(f"Failed to log to KSTAR: {e}")


async def log_tool_result(tool_name: str, is_error: bool, session_id: str = "unknown"):
    """
    Log tool result to KSTAR memory.

    This implements the A→R transition in the KSTAR cognitive cycle:
    - Action has been executed
    - Result is being recorded
    """
    if not _kstar_memory:
        return

    try:
        await _kstar_memory.store_perception({
            "content": f"Tool {tool_name} {'failed' if is_error else 'succeeded'}",
            "context": {
                "domain": "ieee3394_agent",
                "source": "tool_execution",
                "confidence": 1.0
            },
            "tags": ["tool_result", tool_name],
            "importance": 0.5 if not is_error else 0.8
        })
    except Exception as e:
        logger.warning(f"Failed to log result to KSTAR: {e}")
