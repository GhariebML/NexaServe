import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import QRCode from 'qrcode';
import qrcodeTerminal from 'qrcode-terminal';
import pino from 'pino';
import { extractN8nReply } from './n8n-response.js';
import makeWASocket, {
  DisconnectReason,
  useMultiFileAuthState,
  fetchLatestBaileysVersion
} from '@whiskeysockets/baileys';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);

const PORT = process.env.PORT || 8080;
const AUTH_DIR = process.env.AUTH_DIR || path.resolve(__dirname, '../../data/whatsapp-auth');
const N8N_WEBHOOK_URL = process.env.N8N_WEBHOOK_URL || 'http://localhost:5678/webhook/customer-service';
const OLLAMA_URL = process.env.OLLAMA_URL || 'http://localhost:11434/api/generate';
const OLLAMA_MODEL = process.env.OLLAMA_MODEL || 'qwen2.5:3b';

if (!fs.existsSync(AUTH_DIR)) {
  fs.mkdirSync(AUTH_DIR, { recursive: true });
}

let sock = null;
let currentQR = null;
let currentQRDataUrl = null;
let connectionState = 'INITIALIZING';
let connectedUser = null;
let lastDisconnectReason = null;

// Track recently dispatched messages to prevent duplicate echo replies (TTL: 15s)
const recentDispatches = new Map();
function isRecentlyDispatched(key) {
  const now = Date.now();
  if (recentDispatches.has(key) && (now - recentDispatches.get(key) < 15000)) {
    return true;
  }
  recentDispatches.set(key, now);
  for (const [k, ts] of recentDispatches.entries()) {
    if (now - ts > 30000) recentDispatches.delete(k);
  }
  return false;
}

// Response cache for AI generation (TTL: 60s) — prevents duplicate Ollama calls
// Cache keys include KB_CACHE_VERSION so KB updates invalidate old entries
let kbCacheVersion = parseInt(process.env.KB_CACHE_VERSION || '1', 10);
const responseCache = new Map();
function getCacheKey(msg) {
  return kbCacheVersion + ':' + (msg || '').trim().toLowerCase().replace(/\s+/g, ' ');
}
function getCachedReply(msg) {
  const key = getCacheKey(msg);
  if (responseCache.has(key)) {
    const entry = responseCache.get(key);
    if (Date.now() - entry.timestamp < 60000) return entry.reply;
    responseCache.delete(key);
  }
  return null;
}
function setCachedReply(msg, reply) {
  const key = getCacheKey(msg);
  responseCache.set(key, { reply, timestamp: Date.now() });
}
function invalidateCache() {
  kbCacheVersion++;
  responseCache.clear();
  console.log('[Cache] Invalidated. New version:', kbCacheVersion);
  return kbCacheVersion;
}
function detectLanguage(text) {
  const arChars = (text || '').match(/[\u0600-\u06FF]/g);
  const latinChars = (text || '').match(/[a-zA-Z]/g);
  if (arChars && arChars.length > (latinChars ? latinChars.length * 0.3 : 0)) return 'ar';
  return 'en';
}
function replyBilingual(ar, en, lang) {
  return (lang === 'en' && en) ? en : ar + '\n---\n' + en;
}

const JID_CACHE_FILE = path.join(AUTH_DIR, 'jid_cache.json');
let jidMap = { "127182672252935": "127182672252935@lid" };
try {
  if (fs.existsSync(JID_CACHE_FILE)) {
    jidMap = { ...jidMap, ...JSON.parse(fs.readFileSync(JID_CACHE_FILE, 'utf8')) };
  }
} catch (e) {}

function saveJidMap() {
  try {
    fs.writeFileSync(JID_CACHE_FILE, JSON.stringify(jidMap, null, 2));
  } catch (e) {}
}

// =============================================================================
// Offline Resilience, Safe Deterministic Deflection & Retry Queue
// =============================================================================

const OFFLINE_RETRY_QUEUE = [];
const MAX_QUEUE_SIZE = 500;

function enqueueOfflineMessage(senderJid, payload) {
  if (OFFLINE_RETRY_QUEUE.length >= MAX_QUEUE_SIZE) {
    OFFLINE_RETRY_QUEUE.shift(); // Evict oldest
  }
  const item = {
    id: `retry_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`,
    senderJid,
    payload,
    queuedAt: new Date().toISOString(),
    attempts: 0
  };
  OFFLINE_RETRY_QUEUE.push(item);
  console.log(`[Offline Queue] Enqueued message from ${senderJid} (Queue size: ${OFFLINE_RETRY_QUEUE.length})`);
  return item.id;
}

function getDeterministicOfflineReply(customerMessage, senderName) {
  const lang = detectLanguage(customerMessage);
  const ar = 'نعتذر، تعذّر إتمام معالجة استفسارك حالياً نظراً لأعمال صيانة مؤقتة. يمكنك متابعة برامجنا ومبادراتنا الرسمية عبر الروابط المعتمدة التالية:\n' +
    '• مبادرة رواد مصر الرقمية (DEPI): https://depi.gov.eg\n' +
    '• بوابة رواد مصر الرقمية (Digilians): https://digilians.gov.eg\n' +
    '• مبادرة براعم مصر الرقمية (DEBI): https://debi.gov.eg\n' +
    'يرجى إعادة المحاولة لاحقاً أو مراجعة البوابات الرسمية أعلاه.';
  const en = 'We apologize, our automated assistant is currently undergoing temporary maintenance. You can explore all official programs and initiatives through our official portals below:\n' +
    '• Digital Egypt Pioneers Initiative (DEPI): https://depi.gov.eg\n' +
    '• Digital Egypt Platform (Digilians): https://digilians.gov.eg\n' +
    '• Digital Egypt Buds Initiative (DEBI): https://debi.gov.eg\n' +
    'Please try again shortly or visit the official portals above.';
  return lang === 'en' ? en : ar;
}

// Background queue processor to retry messages once n8n is available
setInterval(async () => {
  if (OFFLINE_RETRY_QUEUE.length === 0) return;

  const item = OFFLINE_RETRY_QUEUE[0];
  if (!item) return;

  try {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    const res = await fetch(N8N_WEBHOOK_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(item.payload),
      signal: controller.signal
    });
    clearTimeout(timeout);

    if (res.ok) {
      OFFLINE_RETRY_QUEUE.shift();
      console.log(`[Offline Queue] Successfully drained and delivered queued message: ${item.id} to n8n`);
    } else {
      item.attempts = (item.attempts || 0) + 1;
      if (item.attempts >= 3) {
        console.warn(`[Offline Queue] Dropping message after 3 failed attempts: ${item.id}`);
        OFFLINE_RETRY_QUEUE.shift();
      }
    }
  } catch (e) {
    // n8n still unavailable, wait for next interval
  }
}, 15000);

const logger = pino({ level: process.env.LOG_LEVEL || 'warn' });

async function initWhatsApp() {
  connectionState = 'CONNECTING';
  const { state, saveCreds } = await useMultiFileAuthState(AUTH_DIR);
  const { version, isLatest } = await fetchLatestBaileysVersion();
  console.log(`[WhatsApp Bridge] Baileys v${version.join('.')} (isLatest: ${isLatest})`);

  sock = makeWASocket({
    version,
    logger,
    printQRInTerminal: false,
    auth: state,
    generateHighQualityLinkPreview: true,
    browser: ['NexaServe AI', 'Chrome', '120.0.0']
  });

  sock.ev.on('creds.update', saveCreds);

  sock.ev.on('connection.update', async (update) => {
    const { connection, lastDisconnect, qr } = update;

    if (qr) {
      currentQR = qr;
      connectionState = 'QR_READY';
      try {
        currentQRDataUrl = await QRCode.toDataURL(qr, { margin: 2, scale: 8 });
      } catch (err) {
        console.error('[WhatsApp Bridge] Error generating QR DataURL:', err);
      }
      console.log('\n======================================================');
      console.log(' 📱 SCAN WHATSAPP QR CODE BELOW OR OPEN: http://localhost:' + PORT + '/qr');
      console.log('======================================================');
      qrcodeTerminal.generate(qr, { small: true });
    }

    if (connection === 'close') {
      const statusCode = lastDisconnect?.error?.output?.statusCode;
      const shouldReconnect = statusCode !== DisconnectReason.loggedOut;
      lastDisconnectReason = lastDisconnect?.error?.message || `Status ${statusCode}`;
      connectionState = 'DISCONNECTED';
      connectedUser = null;
      currentQR = null;
      currentQRDataUrl = null;

      console.log(`[WhatsApp Bridge] Connection closed. Reason: ${lastDisconnectReason}. Reconnect: ${shouldReconnect}`);

      if (statusCode === DisconnectReason.loggedOut) {
        console.log('[WhatsApp Bridge] Device logged out. Clearing auth credentials...');
        try {
          const files = fs.readdirSync(AUTH_DIR);
          for (const file of files) {
            fs.rmSync(path.join(AUTH_DIR, file), { recursive: true, force: true });
          }
        } catch (e) {
          console.error('[WhatsApp Bridge] Error clearing auth dir:', e);
        }
      }

      if (shouldReconnect) {
        console.log('[WhatsApp Bridge] Reconnecting in 5 seconds...');
        setTimeout(initWhatsApp, 5000);
      }
    } else if (connection === 'open') {
      connectionState = 'CONNECTED';
      currentQR = null;
      currentQRDataUrl = null;
      connectedUser = sock.user;
      const phone = sock.user?.id ? sock.user.id.split(':')[0] : 'Unknown';
      console.log('\n======================================================');
      console.log(` ✅ WHATSAPP CONNECTED SUCCESSFULLY!`);
      console.log(` 📞 Phone Number: +${phone}`);
      console.log(` 👤 Account Name: ${sock.user?.name || 'NexaServe Client'}`);
      console.log('======================================================\n');
    }
  });

  sock.ev.on('messages.upsert', async (event) => {
    try {
      if (event.type !== 'notify') return;

      for (const msg of event.messages) {
        if (!msg.message || msg.key.fromMe) continue;
        if (msg.key.remoteJid?.endsWith('@broadcast') || msg.key.remoteJid?.endsWith('@g.us')) continue;

        const senderJid = msg.key.remoteJid;
        const phone = senderJid.split('@')[0];
        const pushName = msg.pushName || 'WhatsApp Citizen';

        // Cache the mapping between numeric ID and full JID (@lid or @s.whatsapp.net)
        const cleanId = senderJid.replace(/[^0-9]/g, '');
        jidMap[cleanId] = senderJid;
        jidMap[`+${cleanId}`] = senderJid;
        saveJidMap();

        const text =
          msg.message.conversation ||
          msg.message.extendedTextMessage?.text ||
          msg.message.buttonsResponseMessage?.selectedDisplayText ||
          msg.message.listResponseMessage?.title ||
          '';

        if (!text.trim()) continue;

        console.log(`[WhatsApp Ingress] From ${senderJid} (+${phone}, ${pushName}): "${text}"`);

        const payload = {
          channel: 'whatsapp',
          customer_message: text,
          phone_number: `+${phone}`,
          channel_user_id: phone,
          jid: senderJid,
          full_name: pushName,
          start_time: Date.now(),
          entry: [
            {
              changes: [
                {
                  value: {
                    messaging_product: 'whatsapp',
                    contacts: [
                      {
                        profile: { name: pushName },
                        wa_id: phone
                      }
                    ],
                    messages: [
                      {
                        from: phone,
                        id: msg.key.id,
                        text: { body: text },
                        type: 'text'
                      }
                    ]
                  }
                }
              ]
            }
          ]
        };

        let replyText = null;
        let replySource = 'none';

        // 1. Attempt dispatch to n8n workflow
        try {
          // Check response cache first
          const cached = getCachedReply(text);
          if (cached) {
            replyText = cached;
            replySource = 'cache';
          } else {
            const controller = new AbortController();
            const timeout = setTimeout(() => controller.abort(), 50000); // 50s timeout for RAG pipeline
            const startTime = Date.now();
            const response = await fetch(N8N_WEBHOOK_URL, {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(payload),
              signal: controller.signal
            });
            clearTimeout(timeout);

            const result = await response.json().catch(() => null);
            const elapsed = Date.now() - startTime;
            replyText = extractN8nReply(response.status, result);
            console.log(`[WhatsApp Dispatch -> n8n] Status ${response.status} (${elapsed}ms), customer_reply=${Boolean(replyText)}`);

            // Extract response string if returned synchronously from n8n webhook
            if (replyText) {
              replySource = 'n8n';
              setCachedReply(text, replyText);
            } else {
              console.warn(`[WhatsApp Bridge] n8n did not return a successful customer reply (HTTP ${response.status}).`);
            }
          }
        } catch (webhookErr) {
          console.warn('[WhatsApp Bridge] n8n webhook unreachable or timed out (' + webhookErr.message + '). Engaging safe deterministic deflection and retry queue...');
        }

        // 2. If n8n did not provide an answer (offline/stopped/error), invoke Safe Deterministic Handler
        if (!replyText) {
          replyText = getDeterministicOfflineReply(text, pushName);
          replySource = 'deterministic-offline-fallback';
          enqueueOfflineMessage(senderJid, payload);
        }

        // 3. Dispatch the response directly back to the WhatsApp sender!
        if (replyText && sock) {
          const dispatchKey = `${senderJid}_${msg.key.id || text.slice(0, 30)}`;
          if (!isRecentlyDispatched(dispatchKey)) {
            console.log(`[WhatsApp Live Reply (${replySource})] -> ${senderJid}: "${replyText.slice(0, 60)}..."`);
            try {
              await sock.sendMessage(senderJid, { text: replyText });
              console.log(`[WhatsApp Live Reply] ✅ Sent successfully to ${senderJid}`);
            } catch (sendErr) {
              console.error(`[WhatsApp Live Reply] ❌ Failed to send message to ${senderJid}:`, sendErr.message);
            }
          }
        }
      }
    } catch (e) {
      console.error('[WhatsApp Bridge] Error processing messages.upsert:', e);
    }
  });
}

// -----------------------------------------------------------------------------
// Express Web Server & REST API
// -----------------------------------------------------------------------------
const app = express();
app.use(cors());
app.use(express.json());

app.get('/health', (req, res) => {
  res.json({
    service: 'nexaserve-whatsapp-bridge',
    status: connectionState,
    connected: connectionState === 'CONNECTED',
    phone: connectedUser?.id ? connectedUser.id.split(':')[0] : null,
    user: connectedUser
  });
});

app.get('/status', (req, res) => {
  res.json({
    status: connectionState,
    phone: connectedUser?.id ? connectedUser.id.split(':')[0] : null,
    name: connectedUser?.name || null,
    qr_available: !!currentQRDataUrl,
    last_error: lastDisconnectReason
  });
});

app.get('/qr', (req, res) => {
  const isConnected = connectionState === 'CONNECTED';
  const phone = connectedUser?.id ? connectedUser.id.split(':')[0] : '';
  const qrImg = currentQRDataUrl ? `<img src="${currentQRDataUrl}" alt="WhatsApp QR Code" class="qr-img"/>` : '';

  res.send(`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NexaServe - Real WhatsApp Connection</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">
  <style>
    :root {
      --bg: #0b0f19;
      --card: #151c2c;
      --primary: #25D366;
      --primary-hover: #20ba59;
      --text: #f3f4f6;
      --text-dim: #9ca3af;
      --border: #222f46;
    }
    body {
      margin: 0;
      padding: 2rem;
      background: var(--bg);
      font-family: 'Inter', sans-serif;
      color: var(--text);
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      min-height: 90vh;
    }
    .card {
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 20px;
      padding: 2.5rem;
      max-width: 520px;
      width: 100%;
      text-align: center;
      box-shadow: 0 20px 40px rgba(0,0,0,0.5);
    }
    .logo-badge {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      background: rgba(37, 211, 102, 0.12);
      color: var(--primary);
      padding: 0.5rem 1.2rem;
      border-radius: 999px;
      font-weight: 600;
      font-size: 0.9rem;
      margin-bottom: 1.5rem;
      border: 1px solid rgba(37, 211, 102, 0.3);
    }
    h1 {
      margin: 0 0 0.5rem 0;
      font-size: 1.8rem;
      font-weight: 700;
      letter-spacing: -0.02em;
    }
    p {
      color: var(--text-dim);
      font-size: 0.95rem;
      line-height: 1.6;
      margin: 0 0 1.5rem 0;
    }
    .qr-box {
      background: #ffffff;
      padding: 1rem;
      border-radius: 16px;
      display: inline-block;
      margin-bottom: 1.5rem;
      box-shadow: 0 10px 25px rgba(0,0,0,0.3);
    }
    .qr-img {
      display: block;
      width: 260px;
      height: 260px;
    }
    .steps {
      text-align: left;
      background: rgba(0,0,0,0.25);
      border-radius: 12px;
      padding: 1.2rem 1.5rem;
      margin-bottom: 1.5rem;
      font-size: 0.9rem;
    }
    .steps ol {
      margin: 0;
      padding-left: 1.2rem;
    }
    .steps li {
      margin-bottom: 0.5rem;
      color: #d1d5db;
    }
    .steps li:last-child {
      margin-bottom: 0;
    }
    .status-badge {
      display: inline-block;
      padding: 0.5rem 1rem;
      border-radius: 8px;
      font-weight: 600;
      font-size: 0.9rem;
    }
    .status-connected {
      background: #064e3b;
      color: #34d399;
      border: 1px solid #059669;
    }
    .status-waiting {
      background: #78350f;
      color: #fbbf24;
      border: 1px solid #d97706;
    }
    .btn {
      display: inline-block;
      background: var(--primary);
      color: #0b0f19;
      font-weight: 600;
      padding: 0.75rem 1.5rem;
      border-radius: 10px;
      text-decoration: none;
      transition: all 0.2s ease;
      cursor: pointer;
      border: none;
      margin-top: 1rem;
    }
    .btn:hover {
      background: var(--primary-hover);
      transform: translateY(-2px);
    }
  </style>
</head>
<body>
  <div class="card">
    <div class="logo-badge">
      <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor"><path d="M12.04 2c-5.46 0-9.91 4.45-9.91 9.91 0 1.75.46 3.45 1.32 4.95L2.05 22l5.25-1.38c1.45.79 3.08 1.21 4.74 1.21 5.46 0 9.91-4.45 9.91-9.91 0-2.65-1.03-5.14-2.9-7.01A9.816 9.816 0 0 0 12.04 2z"/></svg>
      NexaServe AI WhatsApp Gateway
    </div>

    ${
      isConnected
        ? `
      <div class="status-badge status-connected">CONNECTED: +${phone}</div>
      <h1 style="margin-top: 1.5rem;">WhatsApp Account Linked!</h1>
      <p>Your real WhatsApp account (+${phone}) is active and connected to NexaServe. Any inbound customer inquiry sent to this number will be automatically handled by the AI Customer Service Agent!</p>
      <button onclick="window.location.reload()" class="btn">Refresh Status</button>
      <button onclick="fetch('/logout', {method: 'POST'}).then(() => window.location.reload())" class="btn" style="background:#dc2626; color:#fff; margin-left:0.5rem;">Disconnect Account</button>
    `
        : `
      <h1>Link Your WhatsApp Account</h1>
      <p>Scan the QR code below with your phone to connect your real WhatsApp account to the AI agent.</p>

      <div class="qr-box">
        ${
          qrImg ||
          '<div style="width:260px; height:260px; display:flex; align-items:center; justify-content:center; color:#666; font-size:14px;">Generating QR code...</div>'
        }
      </div>

      <div class="steps">
        <ol>
          <li>Open <strong>WhatsApp</strong> on your phone</li>
          <li>Tap <strong>Settings</strong> (or <strong>Menu ⋮</strong> on Android)</li>
          <li>Select <strong>Linked Devices</strong> and tap <strong>Link a Device</strong></li>
          <li>Point your phone camera at this QR code</li>
        </ol>
      </div>

      <div class="status-badge status-waiting">Status: ${connectionState}</div>
      <script>
        setTimeout(() => window.location.reload(), 5000);
      </script>
    `
    }
  </div>
</body>
</html>`);
});

app.get('/qr.png', async (req, res) => {
  if (!currentQR) {
    return res.status(404).send('QR code not available');
  }
  try {
    const buffer = await QRCode.toBuffer(currentQR, { margin: 1, scale: 8 });
    res.setHeader('Content-Type', 'image/png');
    res.send(buffer);
  } catch (err) {
    res.status(500).send(err.message);
  }
});

// Outbound Message Dispatch endpoint (Called by n8n SubWF 06)
app.post('/send', async (req, res) => {
  try {
    const { to, message } = req.body;
    if (!to || !message) {
      return res.status(400).json({ error: 'Parameters "to" and "message" are required.' });
    }

    if (connectionState !== 'CONNECTED' || !sock) {
      return res.status(503).json({
        error: 'WhatsApp is not connected',
        status: connectionState
      });
    }

    const cleanTo = to.replace(/[^0-9]/g, '');
    let remoteJid;

    if (to.includes('@')) {
      remoteJid = to;
    } else if (jidMap[cleanTo] || jidMap[`+${cleanTo}`]) {
      remoteJid = jidMap[cleanTo] || jidMap[`+${cleanTo}`];
    } else if (cleanTo.length > 13) {
      remoteJid = `${cleanTo}@lid`;
    } else {
      remoteJid = `${cleanTo}@s.whatsapp.net`;
    }

    console.log(`[WhatsApp Egress] Resolved target JID: ${remoteJid} for recipient: ${to}`);
    const dispatchKey = `${remoteJid}_${message.slice(0, 30)}`;
    if (isRecentlyDispatched(dispatchKey)) {
      console.log(`[WhatsApp Egress] Duplicate message to ${remoteJid} suppressed.`);
      return res.json({ success: true, duplicate_suppressed: true, target_jid: remoteJid });
    }

    console.log(`[WhatsApp Egress] Dispatching message: "${message.slice(0, 60)}..."`);
    const sent = await sock.sendMessage(remoteJid, { text: message });

    res.json({
      success: true,
      message_id: sent?.key?.id || 'sent',
      to: cleanTo,
      target_jid: remoteJid,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    console.error('[WhatsApp Egress Error]:', err);
    res.status(500).json({ error: err.message });
  }
});

// Simulation endpoint for test and health checks
app.post('/simulate', async (req, res) => {
  try {
    const message = req.body.customer_message || req.body.message || '';
    const name = req.body.full_name || req.body.name || 'Citizen';
    const phone = req.body.phone_number || req.body.phone || '+966500000000';

    // Check cache first
    const cached = getCachedReply(message);
    if (cached) {
      return res.json({
        success: true,
        source: 'cache',
        reply: cached,
        timestamp: new Date().toISOString()
      });
    }

    const payload = {
      channel: 'whatsapp',
      customer_message: message,
      phone_number: phone,
      channel_user_id: phone.replace(/[^0-9]/g, ''),
      full_name: name,
      start_time: Date.now()
    };

    let replyText = null;
    let source = 'autonomous-ai';

    try {
      const controller = new AbortController();
      const timeout = setTimeout(() => controller.abort(), 50000); // 50s timeout for RAG pipeline
      const startTime = Date.now();
      const n8nResp = await fetch(N8N_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeout);
      const elapsed = Date.now() - startTime;
      if (n8nResp.ok) {
        const json = await n8nResp.json();
        replyText = extractN8nReply(n8nResp.status, json);
        if (replyText) {
          source = 'n8n';
          setCachedReply(message, replyText);
        }
        console.log(`[Simulate -> n8n] Status ${n8nResp.status} (${elapsed}ms)`);
      } else {
        console.warn(`[Simulate -> n8n] Rejected HTTP ${n8nResp.status}; no customer reply was returned.`);
      }
    } catch (e) {}

    if (!replyText) {
      replyText = getDeterministicOfflineReply(message, name);
      source = 'deterministic-offline-fallback';
    }

    res.json({
      success: source === 'n8n',
      status: source === 'n8n' ? 'completed' : 'fallback',
      error_code: source === 'n8n' ? null : 'n8n_response_unavailable',
      source: source,
      reply: replyText,
      timestamp: new Date().toISOString()
    });
  } catch (err) {
    res.status(500).json({ success: false, error: err.message });
  }
});

app.post('/logout', async (req, res) => {
  try {
    if (sock) {
      await sock.logout();
    }
    const files = fs.readdirSync(AUTH_DIR);
    for (const file of files) {
      fs.rmSync(path.join(AUTH_DIR, file), { recursive: true, force: true });
    }
    connectionState = 'DISCONNECTED';
    currentQR = null;
    currentQRDataUrl = null;
    connectedUser = null;
    setTimeout(initWhatsApp, 1000);
    res.json({ success: true, message: 'Logged out successfully' });
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// Cache management endpoints
app.get('/cache/status', (req, res) => {
  res.json({
    version: kbCacheVersion,
    entries: responseCache.size,
    maxTTL: 60000
  });
});
app.post('/cache/invalidate', (req, res) => {
  const newVersion = invalidateCache();
  res.json({ success: true, new_version: newVersion, cleared_entries: responseCache.size });
});

// Ollama model pre-warming — fires a dummy request at startup to reduce first-request latency
async function prewarmOllama() {
  try {
    console.log('[Ollama] Pre-warming model...');
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 15000);
    await fetch(OLLAMA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        prompt: 'Hello',
        stream: false,
        options: { num_ctx: 1024, num_predict: 10, temperature: 0.2 }
      }),
      signal: controller.signal
    });
    clearTimeout(timeout);
    console.log('[Ollama] Pre-warming complete.');
  } catch (err) {
    console.warn('[Ollama] Pre-warming failed (non-fatal):', err.message);
  }
}

app.listen(PORT, () => {
  console.log(`[WhatsApp Bridge] HTTP Server listening on port ${PORT}`);
  console.log(`[WhatsApp Bridge] Web UI available at: http://localhost:${PORT}/qr`);
  prewarmOllama();
  initWhatsApp().catch((err) => {
    console.error('[WhatsApp Bridge] Initialization error:', err);
  });
});
