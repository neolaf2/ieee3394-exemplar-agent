"""
IEEE 3394 Exemplar Agent - Entry Point

Main entry point for running the agent in daemon mode or as a client.
"""

import asyncio
import argparse
import logging
import os
import sys

from .server import run_daemon
from .client import run_client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_api_key(required: bool = True) -> str:
    """Get Anthropic API key from environment"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key and required:
        logger.error("ANTHROPIC_API_KEY environment variable not set")
        print("\n❌ Error: ANTHROPIC_API_KEY environment variable not set")
        print("\nPlease set your API key:")
        print("  export ANTHROPIC_API_KEY='your-api-key-here'")
        print("\nOr add to .env file:")
        print("  ANTHROPIC_API_KEY=your-api-key-here")
        sys.exit(1)
    return api_key


async def main():
    parser = argparse.ArgumentParser(
        description="IEEE 3394 Exemplar Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Start agent host (daemon mode)
  python -m ieee3394_agent --daemon

  # Start with Anthropic API server adapter
  python -m ieee3394_agent --daemon --anthropic-api --api-port 8100

  # Connect as client (default)
  python -m ieee3394_agent

  # Custom socket path
  python -m ieee3394_agent --daemon --socket /tmp/my-agent.sock
  python -m ieee3394_agent --socket /tmp/my-agent.sock

  # Enable debug logging
  python -m ieee3394_agent --daemon --debug
"""
    )

    parser.add_argument(
        '--daemon', '-d',
        action='store_true',
        help='Run as daemon (agent host)'
    )

    parser.add_argument(
        '--socket', '-s',
        default='/tmp/ieee3394-agent.sock',
        help='Unix socket path (default: /tmp/ieee3394-agent.sock)'
    )

    parser.add_argument(
        '--anthropic-api',
        action='store_true',
        help='Enable Anthropic API server adapter (makes agent accessible via Anthropic API)'
    )

    parser.add_argument(
        '--api-port',
        type=int,
        default=8100,
        help='Port for Anthropic API server (default: 8100)'
    )

    parser.add_argument(
        '--api-keys',
        type=str,
        help='Comma-separated list of agent-issued API keys (leave empty for testing)'
    )

    parser.add_argument(
        '--p3394-server',
        action='store_true',
        default=True,
        help='Enable P3394 server for agent-to-agent communication (default: enabled)'
    )

    parser.add_argument(
        '--no-p3394-server',
        action='store_false',
        dest='p3394_server',
        help='Disable P3394 server'
    )

    parser.add_argument(
        '--p3394-port',
        type=int,
        default=8101,
        help='Port for P3394 agent server (default: 8101)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    if args.daemon:
        # Run as daemon (agent host)
        api_key = get_api_key(required=True)

        # Parse API keys if provided
        api_keys = None
        if args.api_keys:
            api_keys = set(k.strip() for k in args.api_keys.split(',') if k.strip())

        await run_daemon(
            api_key=api_key,
            debug=args.debug,
            enable_anthropic_api=args.anthropic_api,
            anthropic_api_port=args.api_port,
            anthropic_api_keys=api_keys,
            enable_p3394_server=args.p3394_server,
            p3394_server_port=args.p3394_port
        )
    else:
        # Run as client
        await run_client(socket_path=args.socket)


def run():
    """Entry point for console script"""
    asyncio.run(main())


if __name__ == '__main__':
    run()
