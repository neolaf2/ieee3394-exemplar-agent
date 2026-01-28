"""
IEEE 3394 Exemplar Agent - Entry Point

Main entry point for running the agent with CLI or web channels.
"""

import asyncio
import argparse
import logging
import os
import sys

from .core.gateway import AgentGateway
from .memory.kstar import KStarMemory
from .channels.cli import CLIChannelAdapter
from .plugins.hooks import set_kstar_memory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def get_api_key() -> str:
    """Get Anthropic API key from environment"""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
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
  # Start CLI (default)
  python -m ieee3394_agent

  # Start CLI explicitly
  python -m ieee3394_agent --channel cli

  # Enable debug logging
  python -m ieee3394_agent --debug
"""
    )

    parser.add_argument(
        '--channel', '-c',
        choices=['cli'],
        default='cli',
        help='Channel to start (default: cli)'
    )

    parser.add_argument(
        '--debug',
        action='store_true',
        help='Enable debug logging'
    )

    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    # Get API key
    api_key = get_api_key()

    # Initialize KSTAR memory
    logger.info("Initializing KSTAR memory...")
    kstar = KStarMemory()
    set_kstar_memory(kstar)

    # Initialize gateway
    logger.info("Initializing Agent Gateway...")
    gateway = AgentGateway(kstar_memory=kstar, anthropic_api_key=api_key)

    # Start CLI channel
    if args.channel == 'cli':
        logger.info("Starting CLI channel...")
        cli_channel = CLIChannelAdapter(gateway=gateway)
        await cli_channel.start()


def run():
    """Entry point for console script"""
    asyncio.run(main())


if __name__ == '__main__':
    run()
