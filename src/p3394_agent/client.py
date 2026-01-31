"""
Agent Client (CLI)

Connects to a running Agent Host (daemon) and provides interactive CLI.
"""

import asyncio
import json
import logging
from typing import Optional

from .core.umf import P3394Message, MessageType, ContentType

logger = logging.getLogger(__name__)


class AgentClient:
    """Client that connects to Agent Host via Unix socket"""

    def __init__(self, socket_path: str = "/tmp/ieee3394-agent.sock"):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.session_id: Optional[str] = None

    async def connect(self):
        """Connect to the agent host"""
        try:
            self.reader, self.writer = await asyncio.open_unix_connection(
                self.socket_path
            )
            logger.info(f"Connected to agent host at {self.socket_path}")
            return True
        except FileNotFoundError:
            print(f"\n❌ Error: Agent host not running")
            print(f"   Socket not found: {self.socket_path}")
            print(f"\n💡 Start the agent host first:")
            print(f"   uv run python -m p3394_agent --daemon")
            return False
        except Exception as e:
            print(f"\n❌ Error connecting to agent host: {e}")
            return False

    async def disconnect(self):
        """Disconnect from the agent host"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()

    async def send_message(self, text: str) -> Optional[P3394Message]:
        """Send a message to the agent and get response"""
        if not self.reader or not self.writer:
            raise ConnectionError("Not connected to agent host")

        # Create message
        message = P3394Message.text(text, session_id=self.session_id)

        # Serialize message
        message_data = json.dumps(message.to_dict()).encode('utf-8')
        message_length = len(message_data).to_bytes(4, 'big')

        # Send message
        self.writer.write(message_length + message_data)
        await self.writer.drain()

        # Read response length
        length_bytes = await self.reader.readexactly(4)
        response_length = int.from_bytes(length_bytes, 'big')

        # Read response data
        data = await self.reader.readexactly(response_length)
        response_dict = json.loads(data.decode('utf-8'))

        # Convert to P3394Message
        response = P3394Message.from_dict(response_dict)

        # Store session ID from response
        if response.session_id:
            self.session_id = response.session_id

        return response

    async def start_interactive(self):
        """Start interactive CLI session"""
        # Connect to host
        if not await self.connect():
            return

        # Print banner
        self._print_banner()

        # REPL loop
        try:
            while True:
                try:
                    user_input = await self._async_input(">>> ")

                    if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                        print("\nGoodbye!")
                        break

                    if not user_input.strip():
                        continue

                    # Send message and get response
                    response = await self.send_message(user_input)

                    # Display response
                    self._display_response(response)

                except KeyboardInterrupt:
                    print("\n\nUse 'exit' or '/exit' to quit")
                    continue
                except EOFError:
                    break
                except Exception as e:
                    print(f"\n❌ Error: {e}")
                    logger.exception(f"Client error: {e}")

        finally:
            await self.disconnect()

    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent                        ║
║                   Client Session                             ║
╠══════════════════════════════════════════════════════════════╣
║  Connected to: {self.socket_path:<40} ║
║  Session: {(self.session_id[:20] if self.session_id else 'Initializing...'):<44} ║
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
                print(json.dumps(content.data, indent=2))
            elif content.type == ContentType.MARKDOWN:
                print(content.data)

        print()  # Blank line after response

    async def _async_input(self, prompt: str) -> str:
        """Async-compatible input"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt))


async def run_client(socket_path: str = "/tmp/ieee3394-agent.sock"):
    """Run the agent client"""
    client = AgentClient(socket_path=socket_path)
    await client.start_interactive()
