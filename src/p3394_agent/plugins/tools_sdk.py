"""
Claude Agent SDK Custom Tools for P3394 Agent

Implements custom tools as in-process MCP servers:
- KSTAR memory operations
- P3394 agent discovery
- Skill management
"""

from claude_agent_sdk import tool, create_sdk_mcp_server
from typing import Any, Dict
import logging

logger = logging.getLogger(__name__)


def create_sdk_tools(gateway: "AgentGateway"):
    """
    Create SDK MCP server with P3394-specific custom tools.

    Args:
        gateway: The AgentGateway instance (for accessing memory, skills, etc.)

    Returns:
        SDK MCP server instance
    """

    @tool(
        name="query_memory",
        description="Query KSTAR memory for past traces, perceptions, or skills",
        input_schema={
            "type": "object",
            "properties": {
                "domain": {
                    "type": "string",
                    "description": "Domain to search in (e.g., 'p3394_agent')"
                },
                "goal": {
                    "type": "string",
                    "description": "Goal or task to find similar traces for"
                },
                "limit": {
                    "type": "number",
                    "description": "Maximum number of results to return",
                    "default": 10
                }
            },
            "required": ["domain", "goal"]
        }
    )
    async def query_memory_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Query KSTAR memory for relevant traces"""
        if not gateway.memory:
            return {
                "content": [
                    {"type": "text", "text": "KSTAR memory not available"}
                ]
            }

        try:
            domain = args["domain"]
            goal = args["goal"]
            limit = args.get("limit", 10)

            results = await gateway.memory.query(domain, goal)

            if not results:
                return {
                    "content": [
                        {"type": "text", "text": f"No traces found for goal: {goal}"}
                    ]
                }

            # Format results
            result_text = f"Found {len(results)} traces:\n\n"
            for i, trace in enumerate(results[:limit], 1):
                result_text += f"{i}. Task: {trace.get('task', {}).get('goal', 'Unknown')}\n"
                result_text += f"   Action: {trace.get('action', {}).get('type', 'Unknown')}\n"
                result_text += f"   Result: {trace.get('result', {}).get('status', 'Unknown')}\n\n"

            return {
                "content": [
                    {"type": "text", "text": result_text}
                ]
            }

        except Exception as e:
            logger.exception(f"Error querying memory: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error querying memory: {str(e)}"}
                ],
                "isError": True
            }

    @tool(
        name="store_trace",
        description="Store a new KSTAR trace (episode) in memory",
        input_schema={
            "type": "object",
            "properties": {
                "situation": {
                    "type": "object",
                    "description": "Situation context (domain, actor, etc.)"
                },
                "task": {
                    "type": "object",
                    "description": "Task description (goal, constraints, etc.)"
                },
                "action": {
                    "type": "object",
                    "description": "Action taken (type, parameters, etc.)"
                },
                "result": {
                    "type": "object",
                    "description": "Result of the action (status, outcome, etc.)"
                }
            },
            "required": ["situation", "task", "action"]
        }
    )
    async def store_trace_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Store a KSTAR trace"""
        if not gateway.memory:
            return {
                "content": [
                    {"type": "text", "text": "KSTAR memory not available"}
                ],
                "isError": True
            }

        try:
            trace_id = await gateway.memory.store_trace(args)

            return {
                "content": [
                    {"type": "text", "text": f"Trace stored successfully with ID: {trace_id}"}
                ]
            }

        except Exception as e:
            logger.exception(f"Error storing trace: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error storing trace: {str(e)}"}
                ],
                "isError": True
            }

    @tool(
        name="list_skills",
        description="List all registered skills and their capabilities",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    async def list_skills_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """List registered skills"""
        try:
            if not gateway.skills:
                return {
                    "content": [
                        {"type": "text", "text": "No skills registered yet."}
                    ]
                }

            skills_text = "Registered Skills:\n\n"
            for skill_name, skill_def in gateway.skills.items():
                description = skill_def.get('description', 'No description')
                triggers = skill_def.get('triggers', [])

                skills_text += f"**{skill_name}**\n"
                skills_text += f"  Description: {description}\n"
                if triggers:
                    skills_text += f"  Triggers: {', '.join(triggers)}\n"
                skills_text += "\n"

            return {
                "content": [
                    {"type": "text", "text": skills_text}
                ]
            }

        except Exception as e:
            logger.exception(f"Error listing skills: {e}")
            return {
                "content": [
                    {"type": "text", "text": f"Error listing skills: {str(e)}"}
                ],
                "isError": True
            }

    # Create SDK MCP server with these tools
    server = create_sdk_mcp_server(
        name="p3394_tools",
        version="0.1.0",
        tools=[query_memory_tool, store_trace_tool, list_skills_tool]
    )

    logger.info("Created P3394 SDK MCP server with 3 custom tools")

    return server
