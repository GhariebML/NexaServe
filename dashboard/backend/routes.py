"""
NexaServe Production Admin Dashboard - API Routers & Business Logic
Real queries, Parameterized execution, PII masking, Filter aggregation, Metrics calculation.
"""
import os
import re
import time
import hmac
import urllib.request
import urllib.error
import socket
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from uuid import UUID
from fastapi import APIRouter, Depends, Query, HTTPException, Header, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from urllib.parse import quote
import redis

from database import query_all, query_one, execute_commit, get_db, REPORT_QUERY_DEADLINE
from auth import get_current_user, require_role
from reporting import build_workbook, safe_filename, EXCEL_MIME, MAX_EXPORT_ROWS
from evaluation_summary import summarize_stored_rag_evaluation

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

N8N_HEALTH_URL = os.getenv("N8N_HEALTH_URL", "http://127.0.0.1:5678/healthz")
N8N_UI_URL = os.getenv("N8N_UI_URL", "http://127.0.0.1:5678").rstrip("/")
N8N_API_URL = os.getenv("N8N_API_URL", "http://n8n:5678/api/v1").rstrip("/")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")
N8N_ACTIVATABLE_WORKFLOW_IDS = frozenset({"CSWF000000000001"})
N8N_ACTIVATION_APPROVED = os.getenv("N8N_ACTIVATION_APPROVED", "").lower() == "true"
N8N_IMPORT_ACCEPTANCE_VERIFIED = os.getenv("N8N_IMPORT_ACCEPTANCE_VERIFIED", "").lower() == "true"
N8N_GATEWAY_WEBHOOK = os.getenv("N8N_GATEWAY_WEBHOOK", "http://n8n:5678/webhook/customer-service")
N8N_AGENT_WEBHOOK = os.getenv("N8N_AGENT_WEBHOOK", "http://n8n:5678/webhook/agent-response")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
WHATSAPP_HEALTH_URL = os.getenv("WHATSAPP_HEALTH_URL", "http://127.0.0.1:8080/health")
WHATSAPP_INGEST_TOKEN = os.getenv("WHATSAPP_INGEST_TOKEN", "")


class WhatsAppInboundEvent(BaseModel):
    sender_jid: str
    provider_message_id: str
    text: str
    phone_number: Optional[str] = None
    push_name: Optional[str] = None


class WhatsAppOutboundEvent(BaseModel):
    recipient: str
    text: str
    reply_to_provider_message_id: Optional[str] = None
    # Row already written by the workflow that produced the message (e.g. an agent reply from 04D).
    message_id: Optional[str] = None


class WhatsAppDeliveryEvent(BaseModel):
    message_id: Optional[str] = None
    provider_message_id: Optional[str] = None
    delivery_status: str


def _require_whatsapp_ingest_token(token: Optional[str]) -> None:
    if not WHATSAPP_INGEST_TOKEN:
        raise HTTPException(status_code=503, detail="WhatsApp lifecycle integration is not configured")
    if not token or not hmac.compare_digest(token, WHATSAPP_INGEST_TOKEN):
        raise HTTPException(status_code=401, detail="Unauthorized")


def _normalize_whatsapp_number(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = re.sub(r"\D", "", value)
    return f"+{digits}" if digits else None


def _mask_whatsapp_message(text: str) -> Tuple[str, bool]:
    masked = re.sub(r"\b[12]\d{9}\b|\b[23]\d{13}\b", "[NATIONAL_ID_MASKED]", text)
    masked = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "[CARD_MASKED]", masked)
    masked = re.sub(r"\bSA\d{2}[0-9A-Z]{20}\b|\bEG\d{27}\b", "[IBAN_MASKED]", masked, flags=re.IGNORECASE)
    masked = re.sub(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", "[EMAIL_MASKED]", masked, flags=re.IGNORECASE)
    return masked, masked != text


@router.post("/internal/whatsapp/inbound")
async def persist_whatsapp_inbound(
    event: WhatsAppInboundEvent,
    x_nexaserve_webhook_token: Optional[str] = Header(None, alias="X-NexaServe-Webhook-Token"),
):
    """Persist and deduplicate a WhatsApp inbound event before the bot processes it."""
    _require_whatsapp_ingest_token(x_nexaserve_webhook_token)
    sender_jid = event.sender_jid.strip()
    provider_message_id = event.provider_message_id.strip()
    body = event.text.strip()
    if (not sender_jid or not provider_message_id or not body or len(body) > 10000
            or sender_jid.endswith(("@g.us", "@broadcast"))):
        raise HTTPException(status_code=422, detail="Invalid WhatsApp message event")
    phone = _normalize_whatsapp_number(event.phone_number or sender_jid)
    persisted_body, pii_detected = _mask_whatsapp_message(body)

    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"wa-jid:{sender_jid}",))
            if phone:
                cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (f"wa-phone:{phone}",))
            cur.execute("""
                SELECT id, customer_id, conversation_id, delivery_status
                FROM messages
                WHERE provider = 'whatsapp' AND provider_message_id = %s
                LIMIT 1
            """, (provider_message_id,))
            prior = cur.fetchone()
            if prior:
                conn.commit()
                return {"duplicate": True, "message_id": str(prior[0]), "customer_id": str(prior[1]),
                        "conversation_id": str(prior[2]), "delivery_status": prior[3]}

            cur.execute("""
                SELECT id, phone_number, whatsapp_id FROM customers
                WHERE whatsapp_id = %s LIMIT 1
            """, (sender_jid,))
            by_jid = cur.fetchone()
            by_phone = None
            if phone:
                cur.execute("SELECT id, phone_number, whatsapp_id FROM customers WHERE phone_number = %s LIMIT 1", (phone,))
                by_phone = cur.fetchone()
            if by_jid and by_phone and by_jid[0] != by_phone[0]:
                raise HTTPException(status_code=409, detail="WhatsApp identity conflicts with existing customer records")

            customer = by_jid or by_phone
            if customer:
                customer_id = customer[0]
                if by_jid is None and not customer[2]:
                    cur.execute("UPDATE customers SET whatsapp_id = %s, updated_at = CURRENT_TIMESTAMP WHERE id = %s", (sender_jid, customer_id))
            else:
                cur.execute("""
                    INSERT INTO customers (phone_number, whatsapp_id, full_name, preferred_language)
                    VALUES (%s, %s, %s, 'ar')
                    RETURNING id
                """, (phone, sender_jid, (event.push_name or "WhatsApp Citizen").strip()[:100] or "WhatsApp Citizen"))
                customer_id = cur.fetchone()[0]

            cur.execute("""
                SELECT id FROM conversations
                WHERE customer_id = %s AND channel = 'whatsapp' AND status IN ('active', 'handed_off')
                ORDER BY created_at DESC, id DESC LIMIT 1
            """, (customer_id,))
            conversation = cur.fetchone()
            if conversation:
                conversation_id = conversation[0]
            else:
                cur.execute("""
                    INSERT INTO conversations (customer_id, channel, status, language)
                    VALUES (%s, 'whatsapp', 'active', 'ar') RETURNING id
                """, (customer_id,))
                conversation_id = cur.fetchone()[0]

            cur.execute("""
                INSERT INTO messages
                    (conversation_id, customer_id, sender_type, content, provider,
                     provider_message_id, delivery_status, delivery_updated_at, pii_detected, metadata)
                VALUES (%s, %s, 'customer', %s, 'whatsapp', %s, 'received', CURRENT_TIMESTAMP,
                        %s, jsonb_build_object('source', 'whatsapp_webhook'))
                ON CONFLICT DO NOTHING
                RETURNING id
            """, (conversation_id, customer_id, persisted_body, provider_message_id, pii_detected))
            inserted = cur.fetchone()
            if not inserted:
                cur.execute("""
                    SELECT id, customer_id, conversation_id, delivery_status FROM messages
                    WHERE provider = 'whatsapp' AND provider_message_id = %s LIMIT 1
                """, (provider_message_id,))
                prior = cur.fetchone()
                conn.commit()
                return {"duplicate": True, "message_id": str(prior[0]), "customer_id": str(prior[1]),
                        "conversation_id": str(prior[2]), "delivery_status": prior[3]}
            conn.commit()
            return {"duplicate": False, "message_id": str(inserted[0]), "customer_id": str(customer_id),
                    "conversation_id": str(conversation_id), "delivery_status": "received"}


@router.post("/internal/whatsapp/outbound")
async def persist_whatsapp_outbound(
    event: WhatsAppOutboundEvent,
    x_nexaserve_webhook_token: Optional[str] = Header(None, alias="X-NexaServe-Webhook-Token"),
):
    """Create, claim, or return the single queued record for an outbound WhatsApp message.

    The workflow that produced a message stores it once (05 for bot replies, 04D for agent
    replies); the bridge then claims that row here instead of inserting a copy. A row that was
    already claimed or sent is reported as a duplicate so the bridge never sends it twice.
    """
    _require_whatsapp_ingest_token(x_nexaserve_webhook_token)
    recipient = event.recipient.strip()
    body = event.text.strip()
    if not recipient or not body or len(body) > 10000:
        raise HTTPException(status_code=422, detail="Invalid WhatsApp outbound message")
    if event.message_id:
        try:
            prerecorded_id = UUID(event.message_id)
        except ValueError:
            raise HTTPException(status_code=422, detail="Invalid WhatsApp outbound message")
    phone = _normalize_whatsapp_number(recipient)

    def recipient_matches(cur, customer_id) -> bool:
        cur.execute("SELECT phone_number, whatsapp_id FROM customers WHERE id = %s", (customer_id,))
        identity = cur.fetchone()
        return bool(identity and (
            identity[1] == recipient or
            (phone and _normalize_whatsapp_number(identity[0]) == phone)
        ))

    def claim(cur, row) -> Dict[str, Any]:
        """row = (id, customer_id, conversation_id, provider_message_id, delivery_status, claimed)."""
        message_id, customer_id, conversation_id, provider_message_id, delivery_status, claimed = row
        if provider_message_id or claimed:
            return {"message_id": str(message_id), "provider_message_id": provider_message_id,
                    "delivery_status": delivery_status, "duplicate": True}
        cur.execute("""
            UPDATE messages
            SET provider = 'whatsapp', content = %s, delivery_status = 'queued',
                delivery_updated_at = CURRENT_TIMESTAMP,
                metadata = COALESCE(metadata, '{}'::jsonb)
                           || jsonb_build_object('dispatch_claimed_at', CURRENT_TIMESTAMP::text)
            WHERE id = %s
        """, (body, message_id))
        return {"message_id": str(message_id), "customer_id": str(customer_id),
                "conversation_id": str(conversation_id), "delivery_status": "queued", "duplicate": False}

    claim_columns = """id, customer_id, conversation_id, provider_message_id, delivery_status,
                       COALESCE(metadata ? 'dispatch_claimed_at', FALSE)"""
    lock_key = (f"wa-claim:{event.message_id}" if event.message_id
                else f"wa-reply:{event.reply_to_provider_message_id or recipient}")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))", (lock_key,))
            if event.message_id:
                cur.execute(f"""
                    SELECT {claim_columns} FROM messages
                    WHERE id = %s AND sender_type IN ('ai', 'agent')
                """, (str(prerecorded_id),))
                prerecorded = cur.fetchone()
                if not prerecorded:
                    raise HTTPException(status_code=404, detail="WhatsApp outbound message not found")
                if not recipient_matches(cur, prerecorded[1]):
                    raise HTTPException(status_code=409, detail="Outbound recipient does not match the message's customer")
                result = claim(cur, prerecorded)
                conn.commit()
                return result
            if event.reply_to_provider_message_id:
                cur.execute("""
                    SELECT customer_id, conversation_id FROM messages
                    WHERE provider = 'whatsapp' AND provider_message_id = %s
                      AND sender_type = 'customer' LIMIT 1
                """, (event.reply_to_provider_message_id,))
                inbound = cur.fetchone()
                if not inbound:
                    raise HTTPException(status_code=404, detail="WhatsApp inbound message not found")
                customer_id, conversation_id = inbound
                if not recipient_matches(cur, customer_id):
                    raise HTTPException(status_code=409, detail="Outbound recipient does not match the inbound customer")
                cur.execute(f"""
                    SELECT {claim_columns} FROM messages
                    WHERE provider = 'whatsapp' AND reply_to_provider_message_id = %s
                      AND sender_type IN ('ai', 'agent') LIMIT 1
                """, (event.reply_to_provider_message_id,))
                existing = cur.fetchone()
                if existing:
                    result = claim(cur, existing)
                    conn.commit()
                    return result
            else:
                customer_query = "SELECT id FROM customers WHERE whatsapp_id = %s"
                cur.execute(customer_query + " LIMIT 1", (recipient,))
                customer = cur.fetchone()
                if not customer and phone:
                    cur.execute("SELECT id FROM customers WHERE phone_number = %s LIMIT 1", (phone,))
                    customer = cur.fetchone()
                if not customer:
                    raise HTTPException(status_code=404, detail="WhatsApp customer is not registered")
                customer_id = customer[0]
                cur.execute("""
                    SELECT id FROM conversations
                    WHERE customer_id = %s AND channel = 'whatsapp' AND status IN ('active', 'handed_off')
                    ORDER BY created_at DESC, id DESC LIMIT 1
                """, (customer_id,))
                conversation = cur.fetchone()
                if not conversation:
                    raise HTTPException(status_code=404, detail="Active WhatsApp conversation not found")
                conversation_id = conversation[0]
            cur.execute("""
                INSERT INTO messages
                    (conversation_id, customer_id, sender_type, content, provider,
                     reply_to_provider_message_id, delivery_status, delivery_updated_at, metadata)
                VALUES (%s, %s, 'ai', %s, 'whatsapp', %s, 'queued', CURRENT_TIMESTAMP,
                        jsonb_build_object('source', 'whatsapp_dispatch'))
                RETURNING id
            """, (conversation_id, customer_id, body, event.reply_to_provider_message_id))
            row = cur.fetchone()
            conn.commit()
            return {"message_id": str(row[0]), "customer_id": str(customer_id),
                    "conversation_id": str(conversation_id), "delivery_status": "queued", "duplicate": False}


@router.post("/internal/whatsapp/delivery")
async def update_whatsapp_delivery(
    event: WhatsAppDeliveryEvent,
    x_nexaserve_webhook_token: Optional[str] = Header(None, alias="X-NexaServe-Webhook-Token"),
):
    """Record provider send/receipt state; status is monotonic except terminal failures."""
    _require_whatsapp_ingest_token(x_nexaserve_webhook_token)
    allowed = {"sent", "delivered", "read", "failed", "undelivered"}
    new_status = event.delivery_status.strip().lower()
    provider_message_id = (event.provider_message_id or "").strip()
    if (not provider_message_id and not event.message_id) or new_status not in allowed:
        raise HTTPException(status_code=422, detail="Invalid WhatsApp delivery update")
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE messages
                SET delivery_status = CASE
                        WHEN delivery_status = 'read' THEN 'read'
                        WHEN %s = 'read' THEN 'read'
                        WHEN %s = 'delivered' AND delivery_status NOT IN ('failed', 'undelivered') THEN 'delivered'
                        WHEN %s = 'sent' AND delivery_status IN ('queued', 'sent') THEN 'sent'
                        WHEN %s IN ('failed', 'undelivered') AND delivery_status NOT IN ('delivered', 'read') THEN %s
                        ELSE delivery_status
                    END,
                    provider_message_id = COALESCE(provider_message_id, %s),
                    delivery_updated_at = CURRENT_TIMESTAMP
                WHERE provider = 'whatsapp'
                  AND ((%s IS NOT NULL AND id = %s::uuid)
                       OR (%s IS NULL AND provider_message_id = %s))
                RETURNING id, delivery_status
            """, (new_status, new_status, new_status, new_status, new_status,
                  provider_message_id or None, event.message_id, event.message_id,
                  event.message_id, provider_message_id))
            row = cur.fetchone()
            if not row:
                raise HTTPException(status_code=404, detail="WhatsApp message not found")
            conn.commit()
            return {"message_id": str(row[0]), "delivery_status": row[1]}

def _resolve_n8n_url(url: str) -> str:
    """Fallback hostname if running locally outside Docker network."""
    if "://n8n:5678" in url:
        try:
            socket.gethostbyname("n8n")
        except Exception:
            return url.replace("://n8n:5678", "://127.0.0.1:5678")
    return url

def _n8n_api_request(endpoint: str, method: str = "GET", payload: Optional[Dict[str, Any]] = None, timeout: float = 10.0) -> Tuple[int, Any, Optional[str]]:
    base = _resolve_n8n_url(N8N_API_URL)
    url = f"{base}{endpoint}"
    headers = {
        "X-N8N-API-KEY": N8N_API_KEY,
        "Accept": "application/json",
        "Content-Type": "application/json"
    }
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            res_body = response.read().decode("utf-8")
            return response.getcode(), json.loads(res_body) if res_body else {}, None
    except urllib.error.HTTPError as exc:
        try:
            err_body = exc.read().decode("utf-8")
            return exc.code, json.loads(err_body), str(exc)
        except Exception:
            return exc.code, None, str(exc)
    except Exception as exc:
        return 0, None, type(exc).__name__

def _n8n_webhook_post(url: str, payload: Dict[str, Any], timeout: float = 60.0) -> Tuple[int, Any, Optional[str], float]:
    target_url = _resolve_n8n_url(url)
    # Webhooks authenticate with the shared service token (n8n header auth), never the n8n API
    # key, which would be stored in execution data.
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "X-NexaServe-Webhook-Token": WHATSAPP_INGEST_TOKEN,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(target_url, data=data, headers=headers, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            lat = round((time.time() - t0) * 1000, 1)
            raw = response.read().decode("utf-8")
            try:
                parsed = json.loads(raw) if raw else {}
            except Exception:
                parsed = {"raw": raw}
            return response.getcode(), parsed, None, lat
    except urllib.error.HTTPError as exc:
        lat = round((time.time() - t0) * 1000, 1)
        try:
            err_raw = exc.read().decode("utf-8")
            err_body = json.loads(err_raw)
        except Exception:
            err_body = {"error": str(exc)}
        return exc.code, err_body, str(exc), lat
    except Exception as exc:
        lat = round((time.time() - t0) * 1000, 1)
        return 0, None, str(exc), lat

def _http_probe(url: str, timeout: float = 2.0) -> Tuple[int, Optional[str]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            return response.getcode(), None
    except Exception as exc:
        return 0, type(exc).__name__

def _whatsapp_probe(url: str, timeout: float = 2.0) -> Tuple[int, bool, Optional[str]]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            body = json.loads(response.read().decode("utf-8"))
            return response.getcode(), body.get("connected") is True, None
    except Exception as exc:
        return 0, False, type(exc).__name__

def _is_official_source(url: Optional[str]) -> bool:
    if not url:
        return False
    match = re.match(r"^https://([^/:]+)", url.strip(), flags=re.IGNORECASE)
    if not match:
        return False
    host = match.group(1).lower().rstrip(".")
    return host == "gov.eg" or host.endswith(".gov.eg")

def _execution_status(events: List[Dict[str, Any]]) -> str:
    if any(e["event_type"] == "error" or e["payload"].get("llm_status") == "failed" for e in events):
        return "failed"
    if any(e["payload"].get("guardrail_decision") in {"verified_faq_fallback", "llm_failed_faq_fallback"} for e in events):
        return "fallback"
    if any(e["event_type"] == "turn_completed" for e in events):
        return "completed"
    return "unknown"


async def _collect_export_pages(fetch_page, limit: int = 100) -> List[Dict[str, Any]]:
    """Fetch every matching page through the same authorized view as the UI."""
    first = await fetch_page(1, limit)
    total = int(first.get("total", len(first.get("items", []))) or 0)
    if total > MAX_EXPORT_ROWS:
        raise HTTPException(status_code=413, detail=f"Export exceeds the {MAX_EXPORT_ROWS} row limit")
    result = list(first.get("items", []))
    pages = int(first.get("pages", 1) or 1)
    for page in range(2, pages + 1):
        data = await fetch_page(page, limit)
        result.extend(data.get("items", []))
    if len(result) != total:
        raise HTTPException(status_code=409, detail="Report data changed during generation; retry the export")
    identity_key = next((key for key in ("id", "ticket_number", "request_id")
                         if all(key in row for row in result)), None)
    if identity_key and len({str(row[identity_key]) for row in result}) != len(result):
        raise HTTPException(status_code=409, detail="Report data changed during generation; retry the export")
    return result


def _metric_rows(data: Dict[str, Any], labels: Dict[str, str]) -> List[Dict[str, Any]]:
    return [{"metric": labels.get(key, key.replace("_", " ").title()), "value": value}
            for key, value in data.items()]


def _report_columns(lang: str, fields: List[Tuple[str, str, str, str]]) -> List[Dict[str, str]]:
    """Field tuples are key, English header, Arabic header, and data type."""
    return [{"key": key, "label": ar if lang == "ar" else en, "type": kind}
            for key, en, ar, kind in fields]


async def _report_timeout_scope():
    token = REPORT_QUERY_DEADLINE.set(time.monotonic() + 30)
    try:
        yield None
    finally:
        REPORT_QUERY_DEADLINE.reset(token)

# PII Masking Utility
def mask_phone(phone: Optional[str], authorized: bool = False) -> Optional[str]:
    if not phone:
        return None
    if authorized:
        return phone
    # Mask middle digits: e.g. +201234567890 -> +2012****7890
    clean = phone.strip()
    if len(clean) > 7:
        prefix = clean[:5]
        suffix = clean[-3:]
        return f"{prefix}****{suffix}"
    return "****"

def mask_email(email: Optional[str], authorized: bool = False) -> Optional[str]:
    if not email:
        return None
    if authorized:
        return email
    parts = email.split("@")
    if len(parts) == 2:
        name, domain = parts
        masked_name = name[:2] + "****" if len(name) > 2 else "****"
        return f"{masked_name}@{domain}"
    return "****"

def build_date_filter(period: Optional[str], start_date: Optional[str], end_date: Optional[str], col: str = "created_at") -> Tuple[str, List[Any]]:
    params: List[Any] = []
    if period == "today":
        return f" AND {col} >= CURRENT_DATE", params
    elif period == "yesterday":
        return f" AND {col} >= CURRENT_DATE - INTERVAL '1 day' AND {col} < CURRENT_DATE", params
    elif period == "7d":
        return f" AND {col} >= NOW() - INTERVAL '7 days'", params
    elif period == "30d":
        return f" AND {col} >= NOW() - INTERVAL '30 days'", params
    elif period == "month":
        return f" AND {col} >= date_trunc('month', CURRENT_DATE)", params
    elif start_date and end_date:
        params.extend([start_date, end_date])
        return f" AND {col} >= %s::timestamptz AND {col} <= %s::timestamptz", params
    return "", params

# --- 1. EXECUTIVE KPI CARDS ---
@router.get("/summary")
async def get_summary(
    period: Optional[str] = Query(None),
    program: Optional[str] = Query("all"),
    user: Dict[str, Any] = Depends(get_current_user)
):
    # Total customers
    cust_prog_filter = ""
    cust_params: List[Any] = []
    if program and program.upper() != "ALL":
        cust_prog_filter = " WHERE (metadata->>'program') ILIKE %s"
        cust_params.append(f"%{program}%")
    
    total_customers_row = query_one(f"SELECT COUNT(*) as count FROM customers{cust_prog_filter}", tuple(cust_params))
    total_customers = total_customers_row["count"] if total_customers_row else 0

    # Conversations
    conv_filter = " WHERE 1=1"
    conv_params: List[Any] = []
    if program and program.upper() != "ALL":
        conv_filter += " AND c.id IN (SELECT conv.id FROM conversations conv JOIN customers cust ON conv.customer_id = cust.id WHERE (cust.metadata->>'program') ILIKE %s)"
        conv_params.append(f"%{program}%")
    
    d_filter, d_params = build_date_filter(period, None, None, "c.created_at")
    conv_filter += d_filter
    conv_params.extend(d_params)

    conv_stats = query_one(f"""
        SELECT 
            COUNT(*) as total_convs,
            COUNT(CASE WHEN c.status = 'active' THEN 1 END) as active_convs,
            COUNT(CASE WHEN c.status = 'handed_off' OR c.current_intent = 'human_escalation' THEN 1 END) as escalated_convs
        FROM conversations c {conv_filter}
    """, tuple(conv_params))

    total_convs = conv_stats["total_convs"] if conv_stats else 0
    active_convs = conv_stats["active_convs"] if conv_stats else 0
    escalated_convs = conv_stats["escalated_convs"] if conv_stats else 0

    # Tickets
    tick_filter = " WHERE 1=1"
    tick_params: List[Any] = []
    if program and program.upper() != "ALL":
        tick_filter += " AND t.customer_id IN (SELECT id FROM customers WHERE (metadata->>'program') ILIKE %s)"
        tick_params.append(f"%{program}%")
    
    td_filter, td_params = build_date_filter(period, None, None, "t.created_at")
    tick_filter += td_filter
    tick_params.extend(td_params)

    ticket_stats = query_one(f"""
        SELECT 
            COUNT(*) as total_tickets,
            COUNT(CASE WHEN t.status = 'open' THEN 1 END) as open_tickets,
            COUNT(CASE WHEN t.status = 'in_progress' OR t.status = 'assigned' THEN 1 END) as pending_tickets,
            COUNT(CASE WHEN t.status = 'resolved' OR t.status = 'closed' THEN 1 END) as resolved_tickets,
            COUNT(CASE WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 1 END) as sla_breaches
        FROM tickets t {tick_filter}
    """, tuple(tick_params))

    open_tickets = ticket_stats["open_tickets"] if ticket_stats else 0
    pending_tickets = ticket_stats["pending_tickets"] if ticket_stats else 0
    resolved_tickets = ticket_stats["resolved_tickets"] if ticket_stats else 0
    sla_breaches = ticket_stats["sla_breaches"] if ticket_stats else 0

    # Response Time (Latency from audit_logs) & RAG Success Rate
    perf_where = " WHERE event_type = 'turn_completed'"
    perf_params: List[Any] = []
    if program and program.upper() != "ALL":
        perf_where += " AND payload->>'program' ILIKE %s"
        perf_params.append(f"%{program}%")
    perf_date_filter, perf_date_params = build_date_filter(period, None, None, "created_at")
    perf_where += perf_date_filter
    perf_params.extend(perf_date_params)
    perf_stats = query_one(f"""
        SELECT 
            AVG(latency_ms) as avg_latency,
            COUNT(CASE WHEN payload->>'status' = 'success' THEN 1 END) as success_turns,
            COUNT(*) as total_turns
        FROM audit_logs
        {perf_where}
    """, tuple(perf_params))
    avg_latency_ms = round(float(perf_stats["avg_latency"]), 1) if perf_stats and perf_stats["avg_latency"] is not None else None
    total_turns = perf_stats["total_turns"] if perf_stats else 0
    success_turns = perf_stats["success_turns"] if perf_stats else 0
    rag_success_rate = round((success_turns / total_turns) * 100, 1) if total_turns else None

    return {
        "total_customers": total_customers,
        "active_conversations": active_convs,
        "total_conversations": total_convs,
        "open_tickets": open_tickets,
        "pending_tickets": pending_tickets,
        "resolved_tickets": resolved_tickets,
        "sla_breaches": sla_breaches,
        "escalated_conversations": escalated_convs,
        "avg_response_time_ms": avg_latency_ms,
        "rag_success_rate": rag_success_rate
    }

# --- 2. CUSTOMER / STUDENT ANALYTICS ---
@router.get("/customers")
async def get_customers(
    search: Optional[str] = Query(None),
    program: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    offset = (page - 1) * limit
    where_clauses = ["1=1"]
    params: List[Any] = []

    if program and program.upper() != "ALL":
        where_clauses.append("(c.metadata->>'program') ILIKE %s")
        params.append(f"%{program}%")

    if search:
        where_clauses.append("(c.full_name ILIKE %s OR c.phone_number ILIKE %s OR c.email ILIKE %s)")
        params.extend([f"%{search}%", f"%{search}%", f"%{search}%"])

    where_sql = " AND ".join(where_clauses)
    
    total_row = query_one(f"SELECT COUNT(*) as count FROM customers c WHERE {where_sql}", tuple(params))
    total_count = total_row["count"] if total_row else 0

    query_params = list(params) + [limit, offset]
    rows = query_all(f"""
        SELECT 
            c.id, 
            c.full_name, 
            c.phone_number, 
            c.email,
            COALESCE(c.metadata->>'program', 'UNKNOWN') as program,
            c.created_at,
            c.last_activity_at,
            (SELECT COUNT(*) FROM conversations WHERE customer_id = c.id) as conversation_count,
            (SELECT COUNT(*) FROM tickets WHERE customer_id = c.id AND status = 'open') as open_tickets,
            CASE 
                WHEN (SELECT COUNT(*) FROM tickets WHERE customer_id = c.id AND status = 'open') > 0 THEN 'Pending Action'
                ELSE 'Active'
            END as customer_status
        FROM customers c
        WHERE {where_sql}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
    """, tuple(query_params))

    # RBAC PII Masking: Only admin can see unmasked PII
    can_view_pii = (user.get("role") == "admin")

    items = []
    for r in rows:
        items.append({
            "id": str(r["id"]),
            "full_name": r["full_name"],
            "phone_masked": mask_phone(r["phone_number"], can_view_pii),
            "email_masked": mask_email(r["email"], can_view_pii),
            "program": r["program"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "last_interaction": r["last_activity_at"].isoformat() if r["last_activity_at"] else (r["created_at"].isoformat() if r["created_at"] else None),
            "conversation_count": r["conversation_count"],
            "open_tickets": r["open_tickets"],
            "customer_status": r["customer_status"]
        })

    return {
        "items": items,
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit
    }

@router.get("/customers/{customer_id}")
async def get_customer_profile(
    customer_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Return an authorized customer profile and a paginated list of their conversations."""
    try:
        customer_uuid = str(UUID(customer_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=404, detail="Customer not found")

    customer = query_one("""
        SELECT id, full_name, phone_number, email, preferred_language, metadata, created_at,
               (SELECT MAX(m.created_at) FROM conversations c
                JOIN messages m ON m.conversation_id = c.id
                WHERE c.customer_id = customers.id) AS last_activity_at
        FROM customers WHERE id = %s
    """, (customer_uuid,))
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")

    total_row = query_one("SELECT COUNT(*) AS count FROM conversations WHERE customer_id = %s", (customer_uuid,))
    total = int(total_row["count"] if total_row else 0)
    conversations = query_all("""
        SELECT c.id, c.channel, c.status, c.current_intent, c.language, c.created_at, c.closed_at,
               (SELECT COUNT(*) FROM messages m WHERE m.conversation_id = c.id
                 AND m.sender_type IN ('customer', 'ai', 'agent')) AS message_count,
               (SELECT MAX(m.created_at) FROM messages m WHERE m.conversation_id = c.id
                 AND m.sender_type IN ('customer', 'ai', 'agent')) AS last_message_at
        FROM conversations c
        WHERE c.customer_id = %s
        ORDER BY c.created_at DESC, c.id DESC
        LIMIT %s OFFSET %s
    """, (customer_uuid, limit, (page - 1) * limit))
    can_view_pii = user.get("role") == "admin"
    metadata = customer.get("metadata") or {}
    return {
        "customer": {
            "id": str(customer["id"]),
            "full_name": customer["full_name"],
            "phone_masked": mask_phone(customer.get("phone_number"), can_view_pii),
            "email_masked": mask_email(customer.get("email"), can_view_pii),
            "preferred_language": customer.get("preferred_language"),
            "program": metadata.get("program", "UNKNOWN"),
            "created_at": customer["created_at"].isoformat() if customer.get("created_at") else None,
            "last_activity_at": customer["last_activity_at"].isoformat() if customer.get("last_activity_at") else None
        },
        "conversations": [{
            "id": str(row["id"]), "channel": row["channel"], "status": row["status"],
            "intent": row["current_intent"], "language": row["language"],
            "created_at": row["created_at"].isoformat() if row.get("created_at") else None,
            "closed_at": row["closed_at"].isoformat() if row.get("closed_at") else None,
            "last_message_at": row["last_message_at"].isoformat() if row.get("last_message_at") else None,
            "message_count": row["message_count"]
        } for row in conversations],
        "total": total, "page": page, "limit": limit,
        "pages": (total + limit - 1) // limit
    }

# --- 3. CONVERSATION ANALYTICS ---
@router.get("/conversations")
async def get_conversations(
    period: Optional[str] = Query(None),
    program: Optional[str] = Query("all"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    offset = (page - 1) * limit
    where_clauses = ["1=1"]
    params: List[Any] = []

    if program and program.upper() != "ALL":
        where_clauses.append("(cust.metadata->>'program') ILIKE %s")
        params.append(f"%{program}%")

    d_filter, d_params = build_date_filter(period, None, None, "c.created_at")
    where_clauses.append(d_filter.replace(" AND ", "", 1) if d_filter else "1=1")
    params.extend(d_params)

    where_sql = " AND ".join(where_clauses)

    total_row = query_one(f"""
        SELECT COUNT(*) as count 
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
    """, tuple(params))
    total_count = total_row["count"] if total_row else 0

    query_params = list(params) + [limit, offset]
    rows = query_all(f"""
        SELECT 
            c.id,
            c.customer_id,
            cust.full_name as customer_name,
            COALESCE(cust.metadata->>'program', 'UNKNOWN') as program,
            c.channel,
            c.status,
            COALESCE(c.current_intent, 'general_inquiry') as current_intent,
            c.language,
            c.created_at,
            c.closed_at,
            (SELECT COUNT(*) FROM messages WHERE conversation_id = c.id) as message_count,
            (SELECT AVG(confidence) FROM messages WHERE conversation_id = c.id AND confidence IS NOT NULL) as avg_confidence,
            (SELECT MAX(created_at) FROM messages WHERE conversation_id = c.id) as last_activity_at,
            (SELECT COALESCE(json_agg(json_build_object(
                'id', t.id,
                'ticket_number', t.ticket_number,
                'status', t.status,
                'priority', t.priority,
                'reason', t.reason,
                'created_at', t.created_at
            ) ORDER BY t.created_at DESC), '[]'::json)
             FROM tickets t WHERE t.conversation_id = c.id) as tickets
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
        ORDER BY c.created_at DESC
        LIMIT %s OFFSET %s
    """, tuple(query_params))

    # Aggregate metrics for conversation analytics
    summary_counts = query_one(f"""
        SELECT 
            COUNT(*) as total,
            COUNT(CASE WHEN c.created_at >= CURRENT_DATE THEN 1 END) as today_count,
            COUNT(CASE WHEN c.created_at >= NOW() - INTERVAL '7 days' THEN 1 END) as week_count,
            COUNT(CASE WHEN c.status = 'handed_off' OR c.current_intent = 'human_escalation' THEN 1 END) as escalated_count
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
    """, tuple(params))

    # Aggregations for charts
    prog_dist = query_all(f"""
        SELECT COALESCE(cust.metadata->>'program', 'UNKNOWN') as label, COUNT(*) as count
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
        GROUP BY 1
    """, tuple(params))

    intent_dist = query_all(f"""
        SELECT COALESCE(c.current_intent, 'general_inquiry') as label, COUNT(*) as count
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
        GROUP BY 1
    """, tuple(params))

    lang_dist = query_all(f"""
        SELECT COALESCE(c.language, 'ar') as label, COUNT(*) as count
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
        GROUP BY 1
    """, tuple(params))

    time_series = query_all(f"""
        SELECT TO_CHAR(c.created_at, 'YYYY-MM-DD') as date_label, COUNT(*) as count
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE {where_sql}
        GROUP BY 1
        ORDER BY 1 ASC
        LIMIT 14
    """, tuple(params))

    total_c = summary_counts["total"] if summary_counts and summary_counts["total"] > 0 else 1
    esc_c = summary_counts["escalated_count"] if summary_counts else 0

    return {
        "items": [{
            "id": str(r["id"]),
            "customer_id": str(r["customer_id"]),
            "customer_name": r["customer_name"],
            "program": r["program"],
            "channel": r["channel"],
            "status": r["status"],
            "intent": r["current_intent"],
            "language": r["language"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "last_activity_at": r["last_activity_at"].isoformat() if r.get("last_activity_at") else (r["created_at"].isoformat() if r.get("created_at") else None),
            "message_count": r["message_count"],
            "avg_confidence": round(float(r["avg_confidence"]), 2) if r["avg_confidence"] else None,
            "tickets": [{
                "id": str(t["id"]),
                "ticket_number": t["ticket_number"],
                "status": t["status"],
                "priority": t["priority"],
                "reason": t.get("reason"),
                "created_at": t["created_at"].isoformat() if isinstance(t.get("created_at"), datetime) else t.get("created_at")
            } for t in (r.get("tickets") or [])],
            "ticket_count": len(r.get("tickets") or [])
        } for r in rows],
        "metrics": {
            "total_conversations": summary_counts["total"] if summary_counts else 0,
            "conversations_today": summary_counts["today_count"] if summary_counts else 0,
            "conversations_this_week": summary_counts["week_count"] if summary_counts else 0,
            "escalation_rate": round((esc_c / total_c) * 100, 1),
            "avg_conversation_length": round(float(query_one("SELECT AVG(msg_count) as avg_len FROM (SELECT COUNT(*) as msg_count FROM messages GROUP BY conversation_id) sub")["avg_len"] or 0), 1)
        },
        "charts": {
            "conversations_over_time": time_series,
            "program_distribution": prog_dist,
            "intent_distribution": intent_dist,
            "language_distribution": lang_dist
        },
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit
    }

# --- 4. TICKET / HITL DASHBOARD & LIFECYCLE MANAGEMENT ---
class TicketCreateRequest(BaseModel):
    title: Optional[str] = None
    reason: str
    customer_id: Optional[str] = None
    customer_phone: Optional[str] = None
    customer_name: Optional[str] = None
    conversation_id: Optional[str] = None
    category: Optional[str] = "complaint"
    priority: Optional[str] = "medium"
    source_channel: Optional[str] = "whatsapp"
    external_message_id: Optional[str] = None
    idempotency_key: Optional[str] = None
    assigned_team: Optional[str] = "DEPI Citizen Support"
    assigned_agent: Optional[str] = None

class TicketUpdateRequest(BaseModel):
    status: Optional[str] = None
    priority: Optional[str] = None
    assigned_agent: Optional[str] = None
    assigned_team: Optional[str] = None
    category_id: Optional[int] = None
    title: Optional[str] = None
    resolution_notes: Optional[str] = None
    internal_notes: Optional[str] = None

class TicketNoteRequest(BaseModel):
    note: str
    author: Optional[str] = None

@router.get("/tickets")
async def get_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    channel: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    program: Optional[str] = Query("all"),
    sla_breached: Optional[bool] = Query(None),
    sort_by: Optional[str] = Query("created_at"),
    sort_dir: Optional[str] = Query("desc"),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    offset = (page - 1) * limit
    where_clauses = ["1=1"]
    params: List[Any] = []

    if priority and priority.lower() != "all":
        where_clauses.append("t.priority = %s")
        params.append(priority.lower())

    if category and category.lower() != "all":
        where_clauses.append("EXISTS (SELECT 1 FROM ticket_categories tc_filter WHERE tc_filter.id = t.category_id AND (tc_filter.name ILIKE %s OR tc_filter.name_ar ILIKE %s))")
        params.extend([f"%{category}%", f"%{category}%"])

    if channel and channel.lower() != "all":
        where_clauses.append("(t.source_channel ILIKE %s OR t.escalation_channel ILIKE %s)")
        params.extend([f"%{channel}%", f"%{channel}%"])

    if search and search.strip():
        term = f"%{search.strip()}%"
        where_clauses.append("(t.ticket_number ILIKE %s OR COALESCE(t.title, '') ILIKE %s OR t.reason ILIKE %s OR c.full_name ILIKE %s OR COALESCE(c.phone_number, '') ILIKE %s)")
        params.extend([term, term, term, term, term])

    if program and program.upper() != "ALL":
        where_clauses.append("(c.metadata->>'program') ILIKE %s")
        params.append(f"%{program}%")

    if sla_breached is True:
        where_clauses.append("t.status = 'open' AND t.sla_due_at < NOW()")
    elif sla_breached is False:
        where_clauses.append("(t.status != 'open' OR t.sla_due_at >= NOW())")

    # KPI cards summarise every status for the other active filters.
    metrics_row = query_one(f"""
        SELECT COUNT(*) AS total,
               COUNT(*) FILTER (WHERE t.status = 'open') AS open,
               COUNT(*) FILTER (WHERE t.status IN ('in_progress', 'assigned')) AS pending,
               COUNT(*) FILTER (WHERE t.status = 'open' AND t.sla_due_at < NOW()) AS breached,
               COUNT(*) FILTER (WHERE t.status IN ('resolved', 'closed')) AS resolved
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE {" AND ".join(where_clauses)}
    """, tuple(params)) or {}

    if status and status.lower() != "all":
        where_clauses.append("t.status = %s")
        params.append(status.lower())

    where_sql = " AND ".join(where_clauses)

    total_row = query_one(f"""
        SELECT COUNT(*) as count
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE {where_sql}
    """, tuple(params))
    total_count = total_row["count"] if total_row else 0

    # Dynamic sorting
    sort_dir_norm = "ASC" if sort_dir and sort_dir.lower() == "asc" else "DESC"
    if sort_by == "sla":
        order_sql = f"CASE WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 1 ELSE 2 END, t.sla_due_at {sort_dir_norm}"
    elif sort_by == "priority":
        order_sql = f"CASE t.priority WHEN 'urgent' THEN 1 WHEN 'high' THEN 2 WHEN 'medium' THEN 3 ELSE 4 END, t.created_at {sort_dir_norm}"
    else:
        order_sql = f"t.created_at {sort_dir_norm}"

    can_view_pii = (user.get("role") in ("admin", "supervisor"))
    query_params = list(params) + [limit, offset]
    rows = query_all(f"""
        SELECT 
            t.id,
            t.ticket_number,
            COALESCE(t.title, t.reason) as title,
            t.customer_id,
            t.conversation_id,
            c.full_name as customer_name,
            c.phone_number as customer_phone,
            COALESCE(c.metadata->>'program', 'UNKNOWN') as program,
            t.priority,
            t.status,
            COALESCE(t.assigned_agent, 'Unassigned') as assigned_agent,
            COALESCE(t.assigned_team, 'DEPI Citizen Support') as assigned_team,
            t.reason,
            COALESCE(tc.name, 'general') as category_name,
            COALESCE(tc.name_ar, 'عام') as category_name_ar,
            COALESCE(t.source_channel, t.escalation_channel, 'whatsapp') as source_channel,
            t.created_at,
            t.sla_due_at,
            t.updated_at,
            t.closed_at,
            CASE 
                WHEN t.status IN ('resolved', 'closed') THEN 'RESOLVED'
                WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 'BREACHED'
                WHEN t.status = 'open' AND t.sla_due_at < NOW() + INTERVAL '2 hours' THEN 'AT_RISK'
                ELSE 'ON_TRACK'
            END as sla_status
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        LEFT JOIN ticket_categories tc ON t.category_id = tc.id
        WHERE {where_sql}
        ORDER BY {order_sql}
        LIMIT %s OFFSET %s
    """, tuple(query_params))

    return {
        "items": [{
            "id": str(r["id"]),
            "ticket_number": r["ticket_number"],
            "title": r["title"],
            "customer_id": str(r["customer_id"]),
            "conversation_id": str(r["conversation_id"]) if r.get("conversation_id") else None,
            "customer_name": r["customer_name"],
            "customer_phone_masked": mask_phone(r["customer_phone"], can_view_pii),
            "program": r["program"],
            "priority": r["priority"],
            "status": r["status"],
            "assigned_agent": r["assigned_agent"],
            "assigned_team": r["assigned_team"],
            "category_name": r["category_name"],
            "category_name_ar": r["category_name_ar"],
            "source_channel": r["source_channel"],
            "reason": r["reason"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "sla_deadline": r["sla_due_at"].isoformat() if r["sla_due_at"] else None,
            "sla_status": r["sla_status"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None,
            "closed_at": r["closed_at"].isoformat() if r["closed_at"] else None
        } for r in rows],
        "metrics": {key: int(metrics_row.get(key) or 0) for key in ("total", "open", "pending", "breached", "resolved")},
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit
    }

@router.get("/tickets/{ticket_id}")
async def get_ticket_details(
    ticket_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    ticket = query_one("""
        SELECT 
            t.id,
            t.ticket_number,
            t.title,
            t.customer_id,
            c.full_name as customer_name,
            c.phone_number as customer_phone,
            c.email as customer_email,
            COALESCE(c.metadata->>'program', 'UNKNOWN') as program,
            t.conversation_id,
            t.priority,
            t.status,
            COALESCE(t.assigned_agent, 'Unassigned') as assigned_agent,
            COALESCE(t.assigned_team, 'DEPI Citizen Support') as assigned_team,
            t.reason,
            t.resolution_notes,
            t.internal_notes,
            COALESCE(tc.name, 'general') as category_name,
            COALESCE(tc.name_ar, 'عام') as category_name_ar,
            COALESCE(t.source_channel, t.escalation_channel, 'whatsapp') as source_channel,
            t.created_at,
            t.sla_due_at,
            t.updated_at,
            t.closed_at,
            t.tags,
            CASE 
                WHEN t.status IN ('resolved', 'closed') THEN 'RESOLVED'
                WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 'BREACHED'
                WHEN t.status = 'open' AND t.sla_due_at < NOW() + INTERVAL '2 hours' THEN 'AT_RISK'
                ELSE 'ON_TRACK'
            END as sla_status
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        LEFT JOIN ticket_categories tc ON t.category_id = tc.id
        WHERE t.id::text = %s OR t.ticket_number = %s
    """, (ticket_id, ticket_id))

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    can_view_pii = (user.get("role") in ("admin", "supervisor"))

    # Fetch events timeline
    events = query_all("""
        SELECT id, event_type, actor_type, actor_name, old_value, new_value, message, created_at
        FROM ticket_events
        WHERE ticket_id = %s OR ticket_number = %s
        ORDER BY created_at ASC
    """, (ticket["id"], ticket["ticket_number"]))

    # Fetch conversation messages if conversation_id exists
    messages = []
    if ticket.get("conversation_id"):
        messages = query_all("""
            SELECT id, sender_type, content, intent, created_at
            FROM messages
            WHERE conversation_id = %s
            ORDER BY created_at ASC
        """, (ticket["conversation_id"],))

    return {
        "id": str(ticket["id"]),
        "ticket_number": ticket["ticket_number"],
        "title": ticket["title"] or ticket["reason"][:60],
        "conversation_id": str(ticket["conversation_id"]) if ticket.get("conversation_id") else None,
        "customer": {
            "id": str(ticket["customer_id"]),
            "full_name": ticket["customer_name"],
            "phone_masked": mask_phone(ticket["customer_phone"], can_view_pii),
            "email_masked": mask_email(ticket["customer_email"], can_view_pii),
            "program": ticket["program"]
        },
        "priority": ticket["priority"],
        "status": ticket["status"],
        "assigned_agent": ticket["assigned_agent"],
        "assigned_team": ticket["assigned_team"],
        "reason": ticket["reason"],
        "resolution_notes": ticket["resolution_notes"],
        "internal_notes": ticket["internal_notes"],
        "category_name": ticket["category_name"],
        "category_name_ar": ticket["category_name_ar"],
        "source_channel": ticket["source_channel"],
        "tags": ticket.get("tags") or [],
        "created_at": ticket["created_at"].isoformat() if ticket["created_at"] else None,
        "updated_at": ticket["updated_at"].isoformat() if ticket["updated_at"] else None,
        "closed_at": ticket["closed_at"].isoformat() if ticket["closed_at"] else None,
        "sla_deadline": ticket["sla_due_at"].isoformat() if ticket["sla_due_at"] else None,
        "sla_status": ticket["sla_status"],
        "timeline": [{
            "id": str(e["id"]),
            "event_type": e["event_type"],
            "actor_type": e["actor_type"],
            "actor_name": e["actor_name"],
            "old_value": e["old_value"],
            "new_value": e["new_value"],
            "message": e["message"],
            "created_at": e["created_at"].isoformat() if e["created_at"] else None
        } for e in events],
        "messages": [{
            "id": str(m["id"]),
            "sender_type": m["sender_type"],
            "content": m["content"],
            "intent": m["intent"],
            "created_at": m["created_at"].isoformat() if m["created_at"] else None
        } for m in messages]
    }

@router.post("/tickets")
async def create_or_upsert_ticket(
    req: TicketCreateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    import random

    # 1. Idempotency check: prevent duplicate ticket on webhook retries
    if req.external_message_id or req.idempotency_key:
        existing = query_one("""
            SELECT id, ticket_number, status, priority, reason, created_at, assigned_team
            FROM tickets
            WHERE (external_message_id IS NOT NULL AND external_message_id = %s)
               OR (idempotency_key IS NOT NULL AND idempotency_key = %s)
            LIMIT 1
        """, (req.external_message_id or "__none__", req.idempotency_key or "__none__"))
        if existing:
            return {
                "id": str(existing["id"]),
                "ticket_number": existing["ticket_number"],
                "status": existing["status"],
                "priority": existing["priority"],
                "is_duplicate": True,
                "is_followup": False,
                "message": "Existing ticket returned for idempotent request"
            }

    # 2. Customer resolution
    customer_id = req.customer_id
    if not customer_id and req.customer_phone:
        cleaned_phone = req.customer_phone.strip()
        cust_row = query_one(
            "SELECT id FROM customers WHERE phone_number = %s OR whatsapp_id = %s LIMIT 1",
            (cleaned_phone, cleaned_phone)
        )
        if cust_row:
            customer_id = str(cust_row["id"])
        else:
            new_cust = query_one("""
                INSERT INTO customers (phone_number, whatsapp_id, full_name, preferred_language, metadata)
                VALUES (%s, %s, %s, 'ar', '{"program": "DEPI"}'::jsonb)
                RETURNING id
            """, (cleaned_phone, cleaned_phone, req.customer_name or "WhatsApp Citizen"))
            if new_cust:
                customer_id = str(new_cust["id"])

    if not customer_id:
        customer_id = "a0000000-0000-0000-0000-000000000001"

    # 3. Active ticket follow-up linking: prevent spamming duplicate tickets on consecutive messages
    active_ticket = query_one("""
        SELECT id, ticket_number, status, priority
        FROM tickets
        WHERE customer_id = %s
          AND status IN ('open', 'in_progress', 'assigned', 'waiting_for_customer')
          AND created_at > NOW() - INTERVAL '24 hours'
        ORDER BY created_at DESC
        LIMIT 1
    """, (customer_id,))

    if active_ticket:
        execute_commit("""
            INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, message)
            VALUES (%s, %s, 'customer_followup', 'customer', %s, %s)
        """, (active_ticket["id"], active_ticket["ticket_number"], req.customer_name or "Customer", req.reason))
        execute_commit("UPDATE tickets SET updated_at = NOW() WHERE id = %s", (active_ticket["id"],))

        return {
            "id": str(active_ticket["id"]),
            "ticket_number": active_ticket["ticket_number"],
            "status": active_ticket["status"],
            "priority": active_ticket["priority"],
            "is_followup": True,
            "is_duplicate": False,
            "message": "Message appended to active ticket timeline"
        }

    # 4. Create new ticket
    ticket_num = f"TICK-{random.randint(10000, 99999)}"
    while query_one("SELECT 1 FROM tickets WHERE ticket_number = %s", (ticket_num,)):
        ticket_num = f"TICK-{random.randint(10000, 99999)}"

    # Category resolution
    cat_id = 9  # default 'complaint'
    if req.category:
        cat_row = query_one(
            "SELECT id FROM ticket_categories WHERE name ILIKE %s OR name_ar ILIKE %s LIMIT 1",
            (req.category, req.category)
        )
        if cat_row:
            cat_id = cat_row["id"]

    priority = (req.priority or "medium").lower()
    if priority not in ("low", "medium", "high", "urgent"):
        priority = "medium"

    sla_interval = "INTERVAL '30 minutes'" if priority == "urgent" else ("INTERVAL '2 hours'" if priority == "high" else "INTERVAL '24 hours'")
    title = req.title or (req.reason[:60] if req.reason else "Customer Support Ticket")

    row = query_one(f"""
        INSERT INTO tickets (
            ticket_number, customer_id, conversation_id, title, reason, priority, status,
            assigned_team, assigned_agent, category_id, source_channel, external_message_id,
            idempotency_key, sla_due_at, created_at, updated_at
        ) VALUES (
            %s, %s, %s, %s, %s, %s, 'open',
            %s, %s, %s, %s, %s,
            %s, CURRENT_TIMESTAMP + {sla_interval}, NOW(), NOW()
        )
        RETURNING id, ticket_number, status, priority, sla_due_at, created_at
    """, (
        ticket_num, customer_id, req.conversation_id, title,
        req.reason, priority, req.assigned_team or "DEPI Citizen Support", req.assigned_agent,
        cat_id, req.source_channel or "whatsapp", req.external_message_id, req.idempotency_key
    ))

    ticket_db_id = row["id"]

    # Record initial lifecycle event
    execute_commit("""
        INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, message, new_value)
        VALUES (%s, %s, 'created', 'customer', %s, %s, 'open')
    """, (ticket_db_id, ticket_num, req.customer_name or "Customer", req.reason))

    # Audit log
    execute_commit("""
        INSERT INTO audit_logs (workflow_name, event_type, channel, payload)
        VALUES ('dashboard_ticket_api', 'ticket_created', %s, %s)
    """, (req.source_channel or "whatsapp", json.dumps({
        "ticket_number": ticket_num,
        "priority": priority,
        "category_id": cat_id,
        "customer_id": str(customer_id)
    })))

    return {
        "id": str(ticket_db_id),
        "ticket_number": ticket_num,
        "status": "open",
        "priority": priority,
        "sla_due_at": row["sla_due_at"].isoformat() if row["sla_due_at"] else None,
        "created_at": row["created_at"].isoformat() if row["created_at"] else None,
        "is_followup": False,
        "is_duplicate": False
    }

@router.patch("/tickets/{ticket_id}")
async def update_ticket(
    ticket_id: str,
    req: TicketUpdateRequest,
    user: Dict[str, Any] = Depends(require_role("admin", "agent", "supervisor"))
):
    ticket = query_one("""
        SELECT id, ticket_number, status, priority, assigned_agent, assigned_team, category_id, title
        FROM tickets
        WHERE id::text = %s OR ticket_number = %s
    """, (ticket_id, ticket_id))

    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    updates = []
    params = []
    actor_name = user.get("full_name") or user.get("username", "Agent")

    if req.status and req.status != ticket["status"]:
        updates.append("status = %s")
        params.append(req.status)
        if req.status in ("resolved", "closed"):
            updates.append("closed_at = NOW()")
        elif ticket["status"] in ("resolved", "closed"):
            updates.append("closed_at = NULL")
        execute_commit("""
            INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, old_value, new_value)
            VALUES (%s, %s, 'status_change', 'agent', %s, %s, %s)
        """, (ticket["id"], ticket["ticket_number"], actor_name, ticket["status"], req.status))

    if req.priority and req.priority != ticket["priority"]:
        updates.append("priority = %s")
        params.append(req.priority)
        execute_commit("""
            INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, old_value, new_value)
            VALUES (%s, %s, 'priority_change', 'agent', %s, %s, %s)
        """, (ticket["id"], ticket["ticket_number"], actor_name, ticket["priority"], req.priority))

    if req.assigned_agent is not None and req.assigned_agent != ticket["assigned_agent"]:
        updates.append("assigned_agent = %s")
        params.append(req.assigned_agent)
        execute_commit("""
            INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, old_value, new_value)
            VALUES (%s, %s, 'assignment', 'agent', %s, %s, %s)
        """, (ticket["id"], ticket["ticket_number"], actor_name, ticket["assigned_agent"] or "None", req.assigned_agent))

    if req.assigned_team is not None and req.assigned_team != ticket["assigned_team"]:
        updates.append("assigned_team = %s")
        params.append(req.assigned_team)

    if req.category_id is not None:
        updates.append("category_id = %s")
        params.append(req.category_id)

    if req.title is not None:
        updates.append("title = %s")
        params.append(req.title)

    if req.resolution_notes is not None:
        updates.append("resolution_notes = %s")
        params.append(req.resolution_notes)

    if req.internal_notes is not None:
        updates.append("internal_notes = %s")
        params.append(req.internal_notes)

    if not updates:
        return {"success": True, "message": "No fields to update", "ticket_number": ticket["ticket_number"]}

    updates.append("updated_at = NOW()")
    params.append(ticket["id"])
    execute_commit(f"UPDATE tickets SET {', '.join(updates)} WHERE id = %s", tuple(params))

    return {
        "success": True,
        "ticket_number": ticket["ticket_number"],
        "updated_fields": [u.split()[0] for u in updates if u != "updated_at = NOW()"]
    }

@router.post("/tickets/{ticket_id}/notes")
async def add_ticket_note(
    ticket_id: str,
    req: TicketNoteRequest,
    user: Dict[str, Any] = Depends(require_role("admin", "agent", "supervisor"))
):
    ticket = query_one(
        "SELECT id, ticket_number, internal_notes FROM tickets WHERE id::text = %s OR ticket_number = %s",
        (ticket_id, ticket_id)
    )
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")

    actor = req.author or user.get("full_name") or user.get("username", "Agent")
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    new_entry = f"[{timestamp}] {actor}: {req.note}"
    updated_notes = f"{ticket['internal_notes']}\n{new_entry}" if ticket.get("internal_notes") else new_entry

    execute_commit(
        "UPDATE tickets SET internal_notes = %s, updated_at = NOW() WHERE id = %s",
        (updated_notes, ticket["id"])
    )

    execute_commit("""
        INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, message)
        VALUES (%s, %s, 'internal_note', 'agent', %s, %s)
    """, (ticket["id"], ticket["ticket_number"], actor, req.note))

    return {
        "success": True,
        "ticket_number": ticket["ticket_number"],
        "note": req.note,
        "author": actor
    }

# --- 5. RAG / AI QUALITY DASHBOARD ---
@router.get("/rag")
async def get_rag_metrics(user: Dict[str, Any] = Depends(get_current_user)):
    msg_counts = query_one("""
        SELECT
            COUNT(*) FILTER (WHERE intent = 'faq_query') AS faq_responses,
            COUNT(*) FILTER (WHERE intent = 'human_escalation') AS escalations
        FROM messages WHERE sender_type = 'ai'
    """) or {}

    audit_statuses = query_one("""
        SELECT
            COUNT(*) FILTER (WHERE event_type = 'turn_completed' AND payload->>'status' = 'out_of_scope') AS safe_deflections,
            COUNT(*) FILTER (WHERE event_type = 'turn_completed' AND payload->>'status' = 'clarification_required') AS clarification_requests,
            COUNT(*) FILTER (WHERE event_type = 'turn_completed' AND payload->>'llm_status' = 'failed') AS llm_failures,
            COUNT(*) FILTER (WHERE event_type = 'turn_completed' AND payload->>'guardrail_decision' IN ('verified_faq_fallback','llm_failed_faq_fallback')) AS fallbacks,
            COUNT(*) FILTER (WHERE event_type = 'error' OR payload->>'llm_status' = 'failed') AS error_count,
            COUNT(*) FILTER (WHERE event_type = 'turn_completed' AND payload->>'grounded' = 'true') AS grounded_answers,
            COUNT(*) FILTER (WHERE payload ? 'llm_status') AS telemetry_turns
        FROM audit_logs
    """) or {}

    lat_stats = query_one("""
        SELECT
            AVG(latency_ms) FILTER (WHERE event_type = 'turn_completed' AND latency_ms > 0) AS avg_latency,
            percentile_cont(0.50) WITHIN GROUP (ORDER BY latency_ms)
                FILTER (WHERE event_type = 'turn_completed' AND latency_ms > 0) AS p50,
            percentile_cont(0.95) WITHIN GROUP (ORDER BY latency_ms)
                FILTER (WHERE event_type = 'turn_completed' AND latency_ms > 0) AS p95,
            AVG(latency_ms) FILTER (WHERE event_type = 'rag_retrieved' AND latency_ms > 0) AS retrieval_latency,
            AVG(latency_ms) FILTER (WHERE event_type IN ('llm_completed','llm_failed') AND latency_ms > 0) AS llm_latency
        FROM audit_logs
    """) or {}

    # Confidence distribution
    conf_rows = query_all("""
        SELECT 
            CASE 
                WHEN confidence >= 0.90 THEN '0.90 - 1.00 (High)'
                WHEN confidence >= 0.75 THEN '0.75 - 0.89 (Good)'
                WHEN confidence >= 0.50 THEN '0.50 - 0.74 (Moderate)'
                ELSE '< 0.50 (Low/Uncertain)'
            END as bracket,
            COUNT(*) as count
        FROM messages
        WHERE sender_type = 'ai' AND confidence IS NOT NULL
        GROUP BY 1
        ORDER BY 1 DESC
    """)

    return {
        "rag_queries": int(msg_counts.get("faq_responses") or 0),
        "grounded_answers": int(audit_statuses.get("grounded_answers") or 0),
        "safe_deflections": int(audit_statuses.get("safe_deflections") or 0),
        "clarification_requests": int(audit_statuses.get("clarification_requests") or 0),
        "escalations": int(msg_counts.get("escalations") or 0),
        "average_retrieval_latency_ms": round(float(lat_stats["retrieval_latency"]), 1) if lat_stats.get("retrieval_latency") is not None else None,
        "average_llm_latency_ms": round(float(lat_stats["llm_latency"]), 1) if lat_stats.get("llm_latency") is not None else None,
        "total_latency_ms": round(float(lat_stats["avg_latency"]), 1) if lat_stats.get("avg_latency") is not None else None,
        "p50_latency_ms": round(float(lat_stats["p50"]), 1) if lat_stats.get("p50") is not None else None,
        "p95_latency_ms": round(float(lat_stats["p95"]), 1) if lat_stats.get("p95") is not None else None,
        "cache_hit_rate": None,
        "fallback_count": int(audit_statuses.get("fallbacks") or 0),
        "llm_failure_count": int(audit_statuses.get("llm_failures") or 0) if audit_statuses.get("telemetry_turns") else None,
        "telemetry_turns": int(audit_statuses.get("telemetry_turns") or 0),
        "error_count": int(audit_statuses.get("error_count") or 0),
        "program_isolation": {
            "depi_leakage": None,
            "digilians_leakage": None,
            "status": "not_measured",
        },
        "confidence_distribution": conf_rows
    }

@router.get("/executions")
async def list_executions(
    status_filter: Optional[str] = Query(None, alias="status", pattern="^(completed|fallback|failed|unknown)$"),
    channel: Optional[str] = Query(None, max_length=30),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    user: Dict[str, Any] = Depends(get_current_user),
):
    rows = query_all("""
        SELECT
            COALESCE(NULLIF(payload->>'request_id',''), execution_id) AS request_id,
            MAX(execution_id) AS execution_id,
            MAX(payload->>'workflow_id') AS workflow_id,
            MAX(workflow_name) AS workflow_name,
            MAX(channel) AS channel,
            MAX(payload->>'program') AS program,
            MAX(payload->>'intent') AS intent,
            MAX(latency_ms) FILTER (WHERE event_type = 'turn_completed') AS latency_ms,
            MAX(created_at) AS created_at,
            ARRAY_AGG(DISTINCT event_type) AS events,
            CASE
              WHEN BOOL_OR(event_type = 'error' OR payload->>'llm_status' = 'failed') THEN 'failed'
              WHEN BOOL_OR(event_type = 'turn_completed' AND payload->>'guardrail_decision' IN ('verified_faq_fallback','llm_failed_faq_fallback')) THEN 'fallback'
              WHEN BOOL_OR(event_type = 'turn_completed') THEN 'completed'
              ELSE 'unknown'
            END AS status
        FROM audit_logs
        WHERE COALESCE(NULLIF(payload->>'request_id',''), execution_id) IS NOT NULL
          AND (%s IS NULL OR channel = %s)
        GROUP BY COALESCE(NULLIF(payload->>'request_id',''), execution_id)
        HAVING (%s IS NULL OR
          CASE
            WHEN BOOL_OR(event_type = 'error' OR payload->>'llm_status' = 'failed') THEN 'failed'
            WHEN BOOL_OR(event_type = 'turn_completed' AND payload->>'guardrail_decision' IN ('verified_faq_fallback','llm_failed_faq_fallback')) THEN 'fallback'
            WHEN BOOL_OR(event_type = 'turn_completed') THEN 'completed'
            ELSE 'unknown'
          END = %s)
        ORDER BY MAX(created_at) DESC
        LIMIT %s OFFSET %s
    """, (channel, channel, status_filter, status_filter, limit, offset))

    return {
        "items": [{
            "request_id": row["request_id"],
            "execution_id": row["execution_id"],
            "workflow_id": row["workflow_id"],
            "workflow_name": row["workflow_name"],
            "channel": row["channel"],
            "program": row["program"],
            "intent": row["intent"],
            "status": row["status"],
            "events": row["events"] or [],
            "latency_ms": row["latency_ms"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "n8n_url": f"{N8N_UI_URL}/workflow/{row['workflow_id']}/executions/{row['execution_id']}" if row["workflow_id"] and row["execution_id"] else None,
        } for row in rows]
    }

@router.get("/executions/{request_id}")
async def get_execution_detail(request_id: str, user: Dict[str, Any] = Depends(get_current_user)):
    rows = query_all("""
        SELECT execution_id, workflow_name, event_type, channel,
               latency_ms, created_at, payload
        FROM audit_logs
        WHERE payload->>'request_id' = %s OR execution_id = %s
        ORDER BY created_at ASC
        LIMIT 100
    """, (request_id, request_id))
    if not rows:
        raise HTTPException(status_code=404, detail="Execution not found")

    allowed_payload_keys = (
        "status", "intent", "program", "locale", "llm_status", "grounded",
        "guardrail_decision", "fallback_reason", "retrieved_count", "source_ids",
        "source_urls", "relevance_score", "error_code", "stage",
    )
    events = []
    for row in rows:
        payload = row["payload"] or {}
        safe_payload = {key: payload[key] for key in allowed_payload_keys if key in payload}
        if isinstance(safe_payload.get("source_urls"), list):
            safe_payload["source_urls"] = [url for url in safe_payload["source_urls"] if _is_official_source(url)]
        events.append({
            "execution_id": row["execution_id"],
            "workflow_id": payload.get("workflow_id"),
            "workflow_name": row["workflow_name"],
            "event_type": row["event_type"],
            "channel": row["channel"],
            "latency_ms": row["latency_ms"],
            "created_at": row["created_at"].isoformat() if row["created_at"] else None,
            "details": safe_payload,
        })
    last = rows[-1]
    workflow_id = (last["payload"] or {}).get("workflow_id")
    execution_id = last["execution_id"]
    return {
        "request_id": request_id,
        "status": _execution_status([{"event_type": row["event_type"], "payload": row["payload"] or {}} for row in rows]),
        "events": events,
        "n8n_url": f"{N8N_UI_URL}/workflow/{workflow_id}/executions/{execution_id}" if workflow_id and execution_id else None,
    }

# --- 6. KNOWLEDGE BASE DASHBOARD ---
@router.get("/knowledge-base")
async def get_kb_metrics(user: Dict[str, Any] = Depends(get_current_user)):
    totals = query_one("""
        SELECT 
            COUNT(*) as total_docs,
            COUNT(CASE WHEN is_active = TRUE THEN 1 END) as active_docs,
            COUNT(CASE WHEN embedding IS NOT NULL THEN 1 END) as embedded_rows,
            COUNT(CASE WHEN embedding IS NULL THEN 1 END) as unembedded_rows,
            MAX(created_at) as last_ingestion_time,
            MAX(last_verified_at) as last_update_time
        FROM knowledge_base
    """)

    by_program = query_all("""
        SELECT program, COUNT(*) as count
        FROM knowledge_base
        GROUP BY program
        ORDER BY count DESC
    """)

    by_source = query_all("""
        SELECT COALESCE(source_attribution, 'DEPI / MCIT Official') as source, COUNT(*) as count
        FROM knowledge_base
        GROUP BY source_attribution
        ORDER BY count DESC
    """)

    total_docs = totals["total_docs"] if totals else 0
    embedded_rows = totals["embedded_rows"] if totals else 0

    return {
        "total_kb_documents": total_docs,
        "active_documents": totals["active_docs"] if totals else 0,
        "documents_by_program": by_program,
        "documents_by_source": by_source,
        "embedded_rows": embedded_rows,
        "unembedded_rows": totals["unembedded_rows"] if totals else 0,
        "embedding_status": f"{embedded_rows} / {total_docs}",
        "last_ingestion_time": totals["last_ingestion_time"].isoformat() if totals and totals["last_ingestion_time"] else None,
        "last_update_time": totals["last_update_time"].isoformat() if totals and totals["last_update_time"] else None
    }

# --- 7. SYSTEM HEALTH ---
@router.get("/system-health")
async def get_system_health(user: Dict[str, Any] = Depends(get_current_user)):
    now = datetime.now(timezone.utc).isoformat()
    services = []

    # Component availability is measured independently from workflow/model readiness.
    try:
        t0 = time.time()
        res = query_one("SELECT 1 as ok")
        lat = round((time.time() - t0) * 1000, 1)
        services.append({
            "name": "PostgreSQL (pgvector)",
            "status": "ONLINE" if res and res.get("ok") == 1 else "DEGRADED",
            "latency_ms": lat,
            "last_check": now,
            "error": None
        })
    except Exception as exc:
        services.append({
            "name": "PostgreSQL (pgvector)",
            "status": "OFFLINE",
            "latency_ms": None,
            "last_check": now,
            "error": type(exc).__name__
        })

    try:
        t0 = time.time()
        redis_pw = os.getenv("REDIS_PASSWORD")
        if not redis_pw:
            raise RuntimeError("REDIS_PASSWORD environment variable must be set")
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "6379")),
            password=redis_pw,
            socket_connect_timeout=2,
            socket_timeout=2,
        )
        if r.ping():
            lat = round((time.time() - t0) * 1000, 1)
            services.append({
                "name": "Redis Cache",
                "status": "ONLINE",
                "latency_ms": lat,
                "last_check": now,
                "error": None
            })
        else:
            services.append({
                "name": "Redis Cache",
                "status": "DEGRADED",
                "latency_ms": None,
                "last_check": now,
                "error": "Ping returned False"
            })
    except Exception as exc:
        services.append({
            "name": "Redis Cache",
            "status": "OFFLINE",
            "latency_ms": None,
            "last_check": now,
            "error": type(exc).__name__
        })

    for name, url in (("n8n Workflow Engine", N8N_HEALTH_URL),):
        started = time.time()
        code, error = _http_probe(url)
        services.append({
            "name": name,
            "status": "ONLINE" if code == 200 else ("DEGRADED" if code else "OFFLINE"),
            "latency_ms": round((time.time() - started) * 1000, 1) if code else None,
            "last_check": now,
            "error": error or (None if code == 200 else f"HTTP {code}"),
        })

    whatsapp_started = time.time()
    whatsapp_code, whatsapp_connected, whatsapp_error = _whatsapp_probe(WHATSAPP_HEALTH_URL)
    services.append({
        "name": "WhatsApp Gateway Bridge",
        "status": "ONLINE" if whatsapp_code == 200 and whatsapp_connected else ("DEGRADED" if whatsapp_code else "OFFLINE"),
        "latency_ms": round((time.time() - whatsapp_started) * 1000, 1) if whatsapp_code else None,
        "last_check": now,
        "error": whatsapp_error or (None if whatsapp_connected else "Baileys session is disconnected"),
    })

    ollama_started = time.time()
    code, error = 0, None
    model_ready = False
    try:
        with urllib.request.urlopen(f"{OLLAMA_BASE_URL}/api/tags", timeout=2) as response:
            code = response.getcode()
            model_data = json.loads(response.read().decode("utf-8"))
        if code == 200:
            available = {model.get("name", "").split(":")[0] for model in model_data.get("models", [])}
            required = {os.getenv("OLLAMA_MODEL", "qwen2.5:3b").split(":")[0], os.getenv("EMBED_MODEL", "nomic-embed-text").split(":")[0]}
            model_ready = required.issubset(available)
    except Exception as exc:
        error = type(exc).__name__
    services.append({
        "name": "Ollama API and models",
        "status": "ONLINE" if code == 200 and model_ready else ("DEGRADED" if code else "OFFLINE"),
        "latency_ms": round((time.time() - ollama_started) * 1000, 1) if code else None,
        "last_check": now,
        "error": error or (None if model_ready else "Required chat or embedding model is not available"),
    })

    # Do not run a costly generation request as a periodic health probe. Show
    # inference readiness from real, correlated workflow telemetry instead.
    try:
        inference = query_one("""
            SELECT payload->>'llm_status' AS status, payload->>'error_code' AS error_code,
                   created_at
            FROM audit_logs
            WHERE payload ? 'llm_status'
            ORDER BY created_at DESC LIMIT 1
        """)
        inference_status = "UNKNOWN"
        inference_error = "No correlated model request has been recorded yet"
        inference_time = None
        if inference:
            inference_status = "ONLINE" if inference.get("status") == "succeeded" else "DEGRADED"
            inference_error = inference.get("error_code")
            inference_time = inference["created_at"].isoformat() if inference.get("created_at") else None
        services.append({
            "name": "Ollama generation (observed)",
            "status": inference_status,
            "latency_ms": None,
            "last_check": inference_time or now,
            "error": inference_error,
        })
    except Exception as exc:
        services.append({
            "name": "Ollama generation (observed)", "status": "UNKNOWN",
            "latency_ms": None, "last_check": now, "error": type(exc).__name__,
        })

    statuses = {service["status"] for service in services}
    overall_status = "ONLINE" if statuses == {"ONLINE"} else ("OFFLINE" if statuses == {"OFFLINE"} else "DEGRADED")

    return {
        "overall_status": overall_status,
        "services": services
    }

# --- 8. RECENT ACTIVITY ---
@router.get("/activity")
async def get_recent_activity(
    limit: int = Query(25, ge=5, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    rows = query_all(f"""
        SELECT 
            id,
            workflow_name,
            event_type,
            channel,
            payload,
            latency_ms,
            created_at
        FROM audit_logs
        ORDER BY created_at DESC
        LIMIT %s
    """, (limit,))

    items = []
    for r in rows:
        payload = r["payload"] or {}
        # Format human readable summary based on event_type
        desc = ""
        etype = r["event_type"]
        if etype == "turn_completed":
            desc = f"Turn completed: status={payload.get('status')} intent={payload.get('intent')}"
        elif etype == "message_dispatched":
            desc = f"Message dispatched via {payload.get('channel', 'channel')} to recipient"
        elif etype == "hitl_escalated":
            desc = f"HITL Escalation triggered: reason={payload.get('reason', 'Support escalation')}"
        elif etype == "agent_replied":
            desc = f"Live agent replied: ticket={payload.get('ticket_number', 'N/A')}"
        else:
            desc = f"{etype} recorded on workflow {r['workflow_name']}"

        items.append({
            "id": r["id"],
            "event_type": etype,
            "workflow_name": r["workflow_name"],
            "channel": r["channel"],
            "description": desc,
            "latency_ms": r["latency_ms"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        })

    return {"items": items}

# --- 9. CONVERSATION DETAIL VIEW ---
@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: str,
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    can_view_pii = (user.get("role") == "admin")

    try:
        conversation_uuid = str(UUID(conversation_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=404, detail="Conversation not found")

    conv = query_one("""
        SELECT 
            c.id, c.channel, c.status, c.current_intent, c.language, c.created_at, c.closed_at,
            cust.id as customer_id, cust.full_name, cust.phone_number, cust.email, cust.metadata as customer_metadata
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE c.id = %s
    """, (conversation_uuid,))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    message_total_row = query_one("""
        SELECT COUNT(*) AS count FROM messages
        WHERE conversation_id = %s AND sender_type IN ('customer', 'ai', 'agent')
    """, (conversation_uuid,))
    message_total = int(message_total_row["count"] if message_total_row else 0)

    messages = query_all("""
        SELECT 
            id, sender_type, content, intent, confidence, created_at, metadata,
            delivery_status, provider_message_id, delivery_updated_at
        FROM messages
        WHERE conversation_id = %s AND sender_type IN ('customer', 'ai', 'agent')
        ORDER BY created_at ASC, id ASC
        LIMIT %s OFFSET %s
    """, (conversation_uuid, limit, (page - 1) * limit))

    summary_row = query_one("""
        SELECT summary, unresolved_questions, topics
        FROM conversation_summaries
        WHERE conversation_id = %s
    """, (conversation_uuid,))

    tickets = query_all("""
        SELECT 
            id, ticket_number, priority, status, reason, sla_due_at, assigned_agent, created_at
        FROM tickets
        WHERE conversation_id = %s
        ORDER BY created_at DESC
    """, (conversation_uuid,))

    # Sanitize message metadata to ensure system prompts or internal keys are never exposed
    safe_messages = []
    for m in messages:
        raw_meta = m.get("metadata") or {}
        safe_meta = {
            "sentiment": raw_meta.get("sentiment"),
            "order_number": raw_meta.get("order_number"),
            "rag_evidence": raw_meta.get("rag_evidence") or raw_meta.get("sources"),
            "delivery_status": m.get("delivery_status") or raw_meta.get("delivery_status"),
            "provider_message_id": m.get("provider_message_id") or raw_meta.get("provider_message_id"),
            "delivery_updated_at": m["delivery_updated_at"].isoformat() if m.get("delivery_updated_at") else (raw_meta.get("delivery_updated_at") if isinstance(raw_meta.get("delivery_updated_at"), str) else None)
        }
        safe_messages.append({
            "id": str(m["id"]),
            "sender_type": m["sender_type"],
            "content": m["content"],
            "intent": m["intent"],
            "confidence": float(m["confidence"]) if m["confidence"] is not None else None,
            "created_at": m["created_at"].isoformat() if m["created_at"] else None,
            "metadata": safe_meta
        })

    return {
        "conversation": {
            "id": str(conv["id"]),
            "channel": conv["channel"],
            "status": conv["status"],
            "intent": conv["current_intent"],
            "language": conv["language"],
            "created_at": conv["created_at"].isoformat() if conv["created_at"] else None,
            "closed_at": conv["closed_at"].isoformat() if conv["closed_at"] else None
        },
        "customer": {
            "id": str(conv["customer_id"]),
            "full_name": conv["full_name"],
            "phone_masked": mask_phone(conv["phone_number"], can_view_pii),
            "email_masked": mask_email(conv["email"], can_view_pii),
            "program": (conv["customer_metadata"] or {}).get("program", "UNKNOWN")
        },
        "summary": summary_row["summary"] if summary_row else "No automated summary generated yet.",
        "unresolved_questions": summary_row["unresolved_questions"] if summary_row else None,
        "messages": safe_messages,
        "message_page": page,
        "message_limit": limit,
        "message_total": message_total,
        "message_pages": (message_total + limit - 1) // limit,
        "tickets": [{
            "id": str(t["id"]),
            "ticket_number": t["ticket_number"],
            "priority": t["priority"],
            "status": t["status"],
            "reason": t["reason"],
            "assigned_agent": t["assigned_agent"],
            "sla_deadline": t["sla_due_at"].isoformat() if t["sla_due_at"] else None,
            "created_at": t["created_at"].isoformat() if t["created_at"] else None
        } for t in tickets]
    }

@router.get("/conversations/{conversation_id}/tickets")
async def get_conversation_tickets(
    conversation_id: str,
    user: Dict[str, Any] = Depends(get_current_user)
):
    try:
        conversation_uuid = str(UUID(conversation_id))
    except (ValueError, TypeError, AttributeError):
        raise HTTPException(status_code=404, detail="Conversation not found")
        
    tickets = query_all("""
        SELECT 
            t.id, t.ticket_number, t.title, t.priority, t.status, t.reason,
            t.assigned_agent, t.assigned_team, t.sla_due_at, t.created_at, t.updated_at
        FROM tickets t
        WHERE t.conversation_id = %s
        ORDER BY t.created_at DESC
    """, (conversation_uuid,))
    
    return {
        "conversation_id": conversation_id,
        "total": len(tickets),
        "items": [{
            "id": str(t["id"]),
            "ticket_number": t["ticket_number"],
            "title": t["title"] or t["reason"][:60],
            "priority": t["priority"],
            "status": t["status"],
            "reason": t["reason"],
            "assigned_agent": t["assigned_agent"],
            "assigned_team": t["assigned_team"],
            "sla_deadline": t["sla_due_at"].isoformat() if t["sla_due_at"] else None,
            "created_at": t["created_at"].isoformat() if t["created_at"] else None,
            "updated_at": t["updated_at"].isoformat() if t["updated_at"] else None
        } for t in tickets]
    }

# --- 10. REAL-TIME N8N ORCHESTRATION & TELEMETRY ---

class SimulateRequest(BaseModel):
    message: str
    full_name: Optional[str] = "Live Simulator User"
    phone_number: Optional[str] = "+201000000000"
    channel: Optional[str] = "simulator"
    program: Optional[str] = "DEPI"

class TicketRespondRequest(BaseModel):
    response_message: str
    agent_name: Optional[str] = "Support Agent"
    action: Optional[str] = "resolve"
    notes: Optional[str] = None

@router.get("/n8n/overview")
async def get_n8n_overview(user: Dict[str, Any] = Depends(get_current_user)):
    """Provides consolidated operational status of n8n workflows and webhook endpoints."""
    code, data, err = _n8n_api_request("/workflows")
    connected = (code == 200)
    workflows = data.get("data", []) if connected else []
    active_count = sum(1 for w in workflows if w.get("active") is True)
    
    probe_code, probe_err = _http_probe(N8N_HEALTH_URL)
    
    return {
        "connected": connected,
        "api_code": code,
        "health_status": "ONLINE" if probe_code == 200 else "OFFLINE",
        "total_workflows": len(workflows),
        "active_workflows": active_count,
        "ui_url": N8N_UI_URL,
        "api_url": N8N_API_URL,
        "gateway_webhook": N8N_GATEWAY_WEBHOOK,
        "agent_webhook": N8N_AGENT_WEBHOOK,
        "error": err
    }

@router.get("/n8n/workflows")
async def get_n8n_workflows(user: Dict[str, Any] = Depends(get_current_user)):
    """Lists real n8n workflows from n8n REST API with active toggle state."""
    code, data, err = _n8n_api_request("/workflows")
    if code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to query n8n API: {err or code}")
    
    items = []
    for wf in data.get("data", []):
        wf_id = wf.get("id")
        items.append({
            "id": wf_id,
            "name": wf.get("name"),
            "active": wf.get("active", False),
            "nodes_count": len(wf.get("nodes", [])),
            "tags": [t.get("name") for t in wf.get("tags", [])] if wf.get("tags") else [],
            "created_at": wf.get("createdAt"),
            "updated_at": wf.get("updatedAt"),
            "n8n_url": f"{N8N_UI_URL}/workflow/{wf_id}"
        })
    return {"items": items, "count": len(items)}

@router.post("/n8n/workflows/{workflow_id}/activate")
async def activate_n8n_workflow(workflow_id: str, user: Dict[str, Any] = Depends(require_role("admin", "supervisor"))):
    """Activates only the explicitly allowlisted customer-service ingress."""
    if not N8N_ACTIVATION_APPROVED:
        raise HTTPException(status_code=403, detail="Workflow activation requires separate operational approval.")
    if not N8N_IMPORT_ACCEPTANCE_VERIFIED:
        raise HTTPException(status_code=403, detail="Target-version import acceptance has not been verified.")
    if workflow_id not in N8N_ACTIVATABLE_WORKFLOW_IDS:
        raise HTTPException(status_code=403, detail="Workflow activation is not allowlisted.")
    code, data, err = _n8n_api_request(f"/workflows/{workflow_id}/activate", method="POST")
    if code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to activate workflow: {err or code}")
    return {"success": True, "workflow_id": workflow_id, "active": True}

@router.post("/n8n/workflows/{workflow_id}/deactivate")
async def deactivate_n8n_workflow(workflow_id: str, user: Dict[str, Any] = Depends(require_role("admin", "supervisor"))):
    """Deactivates a workflow in n8n live via API."""
    code, data, err = _n8n_api_request(f"/workflows/{workflow_id}/deactivate", method="POST")
    if code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to deactivate workflow: {err or code}")
    return {"success": True, "workflow_id": workflow_id, "active": False}

@router.get("/n8n/executions")
async def get_n8n_executions(
    limit: int = Query(25, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Fetches real live executions directly from n8n REST API."""
    code, data, err = _n8n_api_request(f"/executions?limit={limit}")
    if code != 200:
        raise HTTPException(status_code=502, detail=f"Failed to query n8n executions: {err or code}")
    
    raw_list = data.get("data", [])
    executions = []
    for ex in raw_list:
        exec_id = ex.get("id")
        wf_id = ex.get("workflowId")
        st_at = ex.get("startedAt")
        sp_at = ex.get("stoppedAt")
        duration_ms = None
        if st_at and sp_at:
            try:
                t0 = datetime.fromisoformat(st_at.replace("Z", "+00:00"))
                t1 = datetime.fromisoformat(sp_at.replace("Z", "+00:00"))
                duration_ms = int((t1 - t0).total_seconds() * 1000)
            except Exception:
                pass
        
        executions.append({
            "id": exec_id,
            "workflow_id": wf_id,
            "status": ex.get("status", "unknown"),
            "mode": ex.get("mode", "unknown"),
            "finished": ex.get("finished", False),
            "started_at": st_at,
            "stopped_at": sp_at,
            "duration_ms": duration_ms,
            "n8n_url": f"{N8N_UI_URL}/workflow/{wf_id}/executions/{exec_id}" if wf_id and exec_id else None
        })
    return {"items": executions, "count": len(executions)}

@router.post("/n8n/simulate")
async def simulate_system_interaction(
    req: SimulateRequest,
    user: Dict[str, Any] = Depends(get_current_user)
):
    """Sends a real customer message directly into n8n Master Gateway webhook, receives response, and correlates trace."""
    payload = {
        "customer_message": req.message,
        "full_name": req.full_name,
        "phone_number": req.phone_number,
        "channel": req.channel,
        "program": req.program
    }
    
    code, n8n_resp, err, latency = _n8n_webhook_post(N8N_GATEWAY_WEBHOOK, payload, timeout=60.0)
    if code != 200:
        return {
            "success": False,
            "status_code": code,
            "error": err or "n8n Gateway execution failed",
            "latency_ms": latency,
            "response": n8n_resp,
            "trace": []
        }
    
    time.sleep(0.15)
    
    req_id = None
    exec_id = None
    if isinstance(n8n_resp, dict):
        req_id = n8n_resp.get("request_id")
        exec_id = n8n_resp.get("execution_id")
    
    correlated_events = []
    if req_id or exec_id:
        correlated_events = query_all("""
            SELECT execution_id, workflow_name, event_type, channel, latency_ms, payload, created_at
            FROM audit_logs
            WHERE (payload->>'request_id' = %s OR execution_id = %s)
            ORDER BY created_at ASC
            LIMIT 50
        """, (req_id or "", exec_id or ""))
    
    return {
        "success": True,
        "status_code": code,
        "latency_ms": latency,
        "response": n8n_resp,
        "request_id": req_id,
        "execution_id": exec_id,
        "trace": [{
            "execution_id": r["execution_id"],
            "workflow_name": r["workflow_name"],
            "event_type": r["event_type"],
            "channel": r["channel"],
            "latency_ms": r["latency_ms"],
            "payload": r["payload"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None
        } for r in correlated_events]
    }

@router.post("/tickets/{ticket_id}/respond")
async def respond_to_ticket(
    ticket_id: str,
    req: TicketRespondRequest,
    user: Dict[str, Any] = Depends(require_role("admin", "agent", "supervisor"))
):
    """Directly resolves or updates a ticket, dispatches agent response to n8n HITL webhook, and updates PostgreSQL."""
    ticket = query_one("""
        SELECT t.id, t.ticket_number, t.customer_id, t.conversation_id, t.status, c.full_name
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE t.id::text = %s OR t.ticket_number = %s
    """, (ticket_id, ticket_id))
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    agent_payload = {
        "ticket_number": ticket["ticket_number"],
        "agent_message": req.response_message,
        "agent_name": req.agent_name or user.get("full_name", "Support Agent"),
        "action": req.action or "resolve"
    }
    
    n8n_code, n8n_data, n8n_err, n8n_lat = _n8n_webhook_post(N8N_AGENT_WEBHOOK, agent_payload, timeout=20.0)
    
    new_status = "resolved" if req.action == "resolve" else "in_progress"
    execute_commit("""
        UPDATE tickets
        SET status = %s,
            assigned_agent = %s,
            resolution_notes = %s,
            updated_at = NOW()
        WHERE id = %s
    """, (new_status, req.agent_name, req.response_message, ticket["id"]))
    
    # Record event in ticket_events timeline
    execute_commit("""
        INSERT INTO ticket_events (ticket_id, ticket_number, event_type, actor_type, actor_name, message, new_value)
        VALUES (%s, %s, 'agent_reply', 'agent', %s, %s, %s)
    """, (ticket["id"], ticket["ticket_number"], req.agent_name or user.get("full_name", "Agent"), req.response_message, new_status))

    # SubWF 04D records (and for WhatsApp, delivers) the agent message; only keep a record here
    # when n8n did not accept the reply, so the conversation history still shows it.
    if ticket.get("conversation_id") and n8n_code != 200:
        execute_commit("""
            INSERT INTO messages (conversation_id, customer_id, sender_type, content, intent)
            VALUES (%s, %s, 'agent', %s, 'agent_portal_resolution')
        """, (ticket["conversation_id"], ticket["customer_id"], req.response_message))
    
    execute_commit("""
        INSERT INTO audit_logs (workflow_name, event_type, channel, payload)
        VALUES ('dashboard_hitl_portal', %s, 'dashboard', %s)
    """, ("ticket_resolved" if new_status == "resolved" else "ticket_replied", json.dumps({
        "ticket_number": ticket["ticket_number"],
        "agent": req.agent_name,
        "action": req.action,
        "n8n_dispatched": n8n_code == 200,
        "n8n_status_code": n8n_code
    })))
    
    return {
        "success": True,
        "ticket_number": ticket["ticket_number"],
        "status": new_status,
        "n8n_status_code": n8n_code,
        "n8n_dispatched": n8n_code == 200,
        "latency_ms": n8n_lat
    }


@router.get("/rag/evaluation-summary")
async def get_rag_evaluation_summary(user: Dict[str, Any] = Depends(get_current_user)):
    """Read a compact benchmark result; this route never runs inference or a benchmark."""
    summary_path = Path(__file__).resolve().parents[1] / "evaluation" / "rag_evaluation_summary.json"
    return summarize_stored_rag_evaluation(
        summary_path=summary_path,
        active_runtime_identity=os.getenv("DASHBOARD_EVALUATION_RUNTIME_ID"),
        active_corpus_version=os.getenv("DASHBOARD_EVALUATION_CORPUS_VERSION"),
    )


@router.get("/reports/{report_type}/excel")
async def export_dashboard_report(
    report_type: str,
    period: Optional[str] = Query(None, pattern="^(all|today|yesterday|7d|30d|month)?$"),
    program: Optional[str] = Query("all", max_length=40),
    search: Optional[str] = Query(None, max_length=250),
    ticket_status: Optional[str] = Query(None, max_length=30),
    priority: Optional[str] = Query(None, max_length=30),
    sla_breached: Optional[bool] = Query(None),
    execution_status: Optional[str] = Query(None, pattern="^(completed|fallback|failed|unknown)?$"),
    lang: str = Query("en", pattern="^(en|ar)$"),
    user: Dict[str, Any] = Depends(get_current_user),
    _report_scope: Any = Depends(_report_timeout_scope),
):
    """Generate a bounded XLSX from existing authenticated, read-only page adapters."""
    report_started = time.monotonic()
    now = datetime.now().astimezone()
    active_program = program or "all"
    active_period = None if period in (None, "all") else period
    filters: Dict[str, Any] = {}
    sheets: List[Dict[str, Any]] = []
    if report_type == "executive":
        filters = {"period": period or "all", "program": active_program}
        data = await get_summary(period=active_period, program=active_program, user=user)
        metric_labels = {
            "total_customers": "Total customers / إجمالي العملاء",
            "active_conversations": "Active conversations / المحادثات النشطة",
            "total_conversations": "Total conversations / إجمالي المحادثات",
            "open_tickets": "Open tickets / التذاكر المفتوحة",
            "pending_tickets": "Pending tickets / التذاكر قيد المعالجة",
            "resolved_tickets": "Resolved tickets / التذاكر المحلولة",
            "sla_breaches": "SLA breaches / تجاوزات SLA",
            "escalated_conversations": "Escalated conversations / المحادثات المصعدة",
            "avg_response_time_ms": "Average turn latency (ms) / متوسط زمن المعالجة",
            "rag_success_rate": "Operational successful turn rate (%) / نسبة نجاح المعالجة التشغيلية",
        }
        rows = [{"metric": metric_labels[key], "value": value}
                for key, value in data.items()]
        sheets = [{"name": "Overview", "title": "Dashboard overview / ملخص لوحة المعلومات",
                   "columns": _report_columns(lang, [
                       ("metric", "Metric", "المؤشر", "text"),
                       ("value", "Value", "القيمة", "decimal"),
                   ]), "rows": rows}]
    elif report_type == "customers":
        filters = {"program": active_program, "search": search or "(none)"}
        async def fetch_customer_page(page: int, limit: int):
            return await get_customers(search=search, program=active_program,
                                       page=page, limit=limit, user=user)
        items = await _collect_export_pages(fetch_customer_page)
        sheets = [{"name": "Customers", "title": "Customers and students / العملاء والطلاب",
                   "columns": _report_columns(lang, [
                       ("id", "Customer ID", "معرف العميل", "text"),
                       ("full_name", "Name", "الاسم", "text"),
                       ("phone_masked", "Phone (role-masked)", "الهاتف (وفق الصلاحية)", "text"),
                       ("program", "Program", "المبادرة", "text"),
                       ("created_at", "Created at", "تاريخ الإنشاء", "datetime"),
                       ("last_interaction", "Last interaction", "آخر تفاعل", "datetime"),
                       ("conversation_count", "Conversations", "المحادثات", "integer"),
                       ("open_tickets", "Open tickets", "التذاكر المفتوحة", "integer"),
                       ("customer_status", "Status", "الحالة", "text"),
                   ]), "rows": items}]
    elif report_type == "conversations":
        filters = {"period": period or "all", "program": active_program}
        async def fetch_conversation_page(page: int, limit: int):
            return await get_conversations(period=active_period, program=active_program,
                                           page=page, limit=limit, user=user)
        items = await _collect_export_pages(fetch_conversation_page)
        data = await get_conversations(period=active_period, program=active_program,
                                       page=1, limit=1, user=user)
        metrics = data.get("metrics", {})
        sheets = [
            {"name": "Conversations", "title": "Filtered conversations / المحادثات المطابقة",
             "columns": _report_columns(lang, [
                 ("id", "Conversation ID", "معرف المحادثة", "text"),
                 ("customer_name", "Customer", "العميل", "text"),
                 ("program", "Program", "المبادرة", "text"),
                 ("channel", "Channel", "القناة", "text"),
                 ("intent", "Intent", "النية", "text"),
                 ("avg_confidence", "Average confidence", "متوسط الثقة", "decimal"),
                 ("status", "Status", "الحالة", "text"),
                 ("created_at", "Created at", "تاريخ الإنشاء", "datetime"),
                 ("message_count", "Message count", "عدد الرسائل", "integer"),
             ]), "rows": items},
            {"name": "Analytics", "title": "Conversation analytics / تحليلات المحادثات",
             "columns": _report_columns(lang, [
                 ("metric", "Metric", "المؤشر", "text"),
                 ("value", "Value", "القيمة", "decimal"),
             ]), "rows": _metric_rows(metrics, {})},
        ]
        for chart_name, chart_rows in data.get("charts", {}).items():
            sheets.append({"name": chart_name, "title": chart_name.replace("_", " ").title(),
                           "columns": _report_columns(lang, [
                               (key, key.replace("_", " ").title(), key.replace("_", " "), "text" if key in {"label", "date_label"} else "integer")
                               for key in (chart_rows[0].keys() if chart_rows else ["label", "count"])
                           ]), "rows": chart_rows})
    elif report_type == "tickets":
        filters = {"status": ticket_status or "all", "priority": priority or "all",
                   "program": active_program, "sla_breached": sla_breached if sla_breached is not None else "all"}
        async def fetch_ticket_page(page: int, limit: int):
            return await get_tickets(status=ticket_status, priority=priority,
                                     program=active_program, sla_breached=sla_breached,
                                     page=page, limit=limit, user=user)
        items = await _collect_export_pages(fetch_ticket_page)
        # `reason` and record identifiers are omitted: they are not shown in the
        # operational table and can contain unnecessary personal or case details.
        sheets = [{"name": "Tickets", "title": "Filtered support tickets / تذاكر الدعم المطابقة",
                   "columns": _report_columns(lang, [
                       ("ticket_number", "Ticket #", "رقم التذكرة", "text"),
                       ("customer_name", "Customer", "العميل", "text"),
                       ("program", "Program", "المبادرة", "text"),
                       ("priority", "Priority", "الأولوية", "text"),
                       ("status", "Status", "الحالة", "text"),
                       ("assigned_agent", "Assigned agent", "المسؤول المكلف", "text"),
                       ("sla_deadline", "SLA deadline", "موعد SLA", "datetime"),
                       ("sla_status", "SLA status", "حالة SLA", "text"),
                       ("created_at", "Created at", "تاريخ الإنشاء", "datetime"),
                       ("updated_at", "Updated at", "تاريخ التحديث", "datetime"),
                   ]), "rows": items}]
    elif report_type == "rag":
        data = await get_rag_metrics(user=user)
        evaluation = await get_rag_evaluation_summary(user=user)
        operational = {key: value for key, value in data.items()
                       if key not in {"confidence_distribution", "program_isolation"}}
        sheets = [
            {"name": "Runtime telemetry", "title": "Operational RAG telemetry (not answer accuracy)",
             "columns": _report_columns(lang, [
                 ("metric", "Metric", "المؤشر", "text"),
                 ("value", "Value", "القيمة", "decimal"),
             ]), "rows": _metric_rows(operational, {})},
            {"name": "Confidence", "title": "Observed AI confidence distribution",
             "columns": _report_columns(lang, [
                 ("bracket", "Confidence band", "نطاق الثقة", "text"),
                 ("count", "Count", "العدد", "integer"),
             ]), "rows": data.get("confidence_distribution", [])},
            {"name": "Evaluation", "title": "Historical benchmark evaluation summary",
             "columns": _report_columns(lang, [
                 ("metric", "Metric", "المؤشر", "text"),
                 ("value", "Value", "القيمة", "text"),
             ]), "rows": [{"metric": key, "value": value} for key, value in evaluation.items()]},
        ]
    elif report_type == "knowledge-base":
        data = await get_kb_metrics(user=user)
        summary = {key: value for key, value in data.items()
                   if key not in {"documents_by_program", "documents_by_source"}}
        sheets = [
            {"name": "Summary", "title": "Knowledge base metrics / مؤشرات قاعدة المعرفة",
             "columns": _report_columns(lang, [
                 ("metric", "Metric", "المؤشر", "text"),
                 ("value", "Value", "القيمة", "text"),
             ]), "rows": _metric_rows(summary, {})},
            {"name": "By program", "title": "Knowledge documents by program",
             "columns": _report_columns(lang, [
                 ("program", "Program", "المبادرة", "text"),
                 ("count", "Documents", "المستندات", "integer"),
             ]), "rows": data.get("documents_by_program", [])},
            {"name": "By source", "title": "Knowledge documents by attribution source",
             "columns": _report_columns(lang, [
                 ("source", "Source attribution", "جهة الإسناد", "text"),
                 ("count", "Documents", "المستندات", "integer"),
             ]), "rows": data.get("documents_by_source", [])},
        ]
    elif report_type == "health":
        data = await get_system_health(user=user)
        sheets = [{"name": "Health", "title": "System health snapshot / لقطة صحة النظام",
                   "columns": _report_columns(lang, [
                       ("name", "Component", "المكون", "text"),
                       ("status", "Status", "الحالة", "text"),
                       ("latency_ms", "Latency (ms)", "الزمن (مللي ثانية)", "decimal"),
                       ("last_check", "Checked at", "وقت الفحص", "datetime"),
                   ]), "rows": data.get("services", [])}]
    elif report_type == "activity":
        filters = {"execution_status": execution_status or "all (recent execution list)"}
        execution_rows: List[Dict[str, Any]] = []
        offset = 0
        while offset < MAX_EXPORT_ROWS:
            batch = await list_executions(status_filter=execution_status, channel=None,
                                          limit=200, offset=offset, user=user)
            batch_items = batch.get("items", [])
            execution_rows.extend(batch_items)
            if len(batch_items) < 200:
                break
            offset += len(batch_items)
        if len(execution_rows) >= MAX_EXPORT_ROWS:
            probe = await list_executions(status_filter=execution_status, channel=None,
                                          limit=1, offset=MAX_EXPORT_ROWS, user=user)
            if probe.get("items"):
                raise HTTPException(status_code=413, detail=f"Export exceeds the {MAX_EXPORT_ROWS} row limit")
        activity = await get_recent_activity(limit=100, user=user)
        sheets = [
            {"name": "Recent requests", "title": "Recent correlated requests (all matching status)",
             "columns": _report_columns(lang, [
                 ("request_id", "Request ID", "معرف الطلب", "text"),
                 ("execution_id", "Execution ID", "معرف التنفيذ", "text"),
                 ("workflow_name", "Workflow", "سير العمل", "text"),
                 ("channel", "Channel", "القناة", "text"),
                 ("program", "Program", "المبادرة", "text"),
                 ("intent", "Intent", "النية", "text"),
                 ("status", "Status", "الحالة", "text"),
                 ("latency_ms", "Latency (ms)", "الزمن (مللي ثانية)", "decimal"),
                 ("created_at", "Created at", "تاريخ الإنشاء", "datetime"),
             ]), "rows": execution_rows},
            {"name": "Audit activity", "title": "Latest 100 audit events (safe fields only)",
             "columns": _report_columns(lang, [
                 ("id", "Event ID", "معرف الحدث", "text"),
                 ("event_type", "Event type", "نوع الحدث", "text"),
                 ("workflow_name", "Workflow", "سير العمل", "text"),
                 ("channel", "Channel", "القناة", "text"),
                 ("latency_ms", "Latency (ms)", "الزمن (مللي ثانية)", "decimal"),
                 ("created_at", "Created at", "تاريخ الإنشاء", "datetime"),
             ]), "rows": activity.get("items", [])},
        ]
    elif report_type == "n8n":
        try:
            workflows = await get_n8n_workflows(user=user)
            executions = await get_n8n_executions(limit=100, user=user)
        except HTTPException as exc:
            raise HTTPException(status_code=503, detail="The read-only n8n report is currently unavailable") from exc
        sheets = [
            {"name": "Workflows", "title": "Read-only workflow metadata snapshot",
             "columns": _report_columns(lang, [
                 ("id", "Workflow ID", "معرف سير العمل", "text"),
                 ("name", "Workflow name", "اسم سير العمل", "text"),
                 ("nodes_count", "Node count", "عدد العقد", "integer"),
                 ("tags", "Tags", "الوسوم", "text"),
                 ("active", "Active", "نشط", "text"),
                 ("updated_at", "Updated at", "تاريخ التحديث", "datetime"),
             ]), "rows": [{**item, "tags": ", ".join(item.get("tags", [])),
                         "active": "Yes" if item.get("active") else "No"}
                        for item in workflows.get("items", [])]},
            {"name": "Latest executions", "title": "Latest 100 read-only execution summaries",
             "columns": _report_columns(lang, [
                 ("id", "Execution ID", "معرف التنفيذ", "text"),
                 ("workflow_id", "Workflow ID", "معرف سير العمل", "text"),
                 ("status", "Status", "الحالة", "text"),
                 ("mode", "Mode", "النمط", "text"),
                 ("finished", "Finished", "مكتمل", "text"),
                 ("started_at", "Started at", "وقت البدء", "datetime"),
                 ("stopped_at", "Stopped at", "وقت الانتهاء", "datetime"),
                 ("duration_ms", "Duration (ms)", "المدة (مللي ثانية)", "integer"),
             ]), "rows": executions.get("items", [])},
        ]
    else:
        raise HTTPException(status_code=404, detail="No report is available for this dashboard view")

    if report_type in {"executive", "customers", "conversations", "tickets"}:
        filters = {key: value for key, value in filters.items() if value not in (None, "")}
    if time.monotonic() - report_started > 30:
        raise HTTPException(status_code=504, detail="Report generation exceeded the time limit; retry with narrower filters")
    try:
        workbook_bytes = build_workbook(
            report_title=report_type.replace("-", " ").replace("_", " ").title(),
            sheets=sheets,
            filters=filters,
            lang=lang,
            generated_at=now,
        )
    except ValueError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    filename = safe_filename(report_type.replace("-", " ").replace("_", " "))
    disposition = f"attachment; filename=\"{filename}\"; filename*=UTF-8''{quote(filename)}"
    return StreamingResponse(
        iter([workbook_bytes]),
        media_type=EXCEL_MIME,
        headers={"Content-Disposition": disposition, "Cache-Control": "no-store"},
    )
