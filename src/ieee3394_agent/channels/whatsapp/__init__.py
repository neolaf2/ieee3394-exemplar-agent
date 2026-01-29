"""
WhatsApp Channel Adapter

Provides P3394-compliant WhatsApp integration using whatsapp-web.js bridge.
"""

from .adapter import WhatsAppChannelAdapter
from .normalize import normalize_whatsapp_message, normalize_umf_to_whatsapp
from .binding import WhatsAppChannelBinding
from .config import WhatsAppChannelConfig, ServicePrincipal, ServicePrincipalManager

__all__ = [
    "WhatsAppChannelAdapter",
    "WhatsAppChannelBinding",
    "WhatsAppChannelConfig",
    "ServicePrincipal",
    "ServicePrincipalManager",
    "normalize_whatsapp_message",
    "normalize_umf_to_whatsapp",
]
