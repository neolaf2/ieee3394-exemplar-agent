#!/usr/bin/env python3
"""
WhatsApp Channel Configuration Script

Configures the WhatsApp channel service principal with encrypted credentials.

Usage:
    uv run python configure_whatsapp.py \
        --app-id <APP_ID> \
        --app-secret <APP_SECRET> \
        --phone-id <PHONE_ID> \
        --business-id <BUSINESS_ID> \
        --verify-token <VERIFY_TOKEN> \
        [--webhook-url <URL>]
"""

import argparse
import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional

# Add project root to Python path
project_root = Path(__file__).parent.parent.parent.parent.parent
sys.path.insert(0, str(project_root / "src"))

from ieee3394_agent.core.auth.service_principal import (
    ServicePrincipal,
    ServicePrincipalRegistry,
    ChannelEndpoint
)
from ieee3394_agent.core.auth.principal import AssuranceLevel


def validate_inputs(
    app_id: str,
    app_secret: str,
    phone_id: str,
    business_id: str,
    verify_token: str
) -> list[str]:
    """Validate all inputs before configuration."""
    import re

    errors = []

    # App ID: numeric string, 15-20 digits
    if not re.match(r'^\d{15,20}$', app_id):
        errors.append("App ID must be a 15-20 digit number")

    # App Secret: hexadecimal, 32+ characters
    if not re.match(r'^[a-f0-9]{32,}$', app_secret.lower()):
        errors.append("App Secret must be a hexadecimal string (32+ chars)")

    # Phone Number ID: numeric string, 15-20 digits
    if not re.match(r'^\d{15,20}$', phone_id):
        errors.append("Phone Number ID must be a 15-20 digit number")

    # Business Account ID: numeric string, 15-20 digits
    if not re.match(r'^\d{15,20}$', business_id):
        errors.append("Business Account ID must be a 15-20 digit number")

    # Verify token: at least 16 characters
    if len(verify_token) < 16:
        errors.append("Verify token must be at least 16 characters")

    return errors


def backup_existing_config(registry: ServicePrincipalRegistry) -> Optional[str]:
    """Backup existing WhatsApp service principal if it exists."""
    existing_sp = registry.get_service_principal("whatsapp")

    if existing_sp:
        backup_path = Path.home() / ".claude" / "principals" / "backups"
        backup_path.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_file = backup_path / f"whatsapp_sp_backup_{timestamp}.json"

        with open(backup_file, 'w') as f:
            json.dump(existing_sp.to_dict(), f, indent=2)

        print(f"✓ Backed up existing configuration to: {backup_file}")
        return str(backup_file)

    return None


def configure_service_principal(
    registry: ServicePrincipalRegistry,
    app_id: str,
    app_secret: str,
    phone_id: str,
    business_id: str,
    verify_token: str,
    webhook_url: Optional[str] = None
) -> ServicePrincipal:
    """Configure WhatsApp service principal."""

    # Create endpoint (webhook URL if provided)
    endpoint = None
    if webhook_url:
        endpoint = ChannelEndpoint(
            url=webhook_url,
            protocol="https",
            auth_type="webhook_token",
            is_active=True
        )

    # Create service principal
    sp = ServicePrincipal(
        principal_id="urn:principal:org:ieee3394:role:service:channel:whatsapp",
        channel_id="whatsapp",
        assurance_level=AssuranceLevel.MEDIUM,
        endpoint=endpoint,
        credentials={
            "app_id": app_id,
            "app_secret": app_secret,
            "phone_number_id": phone_id,
            "business_account_id": business_id,
            "verify_token": verify_token
        },
        metadata={
            "description": "WhatsApp Business API Service Principal",
            "platform": "meta",
            "api_version": "v18.0",
            "phone_number_id": phone_id,
            "business_account_id": business_id,
            "configured_at": datetime.utcnow().isoformat()
        }
    )

    # Register with encryption
    registry.register_service_principal(sp)

    return sp


def display_next_steps(app_id: str, webhook_url: Optional[str], verify_token: str):
    """Display Meta webhook configuration instructions."""

    webhook_display = webhook_url or "<YOUR_WEBHOOK_URL>"

    print("""
╔══════════════════════════════════════════════════════════════════╗
║           WhatsApp Channel Configuration Complete                ║
╚══════════════════════════════════════════════════════════════════╝

✓ Service principal created and registered
✓ Credentials encrypted and stored
✓ WhatsApp channel ready for webhook configuration

NEXT STEPS - Complete webhook setup in Meta Developer Dashboard:

1. Go to: https://developers.facebook.com/apps/{app_id}/whatsapp-business/wa-settings/

2. Click "Edit" next to Webhook

3. Enter these values:
   Callback URL: {webhook_url}
   Verify Token: {verify_token}

4. Click "Verify and Save"

5. Subscribe to webhook fields (required):
   ✓ messages
   ✓ message_status (optional, for delivery receipts)

6. Test the webhook:
   Send a message to your WhatsApp Business number

   Expected: Agent receives and processes the message

═══════════════════════════════════════════════════════════════════

Webhook Verification Test:

  curl -X GET "{webhook_url}?hub.mode=subscribe&hub.challenge=test&hub.verify_token={verify_token}"

Expected response: "test" (the challenge value echoed back)

═══════════════════════════════════════════════════════════════════

Troubleshooting:

- If webhook verification fails, check:
  1. Webhook URL is publicly accessible (use ngrok for local testing)
  2. Verify token matches exactly
  3. Agent is running and listening on the webhook endpoint

- For more help, see: .claude/skills/whatsapp-config/references/webhook_troubleshooting.md

═══════════════════════════════════════════════════════════════════
""".format(
        app_id=app_id,
        webhook_url=webhook_display,
        verify_token=verify_token
    ))


def main():
    parser = argparse.ArgumentParser(
        description="Configure WhatsApp channel service principal",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic configuration
  uv run python configure_whatsapp.py \\
      --app-id 123456789012345 \\
      --app-secret abc123def456... \\
      --phone-id 109876543210987 \\
      --business-id 987654321098765 \\
      --verify-token $(openssl rand -hex 32)

  # With webhook URL
  uv run python configure_whatsapp.py \\
      --app-id 123456789012345 \\
      --app-secret abc123def456... \\
      --phone-id 109876543210987 \\
      --business-id 987654321098765 \\
      --verify-token my_secure_token_12345 \\
      --webhook-url https://example.com/api/whatsapp/webhook
"""
    )

    parser.add_argument(
        '--app-id',
        required=True,
        help='Meta App ID (from Developer Dashboard → Settings → Basic)'
    )

    parser.add_argument(
        '--app-secret',
        required=True,
        help='Meta App Secret (from Developer Dashboard → Settings → Basic)'
    )

    parser.add_argument(
        '--phone-id',
        required=True,
        help='Phone Number ID (from WhatsApp → API Setup)'
    )

    parser.add_argument(
        '--business-id',
        required=True,
        help='Business Account ID (from WhatsApp → API Setup)'
    )

    parser.add_argument(
        '--verify-token',
        required=True,
        help='Webhook verify token (generate with: openssl rand -hex 32)'
    )

    parser.add_argument(
        '--webhook-url',
        help='Webhook callback URL (e.g., https://example.com/api/whatsapp/webhook)'
    )

    args = parser.parse_args()

    print("═══════════════════════════════════════════════════════════════════")
    print("WhatsApp Channel Configuration")
    print("═══════════════════════════════════════════════════════════════════\n")

    # Validate inputs
    print("Validating inputs...")
    errors = validate_inputs(
        args.app_id,
        args.app_secret,
        args.phone_id,
        args.business_id,
        args.verify_token
    )

    if errors:
        print("\n❌ Validation failed:\n")
        for error in errors:
            print(f"  • {error}")
        print("\nPlease correct the errors and try again.")
        sys.exit(1)

    print("✓ All inputs validated\n")

    # Initialize registry
    print("Initializing service principal registry...")
    registry = ServicePrincipalRegistry()
    print("✓ Registry loaded\n")

    # Backup existing configuration
    print("Checking for existing configuration...")
    backup_file = backup_existing_config(registry)
    if backup_file:
        print(f"  Backup saved: {backup_file}")
    else:
        print("  No existing configuration found")
    print()

    # Configure service principal
    print("Configuring WhatsApp service principal...")
    sp = configure_service_principal(
        registry,
        args.app_id,
        args.app_secret,
        args.phone_id,
        args.business_id,
        args.verify_token,
        args.webhook_url
    )
    print("✓ Service principal configured\n")

    # Display configuration summary
    print("Configuration Summary:")
    print(f"  Principal ID: {sp.principal_id}")
    print(f"  Channel: {sp.channel_id}")
    print(f"  Phone Number ID: {sp.metadata.get('phone_number_id')}")
    print(f"  Business Account ID: {sp.metadata.get('business_account_id')}")
    print(f"  Assurance Level: {sp.assurance_level.value}")
    if sp.endpoint:
        print(f"  Webhook URL: {sp.endpoint.url}")
    print()

    # Display next steps
    display_next_steps(args.app_id, args.webhook_url, args.verify_token)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nConfiguration cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Configuration failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
