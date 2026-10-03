#!/usr/bin/env python3
import json, os, sys
sys.stdout.reconfigure(encoding='utf-8')

for f in sorted(os.listdir('infra/n8n/workflows')):
    if not f.endswith('.json'):
        continue
    with open(f'infra/n8n/workflows/{f}', encoding='utf-8') as fh:
        data = fh.read()
    if 'host.docker.internal' in data:
        print(f'STILL HAS host.docker.internal: {f}')
print('Scan complete')