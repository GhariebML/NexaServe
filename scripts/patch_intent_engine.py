import json

workflow_path = "infra/n8n/workflows/03_ai_intent_engine.json"
with open(workflow_path, "r", encoding="utf-8") as f:
    data = json.load(f)

for node in data.get("nodes", []):
    if node.get("name") == "Build Prompt Payload":
        code = node["parameters"]["jsCode"]
        old_kw = "'exam', 'eligible', 'document', 'fee', 'cost', 'eligib', 'debi', 'digilians', 'رواد', 'بناة', 'فرق', 'مقارنة', 'مقارنه'"
        new_kw = "'exam', 'eligible', 'document', 'fee', 'cost', 'eligib', 'debi', 'digilians', 'رواد', 'بناة', 'فرق', 'مقارنة', 'مقارنه', 'initiative', 'initiatives', 'pioneers', 'pioneer', 'depi', 'builders', 'builder'"
        if old_kw in code:
            node["parameters"]["jsCode"] = code.replace(old_kw, new_kw)
            print("[OK] Updated Build Prompt Payload")
        else:
            print("[WARN] old_kw not found in Build Prompt Payload")
            
    elif node.get("name") == "Parse & Validate AI Schema":
        code = node["parameters"]["jsCode"]
        old_is_faq = "originalMsg.includes('depi')"
        new_is_faq = "originalMsg.includes('depi') || originalMsg.includes('initiative') || originalMsg.includes('initiatives') || originalMsg.includes('pioneers') || originalMsg.includes('pioneer') || originalMsg.includes('builders') || originalMsg.includes('builder')"
        if old_is_faq in code:
            node["parameters"]["jsCode"] = code.replace(old_is_faq, new_is_faq)
            print("[OK] Updated Parse & Validate AI Schema")
        else:
            print("[WARN] old_is_faq not found in Parse & Validate AI Schema")

with open(workflow_path, "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("[SUCCESS] Patched 03_ai_intent_engine.json")
