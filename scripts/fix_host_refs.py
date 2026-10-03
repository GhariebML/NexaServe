#!/usr/bin/env python3
"""Fix host.docker.internal references in n8n workflows"""
import json
import os

WORKFLOWS_DIR = 'infra/n8n/workflows'
FIXES = []

for fname in os.listdir(WORKFLOWS_DIR):
    if not fname.endswith('.json'):
        continue
    path = os.path.join(WORKFLOWS_DIR, fname)
    with open(path, 'r', encoding='utf-8') as f:
        wf = json.load(f)
    
    changed = False
    for node in wf.get('nodes', []):
        params = node.get('parameters', {})
        
        # Fix URL in HTTP Request nodes
        url = params.get('url', '')
        if 'host.docker.internal' in str(url):
            url = str(url).replace('host.docker.internal:11434', 'cs-ollama:11434')
            params['url'] = url
            changed = True
            FIXES.append(f'{fname}/{node["name"]}: URL host.docker.internal → cs-ollama')
        
        # Fix in jsCode
        jscode = params.get('jsCode', '')
        if 'host.docker.internal' in str(jscode):
            jscode = str(jscode).replace('host.docker.internal:11434', 'cs-ollama:11434')
            params['jsCode'] = jscode
            changed = True
            FIXES.append(f'{fname}/{node["name"]}: jsCode host.docker.internal → cs-ollama')
        
        # Fix in jsonBody
        jsonbody = params.get('jsonBody', '')
        if 'host.docker.internal' in str(jsonbody):
            jsonbody = str(jsonbody).replace('host.docker.internal:11434', 'cs-ollama:11434')
            params['jsonBody'] = jsonbody
            changed = True
            FIXES.append(f'{fname}/{node["name"]}: jsonBody host.docker.internal → cs-ollama')
    
    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(wf, f, ensure_ascii=False, indent=2)

print(f'Applied {len(FIXES)} fixes:')
for f in FIXES:
    print(f'  - {f}')