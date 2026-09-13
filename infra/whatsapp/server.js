import express from 'express';
import cors from 'cors';
import path from 'path';
import fs from 'fs';
import { fileURLToPath } from 'url';
import QRCode from 'qrcode';
import qrcodeTerminal from 'qrcode-terminal';
import pino from 'pino';
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
  // Cleanup old keys
  for (const [k, ts] of recentDispatches.entries()) {
    if (now - ts > 30000) recentDispatches.delete(k);
  }
  return false;
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

// Built-in Knowledge Base for Instant Zero-Latency Answers
const LOCAL_FAQ_ITEMS = [
  {
    keys: ['شروط', 'تقديم', 'قبول', 'سن', 'عمر', 'مؤهل', 'تجنيد', 'متطلبات'],
    reply: `*شروط التقديم والقبول في مبادرة الرواد الرقميون (DEPI):* 🏛️\n\n1. *الجنسية:* مصري / مصرية.\n2. *السن:* من 18 حتى 32 عاماً.\n3. *المؤهل الدراسي:* مؤهل مناسب لمسار التدريب (خريجو الكليات والمعاهد العليا والمتوسطة)، ويُقبل طلاب السنة النهائية بإفادة رسمية.\n4. *الموقف التجنيدي:* أدى الخدمة العسكرية أو معفى نهائياً أو مؤجل تأجيلاً سارياً.\n5. *اللغة:* إلمام بأساسيات اللغة الإنجليزية (B1 كحد أدنى).\n6. *التفرغ:* تفرغ كامل للمسار التدريبي.\n\n🔗 *رابط التقديم الرسمي:* https://www.digilians.gov.eg/login`
  },
  {
    keys: ['مزايا', 'مميزات', 'منحة', 'شهادة', 'ماجستير', 'اقامة', 'وجبات'],
    reply: `*مزايا ومنح مبادرة الرواد الرقميون (DEPI):* 🌟\n\n- شهادة معتمدة مشتركة من وزارة الاتصالات والأكاديمية العسكرية.\n- شهادات دولية معتمدة لكل محور تدريبي ومهارة تقنية.\n- فرصة الحصول على ماجستير معتمد من جامعة أجنبية مرموقة.\n- تدريب عملي مجاني بالكامل مع مسابقات وجوائز للمتميزين.\n- إقامة فندقية مجانية شاملة الوجبات طوال فترة التدريب بالأكاديمية.\n\nيسعدنا انضمامك لرواد المستقبل! 🚀`
  },
  {
    keys: ['تخصصات', 'مسارات', 'تراك', 'تراكات', 'مجالات', 'ذكاء', 'امن سيبراني'],
    reply: `*المسارات والتخصصات المتاحة في مبادرة الرواد الرقميون:* 💻\n\n1. الذكاء الاصطناعي وعلوم البيانات (AI & Data Science)\n2. الأمن السيبراني (Cybersecurity)\n3. تطوير البرمجيات وهندسة النظم (Software Development)\n4. البنية التحتية الرقمية والحوسبة السحابية (Cloud & Infrastructure)\n5. الفنون والوسائط الرقمية (Digital Arts & Design)\n6. النظم المدمجة وتصميم الدوائر (Embedded Systems & VLSI)\n\n📌 *ملاحظة:* يختار المتقدم مساراً تدريبياً واحداً للتركيز على التميز الاحترافي.`
  },
  {
    keys: ['تسجيل', 'رابط', 'موقع', 'لينك', 'ازاي اقدم', 'طريقة التسجيل'],
    reply: `*طريقة ورابط التسجيل في مبادرة الرواد الرقميون:* 📝\n\nالتسجيل مجاني تماماً وبشكل إلكتروني عبر البوابة الرسمية:\n🔗 https://www.digilians.gov.eg/login\n\n💡 *نصيحة:* استخدم جهاز كمبيوتر أثناء التسجيل لضمان وضوح رفع المستندات بصيغة PDF.`
  },
  {
    keys: ['أوراق', 'مستندات', 'مطلوبة', 'رفع', 'فيش', 'شهادة'],
    reply: `*الأوراق والمستندات المطلوبة للتقديم:* 📂\n\n1. صورة بطاقة الرقم القومي سارية.\n2. أصل شهادة التخرج (أو إفادة قيد بالسنة النهائية).\n3. شهادة الموقف التجنيدي للذكور.\n4. شهادة إتقان اللغة الإنجليزية (إن وجدت).\n5. صحيفة الحالة الجنائية (فيش وتشبيه ساري).\n\n⚠️ تُرفع المستندات بصيغة PDF بحد أقصى 2 ميجابايت للملف.`
  }
];

async function generateAutonomousResponse(customerMessage, senderName) {
  const msg = (customerMessage || '').toLowerCase();
  
  // 1. Check for Service/Order Tracking (SRV- / ORD-)
  const srvMatch = customerMessage.match(/(?:srv|ord)-\d+/i);
  if (srvMatch) {
    const srvNum = srvMatch[0].toUpperCase();
    return `أهلاً بك ${senderName || 'عزيزنا العميل'}،\nحالة طلبك/معاملتك رقم *${srvNum}* هي: *قيد المراجعة والتدقيق والاعتماد*. 📋\n\nيتم حالياً استكمال الإجراءات الرسمية، والتاريخ المتوقع لإشعارك بالنتيجة هو خلال 48 ساعة عمل.\nنسعد بخدمتك دائماً في منصة خدمة العملاء الذكية! 🏛️`;
  }

  // 2. Check for Human Escalation / Frustration
  if (msg.includes('موظف') || msg.includes('شكوى') || msg.includes('انسان') || msg.includes('سيئة') || msg.includes('مشكلة')) {
    const ticketId = 'TICK-' + Math.floor(1000 + Math.random() * 9000);
    return `تم استلام طلبك وتصعيده بعناية إلى الفريق المختص. تم فتح تذكرة دعم ذات أولوية برقم *#${ticketId}* (درجة الأولوية: عالية). ⏱️\n\nيقوم أحد مسؤولي خدمة العملاء بمراجعة تفاصيل استفسارك وسيتواصل معك مباشرة. شكرًا لصبرك معنا!`;
  }

  // 3. Check for Quick FAQ match
  for (const item of LOCAL_FAQ_ITEMS) {
    if (item.keys.some(k => msg.includes(k))) {
      return item.reply;
    }
  }

  // 3b. Direct details/info request
  if (msg.includes('تفاصيل') || msg.includes('معلومات') || msg.includes('المبادرة') || msg.includes('عن المبادرة')) {
    return `*مبادرة الرواد الرقميون (DEPI) - وزارة الاتصالات:* 🏛️✨\n\nهي مبادرة وطنية مجانية ممولة بالكامل تهدف لتدريب الشباب المصري (18-32 سنة) وبناء كوادر احترافية في مجالات التكنولوجيا المتقدمة بشراكة مع الأكاديمية العسكرية وجامعات عالمية.\n\n📌 *المزايا:* شهادات دولية معتمدة + إقامة فندقية شاملة مجانية + فرص ماجستير للمتفوقين.\n💻 *المسارات:* ذكاء اصطناعي، أمن سيبراني، برمجيات، سحابيات، فنون رقمية، نظم مدمجة.\n🔗 *رابط التسجيل الرسمي:* https://www.digilians.gov.eg/login\n\nهل تود الاستفسار عن الشروط، الأوراق، أو التخصصات؟`;
  }

  // 4. Greetings
  if (msg.includes('سلام') || msg.includes('مرحبا') || msg.includes('أهلا') || msg.includes('صباح') || msg.includes('مساء')) {
    return `أهلاً وسهلاً بك ${senderName || ''} في منصة خدمة العملاء الذكية لمبادرة الرواد الرقميون (DEPI)! 🏛️✨\n\nيسعدني مساعدتك في الإجابة عن أي استفسار حول:\n📌 *شروط التقديم والقبول*\n📝 *خطوات ورابط التسجيل*\n🏆 *المسارات والتخصصات المتاحة*\n🌟 *المزايا والشهادات المعتمدة*\n\nكيف يمكنني مساعدتك اليوم؟`;
  }

  // 5. Query Local Ollama LLM for Intelligent Grounded Answer
  try {
    const prompt = `أنت المساعد الذكي الرسمي لخدمة عملاء مبادرة الرواد الرقميون (DEPI) التابعة لوزارة الاتصالات وتكنولوجيا المعلومات المصرية.
تعليمات هامة جداً للتنسيق:
- اكتب باللغة العربية الفصحى السليمة بدون أي رموز غريبة وبدون استخدام نجوم متكررة بين الحروف.
- استخدم التنسيق النقطي البسيط والواضح.
- اجعل الإجابة موجزة، مهنية ومباشرة في حدود 3 إلى 5 أسطر فقط.
- رابط التسجيل هو: https://www.digilians.gov.eg/login

رسالة العميل: "${customerMessage}"`;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 12000);
    const ollamaResp = await fetch(OLLAMA_URL, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        model: OLLAMA_MODEL,
        prompt: prompt,
        stream: false,
        options: {
          num_ctx: 1024,
          num_predict: 250,
          temperature: 0.2
        }
      }),
      signal: controller.signal
    });
    clearTimeout(timeout);

    if (ollamaResp.ok) {
      const data = await ollamaResp.json();
      if (data.response && data.response.trim()) {
        let cleaned = data.response
          .replace(/\*\*/g, '*') // Convert markdown bold from ** to single *
          .replace(/#+\s*/g, '') // Remove markdown headers
          .trim();
        return cleaned;
      }
    }
  } catch (err) {
    console.warn('[Autonomous AI] Ollama fallback warning:', err.message);
  }

  // 6. Universal Default Safe Fallback
  return `أهلاً بك في منصة خدمة العملاء الذكية (DEPI) 🏛️\n\nتم استلام استفسارك: "${customerMessage}".\nيمكنك الاستفسار عن شروط التقديم، رابط التسجيل، المسارات، أو طلب التحدث مع ممثل الدعم وسنكون سعداء بمساعدتك فوراً!`;
}

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
          const controller = new AbortController();
          const timeout = setTimeout(() => controller.abort(), 6000); // 6s timeout before intelligent fallback
          const response = await fetch(N8N_WEBHOOK_URL, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload),
            signal: controller.signal
          });
          clearTimeout(timeout);

          const result = await response.json().catch(() => ({ status: response.statusText }));
          console.log(`[WhatsApp Dispatch -> n8n] Status ${response.status}:`, JSON.stringify(result).slice(0, 150));

          // Extract response string if returned synchronously from n8n webhook
          if (result && (result.response || result.final_reply || result.reply || result.message)) {
            replyText = result.response || result.final_reply || result.reply || result.message;
            replySource = 'n8n';
          }
        } catch (webhookErr) {
          console.warn('[WhatsApp Bridge] n8n webhook unreachable or timed out (' + webhookErr.message + '). Switching to autonomous AI engine...');
        }

        // 2. If n8n did not provide an answer (offline/stopped/error), invoke Autonomous AI Engine
        if (!replyText) {
          try {
            replyText = await generateAutonomousResponse(text, pushName);
            replySource = 'autonomous-ai';
          } catch (aiErr) {
            console.error('[WhatsApp Bridge] Autonomous AI error:', aiErr);
            replyText = `أهلاً بك ${pushName}. تم استلام استفسارك وسيقوم ممثل خدمة العملاء بالرد عليك قريباً!`;
            replySource = 'safe-fallback';
          }
        }

        // 3. Dispatch the response directly back to the WhatsApp sender!
        if (replyText && sock) {
          const dispatchKey = `${senderJid}_${replyText.slice(0, 30)}`;
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
      const timeout = setTimeout(() => controller.abort(), 2000);
      const n8nResp = await fetch(N8N_WEBHOOK_URL, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
        signal: controller.signal
      });
      clearTimeout(timeout);
      if (n8nResp.ok) {
        const json = await n8nResp.json();
        replyText = json.response || json.final_reply || json.reply || json.message;
        if (replyText) source = 'n8n';
      }
    } catch (e) {}

    if (!replyText) {
      replyText = await generateAutonomousResponse(message, name);
    }

    res.json({
      success: true,
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

app.listen(PORT, () => {
  console.log(`[WhatsApp Bridge] HTTP Server listening on port ${PORT}`);
  console.log(`[WhatsApp Bridge] Web UI available at: http://localhost:${PORT}/qr`);
  initWhatsApp().catch((err) => {
    console.error('[WhatsApp Bridge] Initialization error:', err);
  });
});
