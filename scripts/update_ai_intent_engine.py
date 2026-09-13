import json

path = 'infra/n8n/workflows/03_ai_intent_engine.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

# Read the FAQ
with open('data/depi_faq.txt', 'r', encoding='utf-8') as f:
    faq_text = f.read()

# Make it safe for JavaScript template string
safe_faq = faq_text.replace('`', "'").replace('${', '\\${')

for node in data.get('nodes', []):
    if node.get('id') == 'node-build-payload':
        node['parameters']['jsCode'] = f"""const item = $input.first()?.json || {{}};
const customerMsg = item.sanitized_message || item.customer_message || 'مرحبا';
const locale = item.locale || (customerMsg.match(/[\\u0600-\\u06FF]/) ? 'ar' : 'en');

if (!item.guardrail_safe) {{
  const deflection = locale === 'ar'
    ? 'عذراً، لا يمكن معالجة هذا الطلب وفقاً لمعايير الأمان المعتمدة.'
    : 'Sorry, this request cannot be processed according to enterprise security policies.';
    
  return [{{
    json: {{
      direct_bypass: true,
      ai_output: {{
        intent: 'general_support',
        confidence: 0.99,
        entities: {{}},
        sentiment: 'neutral',
        requires_human: false,
        direct_response: deflection
      }},
      ...item
    }}
  }}];
}}

const history = (item.conversation_history || []).slice(-3).map(h => `${{h.sender_type}}: ${{h.content}}`).join('\\n');

const promptText = `أنت المساعد الذكي الرسمي لخدمة عملاء "مبادرة الرواد الرقميون" (DEPI).
مهمتك الرد على استفسارات الطلاب بأسلوب احترافي وودود ودقيق جداً بناءً على المعلومات التالية فقط (FAQ):

=========================
{safe_faq}
=========================

تعليمات الرد الصارمة:
1. اقرأ سؤال العميل بعناية، ثم استخرج الإجابة من المعلومات السابقة، وقم بصياغتها بشكل منسق ومريح للعين باستخدام نقاط ورموز تعبيرية (Emojis).
2. لا تخترع أي معلومات غير موجودة في النص. إذا سأل عن شيء غير مذكور، قل: "لم يتم تحديد هذه المعلومة رسمياً، يرجى التواصل مع info@digilians.gov.eg للمساعدة."
3. إذا كان العميل غاضباً أو يطلب التحدث لإنسان، اجعل requires_human: true وصنف النية 'human_escalation'.
4. إذا كانت مجرد تحية (السلام عليكم، مرحبا)، رد بتحية ترحيبية مهذبة وعرفه بنفسك والخدمات المتاحة، وضع النية 'general_support'.
5. إذا كان السؤال عن أي من الشروط أو المبادرة، ضع النية 'general_support' واكتب الإجابة المفصلة في 'direct_response'.

يجب أن يكون ردك بصيغة كائن JSON حصراً، بدون أي نصوص أو markdown قبله أو بعده:
{{
  "intent": "general_support" | "human_escalation",
  "confidence": 0.95,
  "entities": {{}},
  "sentiment": "positive" | "neutral" | "frustrated",
  "requires_human": false,
  "direct_response": "إجابتك الاحترافية والواقعية هنا باللغة المناسبة"
}}

${{history ? 'سياق المحادثة السابقة:\\n' + history + '\\n' : ''}}
رسالة العميل الحالية: ${{JSON.stringify(customerMsg)}}`;

return [{{
  json: {{
    ollama_body: {{
      model: 'qwen2.5:3b',
      prompt: promptText,
      stream: false,
      format: 'json',
      options: {{
        num_ctx: 8192,
        num_predict: 800,
        temperature: 0.2,
        top_p: 0.9,
        top_k: 40
      }}
    }},
    direct_bypass: false,
    customer_message: customerMsg,
    customer: item.customer,
    conversation: item.conversation,
    channel: item.channel,
    channel_user_id: item.channel_user_id,
    locale: locale
  }}
}}];"""

with open(path, 'w', encoding='utf-8') as f:
    json.dump(data, f, indent=2, ensure_ascii=False)

print('Updated 03_ai_intent_engine.json with Qwen 2.5 3B LLM!')
