# NexaServe Remote Production Acceptance Test

Audit date: 2026-10-07 (Africa/Cairo). Target: `depi@10.179.0.125`, deployment `/opt/nexaserve/deployment`. Mode: read-only. No workflow, schema, customer, knowledge-base, or service changes were made. No customer WhatsApp messages were sent.

## 1. Executive Summary

The host and six expected application containers are up and Docker reports each healthy. PostgreSQL is reachable, required tables and pgvector exist, and the requested orphan-count checks all returned zero. A minimal harmless generation against the internal production Ollama model returned `NEXASERVE_TEST_OK` on `qwen2.5:3b`.

The deployed system is **not ready for real users**. The running n8n logs show renewed `messages_conversation_id_fkey` failures (12 matching log lines, including October 6) and “there is no parameter” failures (48 matching log lines, including October 6). The database records 16 failed workflow executions in the last seven days. The RAG program inventory contains 36 active entries under `DEBI` and none under `DEPI` or `DIGILIANS`; expected program coverage and isolation therefore are not demonstrated. The deployed Ollama container differs from the host-local Ollama API, making endpoint identity/configuration a material drift. End-to-end and authenticated dashboard behavior were not exercised because they write production rows or require credentials.

OVERALL STATUS: FAIL — NOT READY
PRODUCTION READINESS SCORE: 45/100
PASS: 7 | FAIL: 7 | PARTIAL: 9 | BLOCKED: 6
CRITICAL FINDINGS: Recent session/message foreign-key failures and missing-SQL-parameter failures in production workflow logs; customer-service E2E remains unverified.

## 2. Environment Identity

TEST ID: ENV-01
CATEGORY: Remote identity
STATUS: PASS
LATENCY: SSH connection ~3 seconds
EVIDENCE: `whoami=depi`; `hostname=depi`; shell started in `/home/depi`; `/opt/nexaserve/deployment` exists and was inspected.
IMPACT: Correct Ministry host was reached directly at the supplied IP.
NOTES: SSH alias `nexaserve-ministry` did not resolve in the earlier check; the supplied direct target `depi@10.179.0.125` worked.

TEST ID: ENV-02
CATEGORY: Host platform
STATUS: PASS
LATENCY: N/A
EVIDENCE: Ubuntu 24.04.5 LTS; kernel `6.17.0-1032-oem`; x86_64; Intel Core i7-14700, 28 CPUs; 31 GiB RAM (19 GiB available at observation); NVIDIA RTX 2000 Ada, 16,380 MiB.
IMPACT: GPU and memory resources are present.
NOTES: Snapshot only; no load test performed.

TEST ID: ENV-03
CATEGORY: Runtime versions
STATUS: PASS
LATENCY: N/A
EVIDENCE: Docker 29.8.1; Docker Compose v5.5.1.
IMPACT: Runtime versions recorded.
NOTES: —

## 3. Deployment Version

TEST ID: DEP-01
CATEGORY: Deployment integrity
STATUS: PARTIAL
LATENCY: N/A
EVIDENCE: `VERSION` is `0.1.1`; changelog dated 2026-09-28 describes production reconciliation; all files listed in `MANIFEST.sha256` checked successfully. Top-level bundle includes `application`, `assets`, `checks`, `compose`, `config`, `docs`, `migrations`, `scripts`, and `tests`.
IMPACT: Bundle integrity is supported by matching checksums.
NOTES: No `.git` directory exists in the deployment, so branch, commit, Git status, and tracked-secret checks cannot be established. Effective bundle version is 0.1.1, not a Git-verified revision. Changelog itself describes prior manual hotfix reconciliation.

## 4. Infrastructure Health

TEST ID: INF-01
CATEGORY: Host/network
STATUS: PARTIAL
LATENCY: N/A
EVIDENCE: Host listeners include `0.0.0.0:80`; n8n 5678, dashboard 8090, WhatsApp 8080, and host Ollama 11434 bind to loopback. PostgreSQL 5432 and Redis 6379 are not host-published. No listener on 443 was observed.
IMPACT: Private service ports are loopback/internal, but plain HTTP is exposed on all interfaces and HTTPS was not observed.
NOTES: A proxy container was not present in `docker ps -a`; the process owning port 80 was not identified. Firewall rules were not inspected.

## 5. Service Health

TEST ID: SVC-01
CATEGORY: HTTP service probes
STATUS: PARTIAL
LATENCY: n8n 0.7–1.7 ms; dashboard `/health` 1.2–1.5 ms (404); WhatsApp 1.2–14.8 ms; host Ollama `/api/tags` 1.2–1.6 ms.
EVIDENCE: n8n `/healthz` returned HTTP 200; WhatsApp `/health` returned HTTP 200 and sanitized state `CONNECTED`; Ollama tags returned HTTP 200. Dashboard root returned HTTP 200, while `/health` returned 404 and authenticated system-health route returned 401.
IMPACT: Core probes respond; dashboard health data requires authenticated access.
NOTES: Only three samples per endpoint; insufficient for meaningful p95. Dashboard 404 is not treated as a service failure because it may not be a defined route.

## 6. Docker Health

TEST ID: DKR-01
CATEGORY: Containers
STATUS: PASS
LATENCY: N/A
EVIDENCE: `cs-postgres`, `cs-redis`, `cs-ollama`, `cs-n8n`, `cs-whatsapp`, `cs-dashboard` all running and Docker-healthy; zero restarts. Uptime was 8–9 days. App services share `nexaserve-backend`. GPU reservation exists on `cs-ollama`; `ollama ps` showed the loaded embedding and generation models at 100% GPU.
IMPACT: Expected six services are up without observed crash loops.
NOTES: Compose declares a proxy service, but no proxy container was present. Resource memory/CPU limits were unset (0) in inspected containers. Internal ports: PostgreSQL 5432, Redis 6379, Ollama 11434, n8n 5678, WhatsApp 8080, dashboard 8090.

## 7. Database Integrity

TEST ID: DB-01
CATEGORY: PostgreSQL/schema/integrity
STATUS: PASS
LATENCY: Connection successful; query sub-second (no repeated timing series collected)
EVIDENCE: PostgreSQL 16.15; database `customerservice`; required tables present, including `customers`, `conversations`, `messages`, `tickets`, `audit_logs`, `knowledge_base`, `admin_users`, `customer_memory`, and `conversation_summaries`. pgvector 0.8.6, pg_trgm 1.6, uuid-ossp 1.1, plpgsql 1.0 present. Vector column is `knowledge_base.embedding`, active populated vectors all dimension 768. Requested orphan counts: messages→conversation 0; messages→customer 0; conversations→customer 0; tickets→customer 0; non-null ticket→conversation missing 0.
IMPACT: Current relational data passes these count checks and schema has the expected foreign keys/indexes.
NOTES: Counts do not prevent new application inserts from failing. `messages_conversation_id_fkey` remains an observed runtime regression (see Sections 12, 13, and 19). No customer rows or message bodies were read.

TEST ID: DB-02
CATEGORY: Redis
STATUS: PASS
LATENCY: N/A
EVIDENCE: Unauthenticated Redis ping correctly returned `NOAUTH`; authenticated ping using the container’s existing runtime environment returned `PONG`. Redis container is healthy and port 6379 is not host-published.
IMPACT: Redis responds with authentication enforced.
NOTES: Credential was not printed.

## 8. n8n Workflow Audit

TEST ID: WF-01
CATEGORY: Deployed workflow catalog
STATUS: PASS
LATENCY: N/A
EVIDENCE: Read directly from n8n’s PostgreSQL `workflow_entity`: all 10 workflows active. Master 01 ID `CSWF000000000001` (19 nodes); SubWF 02 `CSWF000000000002` (4); SubWF 03 `CSWF000000000003` (5); SubWF 04A `CSWF000000000004` (3); SubWF 04B `CSWF000000000005` (8); SubWF 04C `CSWF000000000006` (6); SubWF 05 `CSWF000000000007` (5); SubWF 06 ID `F7kjakLJXmzBDsvS` (8); Global Error Handler `CSWF000000000008` (2); extra SubWF 04D (9). Normal workflows reference the global error workflow.
IMPACT: Actual database definitions are active and contain the expected routing, AI, RAG, logger, output, and error nodes.
NOTES: Node inventory examined from deployed definitions. No workflow edits were made.

TEST ID: WF-02
CATEGORY: Identity continuity
STATUS: BLOCKED
LATENCY: N/A
EVIDENCE: Full continuity across customer, conversation, message, request/execution IDs, locale, AI output, and final reply requires executing a workflow; this would exercise production session and logger writes. Logger SQL contains a fallback UUID when conversation/customer identity is absent.
IMPACT: Identity survival across workflow boundaries has not been proven; fallback identity risks foreign-key failures.
NOTES: E2E execution requires approval because workflow nodes persist production customer/session/message/audit records.

## 9. AI / Ollama Validation

TEST ID: AI-01
CATEGORY: Model runtime
STATUS: PARTIAL
LATENCY: Generation returned within the SSH command; a dedicated timing measurement was not obtained.
EVIDENCE: `cs-ollama` contains `qwen2.5:3b` and `nomic-embed-text:latest`; `ollama ps` showed both on 100% GPU. Harmless `ollama run qwen2.5:3b` prompt returned exactly `NEXASERVE_TEST_OK`. Deployed n8n node URLs target `http://cs-ollama:11434`; WhatsApp points to `http://ollama:11434/api/generate`.
IMPACT: Internal configured generation model is present and inference works.
NOTES: A separate host-local Ollama at `127.0.0.1:11434` advertises only `qwen3-vl:8b`; this is distinct from the Compose Ollama container and creates configuration/version-drift risk. Qwen JSON contract was not tested through workflow. Embedding inference was not conclusively exercised; vector dimension is 768 in stored KB.

## 10. RAG Validation

TEST ID: RAG-01
CATEGORY: Retrieval inventory and routing
STATUS: FAIL
LATENCY: Aggregate query only
EVIDENCE: Active KB aggregates show 36 records, all program `DEBI`; no `DEPI`, `DIGILIANS`, or `COMMON` rows were reported. The deployed 04B graph has Program Detector & Query Normalizer, Generate Embedding, Query Bilingual Knowledge Base, Format RAG Knowledge Response, Check if LLM Needed, Qwen RAG Grounded Response, and Guardrail & Professional Formatter.
IMPACT: Expected DEPI and Digilians coverage is absent from the queried active inventory; correct program isolation and official grounding cannot be accepted.
NOTES: No KB record contents were printed. The `DEBI` spelling may be a deliberate internal code, but its mapping to user-facing DEPI is unverified.

TEST ID: RAG-02
CATEGORY: Grounding, thresholds, fallback, leakage
STATUS: BLOCKED
LATENCY: N/A
EVIDENCE: Static workflow graph confirms the intended RAG nodes, but runtime retrieval scores, evidence gate, confidence categories, raw-context leakage, and fallback behavior require safe execution inputs. The normal path includes persistence, so no webhook was triggered.
IMPACT: Hallucination resistance and retrieval correctness are unverified.
NOTES: Prompt-injection, unsupported Digilians, DEPI factual and paraphrase scenarios remain untested.

## 11. AI Response Test Matrix

TEST ID: AI-MATRIX-01
CATEGORY: Greeting/thanks/casual/ambiguous/unsupported/injection/short/Arabic variants
STATUS: BLOCKED
LATENCY: N/A
EVIDENCE: None of the ten requested cases was sent through the production customer-service webhook. Even greeting-like inputs proceed through session creation and message/audit logging in the deployed graph.
IMPACT: Natural response quality, factual grounding, intent/program classification, confidence, execution IDs, and guardrail behavior cannot be claimed.
NOTES: Safe synthetic direct model smoke passed in Section 9, but it is not an end-to-end pipeline result. Matrix is marked blocked pending approval for production writes or an explicitly non-production test channel.

## 12. Session / Conversation Integrity

TEST ID: SES-01
CATEGORY: Session and FK regression
STATUS: FAIL
LATENCY: N/A
EVIDENCE: Container logs contain 12 `messages_conversation_id_fkey` signature lines since deployment, with occurrences on 2026-10-06 as well as first startup. Logger SQL has a hard-coded fallback conversation UUID for missing identity. Aggregate database orphan checks currently return zero.
IMPACT: New message inserts can fail even though existing rows are consistent.
NOTES: Current source bundle changelog mentions earlier hotfix reconciliation, but deployed runtime logs show the failure signature recurring.

## 13. Logging Validation

TEST ID: LOG-01
CATEGORY: Workflow logging
STATUS: FAIL
LATENCY: N/A
EVIDENCE: 16 failed n8n executions in the last seven days: 8 Global Error Handler, 4 Master 01, 2 SubWF 04C, 2 SubWF 05. Logger includes Save Customer Message, Save AI Response, and audit inserts. FK signature appeared in logger-era log timestamps.
IMPACT: Logging and customer-message persistence are not reliably successful.
NOTES: No rows or payload content inspected. Aggregate counts only.

## 14. Error Handling Validation

TEST ID: ERR-01
CATEGORY: Global handler / SQL parameters
STATUS: FAIL
LATENCY: N/A
EVIDENCE: Global Error Handler is active and configured on normal workflows. Its Postgres insert uses `$1`, `$2`, `$3` and has a nonempty n8n `queryParams` expression. Nevertheless, logs contain 48 “there is no parameter” signature lines; the most recent observed burst was 2026-10-06. Eight Global Error Handler executions failed in the last seven days.
IMPACT: Error audit insertion is not demonstrated to work, and error propagation can produce a second failure.
NOTES: The existence of a binding expression is insufficient to call this fixed. No destructive failure was deliberately triggered. Prior parameter error is classified STILL PRESENT in runtime evidence.

## 15. Dashboard Validation

TEST ID: DASH-01
CATEGORY: Authentication and data routes
STATUS: BLOCKED
LATENCY: root ~2.5 ms; protected route ~1 ms
EVIDENCE: Dashboard UI root returned HTTP 200; protected `/api/dashboard/system-health` and `/api/dashboard/summary` returned 401 without credentials. `/api/auth/login` is POST-only; no approved credentials or existing authenticated session were available. OpenAPI lists summary, customers, conversations, tickets, RAG, knowledge-base, activity, and system-health routes.
IMPACT: JWT, RBAC, PostgreSQL data access, and live aggregate views were not verified.
NOTES: No login POST was attempted and no credentials were read or printed.

## 16. WhatsApp Bridge Validation

TEST ID: WA-01
CATEGORY: Bridge state / outbound
STATUS: PARTIAL
LATENCY: health samples 1.2–14.8 ms
EVIDENCE: `/health` returned HTTP 200 with sanitized `status=CONNECTED`, `connected=true`. Bridge container is healthy and binds loopback port 8080; its configured n8n destination uses the internal customer-service webhook.
IMPACT: Bridge reports connected at the service level.
NOTES: No QR/session identifiers or phone details included. No customer messages sent. Actual n8n dispatch/outbound delivery was not exercised.

## 17. Performance Results

TEST ID: PERF-01
CATEGORY: Latency
STATUS: PARTIAL
LATENCY: n8n health 0.7–1.7 ms; dashboard root 2.5 ms; WhatsApp health 1.2–14.8 ms; host-local Ollama tags 1.2–1.6 ms.
EVIDENCE: Three health samples each. DB connection and Redis PONG succeeded. One model smoke succeeded, but dedicated internal generation/embedding timing series were not collected.
IMPACT: Basic local endpoints are responsive at low load.
NOTES: Three samples are insufficient for meaningful p95. No load test performed. p50/p95 not reported as statistically representative.

## 18. Security Findings

TEST ID: SEC-01
CATEGORY: Secret/file exposure
STATUS: PARTIAL
LATENCY: N/A
EVIDENCE: Deployment `.env` mode 0600, owned by `depi`; secrets were not printed. Docker socket mode 0660, root:docker; host account can operate Docker. PostgreSQL and Redis are internal-only; dashboard/n8n/WhatsApp/Ollama host bindings are loopback. Manifest verification passed. Deployment has no Git metadata.
IMPACT: `.env` file permissions are restrictive. Docker group membership grants powerful host control; access should be limited to administrators.
NOTES: Tracked-secret scan cannot be established without a Git repository. Credential/private-key files were not dumped.

TEST ID: SEC-02
CATEGORY: Network exposure
STATUS: FAIL
LATENCY: N/A
EVIDENCE: Host listens on all interfaces at port 80; no 443 listener or proxy container was observed. Firewall state and port-80 process/routing were not established.
IMPACT: Public HTTP and absent observed HTTPS create a transport-security/exposure concern.
NOTES: Severity HIGH until intended ingress and TLS termination are verified.

## 19. Known Issue Regression Tests

TEST ID: REG-01
CATEGORY: Static fallback reply
STATUS: BLOCKED
LATENCY: N/A
EVIDENCE: No workflow response matrix was run.
IMPACT: Cannot determine whether “شكراً على استفسارك. لا تتوفر تفاصيل رسمية...” appears only for unsupported official questions or incorrectly for thanks/general support.
NOTES: Requires pipeline test inputs.

TEST ID: REG-02
CATEGORY: `ERROR IN WORKFLOW`
STATUS: PARTIAL
LATENCY: N/A
EVIDENCE: No exact static phrase appeared in sampled n8n logs; 16 failed executions and missing-parameter/FK signatures did appear.
IMPACT: User-visible error behavior is not established.
NOTES: Absence of that literal does not establish a friendly fallback.

TEST ID: REG-03
CATEGORY: conversation FK
STATUS: FAIL
LATENCY: N/A
EVIDENCE: 12 log lines, including 2026-10-06.
IMPACT: Regression remains observable.
NOTES: See SES-01.

TEST ID: REG-04
CATEGORY: `$1` error handler
STATUS: FAIL
LATENCY: N/A
EVIDENCE: 48 “there is no parameter” log lines; latest observed 2026-10-06; handler has a parameter expression but still records failures.
IMPACT: Logger/error audit reliability is not accepted.
NOTES: See ERR-01.

TEST ID: REG-05
CATEGORY: LLM routing and Qwen JSON contract
STATUS: PARTIAL
LATENCY: N/A
EVIDENCE: Runtime smoke confirms installed `qwen2.5:3b` responds. Deployed n8n workflow has an Ollama cognitive classifier and Qwen RAG grounded response node aimed at internal `cs-ollama`.
IMPACT: Presence of nodes/model does not prove general_support or evidence-backed content reaches Qwen, nor that answer/language/grounded/confidence JSON is parsed correctly.
NOTES: Runtime pipeline test blocked.

TEST ID: REG-06
CATEGORY: Guardrail rejection
STATUS: BLOCKED
LATENCY: N/A
EVIDENCE: Guardrail nodes exist in deployed graph; no unsupported-output test was executed.
IMPACT: Rejection of ungrounded model output is unverified.
NOTES: —

## 20. Production Readiness Score

Equal-weight mean of the 15 requested categories; scores reflect observed evidence and blocked acceptance checks.

| Category | Score |
|---|---:|
| Infrastructure | 75 |
| Database | 82 |
| n8n orchestration | 45 |
| AI/LLM | 60 |
| RAG | 30 |
| Grounding | 20 |
| Guardrails | 30 |
| Session management | 25 |
| Logging | 35 |
| Error handling | 20 |
| Dashboard | 35 |
| WhatsApp | 80 |
| Security | 55 |
| Performance | 60 |
| Testing | 20 |
| **Overall (mean)** | **45** |

Classification: **NOT READY** (<70). Runtime DB FK errors and logging/error-handler failures independently prevent acceptance.

## 21. Critical Findings

1. n8n production logs show repeated missing SQL parameter errors and conversation foreign-key errors, including recent October 6 occurrences.
2. Sixteen workflow executions failed in the last seven days, including eight Global Error Handler runs and two logger runs.
3. Active knowledge-base aggregate contains 36 `DEBI` records but no records under `DEPI` or `DIGILIANS`; intended program taxonomy/coverage must be confirmed.
4. Host-local Ollama advertises `qwen3-vl:8b`, while deployed internal `cs-ollama` uses `qwen2.5:3b` and `nomic-embed-text`; endpoint drift makes status checks ambiguous.
5. Dashboard authentication/data checks and the production end-to-end customer-service path remain unverified.
6. Port 80 listens on all interfaces with no observed 443 listener; ingress/TLS path needs confirmation.

## 22. Recommended Actions

1. Reproduce and resolve the conversation/customer identity flow behind the recurring message foreign-key errors; validate with a disposable non-production database before production acceptance.
2. Inspect why error-handler and logger Postgres nodes emit missing-parameter failures despite configured `queryParams`; run an isolated error-path test after correction.
3. Confirm the intended KB program identifiers and load/verify sanctioned DEPI and Digilians coverage through the approved knowledge process.
4. Standardize the Ollama endpoint/model configuration and make health checks query the same internal service used by n8n.
5. Provide an explicitly non-production channel/database for the full response matrix and E2E synthetic webhook, including RAG/grounding, Qwen JSON, identity continuity, and error-path assertions.
6. Perform authenticated Dashboard verification using an approved test account; validate RBAC and sanitized aggregates.
7. Confirm intended ingress, identify the port-80 listener, and establish TLS/443 availability before real users.

## 23. Final Verdict

**NOT READY FOR REAL USERS.** Infrastructure processes are alive, but production runtime evidence shows unresolved workflow persistence and error-handler failures. RAG coverage/grounding and user-facing workflow behavior have not been proven. No repairs or production mutations were performed.

### Terminal summary

OVERALL STATUS: FAIL — NOT READY
PRODUCTION READINESS SCORE: 45/100
PASS: 7
FAIL: 7
PARTIAL: 9
BLOCKED: 6
CRITICAL FINDINGS: Recurring conversation FK failures; missing SQL parameter errors; 16 failed workflow executions in seven days; KB program mismatch/coverage unknown; no authenticated dashboard or E2E acceptance evidence.
TOP 5 RECOMMENDED ACTIONS:
1. Resolve and non-production-validate conversation/customer ID continuity and message FK failures.
2. Resolve and test Postgres parameter binding in the logger and Global Error Handler.
3. Confirm DEPI/Digilians program identifiers and official KB coverage.
4. Standardize and validate the internal Ollama model endpoint used by n8n.
5. Run the complete synthetic response/E2E matrix against an isolated non-production environment, then verify Dashboard auth and TLS ingress.


