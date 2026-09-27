# NexaServe Production Dashboard Architecture Document

**System Version:** NexaServe V2.0 Hardened Production Baseline  
**Component:** Production Admin & Operations Dashboard  
**Date:** 2026-09-27  
**Status:** **OPERATIONAL & PRODUCTION READY**

---

## 1. Architectural Overview & Design Philosophy

The NexaServe Production Admin Dashboard is engineered as an operations cockpit providing real-time visibility into customer sessions, AI intent classification, RAG retrieval metrics, SLA compliance, and underlying containerized infrastructure health.

```
       ┌────────────────────────────────────────────────────────┐
       │     NexaServe Modern Operations Dashboard (SPA)        │
       │    Vanilla CSS Design System • Chart.js • RTL/LTR       │
       └───────────────────────────┬────────────────────────────┘
                                   │ HTTP / JSON (Bearer JWT)
                                   ▼
       ┌────────────────────────────────────────────────────────┐
       │         NexaServe Dashboard Backend API Service        │
       │      FastAPI • Parameterized Queries • RBAC Engine     │
       └─────┬──────────────┬──────────────┬──────────────┬─────┘
             │              │              │              │
      (psycopg2 Pool)  (redis-py)   (HTTP /healthz) (HTTP /health)
             │              │              │              │
             ▼              ▼              ▼              ▼
     ┌──────────────┐┌──────────────┐┌───────────┐┌──────────────┐
     │  PostgreSQL  ││ Redis Cache  ││    n8n    ││ WhatsApp     │
     │  + pgvector  ││ (Session/KB) ││ Workflows ││ Gateway      │
     │ (Truth Store)│└──────────────┘└───────────┘└──────────────┘
     └──────────────┘
```

### Core Non-Negotiables Enforced:
1. **Single Source of Truth:** PostgreSQL remains the single source of truth (`customerservice` database). Business state is never duplicated into the frontend.
2. **Real Operational Data:** No mock or synthetic KPI cards. All metrics reflect live database counts and audit logs.
3. **Defense-in-Depth Security:** PII is scrubbed and masked server-side by default (`mask_phone`, `mask_email`). Internal credentials, prompt templates, and secrets are strictly excluded from API outputs.
4. **Clean Decoupled Architecture:** Built on lightweight, robust FastAPI with connection pooling (`psycopg2.pool.SimpleConnectionPool`), preventing thread starvation and frontend reload overhead.

---

## 2. Authentication & Authorization (RBAC)

The dashboard implements JSON Web Token (JWT) bearer authentication with cryptographically salted SHA-256 password hashing.

### User Roles & Permission Matrix:

| Role | Unmasked PII Access | Ticket Management | Conversation Content | Analytics & KPIs | System Health |
|:---|:---:|:---:|:---:|:---:|:---:|
| **`admin`** | ✅ Full Cleartext | ✅ Full CRUD | ✅ Full View | ✅ Full View | ✅ Full View |
| **`agent`** | ❌ Masked (`+2010****000`) | ✅ View & Assign | ✅ Turn Messages | ✅ Standard View | ✅ Full View |
| **`readonly`** | ❌ Masked (`+2010****000`) | 👁️ Read-Only | 👁️ Read-Only | ✅ Standard View | 👁️ Read-Only |

*Default seed users created:*
*Accounts are bootstrapped with cryptographically random passwords that must be changed on first login.*
*Credentials are never stored in documentation or source code.*
*Run the bootstrap script (docs/dashboard_operations.md) to provision or rotate access.*

---

## 3. Endpoints Specification

| Method | Route | Description | Auth Required |
|:---|:---|:---|:---:|
| `POST` | `/api/auth/login` | Authenticates operator, issues 12h JWT token | Public |
| `GET` | `/api/dashboard/summary` | Executive KPI cards (real PG aggregation) | Bearer Token |
| `GET` | `/api/dashboard/customers` | Paginated customer registry with PII masking | Bearer Token |
| `GET` | `/api/dashboard/conversations` | Sessions, turns, program & intent distribution | Bearer Token |
| `GET` | `/api/dashboard/conversations/{id}` | Conversation detail, scrubbed messages, tickets | Bearer Token |
| `GET` | `/api/dashboard/tickets` | Human-in-the-Loop tickets, SLA compliance filters | Bearer Token |
| `GET` | `/api/dashboard/rag` | AI retrieval latencies, confidence distribution | Bearer Token |
| `GET` | `/api/dashboard/knowledge-base`| KB document counts, embedding sync (`66 / 66`) | Bearer Token |
| `GET` | `/api/dashboard/system-health` | Probes all 5 components with millisecond latency | Bearer Token |
| `GET` | `/api/dashboard/activity` | Audit log trail from `audit_logs` | Bearer Token |

---

## 4. UI/UX & Localization

- **Responsive Enterprise Layout:** Sidebar navigation with sticky header, responsive card grid, and accessible tables.
- **Bilingual Arabic/English Support:** Built-in `I18N` dictionary with instantaneous direction switching (`dir="rtl"` vs `dir="ltr"`), using `Cairo` typography for Arabic and `Inter` for English.
- **Visual Analytics:** Real-time Chart.js integration rendering:
  - Conversations over time (time series)
  - Program breakdown (DEPI vs Digilians doughnut chart)
  - AI confidence distribution (histogram)
- **Interactive Modals:** Conversation detail modal displaying customer profile, sanitized turn-by-turn history, and attached SLA tickets.

---

## 5. Performance Optimizations & Indexing

The following dashboard-specific database indexes were inspected, validated via `EXPLAIN ANALYZE`, and added:
- `idx_customers_created_at` on `customers(created_at)`
- `idx_tickets_created_at` on `tickets(created_at)`
- `idx_tickets_sla_due_at` on `tickets(sla_due_at)`
- `idx_messages_confidence` on `messages(confidence)`
- `idx_messages_intent` on `messages(intent)`
- `idx_audit_latency` on `audit_logs(latency_ms)`
