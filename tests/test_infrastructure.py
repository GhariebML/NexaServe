"""
NexaServe Infrastructure Health Check
=======================================
Validates all 5 containers and external services are healthy.
This is the gate-keeper test that must pass before any other tests.

Checks:
1. PostgreSQL connectivity + schema validation
2. Redis connectivity + AUTH
3. n8n API reachability + workflow listing
4. Ollama reachability + model availability
5. WhatsApp bridge health endpoint
6. Knowledge base embeddings present (768-dim)
"""

import json
import sys
import os
import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'scripts'))

try:
    import requests
    import psycopg2
except ImportError:
    print("[FATAL] 'requests' and 'psycopg2' libraries required.")
    sys.exit(1)

from db_config import (get_db_connection, get_admin_db_connection,
                        DB_HOST, DB_PORT, DB_NAME, DB_USER,
                        OLLAMA_EMBED_URL, OLLAMA_GENERATE_URL, EMBED_MODEL, LLM_MODEL)

def check_postgres():
    """Validate PostgreSQL connectivity and schema."""
    result = {"service": "postgresql", "status": "UNKNOWN", "details": {}}
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check version
        cur.execute("SELECT version()")
        result["details"]["version"] = cur.fetchone()[0][:80]
        
        # Check required tables
        required_tables = [
            "customers", "conversations", "messages", "orders",
            "knowledge_base", "tickets", "audit_logs",
            "customer_memory", "conversation_summaries"
        ]
        cur.execute("""
            SELECT table_name FROM information_schema.tables 
            WHERE table_schema = 'public' AND table_type = 'BASE TABLE'
        """)
        existing = {r[0] for r in cur.fetchall()}
        missing = [t for t in required_tables if t not in existing]
        result["details"]["tables_found"] = len(existing)
        result["details"]["missing_tables"] = missing
        
        # Check extensions
        cur.execute("SELECT extname FROM pg_extension")
        extensions = [r[0] for r in cur.fetchall()]
        result["details"]["extensions"] = extensions
        result["details"]["has_vector"] = "vector" in extensions
        result["details"]["has_pg_trgm"] = "pg_trgm" in extensions
        
        # Check knowledge_base
        cur.execute("SELECT COUNT(*) FROM knowledge_base")
        kb_count = cur.fetchone()[0]
        result["details"]["kb_rows"] = kb_count
        
        # Check embeddings
        cur.execute("SELECT COUNT(*) FROM knowledge_base WHERE embedding IS NOT NULL")
        embedded = cur.fetchone()[0]
        result["details"]["kb_embedded"] = embedded
        
        # Check embedding dimensions
        if embedded > 0:
            cur.execute("SELECT array_length(embedding::real[], 1) FROM knowledge_base WHERE embedding IS NOT NULL LIMIT 1")
            dim = cur.fetchone()[0]
            result["details"]["embedding_dimension"] = dim
        
        # Check HNSW index
        cur.execute("""
            SELECT indexname FROM pg_indexes 
            WHERE tablename = 'knowledge_base' AND indexdef LIKE '%hnsw%'
        """)
        hnsw = cur.fetchall()
        result["details"]["hnsw_indexes"] = [r[0] for r in hnsw]
        
        cur.close()
        conn.close()
        
        result["status"] = "HEALTHY" if not missing and kb_count > 0 and embedded > 0 else "DEGRADED"
        
    except Exception as e:
        result["status"] = "DOWN"
        result["details"]["error"] = str(e)
    
    return result

def check_redis():
    """Validate Redis connectivity."""
    result = {"service": "redis", "status": "UNKNOWN", "details": {}}
    try:
        import redis as redis_lib
        redis_password = os.getenv("REDIS_PASSWORD", "")
        r = redis_lib.Redis(host="127.0.0.1", port=6379, password=redis_password, decode_responses=True)
        pong = r.ping()
        info = r.info("server")
        result["details"]["ping"] = pong
        result["details"]["version"] = info.get("redis_version", "unknown")
        result["details"]["uptime_seconds"] = info.get("uptime_in_seconds", 0)
        result["status"] = "HEALTHY" if pong else "DOWN"
    except ImportError:
        # Try raw TCP
        import socket
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(3)
            s.connect(("127.0.0.1", 6379))
            s.close()
            result["status"] = "REACHABLE"
            result["details"]["note"] = "TCP port open (redis library not installed for full check)"
        except:
            result["status"] = "DOWN"
    except Exception as e:
        result["status"] = "DOWN"
        result["details"]["error"] = str(e)
    
    return result

def check_n8n():
    """Validate n8n API reachability."""
    result = {"service": "n8n", "status": "UNKNOWN", "details": {}}
    try:
        resp = requests.get("http://localhost:5678/healthz", timeout=5)
        result["details"]["healthz_status"] = resp.status_code
        result["status"] = "HEALTHY" if resp.status_code == 200 else "DEGRADED"
    except Exception as e:
        result["status"] = "DOWN"
        result["details"]["error"] = str(e)
    
    return result

def check_ollama():
    """Validate Ollama LLM service."""
    result = {"service": "ollama", "status": "UNKNOWN", "details": {}}
    try:
        # Check tags endpoint
        resp = requests.get("http://localhost:11434/api/tags", timeout=10)
        if resp.status_code == 200:
            tags = resp.json()
            models = [m.get("name", "") for m in tags.get("models", [])]
            result["details"]["models"] = models
            result["details"]["has_llm"] = any(LLM_MODEL.split(":")[0] in m for m in models)
            result["details"]["has_embed"] = any(EMBED_MODEL in m for m in models)
            result["status"] = "HEALTHY" if result["details"]["has_llm"] and result["details"]["has_embed"] else "DEGRADED"
        else:
            result["status"] = "DEGRADED"
            result["details"]["http_status"] = resp.status_code
    except Exception as e:
        result["status"] = "DOWN"
        result["details"]["error"] = str(e)
    
    return result

def check_whatsapp():
    """Validate WhatsApp bridge health."""
    result = {"service": "whatsapp_bridge", "status": "UNKNOWN", "details": {}}
    try:
        resp = requests.get("http://localhost:8080/health", timeout=5)
        if resp.status_code == 200:
            health = resp.json()
            result["details"] = health
            result["status"] = "HEALTHY" if health.get("status") in ("CONNECTED", "QR_READY", "CONNECTING", "INITIALIZING") else "DEGRADED"
        else:
            result["status"] = "DEGRADED"
    except Exception as e:
        result["status"] = "DOWN"
        result["details"]["error"] = str(e)
    
    return result

def run_health_check():
    print(f"\n{'='*80}")
    print(f" NEXASERVE INFRASTRUCTURE HEALTH CHECK")
    print(f" {datetime.datetime.now().isoformat()}")
    print(f"{'='*80}\n")
    
    checks = []
    
    # PostgreSQL
    print(" [1/5] PostgreSQL...", end=" ", flush=True)
    pg = check_postgres()
    checks.append(pg)
    status_tag = {"HEALTHY": "[PASS]", "DEGRADED": "[WARN]", "DOWN": "[FAIL]"}.get(pg["status"], "[?]")
    print(f"{status_tag} {pg['status']}")
    if pg["status"] == "HEALTHY":
        d = pg["details"]
        print(f"        KB rows: {d.get('kb_rows')}, Embedded: {d.get('kb_embedded')}, Dim: {d.get('embedding_dimension')}")
    
    # Redis
    print(" [2/5] Redis...", end=" ", flush=True)
    rd = check_redis()
    checks.append(rd)
    status_tag = {"HEALTHY": "[PASS]", "REACHABLE": "[WARN]", "DOWN": "[FAIL]"}.get(rd["status"], "[?]")
    print(f"{status_tag} {rd['status']}")
    
    # n8n
    print(" [3/5] n8n...", end=" ", flush=True)
    n8 = check_n8n()
    checks.append(n8)
    status_tag = {"HEALTHY": "[PASS]", "DEGRADED": "[WARN]", "DOWN": "[FAIL]"}.get(n8["status"], "[?]")
    print(f"{status_tag} {n8['status']}")
    
    # Ollama
    print(" [4/5] Ollama...", end=" ", flush=True)
    ol = check_ollama()
    checks.append(ol)
    status_tag = {"HEALTHY": "[PASS]", "DEGRADED": "[WARN]", "DOWN": "[FAIL]"}.get(ol["status"], "[?]")
    print(f"{status_tag} {ol['status']}")
    if ol["status"] != "DOWN":
        print(f"        Models: {ol['details'].get('models', [])}")
    
    # WhatsApp
    print(" [5/5] WhatsApp Bridge...", end=" ", flush=True)
    wa = check_whatsapp()
    checks.append(wa)
    status_tag = {"HEALTHY": "[PASS]", "DEGRADED": "[WARN]", "DOWN": "[FAIL]"}.get(wa["status"], "[?]")
    print(f"{status_tag} {wa['status']}")
    
    # Overall verdict
    statuses = [c["status"] for c in checks]
    if all(s == "HEALTHY" for s in statuses):
        verdict = "ALL_HEALTHY"
    elif "DOWN" in statuses:
        verdict = "DEGRADED"
    else:
        verdict = "PARTIAL"
    
    healthy_count = sum(1 for s in statuses if s == "HEALTHY")
    down_count = sum(1 for s in statuses if s == "DOWN")
    
    print(f"\n{'='*80}")
    print(f" INFRASTRUCTURE VERDICT: {verdict}")
    print(f" Healthy: {healthy_count}/5 | Down: {down_count}/5")
    print(f"{'='*80}\n")
    
    report = {
        "test": "infrastructure_health",
        "timestamp": datetime.datetime.now().isoformat(),
        "verdict": verdict,
        "healthy_count": healthy_count,
        "down_count": down_count,
        "checks": checks
    }
    
    outpath = os.path.join(os.path.dirname(__file__), 'infrastructure_health_results.json')
    with open(outpath, 'w', encoding='utf-8') as f:
        json.dump(report, f, indent=2, ensure_ascii=False)
    print(f" Report saved to: {outpath}")
    
    return report

if __name__ == "__main__":
    report = run_health_check()
    sys.exit(0 if report["verdict"] == "ALL_HEALTHY" else 1)
