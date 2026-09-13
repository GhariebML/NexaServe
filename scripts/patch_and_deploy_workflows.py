# -*- coding: utf-8 -*-
"""
Script to patch workflow files to use stable qwen2.5:1.5b (preventing WSL OOM kills)
and properly configure DEPI FAQ routing and heuristics.
Then imports and publishes them in n8n.
"""
import json
import re
import subprocess

# -------------------------------------------------------------
# 1. Update 03_ai_intent_engine.json
# -------------------------------------------------------------
path_03 = "infra/n8n/workflows/03_ai_intent_engine.json"
with open(path_03, "r", encoding="utf-8") as f:
    data_03 = json.load(f)

for node in data_03.get("nodes", []):
    if node.get("id") == "node-build-payload":
        code = node["parameters"]["jsCode"]
        # Replace model and options
        code = code.replace("model: 'qwen2.5:3b'", "model: 'qwen2.5:1.5b'")
        code = code.replace("num_ctx: 8192", "num_ctx: 2048")
        code = code.replace("num_predict: 800", "num_predict: 350")
        
        # Improve prompt instructions for intent classification
        old_instruction = """تعليمات الرد الصارمة:
1. اقرأ سؤال العميل بعناية، ثم استخرج الإجابة من المعلومات السابقة، وقم بصياغتها بشكل منسق ومريح للعين باستخدام نقاط ورموز تعبيرية (Emojis).
2. لا تخترع أي معلومات غير موجودة في النص. إذا سأل عن شيء غير مذكور، قل: "لم يتم تحديد هذه المعلومة رسمياً، يرجى التواصل مع info@digilians.gov.eg للمساعدة."
3. إذا كان العميل غاضباً أو يطلب التحدث لإنسان، اجعل requires_human: true وصنف النية 'human_escalation'.
4. إذا كانت مجرد تحية (السلام عليكم، مرحبا)، رد بتحية ترحيبية مهذبة وعرفه بنفسك والخدمات المتاحة، وضع النية 'general_support'.
5. إذا كان السؤال عن أي من الشروط أو المبادرة، ضع النية 'general_support' واكتب الإجابة المفصلة في 'direct_response'.

يجب أن يكون ردك بصيغة كائن JSON حصراً، بدون أي نصوص أو markdown قبله أو بعده:
{
  "intent": "general_support" | "human_escalation",
  "confidence": 0.95,
  "entities": {},
  "sentiment": "positive" | "neutral" | "frustrated",
  "requires_human": false,
  "direct_response": "إجابتك الاحترافية والواقعية هنا باللغة المناسبة"
}"""
        new_instruction = """قواعد التصنيف الصارمة (Intent Classification):
1. إذا كانت الرسالة مجرد تحية أو شكر (مثل: السلام عليكم، مرحبا، صباح الخير، شكراً):
   - intent: "general_support"
   - direct_response: ترحيب مهذب ومختصر يعرف بمبادرة الرواد الرقميون والخدمات المتاحة.
2. إذا كان السؤال استفساراً عن المبادرة (الشروط، المؤهلات، السن، المسارات، التخصصات، التسجيل، الامتحانات، SEB، الشهادات، الإقامة، المزايا):
   - intent: "faq_query"
   - direct_response: ملخص دقيق ومباشر للإجابة من المعلومات المذكورة أعلاه.
3. إذا كان السؤال يتضمن رقم طلب أو استعلام عن معاملة (مثل: SRV-1001، ORD-1001، رقم طلبي، تتبع):
   - intent: "order_lookup"
   - entities: {"order_number": "رقم الطلب المستخرج"}
4. إذا كان العميل غاضباً أو يشتكي أو يطلب التحدث لموظف بشري (مثل: خدمة سيئة، أريد موظف، كلمني حد):
   - intent: "human_escalation"
   - requires_human: true

يجب أن يكون الرد بصيغة كائن JSON صالح فقط بدون أي علامات markdown:
{
  "intent": "faq_query" | "order_lookup" | "general_support" | "human_escalation",
  "confidence": 0.95,
  "entities": {},
  "sentiment": "positive" | "neutral" | "frustrated",
  "requires_human": false,
  "direct_response": "نص الإجابة باللغة المناسبة"
}"""
        if old_instruction in code:
            code = code.replace(old_instruction, new_instruction)
        node["parameters"]["jsCode"] = code

    elif node.get("id") == "node-parse-ai":
        code = node["parameters"]["jsCode"]
        # Update heuristic keyword matching
        old_heuristic = "const isFaq = originalMsg.includes('skill') || originalMsg.includes('policy') || originalMsg.includes('hours') || originalMsg.includes('مهارات') || originalMsg.includes('ساعات') || originalMsg.includes('شروط') || originalMsg.includes('تقديم') || originalMsg.includes('خدمات') || originalMsg.includes('الخدمات') || originalMsg.includes('توقيع');"
        new_heuristic = "const isFaq = originalMsg.includes('skill') || originalMsg.includes('policy') || originalMsg.includes('hours') || originalMsg.includes('مهارات') || originalMsg.includes('ساعات') || originalMsg.includes('شروط') || originalMsg.includes('تقديم') || originalMsg.includes('خدمات') || originalMsg.includes('الخدمات') || originalMsg.includes('توقيع') || originalMsg.includes('رواد') || originalMsg.includes('رقميون') || originalMsg.includes('depi') || originalMsg.includes('مسار') || originalMsg.includes('تخصص') || originalMsg.includes('تسجيل') || originalMsg.includes('امتحان') || originalMsg.includes('seb') || originalMsg.includes('شهادة') || originalMsg.includes('اقامة') || originalMsg.includes('مزايا') || originalMsg.includes('منحة');"
        if old_heuristic in code:
            code = code.replace(old_heuristic, new_heuristic)
        node["parameters"]["jsCode"] = code

with open(path_03, "w", encoding="utf-8") as f:
    json.dump(data_03, f, indent=2, ensure_ascii=False)
print("[OK] Updated 03_ai_intent_engine.json with qwen2.5:1.5b and DEPI intent routing")

# -------------------------------------------------------------
# 2. Update 04B_knowledge_base_faq.json
# -------------------------------------------------------------
path_04b = "infra/n8n/workflows/04B_knowledge_base_faq.json"
with open(path_04b, "r", encoding="utf-8") as f:
    data_04b = json.load(f)

for node in data_04b.get("nodes", []):
    if node.get("id") == "node-qwen-rag":
        json_body = node["parameters"]["jsonBody"]
        json_body = json_body.replace("model: 'qwen2.5:3b'", "model: 'qwen2.5:1.5b'")
        json_body = json_body.replace("num_ctx: 3072", "num_ctx: 2048")
        json_body = json_body.replace("num_predict: 400", "num_predict: 300")
        node["parameters"]["jsonBody"] = json_body

with open(path_04b, "w", encoding="utf-8") as f:
    json.dump(data_04b, f, indent=2, ensure_ascii=False)
print("[OK] Updated 04B_knowledge_base_faq.json with qwen2.5:1.5b")

# -------------------------------------------------------------
# 3. Deploy and Import into n8n Container
# -------------------------------------------------------------
import glob
import os

project_dir = "e:/NexaServe"
workflows = glob.glob("infra/n8n/workflows/*.json")

# Get project ID
res = subprocess.run(["docker", "exec", "cs-postgres", "psql", "-U", "postgres", "-d", "n8n", "-t", "-c", "SELECT id FROM project LIMIT 1;"], capture_output=True, text=True)
project_id = res.stdout.strip()
print(f"n8n Project ID: {project_id}")

for wf_path in workflows:
    fname = os.path.basename(wf_path)
    container_dest = f"/tmp/{fname}"
    # copy into container
    subprocess.run(["docker", "cp", wf_path, f"cs-n8n:{container_dest}"], check=True)
    # import
    cmd = ["docker", "exec", "cs-n8n", "n8n", "import:workflow", f"--input={container_dest}"]
    if project_id:
        cmd.append(f"--projectId={project_id}")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  [Imported] {fname}")
    else:
        print(f"  [Error] {fname}: {res.stderr.strip()}")

# Publish all workflows
all_cswfs = [
    "CSWF000000000001",
    "CSWF000000000002",
    "CSWF000000000003",
    "CSWF000000000004",
    "CSWF000000000005",
    "CSWF000000000006",
    "CSWF000000000007",
    "CSWF000000000008",
]

for wf in all_cswfs:
    res = subprocess.run(["docker", "exec", "cs-n8n", "n8n", "publish:workflow", f"--id={wf}"], capture_output=True, text=True)
    if res.returncode == 0:
        print(f"  [Published] {wf}")
    else:
        print(f"  [Publish Warn] {wf}: {res.stderr.strip()}")

print("[DONE] Workflows updated and published!")
