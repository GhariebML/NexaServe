import json

# === Update 04B: Knowledge Base with Smart Search + Qwen RAG Grounding ===
path_04b = 'infra/n8n/workflows/04B_knowledge_base_faq.json'
with open(path_04b, 'r', encoding='utf-8') as f:
    data_04b = json.load(f)

for node in data_04b.get('nodes', []):
    if node.get('id') == 'node-query-kb':
        node['parameters']['operation'] = 'executeQuery'
        node['parameters']['query'] = """=WITH words AS (
  SELECT lower(w) AS word
  FROM unnest(string_to_array('{{ ($json.customer_message || '').replace(/'/g, "''") }}', ' ')) w
  WHERE length(w) > 2
)
SELECT id, category, question, answer, question_ar, answer_ar,
  (SELECT count(*) FROM words WHERE question_ar ILIKE '%' || word || '%' OR answer_ar ILIKE '%' || word || '%' OR question ILIKE '%' || word || '%' OR answer ILIKE '%' || word || '%' OR EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%')) AS relevance_score
FROM knowledge_base
WHERE is_active = TRUE
ORDER BY relevance_score DESC, id ASC
LIMIT 3;"""

    elif node.get('id') == 'node-format-rag':
        node['parameters']['jsCode'] = """const results = ($input.first()?.json || []);
const rows = Array.isArray(results) ? results : (results.results || [results]);
const triggerData = $('Execute Workflow Trigger').first()?.json || {};
const locale = triggerData.locale || 'ar';
const isAr = locale === 'ar';
const customerMsg = triggerData.customer_message || triggerData.sanitized_message || '';

// Filter results with relevance > 0
const relevant = rows.filter(r => r && r.relevance_score > 0);

if (relevant.length > 0) {
  // Build context from top matching FAQ entries
  const contextParts = relevant.map(kb => {
    const q = isAr ? (kb.question_ar || kb.question) : (kb.question || kb.question_ar);
    const a = isAr ? (kb.answer_ar || kb.answer) : (kb.answer || kb.answer_ar);
    return `سؤال: ${q}\\nإجابة: ${a}`;
  });
  const context = contextParts.join('\\n---\\n');

  return [{
    json: {
      status: 'rag_context_found',
      intent_handled: 'faq_query',
      rag_context: context,
      customer_message: customerMsg,
      locale: locale,
      top_category: relevant[0].category,
      relevance_score: relevant[0].relevance_score
    }
  }];
} else {
  // No relevant FAQ found - will trigger guardrail
  return [{
    json: {
      status: 'no_context',
      intent_handled: 'faq_query',
      rag_context: '',
      customer_message: customerMsg,
      locale: locale,
      relevance_score: 0
    }
  }];
}"""

# Add Qwen RAG Grounding node and Guardrail Formatter node
qwen_rag_node = {
    "parameters": {
        "method": "POST",
        "url": "http://host.docker.internal:11434/api/generate",
        "sendBody": True,
        "specifyBody": "json",
        "jsonBody": """={{ JSON.stringify({
  model: 'qwen2.5:3b',
  prompt: `أنت المساعد الذكي الرسمي لمنصة خدمة العملاء التابعة لوزارة الاتصالات وتقنية المعلومات.

قواعد الرد الصارمة (يجب الالتزام بها حرفياً):
1. أجب حصراً وفقط من المعلومات المتوفرة في السياق المرفق أدناه. لا تختلق أي معلومة غير واردة في السياق.
2. صِغ الإجابة بأسلوب خدمة عملاء احترافي ومهذب ومنظم باللغة العربية الفصحى.
3. إذا كان السياق لا يحتوي على إجابة مناسبة لسؤال العميل أو كان فارغاً، أجب حصراً بالنص التالي:
   "عذراً، هذا الاستفسار خارج نطاق خدماتنا المعتمدة حالياً. يسعدني مساعدتك في الاستفسار عن: مبادرة مهارات المستقبل، التوقيع الرقمي، تتبع الطلبات، شكاوى الاتصالات، أو ساعات العمل. يمكنك أيضاً طلب التحدث مع ممثل خدمة العملاء."
4. لا تضف أي معلومات إضافية من خارج السياق. لا تخمّن. لا تؤلف.
5. استخدم نقاطاً ورموزاً توضيحية (📌، 📋، ⏱️) لتنسيق الرد بشكل واضح ومناسب لتطبيق الواتساب.

السياق المعتمد:
${$json.rag_context || 'لا يوجد سياق متاح'}

سؤال العميل: ${$json.customer_message}`,
  stream: false,
  options: {
    num_ctx: 3072,
    num_predict: 400,
    temperature: 0.1,
    top_p: 0.9
  }
}) }}""",
        "options": {
            "timeout": 25000
        }
    },
    "onError": "continueRegularOutput",
    "id": "node-qwen-rag",
    "name": "Qwen RAG Grounded Response",
    "type": "n8n-nodes-base.httpRequest",
    "typeVersion": 4.2,
    "position": [820, 300]
}

guardrail_formatter_node = {
    "parameters": {
        "jsCode": """const ragData = $('Format RAG Knowledge Response').first()?.json || {};
const qwenOutput = $input.first()?.json || {};
const locale = ragData.locale || 'ar';
const isAr = locale === 'ar';

let finalReply = '';

if (ragData.status === 'no_context' || ragData.relevance_score === 0) {
  // Hard guardrail: no relevant FAQ found
  finalReply = isAr
    ? 'عذراً، هذا الاستفسار خارج نطاق خدماتنا المعتمدة حالياً.\\n\\nيسعدني مساعدتك في الاستفسار عن:\\n📌 مبادرة مهارات المستقبل\\n🔐 التوقيع الرقمي والتوكن المشفر\\n📦 تتبع الطلبات والمعاملات\\n📡 شكاوى الاتصالات والفواتير\\n⏱️ ساعات العمل والدعم الفني\\n\\nأو يمكنك طلب التحدث مع ممثل خدمة العملاء.'
    : 'Sorry, this inquiry is outside our current service scope.\\n\\nI can help you with:\\n📌 Future Skills Initiative\\n🔐 Digital Signature & Token\\n📦 Order & Shipment Tracking\\n📡 Telecom Complaints\\n⏱️ Working Hours & SLA\\n\\nOr you may request to speak with a human specialist.';
} else {
  // Use Qwen's grounded response
  finalReply = qwenOutput.response || ragData.rag_context || '';
  
  // Clean up any markdown artifacts that don't render well in WhatsApp
  finalReply = finalReply.replace(/\\*\\*/g, '*').replace(/^#+\\s*/gm, '').trim();
}

return [{
  json: {
    status: ragData.status === 'no_context' ? 'out_of_scope' : 'success',
    intent_handled: 'faq_query',
    category: ragData.top_category || 'general',
    reply: finalReply,
    sources: ragData.status === 'no_context' ? ['Guardrail: Out of Scope'] : ['MCIT Official Knowledge Base - ' + (ragData.top_category || 'General')]
  }
}];"""
    },
    "id": "node-guardrail-formatter",
    "name": "Guardrail & Professional Formatter",
    "type": "n8n-nodes-base.code",
    "typeVersion": 2,
    "position": [1040, 300]
}

# Replace nodes list
data_04b['nodes'] = [n for n in data_04b['nodes'] if n['id'] not in ('node-qwen-rag', 'node-guardrail-formatter')]
data_04b['nodes'].append(qwen_rag_node)
data_04b['nodes'].append(guardrail_formatter_node)

# Update connections
data_04b['connections'] = {
    "Execute Workflow Trigger": {
        "main": [[{"node": "Query Bilingual Knowledge Base", "type": "main", "index": 0}]]
    },
    "Query Bilingual Knowledge Base": {
        "main": [[{"node": "Format RAG Knowledge Response", "type": "main", "index": 0}]]
    },
    "Format RAG Knowledge Response": {
        "main": [[{"node": "Qwen RAG Grounded Response", "type": "main", "index": 0}]]
    },
    "Qwen RAG Grounded Response": {
        "main": [[{"node": "Guardrail & Professional Formatter", "type": "main", "index": 0}]]
    }
}

with open(path_04b, 'w', encoding='utf-8') as f:
    json.dump(data_04b, f, indent=2, ensure_ascii=False)
print('[Done] Updated 04B_knowledge_base_faq.json with Qwen RAG + Guardrails!')

# === Update 01: Gateway Dispatcher - Professional Welcome Message ===
path_01 = 'infra/n8n/workflows/01_gateway_dispatcher.json'
with open(path_01, 'r', encoding='utf-8') as f:
    data_01 = json.load(f)

for node in data_01.get('nodes', []):
    if node.get('id') == 'node-route-general':
        node['parameters']['jsCode'] = """const ai = $('Call SubWF 03 - AI Intent Engine').first()?.json.ai_output || {};
const norm = $('Channel Ingress & PII Sanitizer').first()?.json || {};
const isAr = norm.locale === 'ar';
const customerName = norm.full_name || '';

const welcomeAr = `أهلاً وسهلاً بك${customerName ? ' ' + customerName : ''} في منصة خدمة العملاء الذكية لوزارة الاتصالات وتقنية المعلومات! 🏛️

يسعدني مساعدتك. يمكنك الاستفسار عن أي من خدماتنا التالية:

📌 *مبادرة مهارات المستقبل* - برامج تدريبية وشهادات احترافية
🔐 *التوقيع الرقمي والتوكن* - إصدار وتفعيل الهوية الرقمية
📦 *تتبع الطلبات والمعاملات* - استعلام فوري بالرقم المرجعي
📡 *شكاوى الاتصالات* - تقديم ومتابعة الشكاوى الرسمية
⏱️ *ساعات العمل والدعم الفني* - مواعيد الخدمة واتفاقيات SLA
🛡️ *حماية البيانات الشخصية* - سياسات الخصوصية والأمان

ما الذي تودّ الاستفسار عنه؟`;

const welcomeEn = `Welcome${customerName ? ' ' + customerName : ''} to the MCIT AI Customer Service Platform! 🏛️

I'm here to help. You can inquire about any of our services:

📌 *Future Skills Initiative* - Training & Professional Certifications
🔐 *Digital Signature & Token* - National Digital Identity Issuance
📦 *Order & Shipment Tracking* - Real-time Status by Reference Number
📡 *Telecom Complaints* - File & Track Service Provider Disputes
⏱️ *Working Hours & SLA* - Support Availability & Response Times
🛡️ *Data Privacy & Protection* - PDPL Compliance & Security

What would you like to know more about?`;

return [{
  json: {
    status: 'general',
    intent_handled: 'general_support',
    reply: isAr ? welcomeAr : welcomeEn
  }
}];"""

with open(path_01, 'w', encoding='utf-8') as f:
    json.dump(data_01, f, indent=2, ensure_ascii=False)
print('[Done] Updated 01_gateway_dispatcher.json with professional welcome!')

# === Update 06: Output Channel Dispatcher - Clean WhatsApp Formatting ===
path_06 = 'infra/n8n/workflows/06_output_channel_dispatcher.json'
with open(path_06, 'r', encoding='utf-8') as f:
    data_06 = json.load(f)

for node in data_06.get('nodes', []):
    if node.get('id') == 'node-format-whatsapp':
        node['parameters']['jsCode'] = """const item = $input.first()?.json || {};
const recipient = item.phone_number || item.channel_user_id || item.customer?.phone_number || '+966501234567';
const text = item.reply || item.final_reply || item.message || '';

// Clean for WhatsApp: remove HTML, excessive newlines, fix markdown
let cleanText = text
  .replace(/<[^>]*>/g, '')
  .replace(/\\n{3,}/g, '\\n\\n')
  .replace(/\\*\\*/g, '*')
  .trim();

return [{
  json: {
    channel: 'whatsapp',
    recipient: recipient,
    dispatched: true,
    meta_payload: {
      messaging_product: 'whatsapp',
      recipient_type: 'individual',
      to: recipient.replace(/[^0-9]/g, ''),
      type: 'text',
      text: { body: cleanText }
    },
    message: cleanText,
    timestamp: new Date().toISOString()
  }
}];"""

with open(path_06, 'w', encoding='utf-8') as f:
    json.dump(data_06, f, indent=2, ensure_ascii=False)
print('[Done] Updated 06_output_channel_dispatcher.json with WhatsApp formatting!')
