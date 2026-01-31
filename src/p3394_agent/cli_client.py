"""
CLI Client

A terminal REPL client that connects to the CLI Channel Adapter.
This is the user-facing interface - it presents a simple command-line
interface and communicates with the channel adapter using a simple JSON protocol.
"""

import asyncio
import json
import logging
import sys
from typing import Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class CLIClient:
    """
    CLI Client for interacting with the IEEE 3394 Agent via CLI channel.

    Protocol:
    - Sends: {"text": "user input"}
    - Receives: {"type": "response", "text": "agent output", ...}
    """

    def __init__(self, socket_path: str = "/tmp/ieee3394-agent-cli.sock"):
        self.socket_path = socket_path
        self.reader: Optional[asyncio.StreamReader] = None
        self.writer: Optional[asyncio.StreamWriter] = None
        self.session_id: Optional[str] = None
        self.agent_name: Optional[str] = None
        self.agent_version: Optional[str] = None

    async def connect(self):
        """Connect to the CLI channel adapter"""
        try:
            self.reader, self.writer = await asyncio.open_unix_connection(
                self.socket_path
            )
            logger.info(f"Connected to CLI channel at {self.socket_path}")

            # Receive welcome message
            welcome = await self._receive_message()
            if welcome.get("type") == "welcome":
                self.session_id = welcome.get("session_id")
                self.agent_name = welcome.get("agent")
                self.agent_version = welcome.get("version")
                logger.debug(f"Session started: {self.session_id}")

        except FileNotFoundError:
            print(f"\n❌ Error: Could not connect to CLI channel at {self.socket_path}")
            print("\nMake sure the agent daemon is running:")
            print("  ./scripts/start-daemon.sh")
            print("\nOr check if the socket path is correct.")
            sys.exit(1)
        except Exception as e:
            print(f"\n❌ Error connecting: {e}")
            sys.exit(1)

    async def disconnect(self):
        """Disconnect from the CLI channel adapter"""
        if self.writer:
            self.writer.close()
            await self.writer.wait_closed()
            logger.info("Disconnected from CLI channel")

    async def send_message(self, text: str) -> Optional[dict]:
        """Send a message to the agent"""
        if not self.writer:
            raise RuntimeError("Not connected")

        # Create CLI message
        message = {"text": text}

        # Send message
        message_data = json.dumps(message).encode('utf-8')
        message_length = len(message_data).to_bytes(4, 'big')

        self.writer.write(message_length + message_data)
        await self.writer.drain()

        # Receive response
        response = await self._receive_message()
        return response

    async def _receive_message(self) -> dict:
        """Receive a message from the channel adapter"""
        if not self.reader:
            raise RuntimeError("Not connected")

        # Read message length
        length_bytes = await self.reader.readexactly(4)
        message_length = int.from_bytes(length_bytes, 'big')

        # Read message data
        data = await self.reader.readexactly(message_length)
        message = json.loads(data.decode('utf-8'))

        return message

    def _print_banner(self):
        """Print welcome banner"""
        banner = f"""
╔══════════════════════════════════════════════════════════════╗
║              IEEE 3394 Exemplar Agent                        ║
║                   CLI Client                                 ║
╠══════════════════════════════════════════════════════════════╣
║  Agent:   {self.agent_name or 'Unknown':<48}║
║  Version: {self.agent_version or 'Unknown':<48}║
║  Session: {(self.session_id[:20] if self.session_id else 'N/A'):<48}║
╠══════════════════════════════════════════════════════════════╣
║  Type /help for commands                                     ║
║  Type 'exit' to quit                                         ║
╚══════════════════════════════════════════════════════════════╝
"""
        print(banner)

    def _display_response(self, response: dict):
        """Display a response message"""
        print()  # Blank line before response

        response_type = response.get("type", "response")

        if response_type == "error":
            text = response.get("text", "Unknown error")
            print(f"❌ Error: {text}")
        else:
            text = response.get("text", "")
            if text:
                print(text)

            # Show data if present
            data = response.get("data")
            if data:
                print("\nData:")
                print(json.dumps(data, indent=2))

        print()  # Blank line after response

    async def run_repl(self):
        """Run the REPL loop"""
        await self.connect()
        self._print_banner()

        while True:
            try:
                # Get user input
                user_input = await self._async_input(">>> ")

                # Check for exit commands
                if user_input.lower() in ['exit', 'quit', '/exit', '/quit']:
                    print("\nGoodbye!")
                    break

                # Skip empty input
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
                logger.exception(f"REPL error: {e}")

        await self.disconnect()

    async def _async_input(self, prompt: str) -> str:
        """Async-compatible input"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, lambda: input(prompt))


async def _async_main():
    """Async main entry point for CLI client"""
    import argparse

    parser = argparse.ArgumentParser(
        description="IEEE 3394 Agent CLI Client",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Connect to default CLI channel
  ieee3394-cli

  # Connect to custom socket
  ieee3394-cli --socket /tmp/custom.sock

  # Enable debug logging
  ieee3394-cli --debug
"""
    )

    parser.add_argument(
        '--socket', '-s',
        default='/tmp/ieee3394-agent-cli.sock',
        help='CLI channel socket path (default: /tmp/ieee3394-agent-cli.sock)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Create and run client
    client = CLIClient(socket_path=args.socket)
    await client.run_repl()


def main():
    """Synchronous entry point for console script"""
    asyncio.run(_async_main())


if __name__ == '__main__':
    main()
