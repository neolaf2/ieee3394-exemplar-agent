/**
 * IEEE 3394 WhatsApp UMF Daemon (Baileys)
 *
 * Standalone daemon that:
 * 1. Starts independently and shows QR code in terminal
 * 2. Once WhatsApp connects, establishes session with Agent Gateway
 * 3. Passes through all messages: WhatsApp ↔ UMF ↔ Gateway
 */

import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  WASocket
} from '@whiskeysockets/baileys';
import * as qrcode from 'qrcode-terminal';
import axios from 'axios';
import { v4 as uuidv4 } from 'uuid';
import pino from 'pino';
import {
  P3394Message,
  P3394Content,
  ClientPrincipalAssertion,
  WhatsAppConfig,
  DaemonStatus,
  ContentType,
  MessageType
} from './types';

// =============================================================================
// CONFIGURATION
// =============================================================================

const config: WhatsAppConfig = {
  service_phone: process.env.SERVICE_PHONE || '+12017575100',
  allowed_sender: process.env.ALLOWED_SENDER || '+18625206066',
  gateway_url: process.env.GATEWAY_URL || 'http://localhost:8000/api/umf',
  gateway_ws_url: process.env.GATEWAY_WS_URL || 'ws://localhost:8000/ws/whatsapp',
  echo_mode: process.env.ECHO_MODE === 'true',
  log_level: (process.env.LOG_LEVEL as 'debug' | 'info' | 'warn' | 'error') || 'info'
};

// =============================================================================
// STATE
// =============================================================================

const status: DaemonStatus = {
  running: false,
  whatsapp_ready: false,
  service_phone: config.service_phone,
  allowed_sender: config.allowed_sender,
  gateway_url: config.gateway_url,
  uptime: 0,
  messages_received: 0,
  messages_forwarded: 0
};

let sock: WASocket | null = null;
let reconnectAttempts = 0;
const MAX_RECONNECT_ATTEMPTS = 10;
const startTime = Date.now();

// =============================================================================
// LOGGING
// =============================================================================

function log(level: 'debug' | 'info' | 'warn' | 'error', message: string, data?: any) {
  const levels = { debug: 0, info: 1, warn: 2, error: 3 };
  if (levels[level] >= levels[config.log_level || 'info']) {
    const timestamp = new Date().toISOString();
    const prefix = `[${timestamp}] [${level.toUpperCase()}]`;
    if (data !== undefined) {
      console.log(`${prefix} ${message}`, typeof data === 'object' ? JSON.stringify(data) : data);
    } else {
      console.log(`${prefix} ${message}`);
    }
  }
}

// =============================================================================
// PHONE UTILITIES
// =============================================================================

function jidToPhone(jid: string): string {
  const match = jid.match(/^(\d+)@/);
  return match ? '+' + match[1] : jid;
}

function phoneToJid(phone: string): string {
  const digits = phone.replace(/\D/g, '');
  return `${digits}@s.whatsapp.net`;
}

// =============================================================================
// UMF MESSAGE CREATION
// =============================================================================

function createUMFMessage(
  messageText: string,
  senderJid: string,
  messageId: string,
  timestamp: number
): P3394Message {
  const senderPhone = jidToPhone(senderJid);

  const principal: ClientPrincipalAssertion = {
    channel_id: 'whatsapp',
    channel_identity: senderPhone,
    assurance_level: 'medium',
    authentication_method: 'whatsapp_phone_verification',
    metadata: { jid: senderJid, timestamp }
  };

  return {
    id: uuidv4(),
    type: 'request' as MessageType,
    timestamp: new Date().toISOString(),
    source: {
      agent_id: senderPhone,
      channel_id: 'whatsapp',
      session_id: senderJid
    },
    destination: {
      agent_id: 'ieee3394-exemplar',
      channel_id: 'whatsapp'
    },
    content: [{ type: 'text' as ContentType, data: messageText }],
    session_id: senderJid,
    conversation_id: senderJid,
    metadata: {
      client_principal: principal,
      whatsapp_message_id: messageId,
      whatsapp_timestamp: timestamp
    }
  };
}

// =============================================================================
// GATEWAY COMMUNICATION
// =============================================================================

async function forwardToGateway(umfMessage: P3394Message): Promise<string | null> {
  try {
    log('info', `Forwarding to Gateway: ${umfMessage.id}`);

    const response = await axios.post(config.gateway_url, umfMessage, {
      headers: {
        'Content-Type': 'application/json',
        'X-P3394-Channel': 'whatsapp',
        'X-P3394-Message-Id': umfMessage.id
      },
      timeout: 60000  // 60 second timeout for LLM responses
    });

    status.messages_forwarded++;

    // Extract response text from Gateway's UMF response
    const responseData = response.data;
    if (responseData?.content?.[0]?.data) {
      return responseData.content[0].data;
    }

    return null;
  } catch (error: any) {
    if (error.code === 'ECONNREFUSED') {
      log('warn', 'Gateway not available - running in echo-only mode');
    } else {
      log('error', `Gateway error: ${error.message}`);
    }
    return null;
  }
}

// =============================================================================
// WHATSAPP MESSAGE HANDLER
// =============================================================================

async function handleIncomingMessage(
  messageText: string,
  senderJid: string,
  messageId: string,
  timestamp: number
) {
  const senderPhone = jidToPhone(senderJid);

  log('info', `Message from ${senderPhone}: "${messageText.substring(0, 50)}${messageText.length > 50 ? '...' : ''}"`);
  status.messages_received++;
  status.last_message_at = new Date().toISOString();

  // Create UMF message
  const umfMessage = createUMFMessage(messageText, senderJid, messageId, timestamp);

  // Forward to Gateway and get response
  const gatewayResponse = await forwardToGateway(umfMessage);

  // Send response back to WhatsApp
  if (gatewayResponse && sock) {
    try {
      await sock.sendMessage(senderJid, { text: gatewayResponse });
      log('info', `Reply sent to ${senderPhone}`);
    } catch (err: any) {
      log('error', `Failed to send reply: ${err.message}`);
    }
  } else if (config.echo_mode && sock) {
    // Fallback to echo mode if no gateway response
    try {
      await sock.sendMessage(senderJid, { text: `[Echo] ${messageText}` });
      log('info', `Echo sent to ${senderPhone}`);
    } catch (err: any) {
      log('error', `Failed to send echo: ${err.message}`);
    }
  }
}

// =============================================================================
// WHATSAPP CONNECTION
// =============================================================================

async function connectWhatsApp(): Promise<void> {
  const { state, saveCreds } = await useMultiFileAuthState('./baileys-auth');

  sock = makeWASocket({
    auth: state,
    logger: pino({ level: 'silent' }) as any,
    browser: ['IEEE3394-WhatsApp-Daemon', 'Chrome', '120.0.0'],
    syncFullHistory: false,
    markOnlineOnConnect: true
  });

  // Connection updates
  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    // QR Code display
    if (qr) {
      console.log('\n' + '='.repeat(50));
      console.log('  Scan this QR code with WhatsApp');
      console.log('='.repeat(50) + '\n');
      qrcode.generate(qr, { small: true });
      console.log('\n' + '='.repeat(50) + '\n');
      reconnectAttempts = 0;  // Reset on QR display
    }

    // Connection closed
    if (connection === 'close') {
      status.whatsapp_ready = false;
      const statusCode = (lastDisconnect?.error as any)?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;

      log('warn', `Disconnected (code: ${statusCode})`);

      if (shouldReconnect && reconnectAttempts < MAX_RECONNECT_ATTEMPTS) {
        reconnectAttempts++;
        // Exponential backoff: 3s, 6s, 12s, 24s, 48s...
        const delay = Math.min(3000 * Math.pow(2, reconnectAttempts - 1), 60000);
        log('info', `Reconnecting in ${delay/1000}s (attempt ${reconnectAttempts}/${MAX_RECONNECT_ATTEMPTS})`);
        setTimeout(connectWhatsApp, delay);
      } else if (reconnectAttempts >= MAX_RECONNECT_ATTEMPTS) {
        log('error', 'Max reconnection attempts reached. Please restart manually.');
      }
    }

    // Connected successfully
    if (connection === 'open') {
      reconnectAttempts = 0;
      status.whatsapp_ready = true;

      console.log('\n' + '='.repeat(60));
      console.log('  ✅ WhatsApp Connected Successfully!');
      console.log('='.repeat(60));
      console.log(`  Service Phone:  ${config.service_phone}`);
      console.log(`  Gateway URL:    ${config.gateway_url}`);
      console.log(`  Echo Mode:      ${config.echo_mode ? 'ON' : 'OFF'}`);
      console.log('='.repeat(60));
      console.log('  Listening for messages...');
      console.log('='.repeat(60) + '\n');
    }
  });

  // Save credentials
  sock.ev.on('creds.update', saveCreds);

  // Message handler
  sock.ev.on('messages.upsert', async (m) => {
    for (const msg of m.messages) {
      // Skip if no content or sent by us
      if (!msg.message || msg.key.fromMe) continue;

      const senderJid = msg.key.remoteJid || '';

      // Skip group messages and status updates
      if (senderJid.endsWith('@g.us') || senderJid === 'status@broadcast') continue;

      // Extract message text
      const messageText =
        msg.message.conversation ||
        msg.message.extendedTextMessage?.text ||
        msg.message.imageMessage?.caption ||
        msg.message.videoMessage?.caption ||
        '';

      if (!messageText) continue;

      // Handle the message
      await handleIncomingMessage(
        messageText,
        senderJid,
        msg.key.id || '',
        (msg.messageTimestamp as number) || Math.floor(Date.now() / 1000)
      );
    }
  });
}

// =============================================================================
// MAIN
// =============================================================================

async function main() {
  console.log('\n');
  console.log('╔' + '═'.repeat(58) + '╗');
  console.log('║' + '  IEEE 3394 WhatsApp UMF Daemon'.padEnd(58) + '║');
  console.log('║' + '  Standalone Bridge Service'.padEnd(58) + '║');
  console.log('╠' + '═'.repeat(58) + '╣');
  console.log('║' + `  Service Phone:  ${config.service_phone}`.padEnd(58) + '║');
  console.log('║' + `  Gateway URL:    ${config.gateway_url}`.padEnd(58) + '║');
  console.log('║' + `  Echo Mode:      ${config.echo_mode ? 'ON (fallback)' : 'OFF'}`.padEnd(58) + '║');
  console.log('╚' + '═'.repeat(58) + '╝');
  console.log('\n');

  status.running = true;

  // Graceful shutdown
  const shutdown = () => {
    log('info', 'Shutting down...');
    status.running = false;
    if (sock) {
      sock.end(undefined);
    }
    process.exit(0);
  };

  process.on('SIGINT', shutdown);
  process.on('SIGTERM', shutdown);

  // Connect to WhatsApp
  log('info', 'Starting WhatsApp connection...');
  await connectWhatsApp();

  // Uptime tracker
  setInterval(() => {
    status.uptime = Math.floor((Date.now() - startTime) / 1000);
  }, 1000);
}

// Run
main().catch((error) => {
  console.error('Fatal error:', error);
  process.exit(1);
});
