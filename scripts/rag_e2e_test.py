#!/usr/bin/env python3
"""E2E RAG Evaluation - Live NexaServe Test Suite"""
import json
import sys
import urllib.request
import time
import ssl

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

# Disable SSL verification for local testing
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

N8N_URL = "http://localhost:5678/webhook/customer-service"
SIMULATE_URL = "http://localhost:8080/simulate"

def http_post(url, payload):
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(url, data=data, headers={
        'Content-Type': 'application/json'
    }, method='POST')
    try:
        start = time.time()
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            body = resp.read().decode('utf-8')
            elapsed = (time.time() - start) * 1000
            return {
                'status': resp.status,
                'body': body,
                'elapsed_ms': round(elapsed, 1),
                'error': None
            }
    except urllib.error.HTTPError as e:
        body = e.read().decode('utf-8', errors='replace')
        elapsed = (time.time() - start) * 1000 if 'start' in dir() else 0
        return {
            'status': e.code,
            'body': body,
            'elapsed_ms': round(elapsed, 1) if 'start' in dir() else 0,
            'error': f"HTTP {e.code}"
        }
    except Exception as e:
        return {'status': 0, 'body': str(e), 'elapsed_ms': 0, 'error': str(e)}

def classify_response(result):
    try:
        body = json.loads(result.get('body', '{}')) if result.get('body') else {}
    except:
        body = {'raw': result.get('body', '')}
    
    reply = body.get('response', body.get('final_reply', body.get('reply', body.get('message', ''))))
    if isinstance(reply, dict):
        reply = str(reply)
    
    is_ar = bool(reply and any('\u0600' <= c <= '\u06FF' for c in reply))
    has_escalation = any(w in reply for w in ['تذكرة', 'دعم', 'info@depi', 'escalat', 'موظف', 'مسؤول'])
    has_hallucination_risk = any(w in reply for w in ['بالتأكيد', 'المعلومات العامة', 'كما تعلمون', 'عموماً'])
    is_json = isinstance(body, dict) and 'response' in body
    
    return {
        'status': result.get('status'),
        'error': result.get('error'),
        'elapsed_ms': result.get('elapsed_ms'),
        'is_json': is_json,
        'has_reply': bool(reply and str(reply).strip()),
        'is_arabic': is_ar,
        'has_escalation': has_escalation,
        'has_hallucination_risk': has_hallucination_risk,
        'reply_preview': str(reply)[:200] if reply else '',
        'raw_body_preview': str(body)[:200]
    }

tests = [
    ("T1 - Exact Arabic KB", {"customer_message": "ما هي شروط التقديم؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T2 - Arabic paraphrase", {"customer_message": "كيف أقدر أقدم على مبادرة الرواد؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T3 - English question", {"customer_message": "What are the admission requirements?", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T4 - Mixed Arabic/English", {"customer_message": "ما هي الشروط Admission requirements", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T5 - Unrelated question", {"customer_message": "What is the weather today in Tokyo?", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T6 - Escalation Arabic", {"customer_message": "أريد التحدث مع موظف", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T7 - Escalation English", {"customer_message": "I want to speak to a manager", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T8 - Unsupported date", {"customer_message": "ما هو تاريخ تخرج خريجي الدورة القادمة؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T9 - Greetings Arabic", {"customer_message": "مرحبا، كيف يمكنني المساعدة؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T10 - SRV tracking", {"customer_message": "SRV-1234", "full_name": "Test User", "phone_number": "+966500000000"}),
]

print("=" * 80)
print("E2E RAG EVALUATION SUITE - Live NexaServe")
print("=" * 80)

results = []
for name, payload in tests:
    print("")
    print("-" * 60)
    print("Test: " + name)
    print("Query: " + payload['customer_message'])
    
    result = http_post(N8N_URL, payload)
    classification = classify_response(result)
    
    print("Status: " + str(classification['status']))
    print("Error: " + str(classification['error']))
    print("Latency: " + str(classification['elapsed_ms']) + "ms")
    print("Is JSON: " + str(classification['is_json']))
    print("Has reply: " + str(classification['has_reply']))
    print("Arabic: " + str(classification['is_arabic']))
    print("Escalation: " + str(classification['has_escalation']))
    print("Hallucination risk: " + str(classification['has_hallucination_risk']))
    print("Reply preview: " + classification['reply_preview'][:150])
    
    passed = (classification['status'] in [200, 201] and classification['has_reply'])
    results.append({"test": name, "passed": passed, "classification": classification})
    print("Result: " + ("PASS" if passed else "FAIL"))
