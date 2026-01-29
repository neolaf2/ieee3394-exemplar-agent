/**
 * WhatsApp Web Bridge Server
 *
 * Provides HTTP and WebSocket API for IEEE 3394 Agent to connect to WhatsApp.
 * Uses whatsapp-web.js to interface with WhatsApp Web.
 *
 * Inspired by Moltbot's WhatsApp adapter architecture.
 */

import { Client, LocalAuth } from 'whatsapp-web.js';
import express from 'express';
import { WebSocketServer } from 'ws';
import qrcode from 'qrcode-terminal';

const app = express();
const PORT = process.env.PORT || 3000;

app.use(express.json());

// WhatsApp client instance
let client = null;
let isReady = false;
let isAuthenticated = false;
let currentQR = null;

// WebSocket clients (for real-time updates)
const wsClients = new Set();

// Initialize WhatsApp client
function initializeClient() {
    console.log('Initializing WhatsApp client...');

    client = new Client({
        authStrategy: new LocalAuth({
            dataPath: './whatsapp_auth'
        }),
        puppeteer: {
            headless: true,
            args: ['--no-sandbox', '--disable-setuid-sandbox']
        }
    });

    // QR code for authentication
    client.on('qr', (qr) => {
        console.log('QR Code received');
        currentQR = qr;

        // Display in terminal
        qrcode.generate(qr, { small: true });

        // Broadcast to WebSocket clients
        broadcastToClients({
            type: 'qr',
            qr: qr
        });
    });

    // Client is ready
    client.on('ready', () => {
        console.log('WhatsApp client is ready!');
        isReady = true;
        isAuthenticated = true;
        currentQR = null;

        broadcastToClients({
            type: 'ready',
            timestamp: new Date().toISOString()
        });
    });

    // Authentication successful
    client.on('authenticated', () => {
        console.log('WhatsApp authenticated');
        isAuthenticated = true;
    });

    // Authentication failure
    client.on('auth_failure', (msg) => {
        console.error('Authentication failure:', msg);
        isAuthenticated = false;

        broadcastToClients({
            type: 'auth_failure',
            message: msg
        });
    });

    // Disconnected
    client.on('disconnected', (reason) => {
        console.log('WhatsApp disconnected:', reason);
        isReady = false;
        isAuthenticated = false;

        broadcastToClients({
            type: 'disconnected',
            reason: reason
        });
    });

    // Incoming message
    client.on('message', async (msg) => {
        console.log('Received message from:', msg.from);

        // Convert to JSON-serializable format
        const messageData = {
            id: {
                fromMe: msg.fromMe,
                remote: msg.from,
                id: msg.id.id,
                _serialized: msg.id._serialized
            },
            ack: msg.ack,
            hasMedia: msg.hasMedia,
            body: msg.body,
            type: msg.type,
            timestamp: msg.timestamp,
            from: msg.from,
            to: msg.to,
            author: msg.author,
            isForwarded: msg.isForwarded,
            broadcast: msg.broadcast,
            isStatus: msg.isStatus,
            isGroup: msg.isGroup,
            hasQuotedMsg: msg.hasQuotedMsg
        };

        // Add media info if present
        if (msg.hasMedia) {
            try {
                const media = await msg.downloadMedia();
                messageData.mediaKey = msg.mediaKey;
                messageData.mimetype = media.mimetype;
                messageData.filename = media.filename;
                messageData.filesize = media.filesize;
                // Note: Not sending media.data (base64) to save bandwidth
                // Python adapter can request media separately if needed
            } catch (error) {
                console.error('Error downloading media:', error);
            }
        }

        // Add quoted message info if present
        if (msg.hasQuotedMsg) {
            const quotedMsg = await msg.getQuotedMessage();
            messageData.quotedMsg = {
                id: quotedMsg.id,
                body: quotedMsg.body,
                from: quotedMsg.from
            };
        }

        // Broadcast to WebSocket clients
        broadcastToClients({
            type: 'message',
            message: messageData
        });
    });

    // Message acknowledgment
    client.on('message_ack', (msg, ack) => {
        broadcastToClients({
            type: 'ack',
            messageId: msg.id._serialized,
            ack: ack
        });
    });

    // Initialize the client
    client.initialize();
}

// Broadcast message to all connected WebSocket clients
function broadcastToClients(data) {
    const message = JSON.stringify(data);
    wsClients.forEach(client => {
        if (client.readyState === 1) { // WebSocket.OPEN
            client.send(message);
        }
    });
}

// =========================================================================
// HTTP API ENDPOINTS
// =========================================================================

// Health check
app.get('/status', (req, res) => {
    res.json({
        status: 'running',
        ready: isReady,
        authenticated: isAuthenticated,
        hasQR: currentQR !== null
    });
});

// Authentication status
app.get('/auth/status', (req, res) => {
    res.json({
        authenticated: isAuthenticated,
        ready: isReady
    });
});

// Request QR code
app.post('/auth/qr', (req, res) => {
    if (currentQR) {
        res.json({ qr: currentQR });
    } else {
        res.status(404).json({ error: 'No QR code available' });
    }
});

// Send message
app.post('/send', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp client not ready' });
    }

    const { chatId, content, media, caption, quotedMessageId } = req.body;

    if (!chatId) {
        return res.status(400).json({ error: 'chatId is required' });
    }

    try {
        let result;

        if (media) {
            // Send media message
            const mediaData = {
                mimetype: media.mime_type,
                filename: media.filename || 'file',
                caption: caption || media.caption || content || ''
            };

            // If URL provided, download first
            if (media.url) {
                const response = await fetch(media.url);
                const buffer = await response.arrayBuffer();
                mediaData.data = Buffer.from(buffer).toString('base64');
            }

            result = await client.sendMessage(chatId, mediaData);
        } else {
            // Send text message
            const options = {};

            // Add quoted message if specified
            if (quotedMessageId) {
                options.quotedMessageId = quotedMessageId;
            }

            result = await client.sendMessage(chatId, content, options);
        }

        res.json({
            success: true,
            messageId: result.id._serialized,
            timestamp: result.timestamp
        });

    } catch (error) {
        console.error('Error sending message:', error);
        res.status(500).json({
            error: 'Failed to send message',
            details: error.message
        });
    }
});

// Get chat list
app.get('/chats', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp client not ready' });
    }

    try {
        const chats = await client.getChats();
        const chatList = chats.map(chat => ({
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup,
            unreadCount: chat.unreadCount,
            timestamp: chat.timestamp
        }));

        res.json(chatList);
    } catch (error) {
        console.error('Error getting chats:', error);
        res.status(500).json({
            error: 'Failed to get chats',
            details: error.message
        });
    }
});

// Get specific chat
app.get('/chats/:chatId', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp client not ready' });
    }

    try {
        const chat = await client.getChatById(req.params.chatId);
        res.json({
            id: chat.id._serialized,
            name: chat.name,
            isGroup: chat.isGroup,
            unreadCount: chat.unreadCount,
            timestamp: chat.timestamp
        });
    } catch (error) {
        console.error('Error getting chat:', error);
        res.status(404).json({
            error: 'Chat not found',
            details: error.message
        });
    }
});

// Download media
app.get('/media/:messageId', async (req, res) => {
    if (!isReady) {
        return res.status(503).json({ error: 'WhatsApp client not ready' });
    }

    try {
        // This is a simplified version - in production, you'd need to
        // maintain a cache of recent messages to access by ID
        res.status(501).json({
            error: 'Media download not implemented yet'
        });
    } catch (error) {
        console.error('Error downloading media:', error);
        res.status(500).json({
            error: 'Failed to download media',
            details: error.message
        });
    }
});

// Logout
app.post('/logout', async (req, res) => {
    try {
        await client.logout();
        isAuthenticated = false;
        isReady = false;
        res.json({ success: true });
    } catch (error) {
        console.error('Error logging out:', error);
        res.status(500).json({
            error: 'Failed to logout',
            details: error.message
        });
    }
});

// =========================================================================
// START SERVER
// =========================================================================

// Start HTTP server
const server = app.listen(PORT, () => {
    console.log(`WhatsApp bridge server listening on port ${PORT}`);
    console.log(`HTTP API: http://localhost:${PORT}`);
    console.log(`WebSocket: ws://localhost:${PORT}/ws`);
});

// Start WebSocket server
const wss = new WebSocketServer({ server, path: '/ws' });

wss.on('connection', (ws) => {
    console.log('WebSocket client connected');
    wsClients.add(ws);

    // Send current status
    ws.send(JSON.stringify({
        type: 'status',
        ready: isReady,
        authenticated: isAuthenticated,
        hasQR: currentQR !== null
    }));

    // Send QR if available
    if (currentQR && !isAuthenticated) {
        ws.send(JSON.stringify({
            type: 'qr',
            qr: currentQR
        }));
    }

    ws.on('close', () => {
        console.log('WebSocket client disconnected');
        wsClients.delete(ws);
    });

    ws.on('error', (error) => {
        console.error('WebSocket error:', error);
        wsClients.delete(ws);
    });
});

// Initialize WhatsApp client
initializeClient();

// Graceful shutdown
process.on('SIGINT', async () => {
    console.log('Shutting down...');

    if (client) {
        await client.destroy();
    }

    server.close(() => {
        console.log('Server closed');
        process.exit(0);
    });
});
