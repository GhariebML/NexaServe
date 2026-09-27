# -*- coding: utf-8 -*-
"""Phase 3A: End-to-End RAG Verification Test Suite"""
import requests
import json
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

WEBHOOK_URL = "http://localhost:5678/webhook/customer-service"
TIMEOUT = 120

results = []

def run_test(name, payload, checks):
    """Run a single webhook test and validate the response."""
    print(f"\n{'='*60}")
    print(f"TEST: {name}")
    print(f"{'='*60}")
    print(f"  Query: {payload.get('customer_message', 'N/A')}")
    
    try:
        start = time.time()
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=TIMEOUT)
        elapsed = round(time.time() - start, 2)
        print(f"  HTTP: {resp.status_code} ({elapsed}s)")
        
        if resp.status_code == 200:
            try:
                data = resp.json()
            except:
                data = {"raw": resp.text[:500]}
            
            status = data.get("status", "N/A")
            intent = data.get("intent_handled", "N/A")
            confidence = data.get("confidence_label", data.get("confidence", "N/A"))
            program = data.get("program", data.get("program_scope", "N/A"))
            reply = data.get("reply", data.get("direct_reply", data.get("response", "NO REPLY")))
            guardrail = data.get("guardrail_decision", data.get("validation", {}).get("guardrail_decision", "N/A"))
            
            print(f"  Status: {status}")
            print(f"  Intent: {intent}")
            print(f"  Confidence: {confidence}")
            print(f"  Program: {program}")
            print(f"  Guardrail: {guardrail}")
            if reply:
                print(f"  Reply: {str(reply)[:300]}")
            
            # Run checks
            passed = True
            for check_name, check_fn in checks.items():
                try:
                    result = check_fn(data, reply or "")
                    symbol = "PASS" if result else "FAIL"
                    print(f"  [{symbol}] {check_name}")
                    if not result:
                        passed = False
                except Exception as e:
                    print(f"  [FAIL] {check_name}: {e}")
                    passed = False
            
            results.append({"name": name, "passed": passed, "time": elapsed})
            return data
        else:
            print(f"  Response: {resp.text[:500]}")
            results.append({"name": name, "passed": False, "time": 0})
            return None
    except Exception as e:
        print(f"  [FAIL] Error: {e}")
        results.append({"name": name, "passed": False, "time": 0})
        return None


# ============================================================
# TEST 3: Arabic FAQ Query - Full Pipeline
# ============================================================
run_test(
    "Arabic FAQ Query (Full Pipeline)",
    {
        "customer_message": "ما هي شروط الالتحاق بالمنحة؟",
        "phone_number": "+201234567890",
        "locale": "ar"
    },
    {
        "Returns a response": lambda d, r: len(r) > 10,
        "Has Arabic content": lambda d, r: any(ord(c) >= 0x0600 and ord(c) <= 0x06FF for c in r),
        "Not a raw error": lambda d, r: "error" not in r.lower()[:50],
    }
)

# ============================================================
# TEST 4: Disambiguation Test (Ambiguous Query)
# ============================================================
run_test(
    "Disambiguation (Ambiguous Query)",
    {
        "customer_message": "ما هي شروط التقديم؟",
        "phone_number": "+201111111111",
        "locale": "ar"
    },
    {
        "Returns a response": lambda d, r: len(r) > 5,
    }
)

# ============================================================
# TEST 5: DEBI-specific Query (Program Isolation)
# ============================================================
run_test(
    "DEBI Program Isolation",
    {
        "customer_message": "ما هي شروط الالتحاق بمبادرة رواد مصر الرقمية DEBI؟",
        "phone_number": "+201222222222",
        "locale": "ar"
    },
    {
        "Returns a response": lambda d, r: len(r) > 10,
        "No Digilians leakage": lambda d, r: "الأكاديمية العسكرية" not in r and "digilians" not in r.lower(),
    }
)

# ============================================================
# TEST 6: English Bilingual Query
# ============================================================
run_test(
    "English Bilingual Response",
    {
        "customer_message": "What are the admission requirements for DEBI?",
        "phone_number": "+201333333333",
        "locale": "en"
    },
    {
        "Returns a response": lambda d, r: len(r) > 10,
    }
)

# ============================================================
# TEST 7: Digilians-specific Query
# ============================================================
run_test(
    "Digilians Program Isolation",
    {
        "customer_message": "ما هي مسارات التدريب في مبادرة الرواد الرقميون Digilians؟",
        "phone_number": "+201444444444",
        "locale": "ar"
    },
    {
        "Returns a response": lambda d, r: len(r) > 10,
        "No DEBI leakage": lambda d, r: "جامعة أوتاوا" not in r and "جامعة اوتاوا" not in r,
    }
)

# ============================================================
# TEST 8: Out-of-Scope Query (Hallucination Guard)
# ============================================================
run_test(
    "Out-of-Scope Hallucination Guard",
    {
        "customer_message": "What is the weather in Cairo today?",
        "phone_number": "+201555555555",
        "locale": "en"
    },
    {
        "Returns a response": lambda d, r: len(r) > 5,
    }
)

# ============================================================
# SUMMARY
# ============================================================
print(f"\n{'='*60}")
print("PHASE 3A TEST SUMMARY")
print(f"{'='*60}")
total = len(results)
passed = sum(1 for r in results if r["passed"])
failed = total - passed
for r in results:
    symbol = "PASS" if r["passed"] else "FAIL"
    print(f"  [{symbol}] {r['name']} ({r['time']}s)")
print(f"\n  Total: {total} | Passed: {passed} | Failed: {failed}")
if failed == 0:
    print("  ALL TESTS PASSED!")
else:
    print(f"  {failed} TEST(S) NEED ATTENTION")
