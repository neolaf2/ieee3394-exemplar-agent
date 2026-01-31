"""
xAPI (Experience API) Integration for P3394 Agent

Formats agent interactions as xAPI statements for learning record storage.
xAPI provides a standard format for tracking experiences and activities.

xAPI Statement Format:
{
  "actor": {...},      # Who performed the action
  "verb": {...},       # What action was performed
  "object": {...},     # What was acted upon
  "result": {...},     # Optional: outcome
  "context": {...},    # Optional: context info
  "timestamp": "..."   # ISO 8601 timestamp
}
"""

from typing import Any, Dict, Optional
from datetime import datetime, timezone
from uuid import uuid4

from .umf import P3394Message, MessageType


class xAPIFormatter:
    """Formats P3394 messages as xAPI statements"""

    # xAPI Verbs for agent interactions
    VERBS = {
        "asked": {
            "id": "http://adlnet.gov/expapi/verbs/asked",
            "display": {"en-US": "asked"}
        },
        "responded": {
            "id": "http://adlnet.gov/expapi/verbs/responded",
            "display": {"en-US": "responded"}
        },
        "executed": {
            "id": "http://adlnet.gov/expapi/verbs/executed",
            "display": {"en-US": "executed"}
        },
        "completed": {
            "id": "http://adlnet.gov/expapi/verbs/completed",
            "display": {"en-US": "completed"}
        },
        "interacted": {
            "id": "http://adlnet.gov/expapi/verbs/interacted",
            "display": {"en-US": "interacted"}
        },
        "viewed": {
            "id": "http://adlnet.gov/expapi/verbs/viewed",
            "display": {"en-US": "viewed"}
        }
    }

    # xAPI Activity Types
    ACTIVITY_TYPES = {
        "message": "http://activitystrea.ms/schema/1.0/message",
        "command": "http://activitystrea.ms/schema/1.0/command",
        "conversation": "http://activitystrea.ms/schema/1.0/conversation",
        "agent": "http://activitystrea.ms/schema/1.0/service"
    }

    @classmethod
    def format_actor(cls, agent_id: str, client_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Format an xAPI actor.

        Args:
            agent_id: P3394 agent ID
            client_id: Optional client identifier

        Returns:
            xAPI actor object
        """
        actor = {
            "objectType": "Agent",
            "name": client_id or "anonymous",
            "account": {
                "homePage": f"p3394://{agent_id}",
                "name": client_id or "anonymous"
            }
        }
        return actor

    @classmethod
    def format_verb(cls, verb_key: str) -> Dict[str, Any]:
        """Get an xAPI verb"""
        return cls.VERBS.get(verb_key, cls.VERBS["interacted"])

    @classmethod
    def format_activity(
        cls,
        activity_id: str,
        activity_type: str,
        name: str,
        description: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Format an xAPI activity object.

        Args:
            activity_id: Unique activity identifier
            activity_type: Type of activity (message, command, etc.)
            name: Human-readable name
            description: Optional description

        Returns:
            xAPI activity object
        """
        activity = {
            "objectType": "Activity",
            "id": activity_id,
            "definition": {
                "type": cls.ACTIVITY_TYPES.get(activity_type, activity_type),
                "name": {"en-US": name}
            }
        }

        if description:
            activity["definition"]["description"] = {"en-US": description}

        return activity

    @classmethod
    def message_to_statement(
        cls,
        message: P3394Message,
        session_id: str,
        agent_id: str,
        client_id: Optional[str] = None,
        result: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Convert a P3394 message to an xAPI statement.

        Args:
            message: P3394 message
            session_id: Session identifier
            agent_id: Agent identifier
            client_id: Optional client identifier
            result: Optional result data

        Returns:
            xAPI statement (dict)
        """
        # Determine verb based on message type
        if message.type == MessageType.REQUEST:
            verb = "asked" if message.extract_text().startswith("/") else "interacted"
        elif message.type == MessageType.RESPONSE:
            verb = "responded"
        elif message.type == MessageType.ERROR:
            verb = "completed"  # with error
        else:
            verb = "interacted"

        # Determine activity type
        text = message.extract_text()
        if text.startswith("/"):
            activity_type = "command"
            activity_name = text.split()[0]
        else:
            activity_type = "message"
            activity_name = "User Message"

        # Build statement
        statement = {
            "id": str(uuid4()),
            "actor": cls.format_actor(agent_id, client_id),
            "verb": cls.format_verb(verb),
            "object": cls.format_activity(
                activity_id=f"p3394://message/{message.id}",
                activity_type=activity_type,
                name=activity_name,
                description=text[:100] + "..." if len(text) > 100 else text
            ),
            "timestamp": message.timestamp,
            "context": {
                "contextActivities": {
                    "parent": [{
                        "objectType": "Activity",
                        "id": f"p3394://session/{session_id}",
                        "definition": {
                            "type": cls.ACTIVITY_TYPES["conversation"],
                            "name": {"en-US": f"Session {session_id[:8]}"}
                        }
                    }]
                },
                "extensions": {
                    "http://id.tincanapi.com/extension/p3394-message-id": message.id,
                    "http://id.tincanapi.com/extension/p3394-message-type": message.type.value
                }
            }
        }

        # Add result if provided
        if result:
            statement["result"] = result

        # Add reply_to if present
        if message.reply_to:
            statement["context"]["extensions"]["http://id.tincanapi.com/extension/reply-to"] = message.reply_to

        return statement


class LRSWriter:
    """
    Writes xAPI statements to a Learning Record Store.

    Can be backed by:
    - Local JSONL file (default)
    - MCP server (xAPI LRS agent)
    - Remote LRS endpoint
    """

    def __init__(
        self,
        storage_path: Optional[str] = None,
        mcp_client=None,
        remote_endpoint: Optional[str] = None
    ):
        """
        Initialize LRS writer.

        Args:
            storage_path: Path to local JSONL file
            mcp_client: MCP client for xAPI LRS agent
            remote_endpoint: URL of remote LRS
        """
        self.storage_path = storage_path
        self.mcp_client = mcp_client
        self.remote_endpoint = remote_endpoint

    async def write_statement(self, statement: Dict[str, Any]) -> str:
        """
        Write an xAPI statement to the LRS.

        Args:
            statement: xAPI statement dict

        Returns:
            Statement ID
        """
        statement_id = statement.get("id", str(uuid4()))

        # Write to local file
        if self.storage_path:
            await self._write_to_file(statement)

        # Write to MCP agent
        if self.mcp_client:
            await self._write_to_mcp(statement)

        # Write to remote LRS
        if self.remote_endpoint:
            await self._write_to_remote(statement)

        return statement_id

    async def _write_to_file(self, statement: Dict[str, Any]):
        """Write to local JSONL file"""
        import json
        from pathlib import Path

        path = Path(self.storage_path)
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open('a') as f:
            f.write(json.dumps(statement) + '\n')

    async def _write_to_mcp(self, statement: Dict[str, Any]):
        """Write to MCP xAPI LRS agent"""
        if not self.mcp_client:
            return

        try:
            await self.mcp_client.call_tool(
                "xapi_store_statement",
                {"statement": statement}
            )
        except Exception as e:
            # Log error but don't fail
            import logging
            logging.getLogger(__name__).warning(f"Failed to write to MCP LRS: {e}")

    async def _write_to_remote(self, statement: Dict[str, Any]):
        """Write to remote LRS endpoint"""
        if not self.remote_endpoint:
            return

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                await client.post(
                    f"{self.remote_endpoint}/statements",
                    json=statement,
                    headers={
                        "X-Experience-API-Version": "1.0.3",
                        "Content-Type": "application/json"
                    }
                )
        except Exception as e:
            import logging
            logging.getLogger(__name__).warning(f"Failed to write to remote LRS: {e}")

    async def read_statements(
        self,
        session_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        limit: int = 100
    ) -> list[Dict[str, Any]]:
        """
        Read xAPI statements from local storage.

        Args:
            session_id: Filter by session
            agent_id: Filter by agent
            limit: Maximum statements to return

        Returns:
            List of xAPI statements
        """
        if not self.storage_path:
            return []

        import json
        from pathlib import Path

        path = Path(self.storage_path)
        if not path.exists():
            return []

        statements = []
        with path.open('r') as f:
            for line in f:
                if not line.strip():
                    continue

                statement = json.loads(line)

                # Apply filters
                if session_id:
                    context = statement.get("context", {})
                    parent_id = context.get("contextActivities", {}).get("parent", [{}])[0].get("id", "")
                    if f"session/{session_id}" not in parent_id:
                        continue

                if agent_id:
                    actor = statement.get("actor", {})
                    actor_agent = actor.get("account", {}).get("homePage", "")
                    if agent_id not in actor_agent:
                        continue

                statements.append(statement)

                if len(statements) >= limit:
                    break

        return statements
