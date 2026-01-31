"""
MCP Tools for KSTAR+ Control Token Management

Provides tools for storing and retrieving control tokens with:
- Guaranteed key-value resolution (symbolic accuracy)
- Lineage/provenance tracking
- Token lifecycle management

These tools bridge the gap between "thought" and "action" by managing
the authority tokens that unlock execution.
"""

from claude_agent_sdk import tool
from typing import Any, Dict, List
import logging

logger = logging.getLogger(__name__)


def create_token_tools(gateway: "AgentGateway"):
    """
    Create MCP tools for control token operations.

    Args:
        gateway: The AgentGateway instance

    Returns:
        List of tool functions for registration
    """

    @tool(
        name="store_control_token",
        description="""Store a KSTAR+ Control Token for guaranteed key-value resolution.

Control tokens are the 4th memory class - they authorize execution.
Unlike semantic memory, tokens provide EXACT lookup by key.

Examples:
- Store API key: key="anthropic", value="sk-...", token_type="api_key"
- Store phone binding: key="whatsapp:+1234567890", value="+1234567890", token_type="phone"
- Store capability: key="mcp:memory:write", value="granted", token_type="capability"
""",
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The lookup key (e.g., 'anthropic', 'whatsapp:+1234567890')"
                },
                "value": {
                    "type": "string",
                    "description": "The secret value (will be hashed for storage)"
                },
                "token_type": {
                    "type": "string",
                    "description": "Type of token",
                    "enum": [
                        "api_key", "oauth", "session", "password",
                        "file_path", "inode", "permission",
                        "skill_id", "capability", "manifest", "mcp_tool",
                        "phone", "email", "biometric", "badge",
                        "function_ptr", "agent_uri", "channel_binding"
                    ]
                },
                "binding_target": {
                    "type": "string",
                    "description": "What this token unlocks (e.g., 'claude-sonnet-4', 'mcp__tool__xyz')"
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Permissions granted: read, write, execute, admin, delete, *",
                    "default": ["read"]
                },
                "provenance_source": {
                    "type": "string",
                    "description": "Who/what issued this token",
                    "default": "agent"
                },
                "provenance_method": {
                    "type": "string",
                    "description": "How the token was obtained",
                    "enum": ["issued", "delegated", "discovered", "user_provided", "generated", "rotated"],
                    "default": "user_provided"
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata to store with the token"
                }
            },
            "required": ["key", "value", "token_type", "binding_target"]
        }
    )
    async def store_control_token(args: Dict[str, Any]) -> Dict[str, Any]:
        """Store a control token for guaranteed key-value resolution."""
        try:
            from ..memory.supabase_token_store import store_token

            result = await store_token(
                key=args["key"],
                value=args["value"],
                token_type=args["token_type"],
                binding_target=args["binding_target"],
                scopes=args.get("scopes", ["read"]),
                provenance_source=args.get("provenance_source", "agent"),
                provenance_method=args.get("provenance_method", "user_provided"),
                metadata=args.get("metadata", {})
            )

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Control token stored\n\n"
                            f"**Token ID:** {result['token_id']}\n"
                            f"**Key:** {result['key']}\n"
                            f"**Type:** {args['token_type']}\n"
                            f"**Binding:** {args['binding_target']}\n\n"
                            f"Token is now available for guaranteed key-value lookup."
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to store control token: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error storing control token: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="get_control_token",
        description="""Retrieve a control token by key (guaranteed resolution).

This is the EXACT lookup for control tokens - no fuzzy matching.
Use this when you need to authorize an action.

Returns token metadata (NOT the secret value) for verification.
""",
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The lookup key"
                },
                "token_type": {
                    "type": "string",
                    "description": "Optional: filter by token type",
                    "enum": [
                        "api_key", "oauth", "session", "password",
                        "file_path", "inode", "permission",
                        "skill_id", "capability", "manifest", "mcp_tool",
                        "phone", "email", "biometric", "badge",
                        "function_ptr", "agent_uri", "channel_binding"
                    ]
                }
            },
            "required": ["key"]
        }
    )
    async def get_control_token(args: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve a control token by key."""
        try:
            from ..memory.supabase_token_store import get_token

            result = await get_token(
                key=args["key"],
                token_type=args.get("token_type")
            )

            if result["success"]:
                token = result["token"]
                return {
                    "content": [{
                        "type": "text",
                        "text": f"✓ Token found\n\n"
                                f"**Token ID:** {token['token_id']}\n"
                                f"**Key:** {token['key']}\n"
                                f"**Type:** {token['token_type']}\n"
                                f"**Binding:** {token['binding_target']}\n"
                                f"**Scopes:** {', '.join(token['scopes'])}\n"
                                f"**Valid:** {'Yes' if not token['is_revoked'] else 'No (revoked)'}\n"
                                f"**Use Count:** {token['use_count']}\n"
                                f"**Created:** {token['created_at']}"
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ No valid token found for key: {args['key']}"
                    }]
                }

        except Exception as e:
            logger.exception(f"Failed to get control token: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting control token: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="verify_control_token",
        description="""Verify a token value against stored hash.

Use this before executing an action to confirm the token is valid.
This is the GATE between thought and action.
""",
        input_schema={
            "type": "object",
            "properties": {
                "key": {
                    "type": "string",
                    "description": "The token key"
                },
                "value": {
                    "type": "string",
                    "description": "The value to verify"
                }
            },
            "required": ["key", "value"]
        }
    )
    async def verify_control_token(args: Dict[str, Any]) -> Dict[str, Any]:
        """Verify a token value against stored hash."""
        try:
            from ..memory.supabase_token_store import verify_token

            result = await verify_token(
                key=args["key"],
                value=args["value"]
            )

            if result["valid"]:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"✓ Token verified for key: {args['key']}\n\n"
                                f"The GATE is open - action is authorized."
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ Token verification failed for key: {args['key']}\n\n"
                                f"The GATE is closed - action is NOT authorized."
                    }]
                }

        except Exception as e:
            logger.exception(f"Failed to verify control token: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error verifying control token: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="revoke_control_token",
        description="""Revoke a control token (closes the gate).

Revoked tokens can no longer authorize actions.
Use this for security incidents or credential rotation.
""",
        input_schema={
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "The token ID to revoke"
                },
                "reason": {
                    "type": "string",
                    "description": "Reason for revocation"
                }
            },
            "required": ["token_id"]
        }
    )
    async def revoke_control_token(args: Dict[str, Any]) -> Dict[str, Any]:
        """Revoke a control token."""
        try:
            from ..memory.supabase_token_store import revoke_token

            # Get current principal from gateway context
            principal_id = "system:agent"  # Default

            result = await revoke_token(
                token_id=args["token_id"],
                by=principal_id,
                reason=args.get("reason", "Revoked by agent")
            )

            if result["success"]:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"✓ Token revoked: {args['token_id']}\n\n"
                                f"The GATE is now permanently closed for this token."
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"❌ Failed to revoke token: {args['token_id']}"
                    }],
                    "isError": True
                }

        except Exception as e:
            logger.exception(f"Failed to revoke control token: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error revoking control token: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="get_token_lineage",
        description="""Get the provenance chain for a token.

Shows the full delegation history - who issued it, who delegated it,
and the complete chain of custody.
""",
        input_schema={
            "type": "object",
            "properties": {
                "token_id": {
                    "type": "string",
                    "description": "The token ID to trace"
                }
            },
            "required": ["token_id"]
        }
    )
    async def get_token_lineage(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get the provenance chain for a token."""
        try:
            from ..memory.supabase_token_store import get_lineage

            result = await get_lineage(args["token_id"])

            if result["chain"]:
                chain_text = "**Provenance Chain:**\n\n"
                for i, token in enumerate(result["chain"]):
                    prefix = "└─" if i == len(result["chain"]) - 1 else "├─"
                    prov = token.get("provenance", {})
                    chain_text += f"{prefix} **{token['token_id']}**\n"
                    chain_text += f"   Type: {token['token_type']}\n"
                    chain_text += f"   Source: {prov.get('source', 'unknown')}\n"
                    chain_text += f"   Method: {prov.get('method', 'unknown')}\n\n"

                return {
                    "content": [{
                        "type": "text",
                        "text": f"✓ Lineage found ({result['chain_length']} tokens)\n\n{chain_text}"
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"No lineage found for token: {args['token_id']}"
                    }]
                }

        except Exception as e:
            logger.exception(f"Failed to get token lineage: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting token lineage: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="list_tokens_by_type",
        description="""List all tokens of a specific type.

Useful for auditing and managing token inventory.
""",
        input_schema={
            "type": "object",
            "properties": {
                "token_type": {
                    "type": "string",
                    "description": "Type of tokens to list",
                    "enum": [
                        "api_key", "oauth", "session", "password",
                        "file_path", "inode", "permission",
                        "skill_id", "capability", "manifest", "mcp_tool",
                        "phone", "email", "biometric", "badge",
                        "function_ptr", "agent_uri", "channel_binding"
                    ]
                },
                "include_revoked": {
                    "type": "boolean",
                    "description": "Include revoked tokens",
                    "default": False
                }
            },
            "required": ["token_type"]
        }
    )
    async def list_tokens_by_type(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all tokens of a specific type."""
        try:
            from ..memory.supabase_token_store import get_token_store
            from ..memory.control_tokens import TokenType

            store = get_token_store()
            tokens = await store.list_by_type(
                TokenType(args["token_type"]),
                include_revoked=args.get("include_revoked", False)
            )

            if tokens:
                token_list = f"**{args['token_type']} Tokens ({len(tokens)}):**\n\n"
                for token in tokens:
                    status = "🔴 Revoked" if token.is_revoked else "🟢 Active"
                    token_list += f"- **{token.key}** ({status})\n"
                    token_list += f"  ID: {token.token_id}\n"
                    token_list += f"  Binding: {token.binding_target}\n"
                    token_list += f"  Uses: {token.use_count}\n\n"

                return {
                    "content": [{
                        "type": "text",
                        "text": token_list
                    }]
                }
            else:
                return {
                    "content": [{
                        "type": "text",
                        "text": f"No tokens found of type: {args['token_type']}"
                    }]
                }

        except Exception as e:
            logger.exception(f"Failed to list tokens: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error listing tokens: {str(e)}"
                }],
                "isError": True
            }

    # Return all tools
    return [
        store_control_token,
        get_control_token,
        verify_control_token,
        revoke_control_token,
        get_token_lineage,
        list_tokens_by_type
    ]
