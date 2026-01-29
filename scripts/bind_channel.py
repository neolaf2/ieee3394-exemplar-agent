#!/usr/bin/env python3
"""
Bind Channel Adapter CLI

Interactive CLI tool for binding channel adapters to the agent.
Handles service principal authentication and channel-specific auth (QR codes, OAuth, etc.).

Usage:
    python scripts/bind_channel.py whatsapp
    python scripts/bind_channel.py telegram
    python scripts/bind_channel.py slack --web-ui
"""

import argparse
import asyncio
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ieee3394_agent.channels.binding import (
    ChannelBindingManager,
    TerminalBindingUI,
    WebBindingUI,
)


async def bind_whatsapp(args):
    """Bind WhatsApp channel."""
    from src.ieee3394_agent.channels.whatsapp.binding import WhatsAppChannelBinding
    from src.ieee3394_agent.channels.whatsapp.config import (
        WhatsAppChannelConfig,
        ServicePrincipalManager,
    )

    print("=" * 70)
    print("WhatsApp Channel Binding")
    print("=" * 70)
    print()

    # Load or create service principal
    sp_manager = ServicePrincipalManager(
        Path.home() / ".ieee3394" / "service_principals"
    )

    # Check if config exists
    config_path = Path(args.config) if args.config else (
        Path.home() / ".ieee3394" / "whatsapp_config.json"
    )

    if config_path.exists():
        print(f"Loading configuration from: {config_path}")
        config = WhatsAppChannelConfig.from_file(config_path)
        print(f"Using service principal: {config.service_principal.client_id}")
    else:
        print("No configuration found. Creating new service principal...")
        print()

        # Create service principal
        sp = sp_manager.create_service_principal(
            channel_type="whatsapp",
            permissions=[
                "channel.whatsapp.read",
                "channel.whatsapp.write",
                "gateway.message.send",
                "gateway.message.receive",
            ],
            expires_in_days=args.expires_days,
        )

        print(f"✓ Service Principal Created: {sp.client_id}")
        print()

        # Create default config
        from src.ieee3394_agent.channels.whatsapp.config import create_default_whatsapp_config

        config = create_default_whatsapp_config(
            service_principal=sp,
            bridge_url=args.bridge_url,
        )

        # Save config
        config.to_file(config_path)
        print(f"✓ Configuration saved to: {config_path}")
        print()

    # Validate config
    is_valid, errors = config.validate()
    if not is_valid:
        print("❌ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print("✓ Configuration validated")
    print()

    # Check if bridge is running
    print(f"Checking WhatsApp bridge at {config.bridge_url}...")
    import aiohttp

    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{config.bridge_url}/status", timeout=3) as resp:
                if resp.status == 200:
                    print("✓ Bridge is running")
                else:
                    print(f"❌ Bridge returned status {resp.status}")
                    sys.exit(1)
    except Exception as e:
        print(f"❌ Cannot connect to bridge: {e}")
        print()
        print("Please start the WhatsApp bridge first:")
        print("  cd whatsapp_bridge")
        print("  npm install  # (first time only)")
        print("  npm start")
        print()
        sys.exit(1)

    print()

    # Create binding implementation
    binding = WhatsAppChannelBinding(
        config=config,
        bridge_url=config.bridge_url,
        bridge_ws_url=config.bridge_ws_url
    )

    # Create UI
    if args.web_ui:
        ui = WebBindingUI(port=args.web_port)
        await ui.start()
        manager = ChannelBindingManager(ui_callback=ui.update)
    else:
        ui = TerminalBindingUI()
        manager = ChannelBindingManager(ui_callback=ui.update)

    # Execute binding
    try:
        context = await manager.bind_channel(binding, timeout_seconds=args.timeout)

        print()
        print("=" * 70)
        print("✅ BINDING COMPLETE")
        print("=" * 70)
        print()
        print(f"Channel: {context.channel_type}")
        print(f"Status: {context.status.value}")
        print(f"Started: {context.started_at}")
        print(f"Completed: {context.completed_at}")
        print()
        print("The WhatsApp channel is now ready to use!")
        print()
        print("Start the agent with:")
        print("  python -m ieee3394_agent --channel whatsapp")
        print()

    except TimeoutError:
        print()
        print("❌ Authentication timeout")
        print("Please try again and scan the QR code within the time limit.")
        sys.exit(1)

    except Exception as e:
        print()
        print(f"❌ Binding failed: {e}")
        sys.exit(1)

    finally:
        if args.web_ui:
            await ui.stop()


async def bind_telegram(args):
    """Bind Telegram channel (placeholder for future implementation)."""
    print("Telegram binding not yet implemented")
    print("Coming soon!")
    sys.exit(1)


async def bind_slack(args):
    """Bind Slack channel (placeholder for future implementation)."""
    print("Slack binding not yet implemented")
    print("Coming soon!")
    sys.exit(1)


async def main():
    parser = argparse.ArgumentParser(
        description="Bind channel adapters to IEEE 3394 Agent",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Bind WhatsApp channel (terminal UI)
  python scripts/bind_channel.py whatsapp

  # Bind WhatsApp with web UI
  python scripts/bind_channel.py whatsapp --web-ui

  # Bind with custom configuration
  python scripts/bind_channel.py whatsapp --config /path/to/config.json

  # Bind with custom timeout
  python scripts/bind_channel.py whatsapp --timeout 600

Supported Channels:
  - whatsapp: WhatsApp via QR code authentication
  - telegram: Telegram Bot API (coming soon)
  - slack: Slack OAuth flow (coming soon)
"""
    )

    parser.add_argument(
        "channel",
        choices=["whatsapp", "telegram", "slack"],
        help="Channel type to bind"
    )

    parser.add_argument(
        "--config",
        type=str,
        help="Path to channel configuration file"
    )

    parser.add_argument(
        "--bridge-url",
        type=str,
        default="http://localhost:3000",
        help="WhatsApp bridge URL (default: http://localhost:3000)"
    )

    parser.add_argument(
        "--timeout",
        type=int,
        default=300,
        help="Authentication timeout in seconds (default: 300)"
    )

    parser.add_argument(
        "--expires-days",
        type=int,
        default=None,
        help="Service principal expiration in days (default: no expiration)"
    )

    parser.add_argument(
        "--web-ui",
        action="store_true",
        help="Use web UI instead of terminal UI"
    )

    parser.add_argument(
        "--web-port",
        type=int,
        default=8200,
        help="Web UI port (default: 8200)"
    )

    args = parser.parse_args()

    # Route to channel-specific binding
    if args.channel == "whatsapp":
        await bind_whatsapp(args)
    elif args.channel == "telegram":
        await bind_telegram(args)
    elif args.channel == "slack":
        await bind_slack(args)
    else:
        print(f"Unknown channel: {args.channel}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\nBinding cancelled by user")
        sys.exit(1)
