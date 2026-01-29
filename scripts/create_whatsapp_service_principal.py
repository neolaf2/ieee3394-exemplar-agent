#!/usr/bin/env python3
"""
Create Service Principal for WhatsApp Channel Adapter

This script creates a service principal with proper identity binding
and permissions for the WhatsApp channel adapter.

Usage:
    python scripts/create_whatsapp_service_principal.py
    python scripts/create_whatsapp_service_principal.py --expires-days 365
    python scripts/create_whatsapp_service_principal.py --output config.json
"""

import argparse
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ieee3394_agent.channels.whatsapp.config import (
    ServicePrincipalManager,
    WhatsAppChannelConfig,
    create_default_whatsapp_config,
)


def main():
    parser = argparse.ArgumentParser(
        description="Create service principal for WhatsApp channel adapter",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Create service principal with default settings
  python scripts/create_whatsapp_service_principal.py

  # Create with expiration in 1 year
  python scripts/create_whatsapp_service_principal.py --expires-days 365

  # Save configuration to specific file
  python scripts/create_whatsapp_service_principal.py --output whatsapp_config.json

Security Notes:
  - The client_secret is a sensitive credential. Store it securely!
  - Do not commit the configuration file to version control
  - Use environment variables for production deployments
"""
    )

    parser.add_argument(
        "--storage-dir",
        type=Path,
        default=Path.home() / ".ieee3394" / "service_principals",
        help="Directory to store service principal data (default: ~/.ieee3394/service_principals)"
    )

    parser.add_argument(
        "--expires-days",
        type=int,
        default=None,
        help="Service principal expiration in days (default: no expiration)"
    )

    parser.add_argument(
        "--bridge-url",
        type=str,
        default="http://localhost:3000",
        help="URL of WhatsApp bridge (default: http://localhost:3000)"
    )

    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path.home() / ".ieee3394" / "whatsapp_config.json",
        help="Output configuration file (default: ~/.ieee3394/whatsapp_config.json)"
    )

    parser.add_argument(
        "--permissions",
        nargs="+",
        default=[
            "channel.whatsapp.read",
            "channel.whatsapp.write",
            "gateway.message.send",
            "gateway.message.receive",
        ],
        help="List of permissions to grant (space-separated)"
    )

    args = parser.parse_args()

    print("=" * 70)
    print("IEEE 3394 WhatsApp Service Principal Creator")
    print("=" * 70)
    print()

    # Create service principal manager
    manager = ServicePrincipalManager(args.storage_dir)

    print(f"Creating service principal for WhatsApp channel...")
    print(f"Storage directory: {args.storage_dir}")
    print()

    # Create service principal
    sp = manager.create_service_principal(
        channel_type="whatsapp",
        permissions=args.permissions,
        expires_in_days=args.expires_days,
        metadata={
            "created_by": "create_whatsapp_service_principal.py",
            "bridge_url": args.bridge_url,
        }
    )

    print("✓ Service Principal Created Successfully!")
    print()
    print("-" * 70)
    print("SERVICE PRINCIPAL CREDENTIALS")
    print("-" * 70)
    print(f"Client ID:     {sp.client_id}")
    print(f"Client Secret: {sp.client_secret}")
    print(f"Channel Type:  {sp.channel_type}")
    print(f"Created At:    {sp.created_at}")
    if sp.expires_at:
        print(f"Expires At:    {sp.expires_at}")
    print(f"Permissions:   {', '.join(sp.permissions)}")
    print("-" * 70)
    print()

    print("⚠️  SECURITY WARNING:")
    print("   Save the Client Secret in a secure location!")
    print("   It will not be shown again.")
    print()

    # Create configuration
    config = create_default_whatsapp_config(
        service_principal=sp,
        bridge_url=args.bridge_url
    )

    # Save configuration
    args.output.parent.mkdir(parents=True, exist_ok=True)
    config.to_file(args.output)

    print(f"✓ Configuration saved to: {args.output}")
    print()

    # Validate configuration
    is_valid, errors = config.validate()
    if is_valid:
        print("✓ Configuration validation passed")
    else:
        print("✗ Configuration validation failed:")
        for error in errors:
            print(f"  - {error}")
        sys.exit(1)

    print()
    print("=" * 70)
    print("NEXT STEPS")
    print("=" * 70)
    print()
    print("1. Start the WhatsApp bridge:")
    print("   cd whatsapp_bridge && npm install && npm start")
    print()
    print("2. Use this configuration in your agent:")
    print()
    print("   from ieee3394_agent.channels.whatsapp import WhatsAppChannelAdapter")
    print("   from ieee3394_agent.channels.whatsapp.config import WhatsAppChannelConfig")
    print()
    print(f"   config = WhatsAppChannelConfig.from_file(Path('{args.output}'))")
    print("   adapter = WhatsAppChannelAdapter(gateway, config)")
    print("   await adapter.start()")
    print()
    print("3. Scan the QR code with WhatsApp to authenticate")
    print()
    print("=" * 70)


if __name__ == "__main__":
    main()
