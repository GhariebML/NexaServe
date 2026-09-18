# -*- coding: utf-8 -*-
"""RAG Evaluation Suite - DEPI Knowledge Base
Tests retrieval confidence, grounding, and response quality."""
import json
import sys
import urllib.request

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

KB_URL = "http://localhost:5678/webhook/customer-service"
SIMULATE_URL = "http://localhost:8080/simulate"

def test_query(message, name):
    payload = {"customer_message": message, "full_name": "Test User", "phone_number": "+966500000000"}
    try:
        req = urllib.request.Request(KB_URL, data=json.dumps(payload).encode('utf-8'),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        controller = None
        import threading
        result = {}
        def fetch():
            try:
                with urllib.request.urlopen(req, timeout=30) as resp:
                    result['data'] = json.loads(resp.read().decode('utf-8'))
                    result['status'] = 'ok'
            except Exception as e:
                result['status'] = 'error'
                result['error'] = str(e)
        t = threading.Thread(target=fetch)
        t.start()
        t.join(timeout=30)
        return result.get('data', {})
    except Exception as e:
        return {"error": str(e)}

def classify_test(result):
    reply = result.get('response', result.get('final_reply', result.get('reply', '')))
    reply_ar = reply if any('\u0600' <= c <= '\u06FF' for c in reply) else ''
    return {
        'has_reply': bool(reply and reply.strip()),
        'is_arabic': bool(reply_ar),
        'has_escalation': 'تذكرة' in reply or 'دعم' in reply or 'info@depi.gov' in reply,
        'has_hallucination_risk': any(w in reply for w in ['بالتأكيد', 'المعلومات العامة', 'كما تعلمون']),
        'reply_preview': reply[:120] if reply else ''
    }

tests = [
    ("T1 - Exact Arabic KB question", "ما هي شروط التقديم والقبول في مبادرة الرواد الرقميون؟",
     {"has_reply": True, "is_arabic": True}),
    ("T2 - Arabic paraphrase", "كيف أقدر أقدم على مبادرة الرواد؟",
     {"has_reply": True}),
    ("T3 - Arabic spelling variation", "شروط التقديم في الرواد الرقميون",
     {"has_reply": True}),
    ("T4 - English question", "What are the admission requirements for DEPI?",
     {"has_reply": True}),
    ("T5 - Mixed Arabic/English", "ما هي الشروط Admission requirements",
     {"has_reply": True}),
    ("T6 - Unrelated question", "What is the weather today in Tokyo?",
     {"has_escalation": True}),
    ("T7 - Similar but unsupported", "كيف أقدم على منحة دراسية خارج DEPI؟",
     {"has_escalation": True}),
    ("T8 - Keyword collision", "ماذا أفعل في حالة حدوث طارئ أو حادث أثناء الامتحان؟",
     {"has_reply": True}),
    ("T9 - Multi-topic question", "ما هي الشروط وكيف يمكنني التواصل مع الدعم؟",
     {"has_reply": True}),
    ("T10 - Unsupported date/policy", "ما هو تاريخ تخرج خريجي الدورة القادمة؟",
     {"has_escalation": True}),
]

print("=" * 80)
print("RAG EVALUATION SUITE - DEPI Knowledge Base")
print("=" * 80)

passed = 0
failed = 0
results = []

for name, query, expected in tests:
    print(f"\n{'─' * 60}")
    print(f"Test: {name}")
    print(f"Query: {query}")
    result = test_query(query, name)
    classification = classify_test(result)
    print(f"Reply preview: {classification['reply_preview']}")
    print(f"Has reply: {classification['has_reply']}")
    print(f"Arabic: {classification['is_arabic']}")
    print(f"Has escalation: {classification['has_escalation']}")
    print(f"Hallucination risk: {classification['has_hallucination_risk']}")

    test_passed = all(classification.get(k) == v for k, v in expected.items())
    if test_passed:
        print("RESULT: PASS")
        passed += 1
    else:
        print("RESULT: FAIL")
        failed += 1
    results.append({"test": name, "passed": test_passed, "classification": classification})

print(f"\n{'=' * 80}")
print(f"RESULTS: {passed}/{len(tests)} passed, {failed}/{len(tests)} failed")
print("=" * 80)

if failed == 0:
    print("ALL TESTS PASSED ✅")
else:
    print(f"FAILED TESTS: {[r['test'] for r in results if not r['passed']]}")
    print("See details above for investigation.")
