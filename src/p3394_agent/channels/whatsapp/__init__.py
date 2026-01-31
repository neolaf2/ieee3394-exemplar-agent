"""
WhatsApp Channel - Companion Agent Mode

This channel implements Companion Agent Mode for WhatsApp:
- Simple allowlist-based authentication (phone → principal)
- No complex credential exchange needed
- Once on allowlist, user is trusted with their configured scopes

Architecture:
    WhatsApp User <-> Bridge (Node.js) <-> WhatsAppChannelAdapter <-> Gateway

Components:
- WhatsAppBridgeClient: Connects to Node.js bridge
- WhatsAppChannelAdapter: P3394 channel adapter with auth
- WhatsAppConfig: Configuration for companion mode

The Node.js bridge at bridge/whatsapp-bridge/ handles:
- WhatsApp Web connection via whatsapp-web.js (Puppeteer)
- QR code authentication
- Message sending/receiving

Usage:
    1. Start the bridge:  cd bridge/whatsapp-bridge && npm start
    2. Scan QR code with WhatsApp
    3. Start the adapter (see scripts/start_whatsapp.py)

Allowlist configuration:
    Add phone numbers to .claude/principals/credential_bindings.json
    with channel="whatsapp" and binding_type="phone"
"""

from .client import WhatsAppBridgeClient, WhatsAppMessage
from .adapter import WhatsAppChannelAdapter, WhatsAppConfig

__all__ = [
    "WhatsAppBridgeClient",
    "WhatsAppMessage",
    "WhatsAppChannelAdapter",
    "WhatsAppConfig"
]
