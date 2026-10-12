# Dashboard RAG quality and Excel reporting

## Baseline inspected

The active application source is `dashboard/`: FastAPI serves a single vanilla JavaScript interface. The main container in the root `docker-compose.yml` builds from that directory. The separately packaged `deployment/application/dashboard` source is synchronized for the deployment compose build as well. The interface has no client-side route framework; `switchView()` selects its nine navigation views. All dashboard reads use the current bearer token and `get_current_user`. The ticket-response action requires `admin`, `agent`, or `supervisor`; n8n activate/deactivate actions require `admin` or `supervisor`. The existing customer API un-masks phone and email only for admins; this export omits email and reuses the API's role-masked phone value.

## Authenticated page inventory and export coverage

| UI view | Purpose and current source | Page filters and displayed metrics | Permission / privacy behavior | Excel report |
|---|---|---|---|---|
| Executive KPIs (`GET /summary`) | Customer, conversation, ticket, and audit-log aggregates from PostgreSQL | Global period and program selectors; customer count is program-scoped, conversation/ticket counts use the selected period and program, operational turn telemetry now uses both | Any authenticated dashboard role; aggregated data only | `executive`: one metrics sheet; period/program included |
| Customers (`GET /customers`) | Customer registry joined to conversation/ticket counts | Program, search text, 10-row UI pagination | Existing endpoint masks phone/email except for admins; workbook includes role-masked phone only and no email | `customers`: all matching rows, up to 5,000, not just visible page |
| Conversations (`GET /conversations`, `GET /conversations/{id}`) | Conversation summaries and aggregate/chart queries | Period, program, 10-row UI pagination | Any authenticated role; no message bodies or detail-modal history in workbook | `conversations`: all matching summaries plus analytics and chart-source sheets; individual detail excluded |
| Tickets (`GET /tickets`, `POST /tickets/{id}/respond`) | Ticket queue joined to customers | Status, priority, program; API also supports SLA-breached filter; UI has no period filter | Any authenticated role can read; response action requires admin/agent/supervisor. Workbook omits ticket `reason` and internal IDs | `tickets`: all matching list rows, up to 5,000 |
| n8n Automation (`GET /n8n/overview`, `/workflows`, `/executions`) | Read-only n8n API snapshots | No page filters; UI shows workflow metadata and latest executions | Dashboard authentication as existing read endpoints; no credential values or execution payloads exported. Activate/deactivate actions are not called | `n8n`: workflows plus latest 100 execution summaries; current API exposes a 100-item cap |
| Live AI Simulator (`POST /n8n/simulate`) | Sends a live customer inquiry to the configured gateway and may create operational events | Program/channel and submitted inquiry | Authenticated live action; not a passive dataset | Not offered: a report action must not dispatch a live customer request |
| RAG & AI Quality (`GET /rag`) | Operational database telemetry, latency, confidence distribution | No page-specific filters; the global toolbar is not applied by this existing view | Any authenticated role; no prompts or answer content exported | `rag`: operational telemetry, confidence distribution, and sanitized historical benchmark summary |
| Knowledge Base (`GET /knowledge-base`) | PostgreSQL document/embedding aggregates | No page-specific filters | Any authenticated role; route exposes aggregate counts, not document rows or provenance | `knowledge-base`: current summary, program, and attribution aggregates; this view has no record listing |
| System Health (`GET /system-health`) | Snapshot of database/Redis/model/gateway service probes | No filters | Any authenticated role; report includes only component, status, latency, and check time | `health`: read-only point-in-time health snapshot |
| Recent Activity (`GET /executions`, `/activity`) | Correlated audit-log requests and latest audit events | Request status selector; audit event table has no filter; global toolbar is not used by this page | Any authenticated role; only safe summary fields exported, not raw audit payloads or messages | `activity`: all status-matching correlated requests up to 5,000 plus the latest 100 safe audit summaries |

### API route inventory

| Route | Auth / role | Purpose |
|---|---|---|
| `POST /api/auth/login` | Public login | Issues bearer token after authentication |
| `POST /api/auth/change-password` | Authenticated | Changes current account password |
| `GET /api/dashboard/summary` | Authenticated | Overview metrics |
| `GET /api/dashboard/customers` | Authenticated | Filtered customer registry |
| `GET /api/dashboard/conversations` | Authenticated | Filtered conversation summaries and analytics |
| `GET /api/dashboard/conversations/{conversation_id}` | Authenticated | Conversation detail, including message history subject to existing PII rules |
| `GET /api/dashboard/tickets` | Authenticated | Filtered ticket list |
| `POST /api/dashboard/tickets/{ticket_id}/respond` | Admin, agent, supervisor | Mutating response/resolve workflow; not invoked by report generation |
| `GET /api/dashboard/rag` | Authenticated | Operational RAG telemetry, not benchmark accuracy |
| `GET /api/dashboard/rag/evaluation-summary` | Authenticated | Sanitized read of benchmark result summary; no inference or benchmark execution |
| `GET /api/dashboard/knowledge-base` | Authenticated | Knowledge-base aggregates |
| `GET /api/dashboard/system-health` | Authenticated | Service health probes |
| `GET /api/dashboard/activity` | Authenticated | Latest safe audit-event summaries |
| `GET /api/dashboard/executions` | Authenticated | Paginated correlated request summaries |
| `GET /api/dashboard/executions/{request_id}` | Authenticated | Redacted execution detail |
| `GET /api/dashboard/n8n/overview` | Authenticated | Read-only workflow/gateway overview |
| `GET /api/dashboard/n8n/workflows` | Authenticated | Read-only n8n workflow metadata |
| `GET /api/dashboard/n8n/executions` | Authenticated | Read-only latest n8n execution summaries |
| `POST /api/dashboard/n8n/workflows/{workflow_id}/activate` | Admin, supervisor | Mutating workflow control; never called by export |
| `POST /api/dashboard/n8n/workflows/{workflow_id}/deactivate` | Admin, supervisor | Mutating workflow control; never called by export |
| `POST /api/dashboard/n8n/simulate` | Authenticated | Live gateway action; not invoked by export |
| `GET /api/dashboard/reports/{report_type}/excel` | Authenticated | Bounded page-specific XLSX export |

`GET /health/live`, `GET /health/ready`, and `GET /` are public operational/static routes rather than authenticated data pages. The ready probe checks configured dependencies; it was not called for this task.

## RAG evaluation interpretation

The dashboard reads the sanitized `dashboard/data/rag_evaluation_summary.json` artifact. `scripts/build_dashboard_rag_summary.py` derives it from the master and golden RAG result files only after the master run records a completed golden report. It stores aggregate counts, explicitly recorded runtime/corpus identity, timestamps, and SHA-256 checksums; it never copies prompts, answers, or case-level content. `tests/run_all_tests.py` invokes this builder after a completed RAG run and refreshes the root and deployment dashboard copies. The Docker images copy only this small sanitized artifact, not the repository's raw benchmark files.

The latest artifact records 36 planned cases: 33 passed, 2 failed, and 1 blocked. The acceptance pass rate among completed cases is `33 / (33 + 2) = 94.3%`; the blocked case is separately reported. This is not answer accuracy. The earlier 8/10 acceptance result described in the project brief remains an older acceptance result and is not relabeled as answer accuracy. The latest machine artifact has no evaluated runtime identity, corpus version, or timezone. It therefore cannot be connected to the active dashboard runtime and is shown as **BLOCKED / historical**, not healthy or live. The separate operational successful-turn rate is not an answer-quality measure either.

The summary endpoint performs one sanitized-file read only. It does not query PostgreSQL, launch a benchmark, or invoke a model. The builder requires the golden output timestamp to match the latest master run and the master suite output to confirm that a report was written. With a clean artifact, `HEALTHY` is possible only when its recorded runtime and corpus identifiers exactly match both configured active identifiers and the evaluation is within the seven-day freshness window; failures then display `NEEDS_IMPROVEMENT`. Missing or invalid artifacts display `NOT_EVALUATED`.

## Workbook behavior

- Reports are generated on demand with `openpyxl`, using the dashboard's navy/blue palette.
- Arabic reports set worksheet right-to-left and retain UTF-8 content. Datetimes with offsets are normalized to UTC-naive Excel datetimes; the report timestamp is included.
- Tables have a frozen header, filters, readable widths, wrapped content, alternating rows, and a filter summary. No workbook combines/decorates the tabular data range.
- Exports have a 5,000-row per-sheet ceiling, a 30-second total report deadline and 10-second PostgreSQL statement deadline, return the XLSX MIME type and a date-stamped ASCII filename, and use `Cache-Control: no-store`.
- Untrusted strings whose first non-whitespace character is `=`, `+`, `-`, or `@` are written as inert text. Numeric negative values remain numeric.
- Exports reuse the page API functions and role-filtered values. They omit email, raw message history, ticket reason, and raw audit payloads. No password, token, credential, or session fields are selected.
- Report creation is read-only. It does not activate workflows, dispatch simulator requests, or write to PostgreSQL.

## UI/UX roadmap

- **P0 — Correctness and safety:** distinguish operational turn telemetry from measured answer quality; show the real historical benchmark as blocked because runtime/corpus linkage is absent; keep RAG/API and Excel paths read-only, authenticated, bounded, and formula-safe. Core changes implemented.
- **P1 — Consistent reports and structure:** shared bilingual export action, page adapters, page filters, masking, and styled XLSX output; keep live simulator and message-detail actions outside report generation. Core report coverage implemented for every passive data view.
- **P2 — Accessibility, responsive behavior, and performance:** visible keyboard focus, native keyboard-operable export button, live download feedback, mobile toolbar/card stacking, bounded pagination. Automated checks cover these source-level behaviors. Manual browser/assistive-technology QA and visual viewport testing remain outstanding.

## Remaining limits and verification

- Knowledge Base currently exposes aggregates only, so this report cannot contain individual knowledge records or source-provenance rows.
- n8n exports are read-only snapshots; the existing API caps executions at 100. The activity view's audit-event source is capped at its latest 100 rows by its existing endpoint.
- Simulator submissions and conversation-detail/message-history exports are intentionally unsupported because they are live actions or sensitive content rather than a safe passive report.
- This task did not connect to the configured database, Redis, n8n, Ollama, WhatsApp, or Ministry systems. The existing full production dashboard test suite depends on live services; only isolated unit/API tests and static syntax checks are appropriate here.

### Local verification

From `E:\NexaServe`:

```powershell
python -m pytest -q tests/test_dashboard_reporting.py tests/test_dashboard_runtime_observability.py
node --check dashboard/frontend/app.js
python -m compileall -q dashboard/backend
```

The normal backend startup is `uvicorn main:app --host 127.0.0.1 --port 8090` from `dashboard\backend`, with local-only `DASHBOARD_JWT_SECRET` and `CS_DB_PASSWORD` and an isolated development database configured. The application initializes a PostgreSQL pool at startup, so no service was started during this verification. Root Docker Compose builds from `./dashboard`; the deployment compose bundle builds from `deployment/application/dashboard`, whose dashboard sources, sanitized RAG artifact, and dependencies are synchronized for this change. After a completed RAG suite, the master runner refreshes the packaged summary. To associate a benchmark with a runtime/corpus, explicitly supply `--evaluation-runtime-identity` and `--evaluation-corpus-version` to `tests/run_all_tests.py`; those values are optional and are never invented by the runner.
