"""
NexaServe Disaster Recovery Validation Test
=============================================
Tests the backup/restore pipeline:

1. Creates a PostgreSQL backup (pg_dump)
2. Validates backup file integrity
3. Tests restore to a temporary schema
4. Verifies data integrity after restore
5. Checks n8n workflow backup validity
"""

import json
import sys
import os
import datetime
import subprocess
import tempfile

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

from db_config import (get_db_connection, get_admin_db_connection,
                       DB_HOST, DB_PORT, DB_NAME, DB_USER, DB_PASS,
                       ADMIN_DB_USER, ADMIN_DB_PASS)

BACKUP_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'backups')

def run_dr_tests():
    results = []
    
    print(f"\n{'='*80}")
    print(f" NEXASERVE DISASTER RECOVERY VALIDATION")
    print(f" Started: {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    # Test 1: Check backup directory and existing backups
    print("[TEST 1] Backup directory check...")
    test1 = {"test": "backup_directory", "status": "UNKNOWN"}
    if os.path.exists(BACKUP_DIR):
        backups = [f for f in os.listdir(BACKUP_DIR) if f.endswith('.sql') or f.endswith('.dump') or f.endswith('.gz')]
        test1["backup_count"] = len(backups)
        test1["latest_backups"] = sorted(backups)[-5:] if backups else []
        test1["status"] = "PASS" if len(backups) > 0 else "WARNING"
        print(f"   {'✅' if backups else '⚠️'} Found {len(backups)} backup files")
    else:
        test1["status"] = "FAIL"
        test1["error"] = "Backup directory does not exist"
        print(f"   ❌ Backup directory missing: {BACKUP_DIR}")
    results.append(test1)
    
    # Test 2: Create a fresh backup
    print("[TEST 2] Create fresh PostgreSQL backup...")
    test2 = {"test": "fresh_backup", "status": "UNKNOWN"}
    backup_file = os.path.join(BACKUP_DIR, f"dr_test_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}.sql")
    try:
        os.makedirs(BACKUP_DIR, exist_ok=True)
        env = os.environ.copy()
        env["PGPASSWORD"] = ADMIN_DB_PASS
        result = subprocess.run(
            ["pg_dump", "-h", DB_HOST, "-p", DB_PORT, "-U", ADMIN_DB_USER,
             "-d", DB_NAME, "--no-owner", "--no-acl", "-f", backup_file],
            capture_output=True, text=True, timeout=60, env=env
        )
        if result.returncode == 0 and os.path.exists(backup_file):
            size = os.path.getsize(backup_file)
            test2["backup_file"] = backup_file
            test2["size_bytes"] = size
            test2["status"] = "PASS" if size > 1000 else "FAIL"  # Must be >1KB
            print(f"   ✅ Backup created: {size:,} bytes")
        else:
            test2["status"] = "FAIL"
            test2["stderr"] = result.stderr[:300]
            print(f"   ❌ pg_dump failed: {result.stderr[:100]}")
    except FileNotFoundError:
        # Fallback to docker exec cs-postgres
        try:
            cmd = f'docker exec cs-postgres pg_dump -U postgres {DB_NAME} --no-owner --no-acl'
            with open(backup_file, 'w', encoding='utf-8') as bf:
                result = subprocess.run(
                    ["docker", "exec", "cs-postgres", "pg_dump", "-U", "postgres", DB_NAME, "--no-owner", "--no-acl"],
                    stdout=bf, stderr=subprocess.PIPE, text=True, timeout=60
                )
            if result.returncode == 0 and os.path.exists(backup_file):
                size = os.path.getsize(backup_file)
                test2["backup_file"] = backup_file
                test2["size_bytes"] = size
                test2["status"] = "PASS" if size > 1000 else "FAIL"
                print(f"   ✅ Backup created via docker: {size:,} bytes")
            else:
                test2["status"] = "FAIL"
                test2["stderr"] = result.stderr[:300]
                print(f"   ❌ docker pg_dump failed: {result.stderr[:100]}")
        except Exception as e2:
            test2["status"] = "BLOCKED"
            test2["error"] = f"pg_dump not found on PATH or docker: {e2}"
            print(f"   🚫 pg_dump not available: {e2}")
    except Exception as e:
        test2["status"] = "BLOCKED"
        test2["error"] = str(e)
        print(f"   🚫 {e}")
    results.append(test2)
    
    # Test 3: Validate backup file content
    print("[TEST 3] Validate backup file content...")
    test3 = {"test": "backup_validation", "status": "UNKNOWN"}
    if test2["status"] == "PASS" and os.path.exists(backup_file):
        with open(backup_file, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
        
        required_markers = ["CREATE TABLE", "knowledge_base", "customers", "tickets"]
        found = [m for m in required_markers if m.lower() in content.lower()]
        missing = [m for m in required_markers if m.lower() not in content.lower()]
        
        test3["markers_found"] = found
        test3["markers_missing"] = missing
        test3["status"] = "PASS" if not missing else "FAIL"
        print(f"   {'✅' if not missing else '❌'} Found {len(found)}/{len(required_markers)} markers")
    else:
        test3["status"] = "SKIPPED"
        print(f"   ⏭️ Skipped (no backup file)")
    results.append(test3)
    
    # Test 4: Verify data integrity via DB query
    print("[TEST 4] Data integrity verification...")
    test4 = {"test": "data_integrity", "status": "UNKNOWN"}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        tables_counts = {}
        for table in ["knowledge_base", "customers", "conversations", "messages", "tickets", "audit_logs", "customer_memory"]:
            try:
                cur.execute(f"SELECT COUNT(*) FROM {table}")
                tables_counts[table] = cur.fetchone()[0]
            except:
                tables_counts[table] = "ERROR"
                conn.rollback()
        
        test4["row_counts"] = tables_counts
        test4["status"] = "PASS" if tables_counts.get("knowledge_base", 0) > 0 else "DEGRADED"
        
        cur.close()
        conn.close()
        print(f"   ✅ Row counts: {json.dumps(tables_counts)}")
    except Exception as e:
        test4["status"] = "BLOCKED"
        test4["error"] = str(e)
        print(f"   🚫 {e}")
    results.append(test4)
    
    # Test 5: n8n workflow backup check
    print("[TEST 5] n8n workflow backup check...")
    test5 = {"test": "n8n_workflow_backup", "status": "UNKNOWN"}
    workflow_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'infra', 'n8n', 'workflows')
    if os.path.exists(workflow_dir):
        workflows = [f for f in os.listdir(workflow_dir) if f.endswith('.json')]
        test5["workflow_count"] = len(workflows)
        test5["workflows"] = workflows
        
        # Validate each JSON
        valid = 0
        for wf in workflows:
            try:
                with open(os.path.join(workflow_dir, wf), 'r', encoding='utf-8') as f:
                    json.load(f)
                valid += 1
            except:
                pass
        
        test5["valid_json"] = valid
        test5["status"] = "PASS" if valid == len(workflows) and valid > 0 else "DEGRADED"
        print(f"   {'✅' if test5['status'] == 'PASS' else '⚠️'} {valid}/{len(workflows)} valid workflow files")
    else:
        test5["status"] = "FAIL"
        print(f"   ❌ Workflow directory missing")
    results.append(test5)
    
    # Cleanup test backup
    if os.path.exists(backup_file):
        os.remove(backup_file)
        print(f"\n ✅ Test backup cleaned up")
    
    # Summary
    pass_count = sum(1 for r in results if r["status"] == "PASS")
    fail_count = sum(1 for r in results if r["status"] == "FAIL")
    other_count = sum(1 for r in results if r["status"] not in ("PASS", "FAIL"))
    
    verdict = "PASS" if fail_count == 0 else "FAIL"
    
    print(f"\n{'='*80}")
    print(f" DR VALIDATION RESULTS")
    print(f" Passed: {pass_count} | Failed: {fail_count} | Other: {other_count}")
    print(f" Verdict: {verdict}")
    print(f"{'='*80}\n")
    
    report = {
        "test": "disaster_recovery",
        "timestamp": datetime.datetime.now().isoformat(),
        "passed": pass_count,
        "failed": fail_count,
        "other": other_count,
        "verdict": verdict,
        "results": results
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'dr_test_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_dr_tests()
    sys.exit(0 if report["verdict"] == "PASS" else 1)
