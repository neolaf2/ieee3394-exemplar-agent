"""
Claude Agent SDK Custom Tools for P3394 Agent

Implements custom tools as in-process MCP servers:
- KSTAR memory operations (traces, perceptions, skills)
- KSTAR+ control tokens (the 4th memory class)
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

    # =========================================================================
    # ACL Tools (Capability Access Control)
    # =========================================================================

    @tool(
        name="list_acls",
        description="List all capability ACL definitions",
        input_schema={
            "type": "object",
            "properties": {
                "visibility_filter": {
                    "type": "string",
                    "description": "Filter by visibility tier (public, listed, protected, private, admin)",
                    "enum": ["public", "listed", "protected", "private", "admin"]
                }
            },
            "required": []
        }
    )
    async def list_acls_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all ACL definitions"""
        if not gateway.memory:
            return {
                "content": [{"type": "text", "text": "KSTAR memory not available"}],
                "isError": True
            }

        try:
            acls = await gateway.memory.list_acls()
            visibility_filter = args.get("visibility_filter")

            if visibility_filter:
                acls = [a for a in acls if a.get("visibility") == visibility_filter]

            if not acls:
                return {
                    "content": [{"type": "text", "text": "No ACLs found"}]
                }

            result_text = f"Found {len(acls)} ACLs:\n\n"
            for acl in acls:
                result_text += f"- **{acl.get('capability_id')}**\n"
                result_text += f"  Visibility: {acl.get('visibility', 'unknown')}\n"
                role_perms = acl.get('role_permissions', [])
                if role_perms:
                    roles = [rp.get('role', '?') for rp in role_perms]
                    result_text += f"  Roles: {', '.join(roles)}\n"
                result_text += "\n"

            return {
                "content": [{"type": "text", "text": result_text}]
            }

        except Exception as e:
            logger.exception(f"Error listing ACLs: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    @tool(
        name="get_acl",
        description="Get ACL definition for a specific capability",
        input_schema={
            "type": "object",
            "properties": {
                "capability_id": {
                    "type": "string",
                    "description": "The capability ID to get ACL for"
                }
            },
            "required": ["capability_id"]
        }
    )
    async def get_acl_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get ACL for a capability"""
        if not gateway.memory:
            return {
                "content": [{"type": "text", "text": "KSTAR memory not available"}],
                "isError": True
            }

        try:
            capability_id = args["capability_id"]
            acl = await gateway.memory.get_acl(capability_id)

            if not acl:
                return {
                    "content": [{"type": "text", "text": f"No ACL found for: {capability_id}"}]
                }

            import json
            return {
                "content": [{"type": "text", "text": json.dumps(acl, indent=2)}]
            }

        except Exception as e:
            logger.exception(f"Error getting ACL: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    @tool(
        name="store_acl",
        description="Store or update an ACL definition (admin only)",
        input_schema={
            "type": "object",
            "properties": {
                "capability_id": {
                    "type": "string",
                    "description": "The capability ID"
                },
                "visibility": {
                    "type": "string",
                    "description": "Visibility tier",
                    "enum": ["public", "listed", "protected", "private", "admin"]
                },
                "default_permissions": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Default permissions for unauthenticated access"
                },
                "role_permissions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "role": {"type": "string"},
                            "permissions": {"type": "array", "items": {"type": "string"}},
                            "min_assurance": {"type": "integer"}
                        }
                    },
                    "description": "Role-specific permission mappings"
                }
            },
            "required": ["capability_id", "visibility"]
        }
    )
    async def store_acl_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Store an ACL definition"""
        if not gateway.memory:
            return {
                "content": [{"type": "text", "text": "KSTAR memory not available"}],
                "isError": True
            }

        try:
            acl_id = await gateway.memory.store_acl(args)
            return {
                "content": [{"type": "text", "text": f"ACL stored for capability: {acl_id}"}]
            }

        except Exception as e:
            logger.exception(f"Error storing ACL: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    @tool(
        name="list_principals",
        description="List all principal definitions",
        input_schema={
            "type": "object",
            "properties": {
                "role_filter": {
                    "type": "string",
                    "description": "Filter by role"
                }
            },
            "required": []
        }
    )
    async def list_principals_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all principals"""
        if not gateway.memory:
            return {
                "content": [{"type": "text", "text": "KSTAR memory not available"}],
                "isError": True
            }

        try:
            principals = await gateway.memory.list_principals()
            role_filter = args.get("role_filter")

            if role_filter:
                principals = [
                    p for p in principals
                    if role_filter in p.get("roles", [])
                ]

            if not principals:
                return {
                    "content": [{"type": "text", "text": "No principals found"}]
                }

            result_text = f"Found {len(principals)} principals:\n\n"
            for p in principals:
                result_text += f"- **{p.get('display_name', 'Unknown')}**\n"
                result_text += f"  URN: {p.get('urn', '?')}\n"
                result_text += f"  Roles: {', '.join(p.get('roles', []))}\n\n"

            return {
                "content": [{"type": "text", "text": result_text}]
            }

        except Exception as e:
            logger.exception(f"Error listing principals: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    @tool(
        name="get_memory_stats",
        description="Get KSTAR memory statistics including ACLs and principals",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    async def get_memory_stats_tool(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get memory statistics"""
        if not gateway.memory:
            return {
                "content": [{"type": "text", "text": "KSTAR memory not available"}],
                "isError": True
            }

        try:
            stats = await gateway.memory.get_stats()

            result_text = "KSTAR Memory Statistics:\n\n"
            result_text += f"- Traces: {stats.get('trace_count', 0)}\n"
            result_text += f"- Perceptions: {stats.get('perception_count', 0)}\n"
            result_text += f"- Skills: {stats.get('skill_count', 0)}\n"
            result_text += f"- Capability ACLs: {stats.get('acl_count', 0)}\n"
            result_text += f"- Principals: {stats.get('principal_count', 0)}\n"
            result_text += f"- Credential Bindings: {stats.get('binding_count', 0)}\n"

            return {
                "content": [{"type": "text", "text": result_text}]
            }

        except Exception as e:
            logger.exception(f"Error getting stats: {e}")
            return {
                "content": [{"type": "text", "text": f"Error: {str(e)}"}],
                "isError": True
            }

    # Import and create token tools
    from .token_tools import create_token_tools
    token_tools = create_token_tools(gateway)

    # Combine all tools (including ACL tools)
    acl_tools = [list_acls_tool, get_acl_tool, store_acl_tool, list_principals_tool, get_memory_stats_tool]
    all_tools = [query_memory_tool, store_trace_tool, list_skills_tool] + acl_tools + token_tools

    # Create SDK MCP server with all tools
    server = create_sdk_mcp_server(
        name="p3394_tools",
        version="0.2.0",
        tools=all_tools
    )

    logger.info(f"Created P3394 SDK MCP server with {len(all_tools)} tools (including KSTAR+ control tokens)")

    return server
