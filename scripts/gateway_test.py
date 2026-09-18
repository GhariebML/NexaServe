#!/usr/bin/env python3
"""Gateway test with longer timeout for RAG queries"""
import json
import sys
import urllib.request
import time
import ssl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_URL = "http://localhost:5678/webhook/customer-service"

def http_post(url, payload, timeout=60):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json'
    }, method='POST')
    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            elapsed = time.time() - start
            return {'status': resp.status, 'body': body, 'elapsed': round(elapsed, 2), 'error': None}
    except Exception as e:
        elapsed = time.time() - start
        return {'status': 0, 'body': str(e), 'elapsed': round(elapsed, 2), 'error': str(e)}

tests = [
    ("Arabic FAQ", {"customer_message": "ما هي شروط التقديم؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("Escalation AR", {"customer_message": "أريد التحدث مع موظف", "full_name": "Test User", "phone_number": "+966500000000"}),
]

print("GATEWAY TEST - RAG path with 60s timeout")
print("=" * 60)

for name, payload in tests:
    print("Test: " + name)
    print("Query: " + payload['customer_message'])
    result = http_post(N8N_URL, payload, timeout=60)
    print("Status: " + str(result['status']))
    print("Error: " + str(result['error']))
    print("Elapsed: " + str(result['elapsed']) + "s")
    body_preview = result['body'][:200] if result['body'] else ''
    print("Body: " + body_preview)
    print("")
