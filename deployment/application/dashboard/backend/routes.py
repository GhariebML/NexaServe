"""
NexaServe Production Admin Dashboard - API Routers & Business Logic
Real queries, Parameterized execution, PII masking, Filter aggregation, Metrics calculation.
"""
import os
import re
import time
import urllib.request
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List, Tuple
from fastapi import APIRouter, Depends, Query, HTTPException, status
from pydantic import BaseModel
import redis

from database import query_all, query_one, execute_commit
from auth import get_current_user, require_role

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

N8N_HEALTH_URL = os.getenv("N8N_HEALTH_URL", "http://127.0.0.1:5678/healthz")
N8N_UI_URL = os.getenv("N8N_UI_URL", "http://127.0.0.1:5678").rstrip("/")
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
WHATSAPP_HEALTH_URL = os.getenv("WHATSAPP_HEALTH_URL", "http://127.0.0.1:8080/health")

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
    perf_stats = query_one("""
        SELECT 
            AVG(latency_ms) as avg_latency,
            COUNT(CASE WHEN payload->>'status' = 'success' THEN 1 END) as success_turns,
            COUNT(*) as total_turns
        FROM audit_logs
        WHERE event_type = 'turn_completed'
    """)
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
            (SELECT AVG(confidence) FROM messages WHERE conversation_id = c.id AND confidence IS NOT NULL) as avg_confidence
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
            "message_count": r["message_count"],
            "avg_confidence": round(float(r["avg_confidence"]), 2) if r["avg_confidence"] else None
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

# --- 4. TICKET / HITL DASHBOARD ---
@router.get("/tickets")
async def get_tickets(
    status: Optional[str] = Query(None),
    priority: Optional[str] = Query(None),
    program: Optional[str] = Query("all"),
    sla_breached: Optional[bool] = Query(None),
    page: int = Query(1, ge=1),
    limit: int = Query(10, ge=1, le=100),
    user: Dict[str, Any] = Depends(get_current_user)
):
    offset = (page - 1) * limit
    where_clauses = ["1=1"]
    params: List[Any] = []

    if status and status.lower() != "all":
        where_clauses.append("t.status = %s")
        params.append(status.lower())

    if priority and priority.lower() != "all":
        where_clauses.append("t.priority = %s")
        params.append(priority.lower())

    if program and program.upper() != "ALL":
        where_clauses.append("(c.metadata->>'program') ILIKE %s")
        params.append(f"%{program}%")

    if sla_breached is True:
        where_clauses.append("t.status = 'open' AND t.sla_due_at < NOW()")
    elif sla_breached is False:
        where_clauses.append("(t.status != 'open' OR t.sla_due_at >= NOW())")

    where_sql = " AND ".join(where_clauses)

    total_row = query_one(f"""
        SELECT COUNT(*) as count 
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE {where_sql}
    """, tuple(params))
    total_count = total_row["count"] if total_row else 0

    query_params = list(params) + [limit, offset]
    rows = query_all(f"""
        SELECT 
            t.id,
            t.ticket_number,
            t.customer_id,
            c.full_name as customer_name,
            COALESCE(c.metadata->>'program', 'UNKNOWN') as program,
            t.priority,
            t.status,
            COALESCE(t.assigned_agent, 'Unassigned') as assigned_agent,
            t.reason,
            t.created_at,
            t.sla_due_at,
            t.updated_at,
            CASE 
                WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 'BREACHED'
                WHEN t.status = 'open' AND t.sla_due_at < NOW() + INTERVAL '2 hours' THEN 'AT_RISK'
                WHEN t.status = 'resolved' OR t.status = 'closed' THEN 'RESOLVED'
                ELSE 'ON_TRACK'
            END as sla_status
        FROM tickets t
        JOIN customers c ON t.customer_id = c.id
        WHERE {where_sql}
        ORDER BY 
            CASE WHEN t.status = 'open' AND t.sla_due_at < NOW() THEN 1 ELSE 2 END,
            t.created_at DESC
        LIMIT %s OFFSET %s
    """, tuple(query_params))

    return {
        "items": [{
            "id": str(r["id"]),
            "ticket_number": r["ticket_number"],
            "customer_id": str(r["customer_id"]),
            "customer_name": r["customer_name"],
            "program": r["program"],
            "priority": r["priority"],
            "status": r["status"],
            "assigned_agent": r["assigned_agent"],
            "reason": r["reason"],
            "created_at": r["created_at"].isoformat() if r["created_at"] else None,
            "sla_deadline": r["sla_due_at"].isoformat() if r["sla_due_at"] else None,
            "sla_status": r["sla_status"],
            "updated_at": r["updated_at"].isoformat() if r["updated_at"] else None
        } for r in rows],
        "total": total_count,
        "page": page,
        "limit": limit,
        "pages": (total_count + limit - 1) // limit
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
    user: Dict[str, Any] = Depends(get_current_user)
):
    can_view_pii = (user.get("role") == "admin")

    conv = query_one("""
        SELECT 
            c.id, c.channel, c.status, c.current_intent, c.language, c.created_at, c.closed_at,
            cust.id as customer_id, cust.full_name, cust.phone_number, cust.email, cust.metadata as customer_metadata
        FROM conversations c
        JOIN customers cust ON c.customer_id = cust.id
        WHERE c.id = %s
    """, (conversation_id,))

    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    messages = query_all("""
        SELECT 
            id, sender_type, content, intent, confidence, created_at, metadata
        FROM messages
        WHERE conversation_id = %s
        ORDER BY created_at ASC
    """, (conversation_id,))

    summary_row = query_one("""
        SELECT summary, unresolved_questions, topics
        FROM conversation_summaries
        WHERE conversation_id = %s
    """, (conversation_id,))

    tickets = query_all("""
        SELECT 
            ticket_number, priority, status, reason, sla_due_at, assigned_agent, created_at
        FROM tickets
        WHERE conversation_id = %s
        ORDER BY created_at DESC
    """, (conversation_id,))

    # Sanitize message metadata to ensure system prompts or internal keys are never exposed
    safe_messages = []
    for m in messages:
        raw_meta = m.get("metadata") or {}
        safe_meta = {
            "sentiment": raw_meta.get("sentiment"),
            "order_number": raw_meta.get("order_number"),
            "rag_evidence": raw_meta.get("rag_evidence") or raw_meta.get("sources")
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
        "tickets": [{
            "ticket_number": t["ticket_number"],
            "priority": t["priority"],
            "status": t["status"],
            "reason": t["reason"],
            "assigned_agent": t["assigned_agent"],
            "sla_deadline": t["sla_due_at"].isoformat() if t["sla_due_at"] else None,
            "created_at": t["created_at"].isoformat() if t["created_at"] else None
        } for t in tickets]
    }
