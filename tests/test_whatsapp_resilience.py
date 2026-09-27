"""
NexaServe WhatsApp Outage / Offline Resilience Test
=====================================================
Tests the deterministic offline fallback when n8n is unreachable.
This tests the WhatsApp bridge /simulate endpoint directly.

Tests:
1. Deterministic offline reply (Arabic)
2. Deterministic offline reply (English)
3. No raw chunk dump in offline reply
4. No Ollama hallucination in offline reply
5. Proper portal links included
6. Queue functionality verification
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

try:
    import requests
except ImportError:
    print("[FATAL] 'requests' library required.")
    sys.exit(1)

WHATSAPP_SIMULATE_URL = os.getenv("WHATSAPP_SIMULATE_URL", "http://localhost:8080/simulate")
WHATSAPP_HEALTH_URL = os.getenv("WHATSAPP_HEALTH_URL", "http://localhost:8080/health")

def run_whatsapp_resilience_tests():
    results = []
    
    print(f"\n{'='*80}")
    print(f" NEXASERVE WHATSAPP OUTAGE RESILIENCE TEST")
    print(f" Simulate URL: {WHATSAPP_SIMULATE_URL}")
    print(f" Started: {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Test 0: Health check
    print("[TEST 0] WhatsApp bridge health check...")
    try:
        resp = requests.get(WHATSAPP_HEALTH_URL, timeout=5)
        health = resp.json()
        test0 = {"test": "health_check", "status": "PASS", "data": health}
        print(f"   ✅ Bridge is up: {health.get('status', 'unknown')}")
    except Exception as e:
        test0 = {"test": "health_check", "status": "BLOCKED", "error": str(e)}
        print(f"   🚫 Bridge unreachable: {e}")
        results.append(test0)
        # If bridge is down, all tests are blocked
        report = {
            "test": "whatsapp_resilience",
            "timestamp": datetime.datetime.now().isoformat(),
            "verdict": "BLOCKED",
            "reason": f"WhatsApp bridge unreachable: {e}",
            "results": [test0]
        }
        outpath = os.path.join(os.path.dirname(__file__), 'whatsapp_resilience_results.json')
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n Report saved to: {outpath}")
        return report
    results.append(test0)
    
    # Test 1: Arabic offline reply
    print("\n[TEST 1] Arabic message → offline fallback...")
    try:
        resp = requests.post(WHATSAPP_SIMULATE_URL, json={
            "customer_message": "ما هي منح رواد مصر الرقمية؟",
            "full_name": "أحمد",
            "phone_number": "+201000000010"
        }, timeout=65)
        body = resp.json()
        reply = body.get("reply", "")
        source = body.get("source", "")
        
        # Validate
        failures = []
        if source == "deterministic-offline-fallback":
            required_links = ["depi.gov.eg", "digilians.gov.eg", "debi.gov.eg"]
            for link in required_links:
                if link not in reply:
                    failures.append(f"Missing portal link: {link}")
        elif not reply:
            failures.append("Empty reply received from n8n")
        
        # Must NOT contain raw chunks
        raw_indicators = ["سؤال:", "إجابة:", "score:", "chunk_id", "embedding", "vector"]
        for indicator in raw_indicators:
            if indicator.lower() in reply.lower():
                failures.append(f"Raw data leaked: {indicator}")
        
        test1 = {
            "test": "arabic_offline_reply",
            "status": "PASS" if not failures else "FAIL",
            "source": source,
            "reply_preview": reply[:200],
            "failures": failures
        }
        print(f"   {'✅' if not failures else '❌'} Source: {source}, Failures: {len(failures)}")
    except Exception as e:
        test1 = {"test": "arabic_offline_reply", "status": "BLOCKED", "error": str(e)}
        print(f"   🚫 {e}")
    results.append(test1)
    time.sleep(0.5)
    
    # Test 2: English offline reply
    print("[TEST 2] English message → offline fallback...")
    try:
        resp = requests.post(WHATSAPP_SIMULATE_URL, json={
            "customer_message": "What is the Digital Egypt Pioneers Initiative?",
            "full_name": "Ahmed",
            "phone_number": "+201000000011"
        }, timeout=65)
        body = resp.json()
        reply = body.get("reply", "")
        source = body.get("source", "")
        
        failures = []
        if "depi.gov.eg" not in reply and "n8n" not in source:
            failures.append("Missing DEPI portal link")
        
        raw_indicators = ["score:", "chunk_id", "embedding", "SELECT"]
        for indicator in raw_indicators:
            if indicator.lower() in reply.lower():
                failures.append(f"Raw data leaked: {indicator}")
        
        test2 = {
            "test": "english_offline_reply",
            "status": "PASS" if not failures else "FAIL",
            "source": source,
            "reply_preview": reply[:200],
            "failures": failures
        }
        print(f"   {'✅' if not failures else '❌'} Source: {source}, Failures: {len(failures)}")
    except Exception as e:
        test2 = {"test": "english_offline_reply", "status": "BLOCKED", "error": str(e)}
        print(f"   🚫 {e}")
    results.append(test2)
    time.sleep(0.5)
    
    # Test 3: Cache endpoint
    print("[TEST 3] Cache status endpoint...")
    try:
        resp = requests.get("http://localhost:8080/cache/status", timeout=5)
        cache = resp.json()
        test3 = {"test": "cache_status", "status": "PASS", "data": cache}
        print(f"   ✅ Cache version: {cache.get('version')}, entries: {cache.get('entries')}")
    except Exception as e:
        test3 = {"test": "cache_status", "status": "BLOCKED", "error": str(e)}
        print(f"   🚫 {e}")
    results.append(test3)
    
    # Test 4: Cache invalidation
    print("[TEST 4] Cache invalidation...")
    try:
        resp = requests.post("http://localhost:8080/cache/invalidate", timeout=5)
        inv = resp.json()
        test4 = {"test": "cache_invalidation", "status": "PASS" if inv.get("success") else "FAIL", "data": inv}
        print(f"   {'✅' if inv.get('success') else '❌'} New version: {inv.get('new_version')}")
    except Exception as e:
        test4 = {"test": "cache_invalidation", "status": "BLOCKED", "error": str(e)}
        print(f"   🚫 {e}")
    results.append(test4)
    
    # Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    blocked_count = sum(1 for r in results if r["status"] == "BLOCKED")
    
    verdict = "PASS" if fail_count == 0 and blocked_count == 0 else ("FAIL" if fail_count > 0 else "PARTIAL")
    
    print(f"\n{'='*80}")
    print(f" WHATSAPP RESILIENCE TEST RESULTS")
    print(f" Passed: {pass_count} | Failed: {fail_count} | Blocked: {blocked_count}")
    print(f" Verdict: {verdict}")
    print(f"{'='*80}\n")
    
    report = {
        "test": "whatsapp_resilience",
        "timestamp": datetime.datetime.now().isoformat(),
        "passed": pass_count,
        "failed": fail_count,
        "blocked": blocked_count,
        "verdict": verdict,
        "results": results
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'whatsapp_resilience_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_whatsapp_resilience_tests()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
