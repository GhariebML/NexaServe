# -*- coding: utf-8 -*-
"""
Script to apply speed optimizations, prompt slimming, and Egyptian PII masking
to n8n workflows, and update the n8n database directly.
"""
import json
import re
import subprocess

print("Applying speed and DEPI optimizations...")

# 1. Update 03_ai_intent_engine.json
path_03 = "infra/n8n/workflows/03_ai_intent_engine.json"
with open(path_03, "r", encoding="utf-8") as f:
    wf_03 = json.load(f)

new_js_code_03 = """const item = $input.first()?.json || {};
const customerMsg = item.sanitized_message || item.customer_message || 'مرحبا';
const locale = item.locale || (customerMsg.match(/[\\u0600-\\u06FF]/) ? 'ar' : 'en');

if (!item.guardrail_safe) {
  const deflection = locale === 'ar'
    ? 'عذراً، لا يمكن معالجة هذا الطلب وفقاً لمعايير الأمان المعتمدة.'
    : 'Sorry, this request cannot be processed according to enterprise security policies.';
    
  return [{\\n    json: {\\n      direct_bypass: true,\\n      ai_output: {\\n        intent: 'general_support',\\n        confidence: 0.99,\\n        entities: {},\\n        sentiment: 'neutral',\\n        requires_human: false,\\n        direct_response: deflection\\n      },\\n      ...item\\n    }\\n  }];
}

const history = (item.conversation_history || []).slice(-3).map(h => `${h.sender_type}: ${h.content}`).join('\\n');

const promptText = `أنت محرك تصنيف النوايا (Intent Classifier) الرسمي لمنصة خدمة عملاء "مبادرة الرواد الرقميون" (DEPI).
مهمتك تحليل رسالة العميل وتصنيفها واستخراج الكيانات بدقة وفق القواعد التالية:

قواعد التصنيف:
1. "faq_query": أي سؤال أو استفسار عن مبادرة الرواد الرقميون (DEPI)، شروط التقديم، السن، المؤهلات، المسارات والتخصصات، مواعيد وطريقة التسجيل، الامتحانات وبرنامج SEB، نظام الدراسة والإقامة، الشهادات والمنح، المزايا والجوائز، أو الانسحاب والدعم.
2. "order_lookup": إذا كان العميل يستعلم عن حالة طلب أو معاملة أو شحنة أو رقم تتبع (مثل: SRV-1001، ORD-1001، رقم طلبي، تتبع). استخرج رقم الطلب في entities.order_number.
3. "human_escalation": إذا كان العميل غاضباً، يشتكي من الخدمة، أو يطلب التحدث صراحة مع موظف بشري أو مشرف (مثل: خدمة سيئة، أريد موظف، كلمني حد، شكوى). واجعل requires_human: true.
4. "general_support": التحيات، الشكر، أو المجاملات (مثل: السلام عليكم، مرحبا، شكراً، صباح الخير). واكتب تحية ترحيبية ودودة تعرف بالمبادرة في direct_response.

يجب أن يكون الرد بصيغة كائن JSON صالح فقط بدون أي وسوم:
{
  "intent": "faq_query" | "order_lookup" | "general_support" | "human_escalation",
  "confidence": 0.95,
  "entities": {},
  "sentiment": "positive" | "neutral" | "frustrated",
  "requires_human": false,
  "direct_response": ""
}

${history ? 'سياق المحادثة السابقة:\\n' + history + '\\n' : ''}
رسالة العميل الحالية: ${JSON.stringify(customerMsg)}`;

return [{\\n  json: {\\n    ollama_body: {\\n      model: 'qwen2.5:1.5b',\\n      prompt: promptText,\\n      stream: false,\\n      format: 'json',\\n      options: {\\n        num_ctx: 1024,\\n        num_predict: 150,\\n        temperature: 0.1,\\n        top_p: 0.9\\n      }\\n    },\\n    direct_bypass: false,\\n    customer_message: customerMsg,\\n    customer: item.customer,\\n    conversation: item.conversation,\\n    channel: item.channel,\\n    channel_user_id: item.channel_user_id,\\n    locale: locale\\n  }\\n}];"""

for node in wf_03["nodes"]:
    if node["id"] == "node-build-payload":
        node["parameters"]["jsCode"] = new_js_code_03
    elif node["id"] == "node-ollama":
        node["parameters"]["options"] = {"timeout": 45000}

with open(path_03, "w", encoding="utf-8") as f:
    json.dump(wf_03, f, indent=2, ensure_ascii=False)
print("Updated 03_ai_intent_engine.json")

# 2. Update 04B_knowledge_base_faq.json
path_04b = "infra/n8n/workflows/04B_knowledge_base_faq.json"
with open(path_04b, "r", encoding="utf-8") as f:
    wf_04b = json.load(f)

for node in wf_04b["nodes"]:
    if node["id"] == "node-qwen-rag":
        node["parameters"]["options"] = {"timeout": 60000}
        node["parameters"]["jsonBody"] = """={{ JSON.stringify({
  model: 'qwen2.5:1.5b',
  prompt: `أنت المساعد الذكي الرسمي لمنصة خدمة العملاء التابعة لمبادرة الرواد الرقميون (DEPI).

قواعد الرد الصارمة (يجب الالتزام بها حرفياً):
1. أجب حصراً وفقط من المعلومات المتوفرة في السياق المرفق أدناه. لا تختلق أي معلومة غير واردة في السياق.
2. صِغ الإجابة بأسلوب خدمة عملاء احترافي ومهذب ومنظم باللغة العربية الفصحى.
3. إذا كان السياق لا يحتوي على إجابة مناسبة لسؤال العميل أو كان فارغاً، أجب حصراً بالنص التالي:
   "عذراً، هذا الاستفسار خارج نطاق خدماتنا المعتمدة حالياً. يسعدني مساعدتك في الاستفسار عن: مبادرة الرواد الرقميون (DEPI)، شروط التقديم، أو نظام الدراسة والامتحانات. يمكنك أيضاً طلب التحدث مع ممثل خدمة العملاء."
4. لا تضف أي معلومات إضافية من خارج السياق. لا تخمّن. لا تؤلف.
5. استخدم نقاطاً ورموزاً توضيحية (📌، 📋، ⏱️) لتنسيق الرد بشكل واضح ومناسب لتطبيق الواتساب.

السياق المعتمد:
${$json.rag_context || 'لا يوجد سياق متاح'}

سؤال العميل: ${$json.customer_message}`,
  stream: false,
  options: {
    num_ctx: 2048,
    num_predict: 250,
    temperature: 0.1,
    top_p: 0.9
  }
}) }}"""

with open(path_04b, "w", encoding="utf-8") as f:
    json.dump(wf_04b, f, indent=2, ensure_ascii=False)
print("Updated 04B_knowledge_base_faq.json")

# 3. Update 01_gateway_dispatcher.json (PII regex for Egyptian National ID)
path_01 = "infra/n8n/workflows/01_gateway_dispatcher.json"
with open(path_01, "r", encoding="utf-8") as f:
    wf_01 = json.load(f)

for node in wf_01["nodes"]:
    if node["id"] == "node-normalize-ingress":
        code = node["parameters"]["jsCode"]
        old_pii = """// Saudi National ID (10 digits starting with 1 or 2)
if (/\\b[12]\\d{9}\\b/.test(sanitizedMessage)) {
  sanitizedMessage = sanitizedMessage.replace(/\\b[12]\\d{9}\\b/g, '[NATIONAL_ID_MASKED]');
  piiDetected = true;
}"""
        new_pii = """// Saudi National ID (10 digits starting with 1 or 2) & Egyptian National ID (14 digits starting with 2 or 3)
if (/\\b[12]\\d{9}\\b/.test(sanitizedMessage) || /\\b[23]\\d{13}\\b/.test(sanitizedMessage)) {
  sanitizedMessage = sanitizedMessage.replace(/\\b[12]\\d{9}\\b/g, '[NATIONAL_ID_MASKED]').replace(/\\b[23]\\d{13}\\b/g, '[NATIONAL_ID_MASKED]');
  piiDetected = true;
}"""
        if old_pii in code:
            node["parameters"]["jsCode"] = code.replace(old_pii, new_pii)
            print("Added Egyptian National ID masking to 01_gateway_dispatcher.json")

with open(path_01, "w", encoding="utf-8") as f:
    json.dump(wf_01, f, indent=2, ensure_ascii=False)

# 4. Push updated workflows directly into n8n database
print("Updating workflows in n8n database...")

def update_workflow_in_db(wf_id, file_path):
    with open(file_path, "r", encoding="utf-8") as f:
        wf_data = json.load(f)
    nodes_json = json.dumps(wf_data.get("nodes", []), ensure_ascii=False)
    connections_json = json.dumps(wf_data.get("connections", {}), ensure_ascii=False)
    settings_json = json.dumps(wf_data.get("settings", {}), ensure_ascii=False)
    
    # Write to a temporary sql file or run psql via python
    # We can write a small script that connects to cs-postgres and executes the update
    import tempfile
    with tempfile.NamedTemporaryFile("w", suffix=".sql", encoding="utf-8", delete=False) as tmp:
        tmp.write("UPDATE workflow_entity SET nodes = $json$" + nodes_json + "$json$, connections = $json$" + connections_json + "$json$, settings = $json$" + settings_json + "$json$, \"updatedAt\" = NOW() WHERE id = '" + wf_id + "';\\n")
        tmp_name = tmp.name
        
    subprocess.run(["docker", "cp", tmp_name, "cs-postgres:/tmp/update_wf.sql"], check=True)
    subprocess.run(["docker", "exec", "cs-postgres", "psql", "-U", "postgres", "-d", "n8n", "-f", "/tmp/update_wf.sql"], check=True)
    print(f"Successfully updated workflow {wf_id} in database!")

update_workflow_in_db("CSWF000000000001", path_01)
update_workflow_in_db("CSWF000000000003", path_03)
update_workflow_in_db("CSWF000000000005", path_04b)

print("ALL WORKFLOWS OPTIMIZED AND LIVE IN N8N!")
