"""
KSTAR MCP Tools for Principal, Identity, and Auth Management

Provides MCP tools for unified LTM access following the MCP-first architecture:
- All agent memory operations go through these tools
- Storage backend is abstracted behind the MCP interface
- Consistent P3394 interface for all capabilities

Tool Categories:
1. Principal Management: register, get, list, update principals
2. Identity Resolution: map channel identities to semantic principals
3. Credential Binding: manage credential-to-principal mappings
4. Auth Operations: user creation, authentication, session management
"""

from claude_agent_sdk import tool
from typing import Any, Dict, List, Optional
from datetime import datetime, timedelta
import logging
import hashlib
from uuid import uuid4

logger = logging.getLogger(__name__)


def create_kstar_tools(gateway: "AgentGateway"):
    """
    Create MCP tools for KSTAR principal/auth operations.

    These tools provide the agentic interface to identity management.
    The agent uses these tools to manage its own identity infrastructure.

    Args:
        gateway: The AgentGateway instance

    Returns:
        List of tool functions for registration
    """

    # =========================================================================
    # PRINCIPAL MANAGEMENT TOOLS
    # =========================================================================

    @tool(
        name="kstar_register_principal",
        description="""Register or update a principal in the identity registry.

A Principal is a semantic identity (P3394 Org-Role-Person composite).
Principal URN format: urn:principal:org:{org_id}:role:{role_id}:person:{person_id}

Use this to:
- Create a new principal for a user
- Update an existing principal's metadata
- Set principal active/inactive status

Examples:
- Register human user: org="ieee", role="member", person="jsmith"
- Register service: org="ieee3394", role="service", person="bot-001"
""",
        input_schema={
            "type": "object",
            "properties": {
                "org": {
                    "type": "string",
                    "description": "Organization identifier (e.g., 'ieee', 'ieee3394')"
                },
                "role": {
                    "type": "string",
                    "description": "Role identifier (e.g., 'member', 'admin', 'chair')"
                },
                "person": {
                    "type": "string",
                    "description": "Person/entity identifier (e.g., 'jsmith', 'bot-001')"
                },
                "principal_type": {
                    "type": "string",
                    "description": "Type of principal",
                    "enum": ["human", "agent", "service", "system", "anonymous"],
                    "default": "human"
                },
                "display_name": {
                    "type": "string",
                    "description": "Human-readable name for the principal"
                },
                "email": {
                    "type": "string",
                    "description": "Email address (optional)"
                },
                "is_active": {
                    "type": "boolean",
                    "description": "Whether the principal is active",
                    "default": True
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional metadata for the principal"
                }
            },
            "required": ["org", "role", "person"]
        }
    )
    async def kstar_register_principal(args: Dict[str, Any]) -> Dict[str, Any]:
        """Register or update a principal."""
        try:
            from ..core.auth.principal import Principal, PrincipalType

            # Build principal URN
            org = args["org"]
            role = args["role"]
            person = args["person"]
            principal_id = f"urn:principal:org:{org}:role:{role}:person:{person}"

            # Determine principal type
            ptype_str = args.get("principal_type", "human")
            ptype = PrincipalType(ptype_str)

            # Create principal
            principal = Principal(
                principal_id=principal_id,
                org=f"urn:org:{org}",
                role=f"urn:role:{role}",
                person=f"urn:person:{person}",
                principal_type=ptype,
                display_name=args.get("display_name"),
                email=args.get("email"),
                metadata=args.get("metadata", {}),
                is_active=args.get("is_active", True)
            )

            # Register with gateway's principal registry
            if gateway.principal_registry:
                gateway.principal_registry.register_principal(principal)

            # Also store in KSTAR memory for persistence
            if gateway.memory:
                await gateway.memory.store_principal(principal.to_dict())

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Principal registered\n\n"
                            f"**Principal ID:** {principal_id}\n"
                            f"**Type:** {ptype.value}\n"
                            f"**Display Name:** {args.get('display_name', 'Not set')}\n"
                            f"**Active:** {'Yes' if principal.is_active else 'No'}"
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to register principal: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error registering principal: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_get_principal",
        description="""Get a principal by ID.

Returns the full principal record including metadata, roles, and status.
""",
        input_schema={
            "type": "object",
            "properties": {
                "principal_id": {
                    "type": "string",
                    "description": "Principal URN (e.g., 'urn:principal:org:ieee:role:member:person:jsmith')"
                }
            },
            "required": ["principal_id"]
        }
    )
    async def kstar_get_principal(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get a principal by ID."""
        try:
            principal_id = args["principal_id"]

            # Try registry first (in-memory, fast)
            if gateway.principal_registry:
                principal = gateway.principal_registry.get_principal(principal_id)
                if principal:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"✓ Principal found\n\n"
                                    f"**Principal ID:** {principal.principal_id}\n"
                                    f"**Type:** {principal.principal_type.value}\n"
                                    f"**Org:** {principal.org}\n"
                                    f"**Role:** {principal.role}\n"
                                    f"**Person:** {principal.person}\n"
                                    f"**Display Name:** {principal.display_name or 'Not set'}\n"
                                    f"**Email:** {principal.email or 'Not set'}\n"
                                    f"**Active:** {'Yes' if principal.is_active else 'No'}\n"
                                    f"**Created:** {principal.created_at.isoformat()}"
                        }]
                    }

            # Fall back to KSTAR memory
            if gateway.memory:
                principal_data = await gateway.memory.get_principal(principal_id)
                if principal_data:
                    import json
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"✓ Principal found (from memory)\n\n```json\n{json.dumps(principal_data, indent=2)}\n```"
                        }]
                    }

            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Principal not found: {principal_id}"
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to get principal: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting principal: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_list_principals",
        description="""List all principals, optionally filtered by type.

Returns summary of all registered principals.
""",
        input_schema={
            "type": "object",
            "properties": {
                "principal_type": {
                    "type": "string",
                    "description": "Filter by principal type",
                    "enum": ["human", "agent", "service", "system", "anonymous"]
                },
                "active_only": {
                    "type": "boolean",
                    "description": "Only return active principals",
                    "default": True
                }
            },
            "required": []
        }
    )
    async def kstar_list_principals(args: Dict[str, Any]) -> Dict[str, Any]:
        """List all principals."""
        try:
            from ..core.auth.principal import PrincipalType

            principals = []
            ptype_filter = args.get("principal_type")
            active_only = args.get("active_only", True)

            # Get from registry
            if gateway.principal_registry:
                if ptype_filter:
                    ptype = PrincipalType(ptype_filter)
                    principals = gateway.principal_registry.list_principals(principal_type=ptype)
                else:
                    principals = gateway.principal_registry.list_principals()

                if active_only:
                    principals = [p for p in principals if p.is_active]

            if not principals:
                return {
                    "content": [{
                        "type": "text",
                        "text": "No principals found"
                    }]
                }

            result_text = f"**Principals ({len(principals)}):**\n\n"
            for p in principals:
                status = "🟢" if p.is_active else "🔴"
                result_text += f"{status} **{p.display_name or p.person}** ({p.principal_type.value})\n"
                result_text += f"   URN: {p.principal_id}\n"
                result_text += f"   Role: {p.role}\n\n"

            return {
                "content": [{
                    "type": "text",
                    "text": result_text
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to list principals: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error listing principals: {str(e)}"
                }],
                "isError": True
            }

    # =========================================================================
    # IDENTITY RESOLUTION TOOLS
    # =========================================================================

    @tool(
        name="kstar_resolve_identity",
        description="""Resolve a channel identity to a semantic principal.

This is the CORE P3394 requirement: map channel-specific identities
(phone numbers, emails, usernames) to semantic principals.

Examples:
- channel="whatsapp", identity="+1234567890" → Principal URN
- channel="cli", identity="local:owner" → Principal URN
- channel="web", identity="user@example.com" → Principal URN
""",
        input_schema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID (e.g., 'whatsapp', 'cli', 'web', 'p3394')"
                },
                "channel_identity": {
                    "type": "string",
                    "description": "Channel-specific identity (phone, email, username)"
                }
            },
            "required": ["channel", "channel_identity"]
        }
    )
    async def kstar_resolve_identity(args: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve channel identity to principal."""
        try:
            channel = args["channel"]
            channel_identity = args["channel_identity"]

            if gateway.principal_registry:
                principal = gateway.principal_registry.resolve_channel_identity(
                    channel, channel_identity
                )

                if principal:
                    return {
                        "content": [{
                            "type": "text",
                            "text": f"✓ Identity resolved\n\n"
                                    f"**Channel:** {channel}\n"
                                    f"**Identity:** {channel_identity}\n"
                                    f"**→ Principal:** {principal.principal_id}\n"
                                    f"**Display Name:** {principal.display_name or 'Not set'}\n"
                                    f"**Type:** {principal.principal_type.value}"
                        }]
                    }

            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ No principal found for {channel}:{channel_identity}\n\n"
                            f"The identity is not bound to any principal. Use `kstar_create_binding` to create a binding."
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to resolve identity: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error resolving identity: {str(e)}"
                }],
                "isError": True
            }

    # =========================================================================
    # CREDENTIAL BINDING TOOLS
    # =========================================================================

    @tool(
        name="kstar_create_binding",
        description="""Create a credential binding (channel identity → principal mapping).

This binds a channel-specific credential to a semantic principal.
After creating a binding, the identity can be resolved to the principal.

Examples:
- Bind WhatsApp phone: channel="whatsapp", identity="+1234567890", principal_id="urn:principal:..."
- Bind email: channel="web", identity="user@example.com", principal_id="urn:principal:..."
""",
        input_schema={
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "Channel ID (e.g., 'whatsapp', 'cli', 'web')"
                },
                "external_subject": {
                    "type": "string",
                    "description": "Channel-specific identity to bind"
                },
                "principal_id": {
                    "type": "string",
                    "description": "Principal URN to bind to"
                },
                "binding_type": {
                    "type": "string",
                    "description": "Type of credential",
                    "enum": ["account", "oauth", "api_key", "phone", "email", "os_user", "local_socket"],
                    "default": "account"
                },
                "scopes": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Permissions granted by this binding",
                    "default": ["read", "write"]
                },
                "secret": {
                    "type": "string",
                    "description": "Optional secret (password, API key) to hash and store"
                },
                "expires_in_days": {
                    "type": "number",
                    "description": "Days until binding expires (null = never)"
                }
            },
            "required": ["channel", "external_subject", "principal_id"]
        }
    )
    async def kstar_create_binding(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a credential binding."""
        try:
            from ..core.auth.credential_binding import CredentialBinding, BindingType

            channel = args["channel"]
            external_subject = args["external_subject"]
            principal_id = args["principal_id"]

            # Generate binding ID
            binding_id = f"urn:cred:{channel}:{external_subject.replace('+', '').replace('@', '_').replace(' ', '')}"

            # Determine binding type
            btype_str = args.get("binding_type", "account")
            btype = BindingType(btype_str)

            # Calculate expiry
            expires_at = None
            if args.get("expires_in_days"):
                expires_at = datetime.utcnow() + timedelta(days=args["expires_in_days"])

            # Hash secret if provided
            secret_hash = None
            if args.get("secret"):
                secret_hash = hashlib.sha256(args["secret"].encode()).hexdigest()

            # Create binding
            binding = CredentialBinding(
                binding_id=binding_id,
                principal_id=principal_id,
                channel=channel,
                binding_type=btype,
                external_subject=external_subject,
                scopes=args.get("scopes", ["read", "write"]),
                secret_hash=secret_hash,
                is_active=True,
                expires_at=expires_at
            )

            # Register with gateway
            if gateway.principal_registry:
                gateway.principal_registry.register_binding(binding)

            # Also store in KSTAR memory
            if gateway.memory:
                await gateway.memory.store_credential_binding(binding.to_dict())

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Credential binding created\n\n"
                            f"**Binding ID:** {binding_id}\n"
                            f"**Channel:** {channel}\n"
                            f"**Identity:** {external_subject}\n"
                            f"**→ Principal:** {principal_id}\n"
                            f"**Type:** {btype.value}\n"
                            f"**Scopes:** {', '.join(binding.scopes)}\n"
                            f"**Expires:** {expires_at.isoformat() if expires_at else 'Never'}"
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to create binding: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error creating binding: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_list_bindings",
        description="""List credential bindings, optionally filtered by principal or channel.

Shows all mappings between channel identities and principals.
""",
        input_schema={
            "type": "object",
            "properties": {
                "principal_id": {
                    "type": "string",
                    "description": "Filter by principal ID"
                },
                "channel": {
                    "type": "string",
                    "description": "Filter by channel"
                }
            },
            "required": []
        }
    )
    async def kstar_list_bindings(args: Dict[str, Any]) -> Dict[str, Any]:
        """List credential bindings."""
        try:
            bindings = []

            if gateway.principal_registry:
                bindings = gateway.principal_registry.list_bindings(
                    principal_id=args.get("principal_id"),
                    channel=args.get("channel")
                )

            if not bindings:
                return {
                    "content": [{
                        "type": "text",
                        "text": "No credential bindings found"
                    }]
                }

            result_text = f"**Credential Bindings ({len(bindings)}):**\n\n"
            for b in bindings:
                status = "🟢" if b.is_active and not b.is_expired() else "🔴"
                result_text += f"{status} **{b.channel}:{b.external_subject}**\n"
                result_text += f"   → {b.principal_id}\n"
                result_text += f"   Type: {b.binding_type.value}\n"
                result_text += f"   Scopes: {', '.join(b.scopes)}\n"
                if b.last_used_at:
                    result_text += f"   Last Used: {b.last_used_at.isoformat()}\n"
                result_text += "\n"

            return {
                "content": [{
                    "type": "text",
                    "text": result_text
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to list bindings: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error listing bindings: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_delete_binding",
        description="""Delete a credential binding.

Removes the mapping between a channel identity and principal.
The identity will no longer resolve to any principal.
""",
        input_schema={
            "type": "object",
            "properties": {
                "binding_id": {
                    "type": "string",
                    "description": "Binding ID to delete (e.g., 'urn:cred:whatsapp:1234567890')"
                }
            },
            "required": ["binding_id"]
        }
    )
    async def kstar_delete_binding(args: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a credential binding."""
        try:
            binding_id = args["binding_id"]

            if gateway.principal_registry:
                gateway.principal_registry.delete_binding(binding_id)

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Credential binding deleted: {binding_id}"
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to delete binding: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error deleting binding: {str(e)}"
                }],
                "isError": True
            }

    # =========================================================================
    # AUTH OPERATIONS (User/Session Management)
    # =========================================================================

    @tool(
        name="kstar_create_user",
        description="""Create a user and automatically register as a principal.

This is the MCP-first way to create users. It:
1. Creates the user record
2. Auto-generates a principal URN
3. Creates a credential binding for the email

Use this for web channel user registration.
""",
        input_schema={
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "password": {
                    "type": "string",
                    "description": "User's password (will be hashed)"
                },
                "display_name": {
                    "type": "string",
                    "description": "User's display name"
                },
                "org": {
                    "type": "string",
                    "description": "Organization for principal URN",
                    "default": "users"
                },
                "role": {
                    "type": "string",
                    "description": "Role for principal URN",
                    "default": "member"
                }
            },
            "required": ["email", "password"]
        }
    )
    async def kstar_create_user(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a user with auto-principal registration."""
        try:
            from ..data.models.auth import User
            from ..core.auth.principal import Principal, PrincipalType
            from ..core.auth.credential_binding import CredentialBinding, BindingType

            email = args["email"].lower()
            password = args["password"]
            display_name = args.get("display_name", email.split("@")[0])
            org = args.get("org", "users")
            role = args.get("role", "member")

            # Generate person ID from email
            person_id = email.replace("@", "_").replace(".", "_")

            # Create principal
            principal_id = f"urn:principal:org:{org}:role:{role}:person:{person_id}"
            principal = Principal(
                principal_id=principal_id,
                org=f"urn:org:{org}",
                role=f"urn:role:{role}",
                person=f"urn:person:{person_id}",
                principal_type=PrincipalType.HUMAN,
                display_name=display_name,
                email=email,
                is_active=True
            )

            # Register principal
            if gateway.principal_registry:
                gateway.principal_registry.register_principal(principal)

            # Create email binding
            binding = CredentialBinding(
                binding_id=f"urn:cred:web:{person_id}",
                principal_id=principal_id,
                channel="web",
                binding_type=BindingType.EMAIL,
                external_subject=email,
                secret_hash=hashlib.sha256(password.encode()).hexdigest(),
                scopes=["read", "write", "chat"],
                is_active=True
            )

            if gateway.principal_registry:
                gateway.principal_registry.register_binding(binding)

            # Store in KSTAR memory
            if gateway.memory:
                await gateway.memory.store_principal(principal.to_dict())
                await gateway.memory.store_credential_binding(binding.to_dict())

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ User created\n\n"
                            f"**Email:** {email}\n"
                            f"**Display Name:** {display_name}\n"
                            f"**Principal ID:** {principal_id}\n"
                            f"**Binding:** web:{email} → principal\n\n"
                            f"User can now authenticate via the web channel."
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to create user: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error creating user: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_authenticate_user",
        description="""Authenticate a user with email and password.

Returns authentication result and principal information if successful.
""",
        input_schema={
            "type": "object",
            "properties": {
                "email": {
                    "type": "string",
                    "description": "User's email address"
                },
                "password": {
                    "type": "string",
                    "description": "User's password"
                }
            },
            "required": ["email", "password"]
        }
    )
    async def kstar_authenticate_user(args: Dict[str, Any]) -> Dict[str, Any]:
        """Authenticate a user."""
        try:
            email = args["email"].lower()
            password = args["password"]
            password_hash = hashlib.sha256(password.encode()).hexdigest()

            # Find binding for this email
            if gateway.principal_registry:
                bindings = gateway.principal_registry.list_bindings(channel="web")

                for binding in bindings:
                    if binding.external_subject.lower() == email:
                        # Verify password
                        if binding.secret_hash == password_hash:
                            binding.touch()

                            # Get principal
                            principal = gateway.principal_registry.get_principal(binding.principal_id)

                            if principal and principal.is_active:
                                return {
                                    "content": [{
                                        "type": "text",
                                        "text": f"✓ Authentication successful\n\n"
                                                f"**Principal:** {principal.principal_id}\n"
                                                f"**Display Name:** {principal.display_name}\n"
                                                f"**Type:** {principal.principal_type.value}\n"
                                                f"**Scopes:** {', '.join(binding.scopes)}"
                                    }]
                                }
                            else:
                                return {
                                    "content": [{
                                        "type": "text",
                                        "text": "❌ Authentication failed: Principal is inactive"
                                    }],
                                    "isError": True
                                }
                        else:
                            return {
                                "content": [{
                                    "type": "text",
                                    "text": "❌ Authentication failed: Invalid password"
                                }],
                                "isError": True
                            }

            return {
                "content": [{
                    "type": "text",
                    "text": f"❌ Authentication failed: User not found for {email}"
                }],
                "isError": True
            }

        except Exception as e:
            logger.exception(f"Failed to authenticate user: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error authenticating user: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_create_session",
        description="""Create a session token for an authenticated principal.

Returns a session token that can be used for subsequent requests.
""",
        input_schema={
            "type": "object",
            "properties": {
                "principal_id": {
                    "type": "string",
                    "description": "Principal URN to create session for"
                },
                "channel": {
                    "type": "string",
                    "description": "Channel creating the session",
                    "default": "web"
                },
                "expires_in_hours": {
                    "type": "number",
                    "description": "Session expiry in hours",
                    "default": 24
                },
                "metadata": {
                    "type": "object",
                    "description": "Additional session metadata"
                }
            },
            "required": ["principal_id"]
        }
    )
    async def kstar_create_session(args: Dict[str, Any]) -> Dict[str, Any]:
        """Create a session token."""
        try:
            principal_id = args["principal_id"]
            channel = args.get("channel", "web")
            expires_in_hours = args.get("expires_in_hours", 24)

            # Generate session token
            session_id = str(uuid4())
            token = f"sess_{uuid4().hex}"
            token_hash = hashlib.sha256(token.encode()).hexdigest()
            expires_at = datetime.utcnow() + timedelta(hours=expires_in_hours)

            # Store session in KSTAR memory as a control token
            if gateway.memory:
                await gateway.memory.store_credential_binding({
                    "credential_type": "session",
                    "credential_value": token_hash,
                    "principal_urn": principal_id,
                    "channel": channel,
                    "session_id": session_id,
                    "expires_at": expires_at.isoformat(),
                    "metadata": args.get("metadata", {})
                })

            return {
                "content": [{
                    "type": "text",
                    "text": f"✓ Session created\n\n"
                            f"**Session ID:** {session_id}\n"
                            f"**Token:** {token}\n"
                            f"**Principal:** {principal_id}\n"
                            f"**Channel:** {channel}\n"
                            f"**Expires:** {expires_at.isoformat()}\n\n"
                            f"⚠️ Store the token securely - it won't be shown again."
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to create session: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error creating session: {str(e)}"
                }],
                "isError": True
            }

    @tool(
        name="kstar_validate_session",
        description="""Validate a session token.

Returns the associated principal if the session is valid.
""",
        input_schema={
            "type": "object",
            "properties": {
                "token": {
                    "type": "string",
                    "description": "Session token to validate"
                }
            },
            "required": ["token"]
        }
    )
    async def kstar_validate_session(args: Dict[str, Any]) -> Dict[str, Any]:
        """Validate a session token."""
        try:
            token = args["token"]
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Look up session in KSTAR memory
            if gateway.memory:
                binding = await gateway.memory.get_credential_binding("session", token_hash)

                if binding:
                    # Check expiry
                    expires_at = binding.get("expires_at")
                    if expires_at:
                        exp_dt = datetime.fromisoformat(expires_at.replace("Z", "+00:00"))
                        if datetime.utcnow() > exp_dt.replace(tzinfo=None):
                            return {
                                "content": [{
                                    "type": "text",
                                    "text": "❌ Session expired"
                                }],
                                "isError": True
                            }

                    principal_id = binding.get("principal_urn")

                    # Get principal details
                    if gateway.principal_registry:
                        principal = gateway.principal_registry.get_principal(principal_id)
                        if principal:
                            return {
                                "content": [{
                                    "type": "text",
                                    "text": f"✓ Session valid\n\n"
                                            f"**Session ID:** {binding.get('session_id')}\n"
                                            f"**Principal:** {principal_id}\n"
                                            f"**Display Name:** {principal.display_name}\n"
                                            f"**Expires:** {expires_at}"
                                }]
                            }

                    return {
                        "content": [{
                            "type": "text",
                            "text": f"✓ Session valid\n\n"
                                    f"**Principal:** {principal_id}\n"
                                    f"**Expires:** {expires_at}"
                        }]
                    }

            return {
                "content": [{
                    "type": "text",
                    "text": "❌ Invalid session token"
                }],
                "isError": True
            }

        except Exception as e:
            logger.exception(f"Failed to validate session: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error validating session: {str(e)}"
                }],
                "isError": True
            }

    # =========================================================================
    # REGISTRY STATISTICS
    # =========================================================================

    @tool(
        name="kstar_identity_stats",
        description="""Get identity registry statistics.

Shows counts of principals, bindings, and breakdown by type.
""",
        input_schema={
            "type": "object",
            "properties": {},
            "required": []
        }
    )
    async def kstar_identity_stats(args: Dict[str, Any]) -> Dict[str, Any]:
        """Get identity registry statistics."""
        try:
            stats = {}

            if gateway.principal_registry:
                stats = gateway.principal_registry.get_stats()

            if gateway.memory:
                memory_stats = await gateway.memory.get_stats()
                stats["kstar_principals"] = memory_stats.get("principal_count", 0)
                stats["kstar_bindings"] = memory_stats.get("binding_count", 0)

            result_text = "**Identity Registry Statistics:**\n\n"
            result_text += f"- Total Principals: {stats.get('total_principals', 0)}\n"
            result_text += f"- Active Principals: {stats.get('active_principals', 0)}\n"
            result_text += f"- Total Bindings: {stats.get('total_bindings', 0)}\n"
            result_text += f"- Active Bindings: {stats.get('active_bindings', 0)}\n\n"

            if stats.get("principals_by_type"):
                result_text += "**By Type:**\n"
                for ptype, count in stats["principals_by_type"].items():
                    result_text += f"  - {ptype}: {count}\n"

            if stats.get("bindings_by_channel"):
                result_text += "\n**By Channel:**\n"
                for channel, count in stats["bindings_by_channel"].items():
                    result_text += f"  - {channel}: {count}\n"

            return {
                "content": [{
                    "type": "text",
                    "text": result_text
                }]
            }

        except Exception as e:
            logger.exception(f"Failed to get stats: {e}")
            return {
                "content": [{
                    "type": "text",
                    "text": f"Error getting stats: {str(e)}"
                }],
                "isError": True
            }

    # Return all tools
    return [
        # Principal management
        kstar_register_principal,
        kstar_get_principal,
        kstar_list_principals,
        # Identity resolution
        kstar_resolve_identity,
        # Credential binding
        kstar_create_binding,
        kstar_list_bindings,
        kstar_delete_binding,
        # Auth operations
        kstar_create_user,
        kstar_authenticate_user,
        kstar_create_session,
        kstar_validate_session,
        # Statistics
        kstar_identity_stats,
    ]
