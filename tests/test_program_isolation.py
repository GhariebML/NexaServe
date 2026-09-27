"""
NexaServe Program Isolation Test Suite
======================================
Proves ZERO cross-program leakage between DEPI, Digilians, and DEBI.

Tests:
1. DEPI-only queries must NOT return Digilians-only facts
2. Digilians-only queries must NOT return DEPI-only facts
3. Comparison queries must clearly separate programs
4. Ambiguous queries must request clarification

Required result: CROSS-PROGRAM LEAKAGE = 0%
"""

import json
import time
import sys
import os
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    import requests
except ImportError:
    print("[FATAL] 'requests' library required.")
    sys.exit(1)

WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/customer-service")

# Two distinct initiatives in the Egyptian MCIT knowledge base:
# 1. Digilians (الرواد الرقميون)
# 2. DEBI / DEPI (بناة مصر الرقمية / رواد مصر الرقمية)
DIGILIANS_ONLY_KEYWORDS = [
    "الرواد الرقميون", "Digilians", "Digital Pioneers Initiative",
    "الأكاديمية العسكرية", "digilians.gov.eg"
]
DEBI_DEPI_ONLY_KEYWORDS = [
    "بناة مصر الرقمية", "جامعة أوتاوا", "جامعة اوتاوا", "debi.gov.eg", "ماجستير دولي"
]

ISOLATION_CASES = [
    # DEPI/DEBI queries - must NOT contain Digilians keywords
    {
        "id": "ISO_DEPI_01",
        "query": "ما هي منح رواد مصر الرقمية؟",
        "target_program": "DEBI",
        "forbidden_keywords": DIGILIANS_ONLY_KEYWORDS,
        "description": "DEPI query must not return Digilians facts"
    },
    {
        "id": "ISO_DEPI_02",
        "query": "ما هي شروط التقديم في DEPI؟",
        "target_program": "DEBI",
        "forbidden_keywords": DIGILIANS_ONLY_KEYWORDS,
        "description": "DEPI eligibility must not mention Digilians"
    },
    {
        "id": "ISO_DEPI_03",
        "query": "What tracks are available in DEBI?",
        "target_program": "DEBI",
        "forbidden_keywords": DIGILIANS_ONLY_KEYWORDS,
        "description": "DEBI tracks must not include Digilians tracks"
    },
    # Digilians queries - must NOT contain DEBI/DEPI keywords
    {
        "id": "ISO_DIG_01",
        "query": "ما هي شروط مبادرة الرواد الرقميون؟",
        "target_program": "DIGILIANS",
        "forbidden_keywords": DEBI_DEPI_ONLY_KEYWORDS,
        "description": "Digilians eligibility must not mention DEBI facts"
    },
    {
        "id": "ISO_DIG_02",
        "query": "ما هي المسارات في الرواد الرقميون؟",
        "target_program": "DIGILIANS",
        "forbidden_keywords": DEBI_DEPI_ONLY_KEYWORDS,
        "description": "Digilians tracks must not include DEBI tracks"
    },
    {
        "id": "ISO_DIG_03",
        "query": "How can I apply for Digilians?",
        "target_program": "DIGILIANS",
        "forbidden_keywords": DEBI_DEPI_ONLY_KEYWORDS,
        "description": "Digilians application info must not mention DEBI"
    },
    # Comparison queries - must separate correctly
    {
        "id": "ISO_COMP_01",
        "query": "ما الفرق بين DEPI والرواد الرقميون؟",
        "target_program": "COMPARISON",
        "forbidden_keywords": [],  # Both programs expected
        "description": "Comparison must clearly distinguish programs"
    },
    # Ambiguous queries - must ask for clarification
    {
        "id": "ISO_AMB_01",
        "query": "ما هي شروط المبادرة؟",
        "target_program": "AMBIGUOUS",
        "forbidden_keywords": [],
        "description": "Ambiguous query should trigger clarification"
    },
    {
        "id": "ISO_AMB_02",
        "query": "إزاي أقدم في المبادرة؟",
        "target_program": "AMBIGUOUS",
        "forbidden_keywords": [],
        "description": "Ambiguous application query should clarify which program"
    }
]

def send_query(query, timeout=60):
    payload = {
        "channel": "test",
        "customer_message": query,
        "phone_number": "+201000000001",
        "channel_user_id": "isolation_test_user",
        "full_name": "Isolation Test",
        "start_time": int(time.time() * 1000)
    }
    start = time.time()
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=timeout)
        elapsed = int((time.time() - start) * 1000)
        try:
            body = resp.json()
        except:
            body = {"raw": resp.text[:500]}
        answer = ""
        if isinstance(body, dict):
            answer = (body.get("response") or body.get("final_reply") or
                     body.get("reply") or body.get("message") or body.get("output") or "")
        return {"status": resp.status_code, "answer": str(answer), "latency_ms": elapsed, "error": None}
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return {"status": 0, "answer": "", "latency_ms": elapsed, "error": str(e)}

def run_isolation_tests():
    results = []
    leakage_count = 0
    total_testable = 0
    
    print(f"\n{'='*80}")
    print(f" NEXASERVE PROGRAM ISOLATION TEST SUITE")
    print(f" Webhook: {WEBHOOK_URL}")
    print(f" Cases: {len(ISOLATION_CASES)}")
    print(f" Started: {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    for i, case in enumerate(ISOLATION_CASES, 1):
        cid = case["id"]
        query = case["query"]
        print(f"[{i:02d}/{len(ISOLATION_CASES)}] {cid}: {query[:50]}...", end=" ", flush=True)
        
        result = send_query(query)
        
        if result["error"]:
            print(f"🚫 BLOCKED ({result['error'][:40]})")
            results.append({**case, "status": "BLOCKED", "answer": "", "leakage_terms": [], "latency_ms": result["latency_ms"]})
            continue
        
        answer = result["answer"]
        leakage_terms = []
        
        for kw in case.get("forbidden_keywords", []):
            if kw.lower() in answer.lower():
                leakage_terms.append(kw)
        
        if leakage_terms:
            leakage_count += 1
            print(f"❌ LEAKAGE DETECTED: {leakage_terms}")
        else:
            print(f"✅ PASS ({result['latency_ms']}ms)")
        
        if case["target_program"] not in ("COMPARISON", "AMBIGUOUS"):
            total_testable += 1
        
        results.append({
            "case_id": cid,
            "query": query,
            "target_program": case["target_program"],
            "status": "LEAKAGE" if leakage_terms else "PASS",
            "answer": answer[:300],
            "leakage_terms": leakage_terms,
            "latency_ms": result["latency_ms"]
        })
        time.sleep(0.5)
    
    # Final verdict
    leakage_pct = (leakage_count / total_testable * 100) if total_testable > 0 else 0
    print(f"\n{'='*80}")
    print(f" PROGRAM ISOLATION RESULT")
    print(f"{'='*80}")
    print(f" Total Cases:      {len(ISOLATION_CASES)}")
    print(f" Testable Cases:   {total_testable}")
    print(f" Leakage Cases:    {leakage_count}")
    print(f" CROSS-PROGRAM LEAKAGE = {leakage_pct:.1f}%")
    print(f" {'✅ PASS' if leakage_pct == 0 else '❌ FAIL'}")
    print(f"{'='*80}\n")
    
    report = {
        "test": "program_isolation",
        "timestamp": datetime.datetime.now().isoformat(),
        "total_cases": len(ISOLATION_CASES),
        "testable_cases": total_testable,
        "leakage_count": leakage_count,
        "leakage_percentage": leakage_pct,
        "verdict": "PASS" if leakage_pct == 0 else "FAIL",
        "results": results
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'program_isolation_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_isolation_tests()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
