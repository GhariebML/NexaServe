"""
NexaServe Master Test Runner
==============================
Orchestrates ALL production acceptance gate tests in dependency order.

Order:
  1. Arabic Normalizer Unit Tests (no deps)
  2. Infrastructure Health Check
  3. Memory Continuity Tests (needs PostgreSQL)
  4. Program Isolation Tests (needs n8n + PostgreSQL + Ollama)
  5. Security Regression Tests (needs n8n + Ollama)
  6. HITL E2E Tests (needs n8n + PostgreSQL)
  7. WhatsApp Resilience Tests (needs WhatsApp bridge)
  8. Golden RAG Tests (needs full pipeline)

Usage:
    python tests/run_all_tests.py [--skip-golden] [--report-dir DIR]
"""

import json
import sys
import os
import datetime
import subprocess
import argparse

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
SCRIPTS_DIR = os.path.join(os.path.dirname(TESTS_DIR), 'scripts')

def run_test_module(name, script_path, timeout=600):
    """Run a test module as subprocess and capture results."""
    print(f"\n{'='*80}")
    print(f" RUNNING: {name}")
    print(f" Script: {script_path}")
    print(f"{'='*80}\n")
    
    start = datetime.datetime.now()
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=os.path.dirname(script_path),
            encoding='utf-8',
            errors='replace'
        )
        elapsed = (datetime.datetime.now() - start).total_seconds()
        
        print(result.stdout[-2000:] if len(result.stdout) > 2000 else result.stdout)
        if result.stderr:
            print(f"[STDERR] {result.stderr[-500:]}")
        
        return {
            "test": name,
            "exit_code": result.returncode,
            "status": "PASS" if result.returncode == 0 else "FAIL",
            "elapsed_seconds": round(elapsed, 1),
            "stdout_tail": result.stdout[-500:],
            "stderr_tail": result.stderr[-200:] if result.stderr else ""
        }
    except subprocess.TimeoutExpired:
        elapsed = (datetime.datetime.now() - start).total_seconds()
        return {"test": name, "exit_code": -1, "status": "TIMEOUT", "elapsed_seconds": round(elapsed, 1)}
    except Exception as e:
        elapsed = (datetime.datetime.now() - start).total_seconds()
        return {"test": name, "exit_code": -1, "status": "ERROR", "elapsed_seconds": round(elapsed, 1), "error": str(e)}

def main():
    parser = argparse.ArgumentParser(description="NexaServe Master Test Runner")
    parser.add_argument("--skip-golden", action="store_true", help="Skip the full golden RAG suite (slow)")
    parser.add_argument("--report-dir", default=TESTS_DIR, help="Output directory for final report")
    args = parser.parse_args()
    
    start_time = datetime.datetime.now()
    
    print(f"\n{'#'*80}")
    print(f"#{'NEXASERVE MASTER TEST RUNNER':^78s}#")
    print(f"#{'':^78s}#")
    print(f"# Started: {start_time.isoformat():67s}#")
    print(f"{'#'*80}\n")
    
    all_results = []
    
    # 1. Arabic Normalizer (no deps)
    normalizer_path = os.path.join(SCRIPTS_DIR, 'arabic_normalizer.py')
    if os.path.exists(normalizer_path):
        all_results.append(run_test_module("Arabic Normalizer", normalizer_path, timeout=30))
    
    # 2. Infrastructure Health
    infra_path = os.path.join(TESTS_DIR, 'test_infrastructure.py')
    if os.path.exists(infra_path):
        infra_result = run_test_module("Infrastructure Health", infra_path, timeout=60)
        all_results.append(infra_result)
        
        if infra_result["status"] != "PASS":
            print("\n⚠ Infrastructure not fully healthy. Remaining tests may fail or be blocked.\n")
    
    # 3. Memory Continuity
    mem_path = os.path.join(TESTS_DIR, 'test_memory_continuity.py')
    if os.path.exists(mem_path):
        all_results.append(run_test_module("Memory Continuity", mem_path, timeout=60))
    
    # 4. Program Isolation
    iso_path = os.path.join(TESTS_DIR, 'test_program_isolation.py')
    if os.path.exists(iso_path):
        all_results.append(run_test_module("Program Isolation", iso_path, timeout=300))
    
    # 5. Security Regression
    sec_path = os.path.join(TESTS_DIR, 'test_security.py')
    if os.path.exists(sec_path):
        all_results.append(run_test_module("Security Regression", sec_path, timeout=300))
    
    # 6. HITL E2E
    hitl_path = os.path.join(TESTS_DIR, 'test_hitl_e2e.py')
    if os.path.exists(hitl_path):
        all_results.append(run_test_module("HITL E2E", hitl_path, timeout=120))
    
    # 7. WhatsApp Resilience
    wa_path = os.path.join(TESTS_DIR, 'test_whatsapp_resilience.py')
    if os.path.exists(wa_path):
        all_results.append(run_test_module("WhatsApp Resilience", wa_path, timeout=120))
    
    # 8. Golden RAG (slowest)
    if not args.skip_golden:
        golden_path = os.path.join(TESTS_DIR, 'run_golden_tests.py')
        if os.path.exists(golden_path):
            all_results.append(run_test_module("Golden RAG Suite", golden_path, timeout=600))
    else:
        print("\n[SKIPPED] Golden RAG Suite (--skip-golden)\n")
    
    # Final summary
    end_time = datetime.datetime.now()
    elapsed_total = (end_time - start_time).total_seconds()
    
    pass_count = sum(1 for r in all_results if r["status"] == "PASS")
    fail_count = sum(1 for r in all_results if r["status"] == "FAIL")
    other_count = sum(1 for r in all_results if r["status"] not in ("PASS", "FAIL"))
    
    print(f"\n{'#'*80}")
    print(f"#{'MASTER TEST SUITE FINAL RESULTS':^78s}#")
    print(f"{'#'*80}")
    print(f"\n {'Total Suites':20s}: {len(all_results)}")
    print(f" {'Passed':20s}: {pass_count}")
    print(f" {'Failed':20s}: {fail_count}")
    print(f" {'Blocked/Timeout':20s}: {other_count}")
    print(f" {'Total Time':20s}: {elapsed_total:.1f}s")
    print()
    
    for r in all_results:
        emoji = {"PASS": "✅", "FAIL": "❌", "TIMEOUT": "⏱️", "ERROR": "🚫", "BLOCKED": "🚫"}.get(r["status"], "❓")
        print(f"  {emoji} {r['test']:30s} {r['status']:10s} ({r['elapsed_seconds']:.1f}s)")
    
    verdict = "PRODUCTION_READY" if fail_count == 0 and other_count == 0 else "NOT_READY"
    print(f"\n{'='*80}")
    print(f" VERDICT: {verdict}")
    print(f"{'='*80}\n")
    
    report = {
        "master_test_run": True,
        "started": start_time.isoformat(),
        "finished": end_time.isoformat(),
        "elapsed_seconds": round(elapsed_total, 1),
        "total_suites": len(all_results),
        "passed": pass_count,
        "failed": fail_count,
        "blocked_or_timeout": other_count,
        "verdict": verdict,
        "suite_results": all_results
    }
    
    outpath = os.path.join(args.report_dir, 'FINAL_TEST_RESULTS.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Final report: {outpath}")
    
    sys.exit(0 if verdict == "PRODUCTION_READY" else 1)

if __name__ == "__main__":
    main()
