#!/usr/bin/env python3
"""Synchronize deployment/ with current codebase"""
import json, os, shutil, subprocess

# 1. Sync docker-compose.yml
shutil.copy2('docker-compose.yml', 'deployment/compose/docker-compose.yml')
print('Synced docker-compose.yml')

# 2. Sync all n8n workflows (the canonical 10)
canonical = [
    '00_global_error_handler.json',
    '01_gateway_dispatcher.json',
    '02_customer_session.json',
    '03_ai_intent_engine.json',
    '04A_order_lookup.json',
    '04B_knowledge_base_faq.json',
    '04C_human_escalation.json',
    '04D_agent_response_bridge.json',
    '05_conversation_logger.json',
    '06_output_channel_dispatcher.json',
]
os.makedirs('deployment/assets/n8n/workflows', exist_ok=True)
for wf in canonical:
    src = f'infra/n8n/workflows/{wf}'
    dst = f'deployment/assets/n8n/workflows/{wf}'
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'Synced workflow: {wf}')
    else:
        print(f'MISSING: {src}')

# 3. Sync WhatsApp bridge
os.makedirs('deployment/application/whatsapp', exist_ok=True)
for f in ['server.js', 'package.json', 'Dockerfile']:
    src = f'infra/whatsapp/{f}'
    dst = f'deployment/application/whatsapp/{f}'
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'Synced whatsapp/{f}')

# 4. Sync dashboard
for comp in ['backend', 'frontend']:
    os.makedirs(f'deployment/application/dashboard/{comp}', exist_ok=True)
    if comp == 'backend':
        for f in ['main.py', 'routes.py', 'auth.py', 'database.py', 'requirements.txt']:
            src = f'dashboard/backend/{f}'
            dst = f'deployment/application/dashboard/backend/{f}'
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f'Synced dashboard/backend/{f}')
    else:
        for f in ['index.html', 'app.js', 'style.css']:
            src = f'dashboard/frontend/{f}'
            dst = f'deployment/application/dashboard/frontend/{f}'
            if os.path.exists(src):
                shutil.copy2(src, dst)
                print(f'Synced dashboard/frontend/{f}')

# 5. Sync postgres assets
for f in ['schema.sql', 'init-databases.sh']:
    src = f'infra/postgres/{f}'
    dst = f'deployment/assets/postgres/{f}'
    if os.path.exists(src):
        shutil.copy2(src, dst)
        print(f'Synced postgres/{f}')

# 6. Sync redis config
src = 'infra/redis/redis.conf'
dst = 'deployment/assets/redis/redis.conf'
if os.path.exists(src):
    shutil.copy2(src, dst)
    print('Synced redis.conf')

# 7. Update VERSION
with open('deployment/VERSION', 'w') as f:
    f.write('0.1.0\n')
print('Updated VERSION')

# 8. Update inventory.json
inv_path = 'deployment/inventory.json'
with open(inv_path, 'r', encoding='utf-8') as f:
    inv = json.load(f)

inv['version'] = '0.1.0'
inv['git_commit'] = subprocess.run(['git', 'rev-parse', 'HEAD'], capture_output=True, text=True).stdout.strip()
inv['build_time'] = '2026-09-27T22:10:00Z'
inv['workflows'] = [
    {'id': 'CSWF000000000001', 'name': 'Master 01 - Gateway Dispatcher', 'file': '01_gateway_dispatcher.json'},
    {'id': 'CSWF000000000002', 'name': 'SubWF 02 - Session Manager', 'file': '02_customer_session.json'},
    {'id': 'CSWF000000000003', 'name': 'SubWF 03 - AI Intent Engine', 'file': '03_ai_intent_engine.json'},
    {'id': 'CSWF000000000004', 'name': 'SubWF 04A - Order Lookup', 'file': '04A_order_lookup.json'},
    {'id': 'CSWF000000000005', 'name': 'SubWF 04B - Knowledge Base FAQ', 'file': '04B_knowledge_base_faq.json'},
    {'id': 'CSWF000000000006', 'name': 'SubWF 04C - Human Escalation', 'file': '04C_human_escalation.json'},
    {'id': 'RWLCadRzOPjTHXVo', 'name': 'SubWF 04D - Agent Response Bridge', 'file': '04D_agent_response_bridge.json'},
    {'id': 'CSWF000000000007', 'name': 'SubWF 05 - Conversation Logger', 'file': '05_conversation_logger.json'},
    {'id': 'F7kjakLJXmzBDsvS', 'name': 'SubWF 06 - Output Dispatcher', 'file': '06_output_channel_dispatcher.json'},
    {'id': 'CSWF000000000008', 'name': 'Global Error Handler', 'file': '00_global_error_handler.json'},
]

with open(inv_path, 'w', encoding='utf-8') as f:
    json.dump(inv, f, ensure_ascii=False, indent=2)
print('Updated inventory.json')

print('\nDeployment bundle synchronized.')