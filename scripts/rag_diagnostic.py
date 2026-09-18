#!/usr/bin/env python3
"""Focused diagnostic for failing tests"""
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
    except urllib.error.HTTPError as e:
        return {'status': e.code, 'body': e.read().decode('utf-8', errors='replace'), 'elapsed': round(time.time() - start, 2), 'error': str(e)}
    except Exception as e:
        return {'status': 0, 'body': str(e)[:200], 'elapsed': round(time.time() - start, 2), 'error': str(e)}

tests = [
    ("T2 - Arabic paraphrase", {"customer_message": "كيف أقدر أقدم على مبادرة الرواد؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T5 - Mixed Arabic/English", {"customer_message": "ما هي الشروط Admission requirements", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T7 - Similar unsupported", {"customer_message": "كيف أقدم على منحة دراسية خارج DEPI؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T9 - Multi-topic", {"customer_message": "ما هي الشروط وكيف يمكنني التواصل مع الدعم؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T10 - Unsupported date", {"customer_message": "ما هو تاريخ تخرج خريجي الدورة القادمة؟", "full_name": "Test User", "phone_number": "+966500000000"}),
]

print("FOCUSED DIAGNOSTIC - 90s timeout")
print("=" * 70)

for name, payload in tests:
    print("")
    print("Test: " + name)
    print("Query: " + payload['customer_message'])
    
    result = http_post(N8N_URL, payload, timeout=90)
    reply = result.get('body', '')[:300] if result.get('body') else ''
    
    print("Status: " + str(result['status']))
    print("Error: " + str(result['error']))
    print("Elapsed: " + str(result['elapsed']) + "s")
    print("Reply: " + reply)
    print("Result: " + ("PASS" if result['status'] == 200 and reply else "FAIL"))
