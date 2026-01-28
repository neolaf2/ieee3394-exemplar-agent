"""
CLI Channel Adapter

Provides a terminal REPL interface for interacting with the agent.
Useful for development and testing.
"""

import asyncio
from typing import Optional
import logging

from ..core.umf import P3394Message, ContentType, MessageType
from ..core.gateway import AgentGateway

logger = logging.getLogger(__name__)


class CLIChannelAdapter:
    """
    CLI channel adapter for terminal interaction.
    """

    def __init__(self, gateway: AgentGateway):
        self.gateway = gateway
        self.channel_id = "cli"
        self.is_active = False
        self.session_id: Optional[str] = None

    async def start(self):
        """Start the CLI REPL"""
        self.is_active = True
        self.gateway.register_channel(self.channel_id, self)

        # Create session
        session = await self.gateway.session_manager.create_session(channel_id="cli")
        self.session_id = session.id

        # Print banner
        self._print_banner()

        # REPL loop
        while self.is_active:
            try:
                user_input = await self._async_input(">>> ")

                if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                    print("\nGoodbye!")
                    break

                if not user_input.strip():
                    continue

                # Create message
                message = P3394Message.text(user_input, session_id=self.session_id)

                # Handle message
                response = await self.gateway.handle(message)

                # Display response
                self._display_response(response)

            except KeyboardInterrupt:
                print("\n\nUse 'exit' or '/exit' to quit")
                continue
            except EOFError:
                break
            except Exception as e:
                print(f"\n❌ Error: {e}")
                logger.exception(f"CLI error: {e}")

        await self.gateway.session_manager.end_session(self.session_id)
        self.is_active = False

    async def stop(self):
        """Stop the CLI"""
        self.is_active = False

    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent                        ║
║                   CLI Channel                                ║
╠══════════════════════════════════════════════════════════════╣
║  Version: {self.gateway.AGENT_VERSION:<15}                               ║
║  Session: {self.session_id[:20] if self.session_id else 'N/A':<20}                       ║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                     ║
║  Type 'exit' to quit                                         ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def _display_response(self, message: P3394Message):
        """Display a response message"""
        print()  # Blank line before response

        # Handle error messages
        if message.type == MessageType.ERROR:
            for content in message.content:
                if content.type == ContentType.JSON:
                    error_data = content.data
                    print(f"❌ Error: {error_data.get('message', 'Unknown error')}")
                else:
                    print(f"❌ {content.data}")
            print()
            return

        # Handle normal responses
        for content in message.content:
            if content.type == ContentType.TEXT:
                print(content.data)
            elif content.type == ContentType.JSON:
                import json
                print(json.dumps(content.data, indent=2))
            elif content.type == ContentType.MARKDOWN:
                print(content.data)

        print()  # Blank line after response

    async def _async_input(self, prompt: str) -> str:
        """Async-compatible input"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt))
