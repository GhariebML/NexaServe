#!/usr/bin/env python3
"""T7 deep dive + cache invalidation test"""
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
SIMULATE_URL = "http://localhost:8080/simulate"

def http_post(url, payload, timeout=90):
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
        return {'status': 0, 'body': str(e)[:200], 'elapsed': round(elapsed, 2), 'error': str(e)}

def parse(result):
    try:
        body = json.loads(result.get('body', '{}')) if result.get('body') else {}
    except:
        return {'raw': result.get('body', '')[:300]}
    return {
        'status': body.get('status'),
        'intent': body.get('intent') or body.get('ai_output', {}).get('intent'),
        'reply': body.get('response', body.get('final_reply', '')),
        'confidence': body.get('confidence'),
        'latency_ms': body.get('latency_ms'),
    }

print("=" * 80)
print("T7 DEEP DIVE - Scholarship outside DEPI")
print("=" * 80)

payload = {"customer_message": "كيف أقدم على منحة دراسية خارج DEPI؟", "full_name": "Test User", "phone_number": "+966500000000"}
result = http_post(N8N_URL, payload, timeout=90)
parsed = parse(result)
print("Status: " + str(result['status']))
print("Elapsed: " + str(result['elapsed']) + "s")
print("Intent: " + str(parsed.get('intent')))
print("Confidence: " + str(parsed.get('confidence')))
print("Reply: " + str(parsed.get('reply'))[:500] if parsed.get('reply') else 'None')
print("")

print("=" * 80)
print("CACHE INVALIDATION TEST")
print("=" * 80)

# Step 1: Request KB-backed question
print("")
print("Step 1: Request KB-backed question (admission requirements)")
payload = {"customer_message": "ما هي شروط التقديم؟", "full_name": "Test User", "phone_number": "+966500000000"}
r1 = http_post(SIMULATE_URL, payload, timeout=90)
print("Status: " + str(r1['status']))
print("Elapsed: " + str(r1['elapsed']) + "s")

# Step 2: Request again (should be cache hit via server.js cache)
print("")
print("Step 2: Request same question again (should be cache hit)")
r2 = http_post(SIMULATE_URL, payload, timeout=90)
print("Status: " + str(r2['status']))
print("Elapsed: " + str(r2['elapsed']) + "s")

# Step 3: Check cache status via server.js endpoint
print("")
print("Step 3: Check cache status")
try:
    req = urllib.request.Request("http://localhost:8080/cache/status", method='GET')
    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
        cache_info = json.loads(resp.read().decode('utf-8'))
        print("Cache info: " + json.dumps(cache_info, ensure_ascii=False))
except Exception as e:
    print("Cache status error: " + str(e))

# Step 4: Bump cache version via invalidation endpoint
print("")
print("Step 4: Bump cache version via invalidation endpoint")
try:
    req = urllib.request.Request("http://localhost:8080/cache/invalidate", method='POST')
    with urllib.request.urlopen(req, timeout=5, context=ctx) as resp:
        inv_info = json.loads(resp.read().decode('utf-8'))
        print("Invalidation: " + json.dumps(inv_info, ensure_ascii=False))
except Exception as e:
    print("Invalidation error: " + str(e))

# Step 5: Check KB_CACHE_VERSION file
print("")
print("Step 5: Check KB_CACHE_VERSION file")
import os
version_file = 'infra/whatsapp/KB_CACHE_VERSION'
if os.path.exists(version_file):
    with open(version_file, 'r') as f:
        print("KB_CACHE_VERSION: " + f.read().strip())
else:
    print("KB_CACHE_VERSION file not found")

# Step 6: Test that server.js picks up new version
print("")
print("Step 6: Request after invalidation (cache should be cleared)")
r3 = http_post(SIMULATE_URL, payload, timeout=90)
print("Status: " + str(r3['status']))
print("Elapsed: " + str(r3['elapsed']) + "s (should be >2s if cache was cleared)")
