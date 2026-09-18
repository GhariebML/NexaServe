import json
import os

def ensure_utf8(filepath):
    with open(filepath, 'rb') as f:
        data = f.read()
    try:
        data.decode('utf-8')
        return True
    except UnicodeDecodeError:
        data = data.decode('cp1252', errors='replace').encode('utf-8')
        with open(filepath, 'wb') as f:
            f.write(data)
        return True

# Fix CSAT survey file encoding
csat_path = 'infra/n8n/workflows/08_csat_survey.json'
ensure_utf8(csat_path)
with open(csat_path, 'r', encoding='utf-8') as f:
    csat = json.load(f)
print(f"CSAT: {csat['id']} - {csat['name']} - OK")

# Validate all new workflows
for wf in ['07_analytics_reporting.json', '08_csat_survey.json', '09_automation_rules.json']:
    path = f'infra/n8n/workflows/{wf}'
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"{data['id']} ({data['name']}): {len(data.get('nodes',[]))} nodes - OK")
