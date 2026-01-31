"""
Onboarding and Configuration Flow

This module handles the initial setup and configuration of channels,
particularly for platforms requiring API credentials (like WhatsApp Business API).
"""

import asyncio
from typing import Dict, Optional
import logging
from pathlib import Path

from .auth.service_principal import ServicePrincipalRegistry

logger = logging.getLogger(__name__)


class ChannelOnboarding:
    """
    Interactive onboarding flow for configuring channels.
    """

    def __init__(self, registry: ServicePrincipalRegistry):
        self.registry = registry

    async def configure_whatsapp(self, interactive: bool = True) -> bool:
        """
        Configure WhatsApp Business API channel.

        Args:
            interactive: If True, prompt user for values. If False, use environment variables.

        Returns:
            True if configuration successful, False otherwise
        """
        print("\n" + "="*60)
        print("WhatsApp Business API Configuration")
        print("="*60)

        if interactive:
            print("\nTo configure WhatsApp, you'll need:")
            print("1. WhatsApp Business Account ID")
            print("2. Phone Number ID (from Meta Business Manager)")
            print("3. Access Token (from Meta App Dashboard)")
            print("4. Webhook Verify Token (create your own secret)")
            print("5. Your WhatsApp Business Phone Number")
            print("\nFor testing, you can use the test credentials:")
            print("- Phone Number: +15551234567 (example)")
            print("- Phone Number ID: test_phone_id")
            print("- Access Token: test_access_token")
            print("- Webhook Token: test_webhook_token_12345")

            # Get inputs
            phone_number = input("\n📱 WhatsApp Business Phone Number (e.g., +15551234567): ").strip()
            phone_number_id = input("📋 Phone Number ID: ").strip()
            business_account_id = input("🏢 Business Account ID (optional): ").strip() or "unknown"
            access_token = input("🔑 Access Token: ").strip()
            verify_token = input("🔐 Webhook Verify Token: ").strip()
            webhook_url = input("🌐 Webhook URL (e.g., https://your-domain.com/webhook/whatsapp): ").strip()

        else:
            import os
            phone_number = os.getenv("WHATSAPP_PHONE_NUMBER", "+15551234567")
            phone_number_id = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "test_phone_id")
            business_account_id = os.getenv("WHATSAPP_BUSINESS_ACCOUNT_ID", "unknown")
            access_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "test_access_token")
            verify_token = os.getenv("WHATSAPP_VERIFY_TOKEN", "test_webhook_token_12345")
            webhook_url = os.getenv("WHATSAPP_WEBHOOK_URL", "https://ieee3394.org/webhook/whatsapp")

        if not all([phone_number, phone_number_id, access_token, verify_token]):
            print("\n❌ Error: Missing required configuration values")
            return False

        # Validate phone number format
        if not phone_number.startswith('+'):
            print(f"\n⚠️  Warning: Phone number should include country code (e.g., +1...)")
            phone_number = '+' + phone_number

        # Store credentials securely
        credentials = {
            "whatsapp:access_token": access_token,
            "whatsapp:verify_token": verify_token
        }

        metadata = {
            "phone_number": phone_number,
            "phone_number_id": phone_number_id,
            "business_account_id": business_account_id,
            "webhook_url": webhook_url,
            "api_version": "v18.0",
            "configured_at": str(asyncio.get_event_loop().time())
        }

        try:
            # Configure the channel
            self.registry.configure_channel(
                channel_id="whatsapp",
                endpoint=phone_number,
                credentials=credentials,
                metadata=metadata
            )

            print("\n✅ WhatsApp channel configured successfully!")
            print(f"\n📱 Your agent is now reachable at: {phone_number}")
            print(f"🌐 Webhook endpoint: {webhook_url}")
            print("\n⚠️  Next steps:")
            print("1. Configure your Meta App webhook to point to the webhook URL")
            print(f"2. Use verify token: {verify_token}")
            print("3. Subscribe to 'messages' webhook events")
            print("4. Add test numbers to your WhatsApp Business Account")

            return True

        except Exception as e:
            logger.exception("Failed to configure WhatsApp channel")
            print(f"\n❌ Error configuring WhatsApp: {e}")
            return False

    async def configure_cli(self) -> bool:
        """
        Configure CLI channel (typically no external credentials needed).
        """
        print("\n" + "="*60)
        print("CLI Channel Configuration")
        print("="*60)

        try:
            self.registry.configure_channel(
                channel_id="cli",
                endpoint="stdio",
                credentials={},  # No external credentials needed
                metadata={
                    "type": "stdio",
                    "description": "Command-line interface"
                }
            )

            print("\n✅ CLI channel configured successfully!")
            print("📟 Run the agent with: python -m p3394_agent --channel cli")

            return True

        except Exception as e:
            logger.exception("Failed to configure CLI channel")
            print(f"\n❌ Error configuring CLI: {e}")
            return False

    async def configure_web(self, port: int = 8000, host: str = "0.0.0.0") -> bool:
        """
        Configure Web channel.
        """
        print("\n" + "="*60)
        print("Web Channel Configuration")
        print("="*60)

        domain = input(f"\n🌐 Public domain (e.g., ieee3394.org) or leave blank for localhost: ").strip()

        if domain:
            endpoint = f"https://{domain}"
        else:
            endpoint = f"http://localhost:{port}"

        try:
            self.registry.configure_channel(
                channel_id="web",
                endpoint=endpoint,
                credentials={},  # No external credentials needed (TLS certs handled separately)
                metadata={
                    "host": host,
                    "port": port,
                    "domain": domain or "localhost"
                }
            )

            print(f"\n✅ Web channel configured successfully!")
            print(f"🌐 Your agent is now reachable at: {endpoint}")
            print(f"💬 Chat interface: {endpoint}/chat")
            print(f"📚 Documentation: {endpoint}/docs")

            return True

        except Exception as e:
            logger.exception("Failed to configure Web channel")
            print(f"\n❌ Error configuring Web: {e}")
            return False

    async def show_configuration(self):
        """Display current channel configuration."""
        print("\n" + "="*60)
        print("Current Channel Configuration")
        print("="*60)

        sp = self.registry.service_principal
        print(f"\n🤖 Agent: {sp.display_name}")
        print(f"🆔 Service Principal ID: {sp.service_principal_id}")
        print(f"🏢 Organization: {sp.organization}")

        print("\n📡 Active Channels:")
        if not sp.channels:
            print("   (No channels configured)")
        else:
            for channel_id, channel in sp.channels.items():
                status = "🟢 Active" if channel.is_active else "🔴 Inactive"
                print(f"\n   {status} {channel_id.upper()}")
                print(f"      Endpoint: {channel.endpoint}")
                if channel.metadata:
                    for key, value in channel.metadata.items():
                        if "token" not in key.lower() and "secret" not in key.lower():
                            print(f"      {key}: {value}")

        print("\n" + "="*60)

    async def interactive_setup(self):
        """Interactive setup wizard for all channels."""
        print("\n" + "="*60)
        print("IEEE 3394 Exemplar Agent - Channel Setup")
        print("="*60)

        print("\nThis wizard will help you configure channels for your agent.")
        print("You can configure multiple channels or skip any you don't need.")

        # Check what's already configured
        existing = self.registry.get_public_endpoints()
        if existing:
            print("\n✅ Already configured channels:")
            for channel_id, endpoint in existing.items():
                print(f"   - {channel_id}: {endpoint}")

        # CLI (always configure, no credentials needed)
        print("\n1️⃣  Configuring CLI channel...")
        await self.configure_cli()

        # Web
        configure_web = input("\n2️⃣  Configure Web channel? (y/n): ").lower().strip()
        if configure_web == 'y':
            await self.configure_web()

        # WhatsApp
        configure_wa = input("\n3️⃣  Configure WhatsApp Business API? (y/n): ").lower().strip()
        if configure_wa == 'y':
            await self.configure_whatsapp(interactive=True)

        # Summary
        print("\n" + "="*60)
        print("Configuration Complete!")
        print("="*60)
        await self.show_configuration()


async def run_onboarding(storage_dir: Path, channel: Optional[str] = None):
    """
    Run the onboarding flow.

    Args:
        storage_dir: Directory for storing configuration
        channel: Specific channel to configure, or None for interactive wizard
    """
    registry = ServicePrincipalRegistry(storage_dir)
    onboarding = ChannelOnboarding(registry)

    if channel:
        # Configure specific channel
        if channel == "whatsapp":
            await onboarding.configure_whatsapp(interactive=True)
        elif channel == "cli":
            await onboarding.configure_cli()
        elif channel == "web":
            await onboarding.configure_web()
        elif channel == "show":
            await onboarding.show_configuration()
        else:
            print(f"Unknown channel: {channel}")
    else:
        # Run interactive wizard
        await onboarding.interactive_setup()


if __name__ == "__main__":
    import sys
    storage = Path(".claude/principals")

    if len(sys.argv) > 1:
        channel_name = sys.argv[1]
        asyncio.run(run_onboarding(storage, channel_name))
    else:
        asyncio.run(run_onboarding(storage))
