"""
Token Necessity Evaluator

Analyzes agent interactions to detect information that MUST be persisted
as Control Tokens for guaranteed recovery. This is the "gate detector" -
identifying moments where thought crosses into action authority.

Categories of Necessary Tokens:
1. Credentials: API keys, passwords, OAuth tokens
2. Bindings: Channel→Principal mappings, capability assignments
3. Paths: File paths, URLs, endpoints that unlock resources
4. Identities: Phone numbers, emails, agent URIs
5. Capabilities: Granted permissions, skill activations

The evaluator runs at key points in the agent loop to ensure
nothing important is lost.
"""

import re
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Set

from .control_tokens import (
    ControlToken, TokenType, TokenScope, TokenProvenance,
    ProvenanceMethod, ConsumptionMode
)

logger = logging.getLogger(__name__)


class NecessityCategory(str, Enum):
    """Categories of information that require token persistence"""
    CREDENTIAL = "credential"           # API keys, passwords, secrets
    BINDING = "binding"                 # Identity mappings
    PATH = "path"                       # File paths, URLs
    IDENTITY = "identity"               # Phone, email, agent URI
    CAPABILITY = "capability"           # Permissions, grants
    CONFIGURATION = "configuration"     # Settings that affect behavior
    SESSION = "session"                 # Session-specific tokens


@dataclass
class DetectedToken:
    """A token detected by the necessity evaluator"""
    key: str
    value: str
    token_type: TokenType
    category: NecessityCategory
    binding_target: str
    scopes: List[TokenScope]
    confidence: float  # 0.0 to 1.0
    source_context: str  # Where it was detected
    tags: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_control_token(self, provenance_source: str = "necessity_evaluator") -> ControlToken:
        """Convert to ControlToken for storage"""
        return ControlToken.create(
            key=self.key,
            value=self.value,
            token_type=self.token_type,
            binding_target=self.binding_target,
            scopes=self.scopes,
            provenance_source=provenance_source,
            provenance_method=ProvenanceMethod.DISCOVERED,
            metadata={
                "category": self.category.value,
                "confidence": self.confidence,
                "source_context": self.source_context,
                "tags": self.tags,
                **self.metadata
            }
        )


class NecessityEvaluator:
    """
    Evaluates agent interactions to detect tokens that must be persisted.

    This is a key component of the KSTAR+ memory system - it ensures that
    credentials, bindings, and other critical information are automatically
    captured and stored for guaranteed recovery.
    """

    # Patterns for detecting different token types
    PATTERNS = {
        # API Keys
        TokenType.API_KEY: [
            (r'sk-ant-api\d+-[A-Za-z0-9_-]+', "anthropic_api_key"),
            (r'sk-[A-Za-z0-9]{20,}', "openai_api_key"),
            (r'AIza[A-Za-z0-9_-]{35}', "google_api_key"),
            (r'xox[baprs]-[A-Za-z0-9-]+', "slack_token"),
            (r'ghp_[A-Za-z0-9]{36}', "github_pat"),
            (r'glpat-[A-Za-z0-9_-]{20}', "gitlab_pat"),
        ],
        # OAuth tokens
        TokenType.OAUTH_TOKEN: [
            (r'ya29\.[A-Za-z0-9_-]+', "google_oauth"),
            (r'EAA[A-Za-z0-9]+', "facebook_oauth"),
        ],
        # Phone numbers
        TokenType.PHONE_NUMBER: [
            (r'\+\d{1,3}[\s.-]?\d{3,14}', "phone_number"),
            (r'\+\d{10,15}', "phone_e164"),
        ],
        # Email addresses
        TokenType.EMAIL: [
            (r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', "email"),
        ],
        # File paths
        TokenType.FILE_PATH: [
            (r'(?:/[a-zA-Z0-9._-]+)+', "unix_path"),
            (r'[A-Za-z]:\\(?:[^\\/:*?"<>|\r\n]+\\)*[^\\/:*?"<>|\r\n]*', "windows_path"),
        ],
        # URLs/Endpoints
        TokenType.AGENT_URI: [
            (r'https?://[^\s<>"{}|\\^`\[\]]+', "http_url"),
            (r'wss?://[^\s<>"{}|\\^`\[\]]+', "websocket_url"),
            (r'p3394://[^\s<>"{}|\\^`\[\]]+', "p3394_uri"),
        ],
        # Note: SKILL_ID patterns removed from here - handled by dedicated SKILL_PATTERNS below
    }

    # Skill-specific patterns for dynamic import tracking
    # These are processed separately to ensure proper folder name extraction
    SKILL_PATTERNS = [
        # Path-based patterns (extract folder name from path)
        (r'\.claude/skills/([a-zA-Z0-9_-]+)(?:/|$)', "skill_folder_path"),
        (r'/skills/([a-zA-Z0-9_-]+)/', "skill_directory"),
        (r'skills/([a-zA-Z0-9_-]+)/SKILL\.md', "skill_definition"),
        # Action-based patterns (extract skill name from commands)
        (r'invoke\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_invoke"),
        (r'load\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_load"),
        (r'import\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_import"),
        (r'assign\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_assign"),
        (r'create\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_create"),
        (r'use\s+skill[:\s]+([a-zA-Z0-9_-]+)', "skill_use"),
        # Generic skill reference (must come last - less specific)
        (r'skill[:\s]+([a-zA-Z0-9_][a-zA-Z0-9_-]*)', "skill_reference"),
    ]

    # Keywords that indicate token necessity
    NECESSITY_KEYWORDS = {
        NecessityCategory.CREDENTIAL: [
            "api key", "api_key", "apikey", "secret", "password", "token",
            "credential", "auth", "bearer", "access token", "refresh token",
            "private key", "secret key"
        ],
        NecessityCategory.BINDING: [
            "bind", "binding", "map", "mapping", "associate", "link",
            "principal", "identity", "assign"
        ],
        NecessityCategory.PATH: [
            "path", "file", "directory", "folder", "location", "endpoint",
            "url", "uri", "route"
        ],
        NecessityCategory.IDENTITY: [
            "phone", "email", "user", "account", "whatsapp", "contact",
            "address", "number"
        ],
        NecessityCategory.CAPABILITY: [
            "permission", "scope", "grant", "allow", "capability", "access",
            "role", "privilege"
        ],
        NecessityCategory.CONFIGURATION: [
            "config", "setting", "option", "preference", "parameter",
            "environment", "env"
        ],
    }

    # Context patterns that boost confidence
    CONTEXT_BOOSTERS = [
        (r"store|save|remember|persist|keep", 0.3),
        (r"my|our|the", 0.1),
        (r"is|=|:", 0.1),
        (r"important|critical|needed|required", 0.2),
    ]

    def __init__(self, min_confidence: float = 0.5):
        """
        Initialize evaluator.

        Args:
            min_confidence: Minimum confidence to report a detection (0.0-1.0)
        """
        self.min_confidence = min_confidence
        self._detected_cache: Set[str] = set()  # Avoid duplicate detections

    def evaluate_text(self, text: str, context: str = "unknown") -> List[DetectedToken]:
        """
        Evaluate text for tokens that should be persisted.

        Args:
            text: The text to analyze
            context: Description of where this text came from

        Returns:
            List of detected tokens above confidence threshold
        """
        detected = []
        text_lower = text.lower()

        # Check for pattern matches
        for token_type, patterns in self.PATTERNS.items():
            for pattern, pattern_name in patterns:
                for match in re.finditer(pattern, text):
                    value = match.group(0)
                    # For skill patterns, extract the group if available
                    if token_type == TokenType.SKILL_ID and match.lastindex:
                        value = match.group(1)

                    # Skip if already detected
                    cache_key = f"{token_type.value}:{value}"
                    if cache_key in self._detected_cache:
                        continue

                    # Calculate confidence
                    confidence = self._calculate_confidence(
                        text_lower, value, token_type, pattern_name
                    )

                    if confidence >= self.min_confidence:
                        category = self._categorize_token(token_type)
                        detected.append(DetectedToken(
                            key=self._generate_key(token_type, value, pattern_name),
                            value=value,
                            token_type=token_type,
                            category=category,
                            binding_target=self._infer_binding_target(text, value, token_type),
                            scopes=self._infer_scopes(text_lower, category),
                            confidence=confidence,
                            source_context=context,
                            tags=self._extract_tags(text_lower, category),
                            metadata={"pattern": pattern_name}
                        ))
                        self._detected_cache.add(cache_key)

        # Also check skill-specific patterns for dynamic import tracking
        detected.extend(self._detect_skill_references(text, context))

        return detected

    def _detect_skill_references(self, text: str, context: str) -> List[DetectedToken]:
        """
        Detect skill folder names and references for dynamic import recovery.

        Skill folder names are critical tokens because:
        - They are used for dynamic import/loading
        - They enable capability recovery after restart
        - They track which skills have been assigned/invoked
        """
        detected = []

        for pattern, pattern_name in self.SKILL_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                skill_name = match.group(1) if match.lastindex else match.group(0)

                # Skip if already detected
                cache_key = f"skill_id:{skill_name}"
                if cache_key in self._detected_cache:
                    continue

                # Skill folder names have high confidence - they're explicit references
                confidence = 0.85

                detected.append(DetectedToken(
                    key=f"skill:folder:{skill_name}",
                    value=skill_name,
                    token_type=TokenType.SKILL_ID,
                    category=NecessityCategory.CAPABILITY,
                    binding_target=f"skill:{skill_name}",
                    scopes=[TokenScope.EXECUTE, TokenScope.READ],
                    confidence=confidence,
                    source_context=context,
                    tags=["skill", "dynamic_import", pattern_name, skill_name],
                    metadata={
                        "pattern": pattern_name,
                        "is_dynamic_import": True,
                        "skill_folder": skill_name
                    }
                ))
                self._detected_cache.add(cache_key)

        return detected

    def evaluate_tool_input(
        self,
        tool_name: str,
        tool_input: Dict[str, Any],
        context: str = "tool_input"
    ) -> List[DetectedToken]:
        """
        Evaluate tool input for tokens that should be persisted.

        Args:
            tool_name: Name of the tool being called
            tool_input: The tool's input parameters
            context: Additional context

        Returns:
            List of detected tokens
        """
        detected = []

        # Flatten tool input to searchable text
        text_parts = []
        for key, value in tool_input.items():
            if isinstance(value, str):
                text_parts.append(f"{key}: {value}")
            elif isinstance(value, dict):
                for k, v in value.items():
                    if isinstance(v, str):
                        text_parts.append(f"{k}: {v}")

        text = "\n".join(text_parts)
        full_context = f"{context}:{tool_name}"

        # Run text evaluation
        detected.extend(self.evaluate_text(text, full_context))

        # Special handling for specific tools
        if tool_name == "Bash":
            command = tool_input.get("command", "")
            # Look for export statements with credentials
            export_matches = re.findall(
                r'export\s+([A-Z_]+)=["\']?([^"\';\n]+)["\']?',
                command
            )
            for var_name, var_value in export_matches:
                if any(kw in var_name.lower() for kw in ["key", "token", "secret", "password"]):
                    detected.append(DetectedToken(
                        key=f"env:{var_name.lower()}",
                        value=var_value,
                        token_type=TokenType.API_KEY,
                        category=NecessityCategory.CREDENTIAL,
                        binding_target=f"env:{var_name}",
                        scopes=[TokenScope.EXECUTE],
                        confidence=0.9,
                        source_context=f"bash:export:{var_name}",
                        tags=["environment", "credential", var_name.lower()]
                    ))

        return detected

    def evaluate_tool_result(
        self,
        tool_name: str,
        tool_result: Any,
        context: str = "tool_result"
    ) -> List[DetectedToken]:
        """
        Evaluate tool result for tokens to persist.

        Args:
            tool_name: Name of the tool
            tool_result: The tool's output
            context: Additional context

        Returns:
            List of detected tokens
        """
        if isinstance(tool_result, str):
            return self.evaluate_text(tool_result, f"{context}:{tool_name}")
        elif isinstance(tool_result, dict):
            text = str(tool_result)
            return self.evaluate_text(text, f"{context}:{tool_name}")
        return []

    def evaluate_message(
        self,
        message_content: str,
        message_type: str = "user",
        session_id: str = None
    ) -> List[DetectedToken]:
        """
        Evaluate a message for tokens to persist.

        Args:
            message_content: The message text
            message_type: Type of message (user, assistant, system)
            session_id: Optional session ID for context

        Returns:
            List of detected tokens
        """
        context = f"message:{message_type}"
        if session_id:
            context += f":{session_id[:8]}"

        return self.evaluate_text(message_content, context)

    def _calculate_confidence(
        self,
        text_lower: str,
        value: str,
        token_type: TokenType,
        pattern_name: str
    ) -> float:
        """Calculate confidence score for a detection"""
        base_confidence = 0.4

        # Boost for context keywords
        for category, keywords in self.NECESSITY_KEYWORDS.items():
            for keyword in keywords:
                if keyword in text_lower:
                    base_confidence += 0.1
                    break

        # Boost for explicit save/store intent
        for pattern, boost in self.CONTEXT_BOOSTERS:
            if re.search(pattern, text_lower):
                base_confidence += boost

        # Boost for high-value patterns
        if "api" in pattern_name.lower():
            base_confidence += 0.2
        if "secret" in pattern_name.lower() or "private" in pattern_name.lower():
            base_confidence += 0.3

        # Cap at 1.0
        return min(1.0, base_confidence)

    def _categorize_token(self, token_type: TokenType) -> NecessityCategory:
        """Map token type to necessity category"""
        type_to_category = {
            TokenType.API_KEY: NecessityCategory.CREDENTIAL,
            TokenType.OAUTH_TOKEN: NecessityCategory.CREDENTIAL,
            TokenType.PASSWORD_HASH: NecessityCategory.CREDENTIAL,
            TokenType.SESSION_TOKEN: NecessityCategory.SESSION,
            TokenType.FILE_PATH: NecessityCategory.PATH,
            TokenType.INODE: NecessityCategory.PATH,
            TokenType.PHONE_NUMBER: NecessityCategory.IDENTITY,
            TokenType.EMAIL: NecessityCategory.IDENTITY,
            TokenType.AGENT_URI: NecessityCategory.IDENTITY,
            TokenType.CAPABILITY_HANDLE: NecessityCategory.CAPABILITY,
            TokenType.SKILL_ID: NecessityCategory.CAPABILITY,
            TokenType.MCP_TOOL_REF: NecessityCategory.CAPABILITY,
            TokenType.CHANNEL_BINDING: NecessityCategory.BINDING,
        }
        return type_to_category.get(token_type, NecessityCategory.CONFIGURATION)

    def _generate_key(self, token_type: TokenType, value: str, pattern_name: str) -> str:
        """Generate a lookup key for the token"""
        # Create a meaningful key based on type and pattern
        if token_type == TokenType.API_KEY:
            # For API keys, use a prefix based on pattern
            prefix = pattern_name.replace("_api_key", "").replace("_pat", "")
            return f"{prefix}:api_key"
        elif token_type == TokenType.PHONE_NUMBER:
            # For phones, normalize the number
            normalized = re.sub(r'[\s.-]', '', value)
            return f"phone:{normalized}"
        elif token_type == TokenType.EMAIL:
            return f"email:{value.lower()}"
        elif token_type == TokenType.FILE_PATH:
            # Use last path component
            parts = value.replace("\\", "/").split("/")
            return f"path:{parts[-1]}"
        elif token_type == TokenType.AGENT_URI:
            return f"uri:{value[:50]}"
        else:
            # Hash the value for key
            import hashlib
            hash_suffix = hashlib.sha256(value.encode()).hexdigest()[:8]
            return f"{token_type.value}:{hash_suffix}"

    def _infer_binding_target(self, text: str, value: str, token_type: TokenType) -> str:
        """Infer what this token unlocks"""
        text_lower = text.lower()

        # Look for explicit binding mentions
        binding_patterns = [
            (r'for\s+(\w+)', 1),
            (r'to\s+(\w+)', 1),
            (r'(\w+)\s+api', 1),
            (r'(\w+)\s+service', 1),
        ]

        for pattern, group in binding_patterns:
            match = re.search(pattern, text_lower)
            if match:
                return match.group(group)

        # Default based on type
        if token_type == TokenType.API_KEY:
            if "anthropic" in text_lower or "claude" in text_lower:
                return "anthropic:claude"
            elif "openai" in text_lower or "gpt" in text_lower:
                return "openai:gpt"
        elif token_type == TokenType.PHONE_NUMBER:
            if "whatsapp" in text_lower:
                return "whatsapp:channel"

        return "unknown"

    def _infer_scopes(self, text_lower: str, category: NecessityCategory) -> List[TokenScope]:
        """Infer what permissions this token grants"""
        scopes = []

        if "read" in text_lower:
            scopes.append(TokenScope.READ)
        if "write" in text_lower:
            scopes.append(TokenScope.WRITE)
        if "execute" in text_lower or "run" in text_lower:
            scopes.append(TokenScope.EXECUTE)
        if "admin" in text_lower:
            scopes.append(TokenScope.ADMIN)
        if "delete" in text_lower:
            scopes.append(TokenScope.DELETE)
        if "all" in text_lower or "*" in text_lower:
            scopes.append(TokenScope.ALL)

        # Default based on category
        if not scopes:
            if category == NecessityCategory.CREDENTIAL:
                scopes = [TokenScope.EXECUTE]
            elif category == NecessityCategory.BINDING:
                scopes = [TokenScope.READ]
            else:
                scopes = [TokenScope.READ]

        return scopes

    def _extract_tags(self, text_lower: str, category: NecessityCategory) -> List[str]:
        """Extract relevant tags from context"""
        tags = [category.value]

        # Add service-specific tags
        services = ["anthropic", "openai", "google", "github", "gitlab",
                   "slack", "whatsapp", "supabase", "aws", "azure"]
        for service in services:
            if service in text_lower:
                tags.append(service)

        # Add action tags
        actions = ["store", "save", "create", "update", "delete", "bind"]
        for action in actions:
            if action in text_lower:
                tags.append(f"action:{action}")
                break

        return tags

    def clear_cache(self):
        """Clear the detection cache"""
        self._detected_cache.clear()
