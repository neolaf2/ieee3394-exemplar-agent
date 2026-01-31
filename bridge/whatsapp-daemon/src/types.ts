/**
 * P3394 Universal Message Format (UMF) Types
 */

export type MessageType = 'request' | 'response' | 'notification' | 'error';
export type ContentType = 'text' | 'json' | 'markdown' | 'html' | 'binary' | 'image' | 'file';

export interface P3394Address {
  agent_id: string;
  channel_id?: string;
  session_id?: string;
}

export interface P3394Content {
  type: ContentType;
  data: string | object;
  mime_type?: string;
  metadata?: Record<string, any>;
}

export interface P3394Message {
  id: string;
  type: MessageType;
  timestamp: string;
  source?: P3394Address;
  destination?: P3394Address;
  reply_to?: string;
  content: P3394Content[];
  session_id?: string;
  conversation_id?: string;
  metadata?: Record<string, any>;
}

export interface ClientPrincipalAssertion {
  channel_id: string;
  channel_identity: string;
  assurance_level: 'none' | 'low' | 'medium' | 'high' | 'cryptographic';
  authentication_method: string;
  metadata: Record<string, any>;
}

export interface WhatsAppConfig {
  // Phone numbers
  service_phone: string;      // +12017575100 - the WhatsApp account running the daemon
  allowed_sender: string;     // +18625206066 - the only phone allowed to send messages

  // Gateway connection
  gateway_url: string;        // Where to send UMF messages
  gateway_ws_url?: string;    // WebSocket for real-time (optional)

  // Behavior
  echo_mode?: boolean;        // Echo messages back for testing
  log_level?: 'debug' | 'info' | 'warn' | 'error';
}

export interface DaemonStatus {
  running: boolean;
  whatsapp_ready: boolean;
  service_phone: string;
  allowed_sender: string;
  gateway_url: string;
  uptime: number;
  messages_received: number;
  messages_forwarded: number;
  last_message_at?: string;
}
