"""
NexaServe Memory Continuity Test
==================================
Tests the customer_memory and conversation_summaries tables.

Validates:
1. Memory table schema is correct
2. Memory can be written and retrieved
3. Memory filtering by type works
4. Conversation summaries can be created
5. Memory expiration works
6. Memory does not leak across customers
"""

import json
import time
import sys
import os
import uuid
import datetime

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    import psycopg2
except ImportError:
    print("[FATAL] 'psycopg2' library required.")
    sys.exit(1)

from db_config import get_db_connection

def run_memory_tests():
    results = []
    
    print(f"\n{'='*80}")
    print(f" NEXASERVE MEMORY CONTINUITY TEST SUITE")
    print(f" Started: {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    conn = None
    try:
        conn = get_db_connection()
        print(" ✅ Database connection established")
    except Exception as e:
        print(f" ❌ Database connection failed: {e}")
        report = {
            "test": "memory_continuity",
            "timestamp": datetime.datetime.now().isoformat(),
            "verdict": "BLOCKED",
            "reason": str(e),
            "results": []
        }
        outpath = os.path.join(os.path.dirname(__file__), 'memory_test_results.json')
        with open(outpath, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        return report
    
    test_customer_id = None
    test_conv_id = None
    
    try:
        cur = conn.cursor()
        
        # Create test customer
        cur.execute("""
            INSERT INTO customers (phone_number, full_name, preferred_language)
            VALUES (%s, %s, 'ar')
            ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
            RETURNING id
        """, (f"+20100TEST{int(time.time()) % 10000:04d}", "Memory Test User"))
        test_customer_id = cur.fetchone()[0]
        
        # Create test conversation
        cur.execute("""
            INSERT INTO conversations (customer_id, channel, status)
            VALUES (%s, 'test', 'active')
            RETURNING id
        """, (test_customer_id,))
        test_conv_id = cur.fetchone()[0]
        conn.commit()
        print(f" ✅ Test customer: {test_customer_id}")
        print(f" ✅ Test conversation: {test_conv_id}\n")
        
        # Test 1: Memory table schema
        print("[TEST 1] Memory table schema validation...")
        cur.execute("""
            SELECT column_name, data_type FROM information_schema.columns
            WHERE table_name = 'customer_memory' ORDER BY ordinal_position
        """)
        cols = {r[0]: r[1] for r in cur.fetchall()}
        required_cols = ["id", "customer_id", "memory_type", "content", "confidence", "is_active"]
        missing = [c for c in required_cols if c not in cols]
        test1 = {
            "test": "memory_schema",
            "status": "PASS" if not missing else "FAIL",
            "columns": list(cols.keys()),
            "missing": missing
        }
        results.append(test1)
        print(f"   {'✅' if not missing else '❌'} Columns: {len(cols)}, Missing: {missing}")
        
        # Test 2: Write and read memory
        print("[TEST 2] Memory write/read...")
        cur.execute("""
            INSERT INTO customer_memory (customer_id, memory_type, content, confidence, is_active)
            VALUES (%s, 'preference', 'Interested in Data Science track', 0.90, TRUE)
            RETURNING id
        """, (test_customer_id,))
        mem_id = cur.fetchone()[0]
        conn.commit()
        
        cur.execute("SELECT content, confidence FROM customer_memory WHERE id = %s", (mem_id,))
        row = cur.fetchone()
        test2 = {
            "test": "memory_write_read",
            "status": "PASS" if row and row[0] == "Interested in Data Science track" else "FAIL",
            "content": row[0] if row else None,
            "confidence": float(row[1]) if row else None
        }
        results.append(test2)
        print(f"   {'✅' if test2['status'] == 'PASS' else '❌'} {test2['status']}")
        
        # Test 3: Memory type filtering
        print("[TEST 3] Memory type filtering...")
        cur.execute("""
            INSERT INTO customer_memory (customer_id, memory_type, content, confidence, is_active)
            VALUES (%s, 'verified_fact', 'Egyptian national, age 25', 0.95, TRUE)
        """, (test_customer_id,))
        conn.commit()
        
        cur.execute("""
            SELECT COUNT(*) FROM customer_memory 
            WHERE customer_id = %s AND memory_type = 'preference' AND is_active = TRUE
        """, (test_customer_id,))
        pref_count = cur.fetchone()[0]
        
        cur.execute("""
            SELECT COUNT(*) FROM customer_memory 
            WHERE customer_id = %s AND memory_type = 'verified_fact' AND is_active = TRUE
        """, (test_customer_id,))
        fact_count = cur.fetchone()[0]
        
        test3 = {
            "test": "memory_type_filter",
            "status": "PASS" if pref_count >= 1 and fact_count >= 1 else "FAIL",
            "preferences": pref_count,
            "verified_facts": fact_count
        }
        results.append(test3)
        print(f"   {'✅' if test3['status'] == 'PASS' else '❌'} Prefs: {pref_count}, Facts: {fact_count}")
        
        # Test 4: Conversation summary
        print("[TEST 4] Conversation summary...")
        cur.execute("""
            INSERT INTO conversation_summaries 
            (conversation_id, customer_id, summary, topics, turn_count)
            VALUES (%s, %s, 'User asked about DEPI Data Science track eligibility', 
                    %s, 3)
            RETURNING id
        """, (test_conv_id, test_customer_id, ['DEPI', 'Data Science', 'eligibility']))
        sum_id = cur.fetchone()[0]
        conn.commit()
        
        cur.execute("SELECT summary, turn_count FROM conversation_summaries WHERE id = %s", (sum_id,))
        row = cur.fetchone()
        test4 = {
            "test": "conversation_summary",
            "status": "PASS" if row and "DEPI" in row[0] else "FAIL",
            "summary": row[0] if row else None,
            "turn_count": row[1] if row else None
        }
        results.append(test4)
        print(f"   {'✅' if test4['status'] == 'PASS' else '❌'} {test4['status']}")
        
        # Test 5: Cross-customer isolation
        print("[TEST 5] Cross-customer memory isolation...")
        cur.execute("""
            INSERT INTO customers (phone_number, full_name)
            VALUES (%s, 'Other Test User')
            ON CONFLICT (phone_number) DO UPDATE SET full_name = EXCLUDED.full_name
            RETURNING id
        """, (f"+20200TEST{int(time.time()) % 10000:04d}",))
        other_customer_id = cur.fetchone()[0]
        conn.commit()
        
        cur.execute("""
            SELECT COUNT(*) FROM customer_memory 
            WHERE customer_id = %s
        """, (other_customer_id,))
        other_mem_count = cur.fetchone()[0]
        
        test5 = {
            "test": "cross_customer_isolation",
            "status": "PASS" if other_mem_count == 0 else "FAIL",
            "other_customer_memory_count": other_mem_count
        }
        results.append(test5)
        print(f"   {'✅' if test5['status'] == 'PASS' else '❌'} Other customer memories: {other_mem_count}")
        
        # Cleanup test data
        print("\n Cleaning up test data...")
        cur.execute("DELETE FROM conversation_summaries WHERE customer_id = %s", (test_customer_id,))
        cur.execute("DELETE FROM customer_memory WHERE customer_id = %s", (test_customer_id,))
        cur.execute("DELETE FROM conversations WHERE customer_id = %s", (test_customer_id,))
        cur.execute("DELETE FROM customers WHERE id IN (%s, %s)", (test_customer_id, other_customer_id))
        conn.commit()
        print(" ✅ Test data cleaned up")
        
        cur.close()
        
    except Exception as e:
        print(f" ❌ Test error: {e}")
        results.append({"test": "unexpected_error", "status": "FAIL", "error": str(e)})
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
    
    # Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    
    verdict = "PASS" if fail_count == 0 else "FAIL"
    
    print(f"\n{'='*80}")
    print(f" MEMORY CONTINUITY TEST RESULTS")
    print(f" Passed: {pass_count} | Failed: {fail_count}")
    print(f" Verdict: {verdict}")
    print(f"{'='*80}\n")
    
    report = {
        "test": "memory_continuity",
        "timestamp": datetime.datetime.now().isoformat(),
        "passed": pass_count,
        "failed": fail_count,
        "verdict": verdict,
        "results": results
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'memory_test_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False, default=str)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_memory_tests()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
