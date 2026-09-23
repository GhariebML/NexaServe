import json

# 1. Update 03_ai_intent_engine.json
with open('infra/n8n/workflows/03_ai_intent_engine.json', 'r', encoding='utf-8') as f:
    wf03 = json.load(f)

for node in wf03['nodes']:
    if node.get('name') == 'Build Prompt Payload':
        js = node['parameters']['jsCode']
        target = "'exam', 'eligible', 'document', 'fee', 'cost', 'eligib'"
        replacement = "'exam', 'eligible', 'document', 'fee', 'cost', 'eligib', 'debi', 'digilians', 'رواد', 'بناة', 'فرق', 'مقارنة', 'مقارنه'"
        if target in js:
            node['parameters']['jsCode'] = js.replace(target, replacement)
            print("Successfully updated 03_ai_intent_engine.json with DEBI & Digilians keywords!")

with open('infra/n8n/workflows/03_ai_intent_engine.json', 'w', encoding='utf-8') as f:
    json.dump(wf03, f, indent=2, ensure_ascii=False)

# 2. Update 01_gateway_dispatcher.json
with open('infra/n8n/workflows/01_gateway_dispatcher.json', 'r', encoding='utf-8') as f:
    wf01 = json.load(f)

for node in wf01['nodes']:
    if node.get('name') == 'General Support Handler':
        js = node['parameters']['jsCode']
        old_wel_ar = "أهلاً وسهلاً في منصة خدمة عملاء مبادرة الرواد الرقميون (DEPI)"
        new_wel_ar = "أهلاً وسهلاً بك في منصة خدمة العملاء الذكية لمبادرات وزارة الاتصالات وتكنولوجيا المعلومات (MCIT): مبادرة الرواد الرقميون (Digilians) ومبادرة رواد مصر الرقمية (DEBI)"
        if old_wel_ar in js:
            node['parameters']['jsCode'] = js.replace(old_wel_ar, new_wel_ar)
            print("Successfully updated General Support Handler welcome message in 01!")

with open('infra/n8n/workflows/01_gateway_dispatcher.json', 'w', encoding='utf-8') as f:
    json.dump(wf01, f, indent=2, ensure_ascii=False)

print("Workflow files updated.")
