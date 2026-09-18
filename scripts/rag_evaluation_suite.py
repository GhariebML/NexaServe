#!/usr/bin/env python3
"""Full E2E test with detailed results and 60s timeout"""
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

def parse_result(result):
    try:
        body = json.loads(result.get('body', '{}')) if result.get('body') else {}
    except:
        return {'raw': result.get('body', '')[:300]}
    
    ai_output = body.get('ai_output', {})
    handler_result = body.get('handler_result', {})
    
    return {
        'status': body.get('status'),
        'intent': ai_output.get('intent'),
        'confidence': ai_output.get('confidence'),
        'reply': body.get('final_reply', body.get('response', '')),
        'handler_status': body.get('handler_status'),
        'latency_ms': body.get('latency_ms'),
        'ai_output': ai_output,
    }

tests = [
    ("T1 - Exact Arabic KB", {"customer_message": "ما هي شروط التقديم والقبول في مبادرة الرواد الرقميون؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T2 - Arabic paraphrase", {"customer_message": "كيف أقدر أقدم على مبادرة الرواد؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T3 - Arabic spelling var", {"customer_message": "شروط التقديم في الرواد الرقميون", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T4 - English question", {"customer_message": "What are the admission requirements for DEPI?", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T5 - Mixed Arabic/English", {"customer_message": "ما هي الشروط Admission requirements", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T6 - Unrelated question", {"customer_message": "What is the weather today in Tokyo?", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T7 - Similar unsupported", {"customer_message": "كيف أقدم على منحة دراسية خارج DEPI؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T8 - Keyword collision", {"customer_message": "ماذا أفعل في حالة حدوث طارئ أو حادث أثناء الامتحان؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T9 - Multi-topic", {"customer_message": "ما هي الشروط وكيف يمكنني التواصل مع الدعم؟", "full_name": "Test User", "phone_number": "+966500000000"}),
    ("T10 - Unsupported date", {"customer_message": "ما هو تاريخ تخرج خريجي الدورة القادمة؟", "full_name": "Test User", "phone_number": "+966500000000"}),
]

print("=" * 80)
print("E2E RAG EVALUATION SUITE - Live NexaServe (60s timeout)")
print("=" * 80)

results = []
for name, payload in tests:
    print("")
    print("-" * 60)
    print("Test: " + name)
    print("Query: " + payload['customer_message'])
    
    result = http_post(N8N_URL, payload, timeout=60)
    parsed = parse_result(result)
    
    reply = parsed.get('reply', '')[:200] if parsed.get('reply') else ''
    intent = parsed.get('intent', 'unknown')
    conf = parsed.get('confidence', 'N/A')
    is_ar = bool(reply and any('\u0600' <= c <= '\u06FF' for c in reply))
    has_escalation = 'تذكرة' in reply or 'دعم' in reply or 'info@depi' in reply
    has_hallucination = any(w in reply for w in ['بالتأكيد', 'المعلومات العامة', 'كما تعلمون'])
    
    passed = (result['status'] == 200 and bool(reply.strip()))
    
    print("HTTP Status: " + str(result['status']))
    print("Gateway latency: " + str(result['elapsed']) + "s")
    print("Intent: " + str(intent or 'N/A'))
    print("Confidence: " + str(conf or 'N/A'))
    print("Arabic reply: " + str(is_ar))
    print("Has escalation: " + str(has_escalation))
    print("Hallucination risk: " + str(has_hallucination))
    print("Reply: " + reply)
    print("Result: " + ("PASS" if passed else "FAIL"))
    
    results.append({
        'test': name, 'passed': passed, 'intent': intent, 'confidence': conf,
        'reply': reply, 'is_ar': is_ar, 'elapsed': result['elapsed'],
        'status': result['status'], 'has_escalation': has_escalation,
        'has_hallucination': has_hallucination
    })

passed_count = sum(1 for r in results if r['passed'])
print("\n" + "=" * 80)
print("RESULTS: " + str(passed_count) + "/" + str(len(tests)) + " passed")
print("=" * 80)
