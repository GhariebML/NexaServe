"""Live new-ticket feed (/api/dashboard/tickets/feed) used by the dashboard alerts."""
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import FastAPI
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
os.environ.setdefault("CS_DB_PASSWORD", "test-only-not-a-real-secret")
os.environ.setdefault("DASHBOARD_JWT_SECRET", "test-only-dashboard-signing-key")
sys.path.insert(0, str(ROOT / "dashboard" / "backend"))

import routes  # noqa: E402

NOW = datetime(2026, 10, 27, 18, 0, tzinfo=timezone.utc)


def _client(monkeypatch, rows=None):
    calls = []

    def query_one(sql, params=None):
        return {"now": NOW} if "NOW() AS now" in sql else {"open": 5, "unassigned": 2, "breached": 1}

    def query_all(sql, params=None):
        calls.append(params)
        return rows or []

    monkeypatch.setattr(routes, "query_one", query_one)
    monkeypatch.setattr(routes, "query_all", query_all)
    app = FastAPI()
    app.include_router(routes.router)
    app.dependency_overrides[routes.get_current_user] = lambda: {"role": "agent"}
    return TestClient(app), calls


def test_feed_requires_auth():
    app = FastAPI()
    app.include_router(routes.router)
    assert TestClient(app).get("/api/dashboard/tickets/feed").status_code == 401


def test_first_poll_returns_only_the_clock_so_history_never_alerts(monkeypatch):
    client, calls = _client(monkeypatch)
    body = client.get("/api/dashboard/tickets/feed").json()
    assert body["server_time"] == NOW.isoformat() and body["items"] == [] and calls == []
    assert body["queue"] == {"open": 5, "unassigned": 2, "breached": 1}


def test_new_tickets_since_the_last_poll_are_returned(monkeypatch):
    row = {"id": uuid4(), "ticket_number": "TICK-50001", "title": "لم يصلني رابط الامتحان", "reason": "r",
           "priority": "high", "status": "open", "source_channel": "whatsapp", "customer_name": "مريم",
           "category_name": "exams", "category_name_ar": "الامتحانات", "sla_due_at": NOW, "created_at": NOW}
    client, calls = _client(monkeypatch, [row])
    body = client.get("/api/dashboard/tickets/feed", params={"since": "2026-10-27T17:59:45+00:00"}).json()
    assert [t["ticket_number"] for t in body["items"]] == ["TICK-50001"]
    assert body["items"][0]["category_name_ar"] == "الامتحانات"
    assert calls[0][0].isoformat() == "2026-10-27T17:59:45+00:00"


def test_feed_is_not_shadowed_by_the_ticket_detail_route(monkeypatch):
    client, _ = _client(monkeypatch)
    assert client.get("/api/dashboard/tickets/feed").status_code == 200
    assert client.get("/api/dashboard/tickets/feed", params={"since": "not-a-date"}).status_code == 422


# --- 04C: how a new escalation ticket is titled and categorised ---------------------------

import json  # noqa: E402
import shutil  # noqa: E402
import subprocess  # noqa: E402

import pytest  # noqa: E402

NODE = shutil.which("node")


def _categorize(message):
    if NODE is None:
        pytest.skip("Node.js is required to execute n8n Code nodes")
    wf = json.loads((ROOT / "infra/n8n/workflows/04C_human_escalation.json").read_text(encoding="utf-8"))
    code = next(n for n in wf["nodes"] if n["name"] == "Categorize Ticket")["parameters"]["jsCode"]
    runner = r"""
const {code, item} = JSON.parse(require('fs').readFileSync(0, 'utf8'));
const $input = {first: () => ({json: item})};
process.stdout.write(JSON.stringify(new Function('$input', code)($input)[0].json));
"""
    out = subprocess.run([NODE, "-e", runner], capture_output=True, text=True, encoding="utf-8", check=True,
                         input=json.dumps({"code": code, "item": {"customer_message": message}}))
    return json.loads(out.stdout)


@pytest.mark.parametrize("message,category", [
    ("عندي مشكلة في الامتحان التقني وعايز أتكلم مع موظف", "exams"),
    ("مش قادر ادخل على منصة LMS", "lms"),
    ("عايز اغير الإيميل بتاعي", "account"),
    ("خلصت التدريب ولسه الشهادة ما ظهرتش", "certificates"),
    ("خدمتكم سيئة جدا وعايز أقدم شكوى", "complaint"),
    ("عايز اتكلم مع موظف", "general"),
])
def test_topic_categories_win_over_generic_problem_words(message, category):
    assert _categorize(message)["category_id"] == category


def test_ticket_title_is_the_customers_words_cut_on_a_word_boundary():
    long = "عندي مشكلة كبيرة في التسجيل " * 6
    title = _categorize(long)["ticket_title"]
    assert len(title) <= 81 and title.endswith("…") and not title[:-1].endswith(" ")
    assert _categorize("  مش  قادر   ادخل ")["ticket_title"] == "مش قادر ادخل"
