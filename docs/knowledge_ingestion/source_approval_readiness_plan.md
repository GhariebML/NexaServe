# Source Approval and Candidate Acceptance Readiness Plan

**Phase:** read-only review and planning. No database writes, service lifecycle changes, workflow activation, model changes, or external connections were performed.

## Prioritized source decisions

1. **Gate S1 — classify the source:** for each `NEEDS_OWNER_APPROVAL` record, an accountable owner must confirm DEPI initiative, intended audience, content correctness, whether the source is official or internal guidance, and retrieval scope. The workbook's DEPI name and matching SHA-256 establish artifact lineage only.
2. **Gate S2 — prove authority and freshness:** attach an official stable URL or owner-signed internal reference, approval identity/date, effective date, expiry/last-verified date, and cycle applicability. Round 3 / April 10 and workbook round-specific items require explicit current-cycle decisions.
3. **Gate S3 — resolve exceptions:** manually review 132 incomplete/reference records; do not invent questions. Resolve 2 explicit cross-initiative eligibility records with both DEPI and DEBI owner decisions. Reconcile duplicate relationships before approval while preserving original source locators. Keep 162 Digilians records out of DEPI retrieval. Keep 625 ticket rows outside RAG.
4. **Gate S4 — produce human-signed approval manifest:** one decision per source record ID/content hash with allowed initiative/scope and evidence references. Only then rerun the existing fail-closed planner in plan mode. The approved count may remain zero.

## Confirmed technical facts

- All original-source byte hashes in the provenance manifest match; all three JSONL companions compare exactly to their JSON datasets.
- Workbook/PDF records are classified as internal guidance with the proposed scope `DEPI_SCOPED_INTERNAL_PENDING_OWNER_APPROVAL`; that scope label makes no claim that the material is official government content.
- Existing inventory/planner reports 0 approved, 1,333 quarantined, 9 duplicate occurrences, 3 metadata files skipped, and no database writes.
- Candidate Compose currently reaches shared n8n, PostgreSQL, Redis, Ollama and WhatsApp; it is not isolated.
- A prior `qwen2.5:3b` generation returned HTTP 500 after the llama-server process was killed. Current read-only telemetry cannot attribute this to OOM or another cause.

## Unverified hypotheses

- Memory pressure may have contributed to the runner termination; no request-time memory sample/event links the four historical cgroup OOM kills to this request.
- Current headroom may not support a separate candidate Ollama instance; one host memory snapshot is not a peak/load profile.
- Historical records in `nexaserve_final` may lack source-record mapping; do not treat them as a verified import of the current converted corpus without reconciliation.

## Actions requiring separate authorization

- Any controlled generation experiment or candidate service start.
- Provisioning candidate-only database, Redis, Ollama storage, n8n keys/credentials, or workflow imports.
- Any write to any database, including a candidate database, and any import/application of an approval manifest.
- Any change to active workflows, credentials, Docker resource limits, model selection, WhatsApp/session state, or production routing.
- Any cutover or public/LAN exposure.

## Acceptance gates before candidate startup

**Gate A — source:** human-approved record-level manifest; zero ambiguous, out-of-scope, incomplete, or stale records in the allowed import set; reproducible hashes and duplicate reconciliation; planner remains fail-closed.

**Gate B — infrastructure isolation:** candidate-only Compose project/network/volumes and services; no candidate route or credentials to baseline Postgres/n8n/Redis/Ollama/WhatsApp; dedicated read-only retrieval credential; no public infrastructure or n8n admin port; dashboard loopback-only.

**Gate C — resources and generation:** measured host/Docker headroom within explicit limits; candidate Ollama isolated from baseline model storage/runtime; one low-concurrency generation request succeeds with captured logs, memory telemetry and response. Abort on OOM or memory stop threshold.

**Gate D — functional checks:** verify candidate workflow IDs and active states only in candidate n8n; retrieval program/scope filters; evidence IDs, source attribution, and URLs passed to generation; Arabic/English relevant-answer tests; DEBI/Digilians deflection; ambiguity abstention; multi-fact answer; session continuity and user isolation; malformed/empty input; error handling. No WhatsApp node or outbound path.

**Gate E — data integrity:** only after separate approval, apply to candidate-only database; compare approved IDs/hashes, row counts, vectors/dimensions, scope counts and source references; perform second plan/apply to demonstrate idempotency; test that candidate read role cannot write; verify baseline DB/workflow/session/WhatsApp snapshots unchanged.

**Gate F — review:** archive traces, source decisions, backups, resource measurements and rollback procedure; request a separate explicit cutover decision. Passing local candidate acceptance never itself authorizes production routing.

## Step-by-step order

1. Complete Gates S1–S4 with source owners and preserve current local backups/artifacts.
2. Confirm Docker/host memory and disk capacity during an approved test window; if insufficient, use a separate host.
3. Prepare candidate-only Compose and secrets outside the baseline files; review resolved configuration for networks, mounts, ports, environment variables and workflow references before starting anything.
4. After explicit authorization, start only candidate services and verify no baseline network/service is reachable; use no knowledge imports at first.
5. Run the isolated model smoke check and candidate workflow structural checks. Stop if the runner is killed or memory thresholds are crossed.
6. After an approved manifest and separate write authorization, import only to the candidate-only database; run integrity/idempotency checks.
7. Execute all functional and isolation acceptance cases through the candidate dashboard, retaining traces and comparing baseline snapshots.
8. Deliver evidence for separate review; stop before any cutover unless explicitly authorized later.

No backups or rollback artifacts were removed or altered in this phase.
