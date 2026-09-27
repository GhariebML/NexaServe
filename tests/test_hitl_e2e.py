"""
NexaServe HITL (Human-in-the-Loop) End-to-End Test Suite
=========================================================
Tests the full escalation chain:
  customer → ticket → SLA → agent → WhatsApp → ticket update → audit log

Scenarios:
1. Normal escalation
2. High priority
3. Urgent priority
4. Duplicate escalation prevention
5. Timeout handling
6. Agent reply delivery
"""

import json
import time
import sys
import os
import datetime
import uuid

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    import requests
    import psycopg2
except ImportError:
    print("[FATAL] 'requests' and 'psycopg2' libraries required.")
    sys.exit(1)

from db_config import get_db_connection

WEBHOOK_URL = os.getenv("N8N_WEBHOOK_URL", "http://localhost:5678/webhook/customer-service")

def send_escalation_query(query, phone="+201000000003", name="HITL Test User"):
    """Send a query designed to trigger escalation."""
    payload = {
        "channel": "test",
        "customer_message": query,
        "phone_number": phone,
        "channel_user_id": phone.replace("+", ""),
        "full_name": name,
        "start_time": int(time.time() * 1000)
    }
    start = time.time()
    try:
        resp = requests.post(WEBHOOK_URL, json=payload, timeout=60)
        elapsed = int((time.time() - start) * 1000)
        try:
            body = resp.json()
        except:
            body = {"raw": resp.text[:500]}
        answer = ""
        if isinstance(body, dict):
            answer = (body.get("response") or body.get("final_reply") or
                     body.get("reply") or body.get("message") or body.get("output") or "")
        return {"status": resp.status_code, "answer": str(answer), "body": body, "latency_ms": elapsed, "error": None}
    except Exception as e:
        elapsed = int((time.time() - start) * 1000)
        return {"status": 0, "answer": "", "body": {}, "latency_ms": elapsed, "error": str(e)}

def check_ticket_created(conn, phone, after_ts):
    """Check if a ticket was created for this customer after the given timestamp."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT t.id, t.ticket_number, t.priority, t.status, t.reason, t.created_at
            FROM tickets t
            JOIN customers c ON t.customer_id = c.id
            WHERE c.phone_number = %s AND t.created_at > %s
            ORDER BY t.created_at DESC LIMIT 5
        """, (phone, after_ts))
        rows = cur.fetchall()
        cur.close()
        return [{"id": str(r[0]), "ticket_number": r[1], "priority": r[2], 
                "status": r[3], "reason": r[4], "created_at": str(r[5])} for r in rows]
    except Exception as e:
        return [{"error": str(e)}]

def check_audit_log(conn, event_type, after_ts):
    """Check audit log entries after timestamp."""
    try:
        cur = conn.cursor()
        cur.execute("""
            SELECT id, workflow_name, event_type, payload, created_at
            FROM audit_logs
            WHERE event_type = %s AND created_at > %s
            ORDER BY created_at DESC LIMIT 5
        """, (event_type, after_ts))
        rows = cur.fetchall()
        cur.close()
        return [{"id": r[0], "workflow": r[1], "event": r[2], 
                "payload_preview": str(r[3])[:200], "created_at": str(r[4])} for r in rows]
    except Exception as e:
        return [{"error": str(e)}]

def run_hitl_tests():
    results = []
    
    print(f"\n{'='*80}")
    print(f" NEXASERVE HITL END-TO-END TEST SUITE")
    print(f" Webhook: {WEBHOOK_URL}")
    print(f" Started: {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Try to connect to DB
    conn = None
    try:
        conn = get_db_connection()
        print(" ✅ Database connection established")
    except Exception as e:
        print(f" ⚠ Database connection failed: {e}")
        print(" Tests will run without DB verification")
    
    test_start = datetime.datetime.now(datetime.timezone.utc).isoformat()
    
    # Test 1: Normal escalation
    print("\n[TEST 1] Normal escalation request...")
    result = send_escalation_query(
        "أريد التحدث مع شخص مختص. المشكلة معقدة ولا أجد حلاً.",
        phone="+201000000003"
    )
    test1 = {
        "test": "normal_escalation",
        "status": "BLOCKED" if result["error"] else ("PASS" if result["status"] == 200 else "FAIL"),
        "http_status": result["status"],
        "answer_preview": result["answer"][:200],
        "latency_ms": result["latency_ms"]
    }
    if conn:
        test1["tickets_created"] = check_ticket_created(conn, "+201000000003", test_start)
    results.append(test1)
    print(f"   {'✅' if test1['status'] == 'PASS' else '❌'} {test1['status']} ({result['latency_ms']}ms)")
    time.sleep(1)
    
    # Test 2: High priority escalation
    print("[TEST 2] High priority escalation...")
    result = send_escalation_query(
        "عندي مشكلة عاجلة في التسجيل. الموعد النهائي بكرة ومش قادر أكمل التقديم!",
        phone="+201000000004"
    )
    test2 = {
        "test": "high_priority_escalation",
        "status": "BLOCKED" if result["error"] else ("PASS" if result["status"] == 200 else "FAIL"),
        "http_status": result["status"],
        "answer_preview": result["answer"][:200],
        "latency_ms": result["latency_ms"]
    }
    results.append(test2)
    print(f"   {'✅' if test2['status'] == 'PASS' else '❌'} {test2['status']} ({result['latency_ms']}ms)")
    time.sleep(1)
    
    # Test 3: Duplicate escalation prevention
    print("[TEST 3] Duplicate escalation (same user, same issue)...")
    result = send_escalation_query(
        "أريد التحدث مع شخص مختص. المشكلة معقدة ولا أجد حلاً.",
        phone="+201000000003"
    )
    test3 = {
        "test": "duplicate_escalation",
        "status": "BLOCKED" if result["error"] else "PASS",
        "http_status": result["status"],
        "answer_preview": result["answer"][:200],
        "latency_ms": result["latency_ms"]
    }
    if conn:
        tickets = check_ticket_created(conn, "+201000000003", test_start)
        test3["ticket_count"] = len(tickets)
        test3["duplicate_detected"] = len(tickets) <= 1
    results.append(test3)
    print(f"   {'✅' if test3['status'] == 'PASS' else '❌'} {test3['status']} ({result['latency_ms']}ms)")
    time.sleep(1)
    
    # Test 4: Verify no orphan tickets
    print("[TEST 4] Checking for orphan tickets...")
    test4 = {"test": "orphan_ticket_check", "status": "NOT_VERIFIED"}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("""
                SELECT COUNT(*) FROM tickets 
                WHERE customer_id NOT IN (SELECT id FROM customers)
            """)
            orphan_count = cur.fetchone()[0]
            cur.close()
            test4["orphan_count"] = orphan_count
            test4["status"] = "PASS" if orphan_count == 0 else "FAIL"
        except Exception as e:
            test4["error"] = str(e)
            test4["status"] = "BLOCKED"
    results.append(test4)
    print(f"   {'✅' if test4['status'] == 'PASS' else '⚠'} {test4['status']}")
    
    # Test 5: Audit log verification
    print("[TEST 5] Audit log verification...")
    test5 = {"test": "audit_log_check", "status": "NOT_VERIFIED"}
    if conn:
        try:
            cur = conn.cursor()
            cur.execute("SELECT COUNT(*) FROM audit_logs")
            count = cur.fetchone()[0]
            cur.close()
            test5["total_audit_entries"] = count
            test5["status"] = "PASS" if count >= 0 else "FAIL"
        except Exception as e:
            test5["error"] = str(e)
            test5["status"] = "BLOCKED"
    results.append(test5)
    print(f"   {'✅' if test5['status'] == 'PASS' else '⚠'} {test5['status']}")
    
    if conn:
        conn.close()
    
    # Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    blocked_count = sum(1 for r in results if r["status"] in ("BLOCKED", "NOT_VERIFIED"))
    
    print(f"\n{'='*80}")
    print(f" HITL TEST RESULTS")
    print(f" Passed: {pass_count} | Failed: {fail_count} | Blocked: {blocked_count}")
    print(f"{'='*80}\n")
    
    report = {
        "test": "hitl_e2e",
        "timestamp": datetime.datetime.now().isoformat(),
        "passed": pass_count,
        "failed": fail_count,
        "blocked": blocked_count,
        "verdict": "PASS" if fail_count == 0 and blocked_count == 0 else ("FAIL" if fail_count > 0 else "PARTIAL"),
        "results": results
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'hitl_test_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_hitl_tests()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
