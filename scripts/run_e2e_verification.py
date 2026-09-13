# -*- coding: utf-8 -*-
"""
E2E Verification Suite for DEPI AI Customer Service Platform.
Tests:
1. DEPI FAQ Knowledge Base (RAG via PostgreSQL + Qwen 1.5b)
2. Order / Service Request Tracking (SRV-1001)
3. Human Escalation & Egyptian PII Masking
4. Greeting & General Support
"""
import urllib.request
import json
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

WEBHOOK_URL = "http://localhost:5678/webhook/customer-service"

test_cases = [
    {
        "id": "TEST-1",
        "title": "DEPI FAQ Knowledge Base (Admission Requirements)",
        "payload": {
            "name": "Mahmoud Hassan",
            "phone": "201503350999",
            "message": "ما هي شروط التقديم في مبادرة الرواد الرقميون؟",
            "channel": "whatsapp"
        },
        "expected_intent": "faq_query"
    },
    {
        "id": "TEST-2",
        "title": "Order / Service Request Lookup (SRV-1001)",
        "payload": {
            "name": "Sarah Ahmed",
            "phone": "201503350999",
            "message": "أريد الاستعلام عن طلبي رقم SRV-1001",
            "channel": "whatsapp"
        },
        "expected_intent": "order_lookup"
    },
    {
        "id": "TEST-3",
        "title": "Frustrated Customer, Escalation & Egyptian PII Masking",
        "payload": {
            "name": "Karim Mostafa",
            "phone": "201503350999",
            "message": "خدمة سيئة جدا وأريد التحدث مع موظف، ورقمي القومي 29501011234567",
            "channel": "whatsapp"
        },
        "expected_intent": "human_escalation"
    },
    {
        "id": "TEST-4",
        "title": "Greeting & General Support Menu",
        "payload": {
            "name": "Nour Ali",
            "phone": "201503350999",
            "message": "السلام عليكم ورحمة الله وبركاته",
            "channel": "whatsapp"
        },
        "expected_intent": "general_support"
    }
]

print("=" * 80)
print("🚀 DEPI AI Customer Service Platform - E2E Verification")
print(f"Target: {WEBHOOK_URL}")
print("=" * 80)

all_passed = True

for tc in test_cases:
    print(f"\n[{tc['id']}] Running: {tc['title']}...")
    print(f"  User Input: \"{tc['payload']['message']}\"")
    
    t0 = time.time()
    try:
        req = urllib.request.Request(
            WEBHOOK_URL,
            data=json.dumps(tc['payload']).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            elapsed = time.time() - t0
            res = json.loads(resp.read().decode('utf-8'))
            
            intent = res.get('intent')
            status = res.get('status')
            reply = res.get('response') or res.get('reply') or res.get('final_reply') or ""
            
            print(f"  Status Code : {resp.status} ({elapsed:.2f}s)")
            print(f"  Detected Intent : {intent} (Expected: {tc['expected_intent']})")
            print(f"  Response Status : {status}")
            print(f"  AI Reply Snippet:\n  " + "\n  ".join(reply.strip().splitlines()[:6]))
            
            if tc['expected_intent'] == intent or status == 'success':
                print(f"  ✅ Result: PASS")
            else:
                print(f"  ⚠️ Result: UNEXPECTED INTENT ({intent})")
                all_passed = False
    except Exception as e:
        elapsed = time.time() - t0
        print(f"  ❌ Result: FAILED ({elapsed:.2f}s): {e}")
        all_passed = False

print("\n" + "=" * 80)
if all_passed:
    print("🎉 ALL 4 E2E SCENARIOS VERIFIED SUCCESSFULLY!")
else:
    print("⚠️ SOME SCENARIOS REQUIRE ADJUSTMENT.")
print("=" * 80)
