"""
Claude Agent SDK Hooks for P3394 Agent

Implements hooks for:
- KSTAR memory logging (traces)
- Control Token necessity evaluation (auto-persist credentials, bindings, etc.)
- P3394 compliance checking
- Security auditing
- Skill folder tracking for dynamic imports
"""

from claude_agent_sdk import HookMatcher
from typing import Any, Dict, Optional
from datetime import datetime, timezone
import logging

from ..memory.memory_system import MemorySystem, get_memory_system
from ..memory.necessity_evaluator import NecessityCategory
from ..memory.control_tokens import TokenType, TokenScope

logger = logging.getLogger(__name__)

# Global memory system reference (initialized on first use)
_memory_system: Optional[MemorySystem] = None


def get_hook_memory_system() -> MemorySystem:
    """Get or create the memory system for hooks"""
    global _memory_system
    if _memory_system is None:
        _memory_system = get_memory_system()
    return _memory_system


def create_sdk_hooks(gateway: "AgentGateway") -> Dict[str, list]:
    """
    Create SDK-compatible hooks for the P3394 agent.

    Args:
        gateway: The AgentGateway instance (for accessing memory, etc.)

    Returns:
        Dictionary of hook event names to hook matcher lists
    """

    async def kstar_pre_tool_hook(
        input_data: Dict[str, Any],
        tool_use_id: str,
        context: Any
    ) -> Dict[str, Any]:
        """
        Pre-tool hook that logs to KSTAR memory and runs necessity evaluation.

        This implements the T→A transition in the KSTAR cognitive cycle:
        - Task has been determined
        - Action is about to be executed
        - Necessity evaluator detects tokens that must be persisted
        """
        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})
        session_id = input_data.get('session_id')

        logger.debug(f"Pre-tool hook: {tool_name}")

        # === Memory System: Necessity Evaluation ===
        # Run the necessity evaluator to auto-detect and persist important tokens
        try:
            memory_system = get_hook_memory_system()
            detected_tokens = await memory_system.on_pre_tool_use(
                tool_name=tool_name,
                tool_input=tool_input,
                session_id=session_id
            )
            if detected_tokens:
                logger.info(f"Pre-tool necessity evaluation detected {len(detected_tokens)} tokens")
        except Exception as e:
            logger.warning(f"Necessity evaluation failed: {e}")

        # === Skill Folder Tracking ===
        # Capture skill folder names for dynamic imports (critical for recovery)
        if tool_name == "Skill" or "skill" in tool_name.lower():
            skill_name = tool_input.get("skill") or tool_input.get("name", "")
            if skill_name:
                try:
                    memory_system = get_hook_memory_system()
                    await memory_system.store_token(
                        key=f"skill:folder:{skill_name}",
                        value=skill_name,
                        token_type=TokenType.SKILL_ID,
                        binding_target=f"skill:{skill_name}",
                        scopes=[TokenScope.EXECUTE],
                        category=NecessityCategory.CAPABILITY,
                        tags=["skill", "dynamic_import", skill_name],
                        metadata={"tool_name": tool_name, "invocation_context": "pre_tool"}
                    )
                    logger.debug(f"Tracked skill folder: {skill_name}")
                except Exception as e:
                    logger.warning(f"Failed to track skill folder: {e}")

        # === KSTAR Trace Logging ===
        if gateway.memory:
            try:
                await gateway.memory.store_trace({
                    "situation": {
                        "domain": "p3394_agent",
                        "actor": "agent",
                        "protocol": "claude_agent_sdk",
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
                    "tags": ["tool_use", tool_name]
                })
            except Exception as e:
                logger.warning(f"Failed to log to KSTAR: {e}")

        return {}

    async def kstar_post_tool_hook(
        input_data: Dict[str, Any],
        tool_use_id: str,
        context: Any
    ) -> Dict[str, Any]:
        """
        Post-tool hook that records results to KSTAR and runs necessity evaluation.

        This implements the A→R transition in the KSTAR cognitive cycle:
        - Action has been executed
        - Result is being recorded
        - Necessity evaluator detects tokens in results (e.g., returned credentials)
        """
        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})
        tool_result = input_data.get('tool_response')
        is_error = input_data.get('is_error', False)
        session_id = input_data.get('session_id')

        logger.debug(f"Post-tool hook: {tool_name}, error={is_error}")

        # === Memory System: Necessity Evaluation on Results ===
        # Run the necessity evaluator on tool results to capture returned tokens
        if not is_error:
            try:
                memory_system = get_hook_memory_system()
                detected_tokens = await memory_system.on_post_tool_use(
                    tool_name=tool_name,
                    tool_input=tool_input,
                    tool_result=tool_result,
                    is_error=is_error,
                    session_id=session_id
                )
                if detected_tokens:
                    logger.info(f"Post-tool necessity evaluation detected {len(detected_tokens)} tokens")
            except Exception as e:
                logger.warning(f"Post-tool necessity evaluation failed: {e}")

        # === Skill Activation Tracking ===
        # Track successful skill activations for recovery
        if not is_error and (tool_name == "Skill" or "skill" in tool_name.lower()):
            skill_name = tool_input.get("skill") or tool_input.get("name", "")
            if skill_name:
                try:
                    memory_system = get_hook_memory_system()
                    await memory_system.store_token(
                        key=f"skill:activated:{skill_name}",
                        value=f"activated:{datetime.now(timezone.utc).isoformat()}",
                        token_type=TokenType.SKILL_ID,
                        binding_target=f"skill:{skill_name}",
                        scopes=[TokenScope.EXECUTE, TokenScope.READ],
                        category=NecessityCategory.CAPABILITY,
                        tags=["skill", "activated", skill_name],
                        metadata={
                            "tool_name": tool_name,
                            "activation_time": datetime.now(timezone.utc).isoformat(),
                            "invocation_context": "post_tool"
                        }
                    )
                    logger.debug(f"Tracked skill activation: {skill_name}")
                except Exception as e:
                    logger.warning(f"Failed to track skill activation: {e}")

        # === KSTAR Perception Logging ===
        if gateway.memory:
            try:
                # Store perception about the result
                await gateway.memory.store_perception({
                    "content": f"Tool {tool_name} {'failed' if is_error else 'succeeded'}",
                    "context": {
                        "domain": "p3394_agent",
                        "source": "tool_execution",
                        "confidence": 1.0
                    },
                    "tags": ["tool_result", tool_name],
                    "importance": 0.5 if not is_error else 0.8
                })
            except Exception as e:
                logger.warning(f"Failed to log result to KSTAR: {e}")

        return {}

    async def p3394_compliance_hook(
        input_data: Dict[str, Any],
        tool_use_id: str,
        context: Any
    ) -> Dict[str, Any]:
        """
        Hook that ensures P3394 compliance in all operations.

        - Validates message formats
        - Ensures proper addressing
        - Logs compliance events
        """
        # For now, just pass through
        # In production, this would validate P3394 requirements
        return {}

    async def security_audit_hook(
        input_data: Dict[str, Any],
        tool_use_id: str,
        context: Any
    ) -> Dict[str, Any]:
        """
        Security audit hook for sensitive operations.

        Blocks dangerous bash commands and other security risks.
        """
        tool_name = input_data.get('tool_name', '')
        tool_input = input_data.get('tool_input', {})

        # Block dangerous operations
        if tool_name == 'Bash':
            command = tool_input.get('command', '')
            dangerous_patterns = ['rm -rf /', 'sudo rm', ':(){:|:&};:', ':(){ :|:& };:']

            for pattern in dangerous_patterns:
                if pattern in command:
                    logger.warning(f"Blocked dangerous command: {command}")
                    return {
                        'hookSpecificOutput': {
                            'hookEventName': 'PreToolUse',
                            'permissionDecision': 'deny',
                            'permissionDecisionReason': f'Dangerous command pattern detected: {pattern}'
                        }
                    }

        return {}

    # Return hook configuration for Claude Agent SDK
    return {
        'PreToolUse': [
            HookMatcher(hooks=[kstar_pre_tool_hook, p3394_compliance_hook]),
            HookMatcher(matcher='Bash', hooks=[security_audit_hook])
        ],
        'PostToolUse': [
            HookMatcher(hooks=[kstar_post_tool_hook])
        ]
    }
