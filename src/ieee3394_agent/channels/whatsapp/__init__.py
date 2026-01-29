"""
WhatsApp Channel Adapter

Provides P3394-compliant WhatsApp integration using whatsapp-web.js bridge.
"""

from .adapter import WhatsAppChannelAdapter
from .normalize import normalize_whatsapp_message, normalize_umf_to_whatsapp

__all__ = [
    "WhatsAppChannelAdapter",
    "normalize_whatsapp_message",
    "normalize_umf_to_whatsapp",
]
