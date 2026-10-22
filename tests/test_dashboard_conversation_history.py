"""Read-only contract tests for the authenticated support history APIs."""
import asyncio
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault("CS_DB_PASSWORD", "unit-test-only")
os.environ.setdefault("DASHBOARD_JWT_SECRET", "unit-test-only-secret")
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "dashboard" / "backend"))

import routes  # noqa: E402
from fastapi import HTTPException  # noqa: E402


NOW = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
CUSTOMER_ID = "11111111-1111-4111-8111-111111111111"
CONVERSATION_ID = "22222222-2222-4222-8222-222222222222"


def test_customer_profile_scopes_and_paginates_conversations(monkeypatch):
    seen = []

    def query_one(sql, params=()):
        seen.append((sql, params))
        if "FROM customers WHERE id" in sql:
            return {
                "id": CUSTOMER_ID, "full_name": "Synthetic User", "phone_number": "+201000000000",
                "email": "synthetic@example.invalid", "preferred_language": "ar",
                "metadata": {"program": "DEPI"}, "created_at": NOW, "last_activity_at": NOW,
            }
        return {"count": 3}

    def query_all(sql, params=()):
        seen.append((sql, params))
        return [{
            "id": CONVERSATION_ID, "channel": "webchat", "status": "active",
            "current_intent": "faq_query", "language": "ar", "created_at": NOW,
            "closed_at": None, "message_count": 2, "last_message_at": NOW,
        }]

    monkeypatch.setattr(routes, "query_one", query_one)
    monkeypatch.setattr(routes, "query_all", query_all)
    result = asyncio.run(routes.get_customer_profile(CUSTOMER_ID, page=2, limit=1, user={"role": "readonly"}))

    assert result["customer"]["id"] == CUSTOMER_ID
    assert result["customer"]["phone_masked"] != "+201000000000"
    assert result["total"] == 3 and result["pages"] == 3 and result["page"] == 2
    assert result["conversations"][0]["id"] == CONVERSATION_ID
    assert any(params == (CUSTOMER_ID, 1, 1) for sql, params in seen if "LIMIT %s OFFSET %s" in sql)


def test_invalid_customer_id_returns_not_found_without_query(monkeypatch):
    monkeypatch.setattr(routes, "query_one", lambda *args: pytest.fail("invalid IDs must not reach SQL"))
    with pytest.raises(HTTPException) as exc:
        asyncio.run(routes.get_customer_profile("not-a-uuid", page=1, limit=20, user={"role": "readonly"}))
    assert exc.value.status_code == 404


def test_conversation_messages_are_scoped_paginated_and_exclude_internal_sender(monkeypatch):
    queries = []

    def query_one(sql, params=()):
        queries.append((sql, params))
        if "JOIN customers cust" in sql:
            return {
                "id": CONVERSATION_ID, "channel": "webchat", "status": "active",
                "current_intent": "faq_query", "language": "ar", "created_at": NOW,
                "closed_at": None, "customer_id": CUSTOMER_ID, "full_name": "Synthetic User",
                "phone_number": "+201000000000", "email": "synthetic@example.invalid",
                "customer_metadata": {"program": "DEPI"},
            }
        if "conversation_summaries" in sql:
            return None
        return {"count": 51}

    def query_all(sql, params=()):
        queries.append((sql, params))
        if "FROM messages" in sql:
            assert "sender_type IN ('customer', 'ai', 'agent')" in sql
            assert "LIMIT %s OFFSET %s" in sql
            return [{
                "id": "33333333-3333-4333-8333-333333333333", "sender_type": "customer",
                "content": "Synthetic question", "intent": "faq_query", "confidence": None,
                "created_at": NOW,
                "metadata": {"delivery_status": "received", "internal_notes": "must-not-escape", "system_prompt": "secret"},
            }]
        return []

    monkeypatch.setattr(routes, "query_one", query_one)
    monkeypatch.setattr(routes, "query_all", query_all)
    result = asyncio.run(routes.get_conversation_detail(CONVERSATION_ID, page=2, limit=50, user={"role": "readonly"}))

    assert result["message_total"] == 51 and result["message_pages"] == 2
    assert result["message_page"] == 2 and len(result["messages"]) == 1
    assert result["messages"][0]["sender_type"] == "customer"
    assert result["messages"][0]["metadata"]["delivery_status"] == "received"
    assert "internal_notes" not in result["messages"][0]["metadata"]
    assert "system_prompt" not in result["messages"][0]["metadata"]
    assert any(params == (CONVERSATION_ID, 50, 50) for sql, params in queries if "LIMIT %s OFFSET %s" in sql)


import pytest  # noqa: E402
