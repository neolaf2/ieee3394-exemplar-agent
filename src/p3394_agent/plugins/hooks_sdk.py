"""
Claude Agent SDK Hooks for P3394 Agent

Implements hooks for:
- KSTAR memory logging (traces)
- P3394 compliance checking
- Security auditing
"""

from claude_agent_sdk import HookMatcher
from typing import Any, Dict
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


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
        Pre-tool hook that logs to KSTAR memory.

        This implements the T→A transition in the KSTAR cognitive cycle:
        - Task has been determined
        - Action is about to be executed
        """
        if not gateway.memory:
            return {}

        tool_name = input_data.get('tool_name', 'unknown')
        tool_input = input_data.get('tool_input', {})

        logger.debug(f"Pre-tool hook: {tool_name}")

        try:
            await gateway.memory.store_trace({
                "situation": {
                    "domain": "p3394_agent",
                    "actor": "agent",
                    "protocol": "claude_agent_sdk",
                    "now": datetime.utcnow().isoformat()
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
        Post-tool hook that records results to KSTAR.

        This implements the A→R transition in the KSTAR cognitive cycle:
        - Action has been executed
        - Result is being recorded
        """
        if not gateway.memory:
            return {}

        tool_name = input_data.get('tool_name', 'unknown')
        is_error = input_data.get('is_error', False)

        logger.debug(f"Post-tool hook: {tool_name}, error={is_error}")

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
