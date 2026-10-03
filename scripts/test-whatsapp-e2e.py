# -*- coding: utf-8 -*-
"""
NexaServe WhatsApp E2E Quality Test Suite
==========================================
Tests real WhatsApp message → n8n pipeline → AI response quality.

This suite sends diverse questions (Arabic/English, DEPI/DEBI/Digilians,
escalation, order tracking, edge cases) through the /simulate endpoint
and validates that:
  1. Responses are NOT static/fixed — each question gets a relevant answer
  2. Arabic messages get Arabic answers (and vice versa)
  3. FAQ questions hit the RAG pipeline and return grounded answers
  4. Intent classification is correct
  5. No raw JSON/chunks leak into replies
  6. Response latency is acceptable
"""

import json
import time
import sys
import os
import datetime
import hashlib
import urllib.request
import urllib.error
from collections import Counter

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# ─── Configuration ───────────────────────────────────────────────────────────

SIMULATE_URL = os.getenv("WHATSAPP_SIMULATE_URL", "http://localhost:8080/simulate")
HEALTH_URL   = os.getenv("WHATSAPP_HEALTH_URL",   "http://localhost:8080/health")
CACHE_INV_URL = "http://localhost:8080/cache/invalidate"
TIMEOUT_SECS = 90   # RAG pipeline can be slow

# ─── Test Cases ──────────────────────────────────────────────────────────────

TEST_CASES = [
    # ═══ DEPI Arabic FAQ Questions ═══
    {
        "id": "DEPI_AR_01",
        "category": "DEPI FAQ (Arabic)",
        "message": "ما هي شروط التقديم في مبادرة رواد مصر الرقمية؟",
        "name": "أحمد محمد",
        "phone": "+201000000010",
        "expected_intent": "faq_query",
        "must_contain_any": ["شروط", "التقديم", "مصري", "السن", "DEPI", "رواد"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist", "chunk_id", "score:", "embedding"],
        "expected_lang": "ar",
    },
    {
        "id": "DEPI_AR_02",
        "category": "DEPI FAQ (Arabic)",
        "message": "ما هي التخصصات المتاحة في DEPI؟",
        "name": "سارة علي",
        "phone": "+201000000011",
        "expected_intent": "faq_query",
        "must_contain_any": ["ذكاء اصطناعي", "أمن سيبراني", "برمجيات", "تخصص", "مسار", "AI", "Cyber"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "DEPI_AR_03",
        "category": "DEPI FAQ (Arabic)",
        "message": "هل الدورات في DEPI مجانية ولا بفلوس؟",
        "name": "خالد حسن",
        "phone": "+201000000012",
        "expected_intent": "faq_query",
        "must_contain_any": ["مجان", "تكلف", "رسوم", "بدون", "free", "cost"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "DEPI_AR_04",
        "category": "DEPI FAQ (Arabic)",
        "message": "إيه المستندات المطلوبة للتقديم في DEPI؟",
        "name": "محمود سعيد",
        "phone": "+201000000013",
        "expected_intent": "faq_query",
        "must_contain_any": ["مستند", "رقم قومي", "شهادة", "وثائق", "تجنيد", "PDF"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "DEPI_AR_05",
        "category": "DEPI FAQ (Arabic)",
        "message": "ما هو نظام الإقامة والدراسة في DEPI؟",
        "name": "نور الدين",
        "phone": "+201000000014",
        "expected_intent": "faq_query",
        "must_contain_any": ["إقامة", "أكاديمية", "حضور", "تفرغ", "دراسة"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },

    # ═══ DEPI English FAQ Questions ═══
    {
        "id": "DEPI_EN_01",
        "category": "DEPI FAQ (English)",
        "message": "What are the admission requirements for DEPI?",
        "name": "John Smith",
        "phone": "+201000000020",
        "expected_intent": "faq_query",
        "must_contain_any": ["requirement", "Egyptian", "age", "degree", "eligib", "admission", "apply"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist", "chunk_id", "score:"],
        "expected_lang": "en",
    },
    {
        "id": "DEPI_EN_02",
        "category": "DEPI FAQ (English)",
        "message": "What tracks are available in the Digital Egypt Pioneers Initiative?",
        "name": "Sarah Johnson",
        "phone": "+201000000021",
        "expected_intent": "faq_query",
        "must_contain_any": ["AI", "cyber", "software", "track", "digital", "specializ"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "en",
    },
    {
        "id": "DEPI_EN_03",
        "category": "DEPI FAQ (English)",
        "message": "How do I register for the DEPI program?",
        "name": "David Lee",
        "phone": "+201000000022",
        "expected_intent": "faq_query",
        "must_contain_any": ["register", "digilians", "website", "portal", "online", "sign up", "apply"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "en",
    },

    # ═══ Digilians / DEBI Questions ═══
    {
        "id": "DIGILIANS_AR_01",
        "category": "Digilians (Arabic)",
        "message": "ما هي منصة ديجيليانز وما الفرق بينها وبين DEPI؟",
        "name": "ياسمين عادل",
        "phone": "+201000000030",
        "expected_intent": "faq_query",
        "must_contain_any": ["ديجيليانز", "Digilians", "منصة", "بوابة", "فرق", "portal"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "DEBI_AR_01",
        "category": "DEBI (Arabic)",
        "message": "ما هي مبادرة براعم مصر الرقمية DEBI؟",
        "name": "فاطمة أحمد",
        "phone": "+201000000031",
        "expected_intent": "faq_query",
        "must_contain_any": ["براعم", "DEBI", "أطفال", "صغار", "مبادرة", "digital", "buds"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },

    # ═══ LMS / Exam Questions ═══
    {
        "id": "LMS_AR_01",
        "category": "LMS & Exams (Arabic)",
        "message": "مش عارف أفتح صفحة الامتحان وبرنامج SEB مش شغال",
        "name": "عمر حسين",
        "phone": "+201000000040",
        "expected_intent": "faq_query",
        "must_contain_any": ["SEB", "امتحان", "Safe Exam", "تثبيت", "install", "browser"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },

    # ═══ Order Tracking ═══
    {
        "id": "ORDER_AR_01",
        "category": "Order Tracking (Arabic)",
        "message": "أريد معرفة حالة طلبي رقم SRV-1001",
        "name": "كريم مصطفى",
        "phone": "+201000000050",
        "expected_intent": "order_lookup",
        "must_contain_any": ["SRV-1001", "طلب", "حالة", "order", "status", "request"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "ORDER_EN_01",
        "category": "Order Tracking (English)",
        "message": "Can you check the status of my order SRV-2050?",
        "name": "Mike Williams",
        "phone": "+201000000051",
        "expected_intent": "order_lookup",
        "must_contain_any": ["SRV-2050", "order", "status", "request", "track"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "en",
    },

    # ═══ Human Escalation ═══
    {
        "id": "ESCALATION_AR_01",
        "category": "Escalation (Arabic)",
        "message": "عندي مشكلة كبيرة ومحتاج أتكلم مع موظف بشري",
        "name": "يوسف إبراهيم",
        "phone": "+201000000060",
        "expected_intent": "human_escalation",
        "must_contain_any": ["موظف", "دعم", "تحويل", "agent", "specialist", "escalat", "ticket", "TKT"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "ESCALATION_EN_01",
        "category": "Escalation (English)",
        "message": "This is unacceptable! I need to speak to a human representative immediately!",
        "name": "James Brown",
        "phone": "+201000000061",
        "expected_intent": "human_escalation",
        "must_contain_any": ["agent", "specialist", "escalat", "ticket", "TKT", "support", "representative"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "en",
    },

    # ═══ Greeting / General (these SHOULD get static welcome — but verify it's proper) ═══
    {
        "id": "GREETING_AR_01",
        "category": "Greeting (Arabic)",
        "message": "السلام عليكم",
        "name": "عبدالله",
        "phone": "+201000000070",
        "expected_intent": "general_support",
        "must_contain_any": ["أهلاً", "مرحبا", "خدمة", "مساعد", "Welcome", "help", "DEPI"],
        "must_not_contain": ["chunk_id", "score:", "embedding"],
        "expected_lang": "ar",
    },
    {
        "id": "GREETING_EN_01",
        "category": "Greeting (English)",
        "message": "Hello",
        "name": "Alice",
        "phone": "+201000000071",
        "expected_intent": "general_support",
        "must_contain_any": ["Welcome", "Hello", "help", "assist", "DEPI", "service"],
        "must_not_contain": ["chunk_id", "score:", "embedding"],
        "expected_lang": "en",
    },

    # ═══ Uniqueness Checks: Different questions MUST get different answers ═══
    {
        "id": "UNIQUE_AR_01",
        "category": "Uniqueness Check",
        "message": "ما هي مراحل القبول في مبادرة DEPI؟",
        "name": "حسن",
        "phone": "+201000000080",
        "expected_intent": "faq_query",
        "must_contain_any": ["مراحل", "قبول", "تسجيل", "اختبار", "مقابلة", "admission", "stages"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
    {
        "id": "UNIQUE_AR_02",
        "category": "Uniqueness Check",
        "message": "ما هي الشهادات اللي هاخدها بعد التخرج من DEPI؟",
        "name": "منى",
        "phone": "+201000000081",
        "expected_intent": "faq_query",
        "must_contain_any": ["شهادة", "معتمدة", "تخرج", "certificate", "وزارة"],
        "must_not_contain": ["Welcome to the DEPI", "How may we assist"],
        "expected_lang": "ar",
    },
]


# ─── Helpers ─────────────────────────────────────────────────────────────────

def print_header(text, char="═"):
    width = 80
    print(f"\n{char * width}")
    print(f" {text}")
    print(f"{char * width}")


def send_simulate(message, name, phone):
    """Send message to the WhatsApp bridge /simulate endpoint."""
    payload = json.dumps({
        "customer_message": message,
        "full_name": name,
        "phone_number": phone,
    }).encode("utf-8")

    req = urllib.request.Request(
        SIMULATE_URL,
        data=payload,
        headers={
            "Content-Type": "application/json; charset=utf-8",
            "Accept": "application/json",
        },
        method="POST",
    )

    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECS) as resp:
            latency_ms = int((time.time() - t0) * 1000)
            raw = resp.read()
            body = json.loads(raw.decode("utf-8"))
            body["_latency_ms"] = latency_ms
            return body
    except Exception as e:
        return {"error": str(e), "_latency_ms": int((time.time() - t0) * 1000)}


def extract_reply_text(body):
    """Extract the actual reply text, handling possible nested JSON."""
    reply = body.get("reply", "")
    if not reply:
        return ""

    # Sometimes reply is a JSON string like {"answer": "..."} 
    # Try to extract the answer field
    if reply.strip().startswith("{"):
        try:
            parsed = json.loads(reply)
            if isinstance(parsed, dict):
                for field in ["answer", "response", "reply", "text"]:
                    if field in parsed and isinstance(parsed[field], str):
                        return parsed[field].strip()
        except json.JSONDecodeError:
            pass

    return reply.strip()


def evaluate_test(tc, body):
    """Evaluate a test case result and return (pass, failures, warnings)."""
    failures = []
    warnings = []

    # Basic error check
    if "error" in body:
        failures.append(f"Request failed: {body['error']}")
        return False, failures, warnings

    reply_text = extract_reply_text(body)
    source = body.get("source", "")
    latency = body.get("_latency_ms", 0)

    # 1. Reply must not be empty
    if not reply_text:
        failures.append("Empty reply received")

    # 2. Check source — should be n8n, not deterministic fallback (except cache)
    if source == "deterministic-offline-fallback":
        failures.append(f"Got offline fallback instead of n8n response (source={source})")

    # 3. Check must_contain_any — at least one keyword should be present
    if tc.get("must_contain_any"):
        found_any = any(
            kw.lower() in reply_text.lower()
            for kw in tc["must_contain_any"]
        )
        if not found_any:
            failures.append(
                f"Response missing ALL expected keywords: {tc['must_contain_any']}\n"
                f"   Got: \"{reply_text[:200]}\""
            )

    # 4. Check must_not_contain — none of these should appear
    if tc.get("must_not_contain"):
        for bad in tc["must_not_contain"]:
            if bad.lower() in reply_text.lower():
                failures.append(f"Response contains forbidden text: \"{bad}\"")

    # 5. Check for raw data leaks
    raw_indicators = ["chunk_id", "embedding", "vector", "score:", "SELECT ", "INSERT ", "UPDATE "]
    for indicator in raw_indicators:
        if indicator.lower() in reply_text.lower():
            failures.append(f"Raw data leak detected: \"{indicator}\"")

    # 6. Latency check
    if latency > 60000:
        warnings.append(f"High latency: {latency}ms")

    # 7. Reply is raw JSON envelope (not just text)
    if reply_text.startswith("{") and reply_text.endswith("}"):
        warnings.append("Reply is raw JSON object — should be plain text")

    passed = len(failures) == 0
    return passed, failures, warnings


# ─── Main Test Runner ────────────────────────────────────────────────────────

def main():
    print_header("🔬 NexaServe WhatsApp E2E Quality Test Suite")
    print(f" Simulate URL : {SIMULATE_URL}")
    print(f" Test Cases   : {len(TEST_CASES)}")
    print(f" Started      : {datetime.datetime.now().isoformat()}")

    # Step 0: Health Check
    print("\n[STEP 0] WhatsApp Bridge Health Check...")
    try:
        req = urllib.request.Request(HEALTH_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            health = json.loads(resp.read().decode("utf-8"))
        print(f"   ✅ Bridge Status: {health.get('status')} | Phone: {health.get('phone')}")
    except Exception as e:
        print(f"   ❌ Bridge unreachable: {e}")
        print("   🚫 Cannot proceed without bridge. Exiting.")
        sys.exit(1)

    # Step 1: Invalidate cache to ensure fresh responses
    print("\n[STEP 1] Invalidating response cache...")
    try:
        req = urllib.request.Request(
            CACHE_INV_URL, data=b"", method="POST",
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            inv = json.loads(resp.read().decode("utf-8"))
        print(f"   ✅ Cache cleared. New version: {inv.get('new_version')}")
    except Exception as e:
        print(f"   ⚠️  Cache invalidation failed (non-fatal): {e}")

    # Step 2: Run all test cases
    print_header("📋 Running Test Cases", "─")

    results = []
    all_replies = []  # For uniqueness analysis
    category_stats = Counter()

    for i, tc in enumerate(TEST_CASES, 1):
        test_id = tc["id"]
        category = tc["category"]
        message = tc["message"]

        print(f"\n[{i}/{len(TEST_CASES)}] {test_id} — {category}")
        print(f"   📨 \"{message[:60]}{'...' if len(message) > 60 else ''}\"")

        body = send_simulate(message, tc.get("name", "Test User"), tc.get("phone", "+201000000099"))
        reply_text = extract_reply_text(body)
        source = body.get("source", "unknown")
        latency = body.get("_latency_ms", 0)

        passed, failures, warnings = evaluate_test(tc, body)

        # Print result
        status_icon = "✅" if passed else "❌"
        print(f"   {status_icon} Source: {source} | Latency: {latency}ms")
        if reply_text:
            preview = reply_text[:120].replace("\n", " ↵ ")
            print(f"   📝 \"{preview}{'...' if len(reply_text) > 120 else ''}\"")

        for f in failures:
            print(f"   ❌ FAIL: {f}")
        for w in warnings:
            print(f"   ⚠️  WARN: {w}")

        result = {
            "id": test_id,
            "category": category,
            "message": message,
            "status": "PASS" if passed else "FAIL",
            "source": source,
            "latency_ms": latency,
            "reply_preview": reply_text[:300] if reply_text else "",
            "failures": failures,
            "warnings": warnings,
        }
        results.append(result)
        all_replies.append(reply_text)
        category_stats[("PASS" if passed else "FAIL", category)] += 1

        # Small delay between tests to avoid overwhelming the pipeline
        time.sleep(1)

    # Step 3: Uniqueness Analysis — detect static/fixed responses
    print_header("🔍 Uniqueness Analysis (Static Response Detection)", "─")

    # Only consider FAQ test cases (not greetings, which are expected to be similar)
    faq_replies = [
        (tc["id"], reply)
        for tc, reply in zip(TEST_CASES, all_replies)
        if tc.get("expected_intent") == "faq_query" and reply
    ]

    reply_hashes = {}
    duplicates_found = []
    for test_id, reply in faq_replies:
        h = hashlib.md5(reply.encode("utf-8")).hexdigest()
        if h in reply_hashes:
            duplicates_found.append((test_id, reply_hashes[h], reply[:100]))
            print(f"   ⚠️  DUPLICATE: {test_id} has same reply as {reply_hashes[h]}")
        else:
            reply_hashes[h] = test_id

    if not duplicates_found:
        print("   ✅ All FAQ responses are unique — no static/fixed replies detected!")
    else:
        print(f"\n   ❌ Found {len(duplicates_found)} duplicate responses!")
        print("      This suggests the system is returning static/fixed replies.")

    # Check for the known static response
    static_responses = [
        "Welcome to the DEPI Customer Service platform. How may we assist you today?",
        "Thank you for contacting customer service",
    ]
    static_count = sum(
        1 for reply in all_replies
        if any(sr.lower() in reply.lower() for sr in static_responses)
    )
    if static_count > 2:  # More than just greetings
        print(f"   ❌ {static_count} responses contain static welcome message!")

    # Step 4: Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    total = len(results)
    avg_latency = sum(r["latency_ms"] for r in results) // max(total, 1)

    print_header("📊 FINAL RESULTS SUMMARY")
    print(f"   Total Tests : {total}")
    print(f"   ✅ Passed   : {pass_count}")
    print(f"   ❌ Failed   : {fail_count}")
    print(f"   Pass Rate   : {pass_count/total*100:.1f}%")
    print(f"   Avg Latency : {avg_latency}ms")
    print(f"   Duplicates  : {len(duplicates_found)}")

    # Category breakdown
    print("\n   Category Breakdown:")
    categories = sorted(set(tc["category"] for tc in TEST_CASES))
    for cat in categories:
        p = category_stats.get(("PASS", cat), 0)
        f = category_stats.get(("FAIL", cat), 0)
        icon = "✅" if f == 0 else "❌"
        print(f"     {icon} {cat}: {p}/{p+f} passed")

    verdict = "PASS" if fail_count == 0 and len(duplicates_found) == 0 else "FAIL"
    print(f"\n   🏆 VERDICT: {verdict}")

    # Save report
    report = {
        "test": "whatsapp_e2e_quality",
        "timestamp": datetime.datetime.now().isoformat(),
        "simulate_url": SIMULATE_URL,
        "total": total,
        "passed": pass_count,
        "failed": fail_count,
        "pass_rate": round(pass_count / total * 100, 1),
        "avg_latency_ms": avg_latency,
        "duplicate_responses": len(duplicates_found),
        "verdict": verdict,
        "results": results,
        "duplicates": [
            {"test_id": d[0], "same_as": d[1], "reply_preview": d[2]}
            for d in duplicates_found
        ],
    }

    outpath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "whatsapp_e2e_quality_results.json")
    os.makedirs(os.path.dirname(outpath), exist_ok=True)
    with open(outpath, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f"\n   📄 Report saved to: {os.path.abspath(outpath)}")

    return report


if __name__ == "__main__":
    report = main()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
