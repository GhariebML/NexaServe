# -*- coding: utf-8 -*-
"""
Comprehensive Verification Test Suite for NexaServe Unified RAG System:
- مبادرة الرواد الرقميون (Digilians)
- مبادرة رواد مصر الرقمية (DEBI)
- Cross-Program Isolation & Zero Leakage
- Ambiguity Clarification & Comparison
- Bilingual English & Arabic Integrity
"""
import json
import urllib.request
import urllib.error
import time
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

WEBHOOK_URL = "http://localhost:5678/webhook/customer-service"

tests = [
    # =========================================================================
    # 1. DIGILIANS SPECIFIC TESTS
    # =========================================================================
    {
        "id": "DIGI-01",
        "category": "Digilians - Admission",
        "query": "ما هي شروط التقديم في مبادرة الرواد الرقميون؟",
        "lang": "ar",
        "expected_program": "DIGILIANS",
        "must_contain": ["18", "32"],
        "must_not_contain": ["جامعة أوتاوا", "جامعة اوتاوا", "debi.gov.eg", "بناة مصر"]
    },
    {
        "id": "DIGI-02",
        "category": "Digilians - Tracks",
        "query": "ما هي المسارات والتخصصات المتاحة في مبادرة الرواد الرقميون (Digilians)؟",
        "lang": "ar",
        "expected_program": "DIGILIANS",
        "must_contain": ["الذكاء الاصطناعي", "الأمن السيبراني"],
        "must_not_contain": ["جامعة أوتاوا", "debi.gov.eg"]
    },
    {
        "id": "DIGI-03",
        "category": "Digilians - English Admission",
        "query": "What are the admission requirements for Digilians?",
        "lang": "en",
        "expected_program": "DIGILIANS",
        "must_contain": ["18", "32"],
        "must_not_contain": ["Ottawa", "debi.gov.eg"]
    },

    # =========================================================================
    # 2. DEBI SPECIFIC TESTS
    # =========================================================================
    {
        "id": "DEBI-01",
        "category": "DEBI - Admission & Grade",
        "query": "ما هي شروط التقديم والقبول في مبادرة رواد مصر الرقمية (DEBI)؟",
        "lang": "ar",
        "expected_program": "DEBI",
        "must_contain": ["جيد جدا", "الهندسة"],
        "must_not_contain": ["طلاب السنة النهائية", "الأكاديمية العسكرية بمصر الجديدة", "digilians.gov.eg"]
    },
    {
        "id": "DEBI-02",
        "category": "DEBI - Master's & Universities",
        "query": "ما هي الجامعات الدولية المانحة لشهادة الماجستير في منحة DEBI؟",
        "lang": "ar",
        "expected_program": "DEBI",
        "must_contain": ["أوتاوا", "ماجستير"],
        "must_not_contain": ["الأكاديمية العسكرية بمصر الجديدة", "digilians.gov.eg"]
    },
    {
        "id": "DEBI-03",
        "category": "DEBI - English Eligibility",
        "query": "What are the eligibility criteria for Digital Egypt Builders Initiative (DEBI)?",
        "lang": "en",
        "expected_program": "DEBI",
        "must_contain": ["Very Good", "Engineering"],
        "must_not_contain": ["final-year", "18 to 32", "Military Academy"]
    },

    # =========================================================================
    # 3. AMBIGUITY & DISAMBIGUATION TESTS
    # =========================================================================
    {
        "id": "AMBIG-01",
        "category": "Ambiguity - Arabic Generic Conditions",
        "query": "ما هي شروط التقديم والقبول؟",
        "lang": "ar",
        "expected_program": "COMMON",
        "must_contain": ["هل تقصد مبادرة الرواد الرقميون (Digilians) أم مبادرة رواد مصر الرقمية (DEBI)؟"],
        "must_not_contain": []
    },
    {
        "id": "AMBIG-02",
        "category": "Ambiguity - English Generic Requirements",
        "query": "What are the admission requirements?",
        "lang": "en",
        "expected_program": "COMMON",
        "must_contain": ["Do you mean Digital Pioneers Initiative (Digilians) or Digital Egypt Builders Initiative (DEBI)?"],
        "must_not_contain": []
    },

    # =========================================================================
    # 4. COMPARISON TESTS
    # =========================================================================
    {
        "id": "COMP-01",
        "category": "Comparison - Arabic",
        "query": "ما الفرق بين مبادرة الرواد الرقميون (Digilians) ومبادرة رواد مصر الرقمية (DEBI)؟",
        "lang": "ar",
        "expected_program": "COMMON",
        "must_contain": ["الرواد الرقميون", "رواد مصر الرقمية"],
        "must_not_contain": []
    },
    {
        "id": "COMP-02",
        "category": "Comparison - English",
        "query": "What is the difference between Digilians and DEBI?",
        "lang": "en",
        "expected_program": "COMMON",
        "must_contain": ["Digilians", "DEBI"],
        "must_not_contain": []
    },

    # =========================================================================
    # 5. CROSS-PROGRAM LEAKAGE DEFENSE TESTS
    # =========================================================================
    {
        "id": "LEAK-01",
        "category": "Leakage Defense - DEBI vs Digilians Age",
        "query": "هل يشترط السن حتى 32 سنة في مبادرة DEBI؟",
        "lang": "ar",
        "expected_program": "DEBI",
        "must_contain": ["26", "DEBI"],
        "must_not_contain": ["digilians.gov.eg"]
    },

    # =========================================================================
    # 6. UNSUPPORTED / OUT-OF-SCOPE SAFE FALLBACK
    # =========================================================================
    {
        "id": "UNSUP-01",
        "category": "Unsupported / Out of Scope",
        "query": "ما هي أسعار تذاكر الطيران إلى كندا في الصيف القادم؟",
        "lang": "ar",
        "expected_program": "ANY",
        "must_contain": ["لا تتوفر معلومات", "الدعم"],
        "must_not_contain": ["سعر التذكرة 500 دولار"]
    }
]

def send_message(query, lang):
    payload = {
        "channel": "whatsapp",
        "customer_message": query,
        "phone_number": "+201503350999",
        "channel_user_id": "201503350999",
        "full_name": "Eng. Mohamed Gharieb",
        "locale": lang,
        "start_time": int(time.time() * 1000)
    }
    
    data = json.dumps(payload).encode('utf-8')
    req = urllib.request.Request(WEBHOOK_URL, data=data, headers={
        "Content-Type": "application/json; charset=utf-8"
    }, method="POST")

    start = time.time()
    try:
        with urllib.request.urlopen(req, timeout=40) as resp:
            body = resp.read().decode('utf-8', errors='replace')
            elapsed = time.time() - start
            res_json = json.loads(body)
            return {
                "status": resp.status,
                "elapsed": round(elapsed, 2),
                "reply": res_json.get("response") or res_json.get("final_reply") or res_json.get("reply") or "",
                "intent": res_json.get("intent") or (res_json.get("ai_output") or {}).get("intent") or "",
                "sources": res_json.get("sources") or [],
                "error": None
            }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "status": 0,
            "elapsed": round(elapsed, 2),
            "reply": "",
            "intent": "",
            "sources": [],
            "error": str(e)
        }

def run_suite():
    print("=" * 85)
    print("🏛️  NEXASERVE — UNIFIED DIGILIANS + DEBI RAG VERIFICATION SUITE")
    print("=" * 85)
    
    passed_count = 0
    total_count = len(tests)

    for t in tests:
        test_id = t["id"].ljust(10)
        cat = t["category"].ljust(35)
        print(f"Running [{test_id}] {cat}...")
        
        res = send_message(t["query"], t["lang"])
        
        reply = res["reply"]
        error = res["error"]
        elapsed = res["elapsed"]
        
        if error:
            print(f"  ❌ FAIL: Request error: {error} (elapsed: {elapsed}s)\n")
            continue
        
        # Check assertions
        failures = []
        for must in t["must_contain"]:
            if must.lower() not in reply.lower():
                failures.append(f"Missing required phrase: '{must}'")
                
        for must_not in t["must_not_contain"]:
            if must_not.lower() in reply.lower():
                failures.append(f"LEAK DETECTED! Found forbidden phrase: '{must_not}'")
        
        if failures:
            print(f"  ❌ FAIL: {', '.join(failures)} (elapsed: {elapsed}s)")
            print(f"     Reply snippet: {reply[:160]}...\n")
        else:
            print(f"  ✅ PASS (elapsed: {elapsed}s)")
            print(f"     Reply snippet: {reply[:140]}...\n")
            passed_count += 1
            
        time.sleep(1) # Brief pause between queries

    print("=" * 85)
    print(f"VERIFICATION RESULT: {passed_count} / {total_count} PASSED")
    print("=" * 85)
    return passed_count == total_count

if __name__ == "__main__":
    success = run_suite()
    sys.exit(0 if success else 1)
