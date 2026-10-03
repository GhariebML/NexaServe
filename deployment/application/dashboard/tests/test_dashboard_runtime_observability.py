import asyncio
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CS_DB_PASSWORD", "test-only-not-a-real-secret")
os.environ.setdefault("DASHBOARD_JWT_SECRET", "test-only-dashboard-signing-key")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "backend"))

import routes


def test_official_source_requires_https_and_government_domain():
    assert routes._is_official_source("https://depi.gov.eg/content/faqs")
    assert routes._is_official_source("https://sub.gov.eg/path")
    assert not routes._is_official_source("http://depi.gov.eg/path")
    assert not routes._is_official_source("https://depi.gov.eg.attacker.example/path")
    assert not routes._is_official_source("https://example.com/depi.gov.eg")


def test_execution_status_prioritizes_failures_and_fallbacks():
    assert routes._execution_status([{"event_type": "turn_completed", "payload": {}}]) == "completed"
    assert routes._execution_status([{"event_type": "turn_completed", "payload": {"guardrail_decision": "verified_faq_fallback"}}]) == "fallback"
    assert routes._execution_status([{"event_type": "error", "payload": {}}]) == "failed"
    assert routes._execution_status([{"event_type": "turn_completed", "payload": {"llm_status": "failed", "guardrail_decision": "verified_faq_fallback"}}]) == "failed"
    assert routes._execution_status([{"event_type": "turn_completed", "payload": {"llm_status": "failed"}}]) == "failed"


def test_rag_metrics_show_unmeasured_values_instead_of_fake_zeros(monkeypatch):
    query_results = iter([
        {"faq_responses": 4, "escalations": 1},
        {"safe_deflections": 1, "clarification_requests": 2, "llm_failures": 0,
         "fallbacks": 1, "error_count": 0, "grounded_answers": 2, "telemetry_turns": 4},
        {"avg_latency": 1000, "p50": 900, "p95": 1400, "retrieval_latency": None, "llm_latency": None},
    ])
    monkeypatch.setattr(routes, "query_one", lambda _sql, _params=None: next(query_results))
    monkeypatch.setattr(routes, "query_all", lambda _sql, _params=None: [{"bracket": "High", "count": 2}])

    result = asyncio.run(routes.get_rag_metrics(user={"role": "admin"}))
    assert result["rag_queries"] == 4
    assert result["average_retrieval_latency_ms"] is None
    assert result["average_llm_latency_ms"] is None
    assert result["cache_hit_rate"] is None
    assert result["program_isolation"]["depi_leakage"] is None


def test_execution_detail_redacts_unapproved_payload_fields(monkeypatch):
    monkeypatch.setattr(routes, "query_all", lambda _sql, _params: [{
        "execution_id": "exec-12",
        "workflow_name": "01_gateway_dispatcher",
        "event_type": "turn_completed",
        "channel": "webchat",
        "latency_ms": 900,
        "created_at": datetime.now(timezone.utc),
        "payload": {
            "request_id": "req-12", "workflow_id": "CSWF000000000001",
            "llm_status": "failed", "guardrail_decision": "verified_faq_fallback",
            "source_urls": ["https://depi.gov.eg/faq", "https://example.com/unsafe"],
            "customer": "must not be returned", "prompt": "must not be returned",
        },
    }])

    result = asyncio.run(routes.get_execution_detail("req-12", user={"role": "admin"}))
    event = result["events"][0]
    assert result["status"] == "failed"
    assert event["details"]["source_urls"] == ["https://depi.gov.eg/faq"]
    assert "customer" not in event["details"]
    assert "prompt" not in event["details"]
    assert result["n8n_url"].endswith("/workflow/CSWF000000000001/executions/exec-12")


def test_system_health_distinguishes_api_from_generation(monkeypatch):
    def query(sql, _params=None):
        if "SELECT 1 as ok" in sql:
            return {"ok": 1}
        return {"status": "failed", "error_code": "generation_failed", "created_at": datetime.now(timezone.utc)}

    class RedisOk:
        def ping(self):
            return True

    monkeypatch.setattr(routes, "query_one", query)
    monkeypatch.setattr(routes.redis, "Redis", lambda **_kwargs: RedisOk())
    monkeypatch.setattr(routes, "_http_probe", lambda _url: (200, None))
    requested = []

    class Response:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def getcode(self):
            return 200
        def read(self):
            return json.dumps({"models": [{"name": "qwen2.5:3b"}, {"name": "nomic-embed-text:latest"}]}).encode()

    def open_url(url, timeout=2):
        requested.append(url)
        return Response()

    monkeypatch.setattr(routes.urllib.request, "urlopen", open_url)
    result = asyncio.run(routes.get_system_health(user={"role": "admin"}))
    statuses = {service["name"]: service["status"] for service in result["services"]}
    assert statuses["Ollama API and models"] == "ONLINE"
    assert statuses["Ollama generation (observed)"] == "DEGRADED"
    assert not any(url.endswith("/api/generate") for url in requested)
    assert statuses["WhatsApp Gateway Bridge"] == "DEGRADED"


def test_whatsapp_probe_requires_connected_session(monkeypatch):
    class DisconnectedResponse:
        def __enter__(self):
            return self
        def __exit__(self, *_args):
            return False
        def getcode(self):
            return 200
        def read(self):
            return b'{"status":"DISCONNECTED","connected":false}'

    monkeypatch.setattr(routes.urllib.request, "urlopen", lambda *_args, **_kwargs: DisconnectedResponse())
    assert routes._whatsapp_probe("http://whatsapp/health") == (200, False, None)
