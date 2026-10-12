# Follow-up Validation Report

**Date:** 2026-10-12  
**Result:** BLOCKED before candidate chat acceptance. Provenance review and runtime diagnosis are complete; no candidate runtime was launched.

## Provenance and reconciliation

Reviewed 1,342 structured records at record level: 717 FAQ/reference rows and 625 ticket rows. The manifest contains full Q/A text and locators for the knowledge rows while omitting ticket contents. All four original source-file SHA-256 checks matched. JSONL companions match the structured JSON records exactly.

Disposition counts: 421 unresolved pending source-owner approval/currentness; 132 unresolved incomplete/reference items; 2 cross-initiative cases quarantined; 162 Digilians records excluded from DEPI retrieval; 625 ticket rows excluded as non-knowledge. Approved for ingestion: **0**. The source manifest records 8 exact duplicate groups with 9 duplicate occurrences. Across the parallel workbook exports, the review also identifies 191 exact normalized content groups (205 repeat occurrences); these export-level matches do not replace or inflate the source-manifest duplicate count. Same-question/different-answer variants remain distinct and are flagged for review.

See [source_reconciliation_report.md](source_reconciliation_report.md) and [source_provenance_review.json](source_provenance_review.json).

## Runtime readiness

The `qwen2.5:3b` generation request returned HTTP 500 because the llama-server process was killed. Memory pressure is plausible, but the inspected evidence does not establish the specific cause. No additional generation request was made against the shared Ollama service. The current candidate compose file points to the shared n8n and WhatsApp services and `test_uat_candidate`; it is not an isolated candidate runtime. No services were started.

See [ollama_generation_diagnosis.md](ollama_generation_diagnosis.md) and [candidate_runtime_readiness.md](candidate_runtime_readiness.md).

## Acceptance cases

| Case | Result | Reason |
|---|---|---|
| Arabic DEPI admission and eligibility | BLOCKED / NOT RUN | No approved source corpus or isolated candidate chat endpoint. |
| DEPI tracks and industry tracks | BLOCKED / NOT RUN | Same blockers. |
| English DEPI vision and objectives | BLOCKED / NOT RUN | Same blockers. |
| General Support / Safe Exam Browser | BLOCKED / NOT RUN | No approved support source and no isolated endpoint. |
| DEBI deflection | BLOCKED / NOT RUN | No candidate endpoint; initiative-labeled content unresolved. |
| Digilians deflection | BLOCKED / NOT RUN | No candidate endpoint. Existing DEPI scope guard remains required. |
| Ambiguous question handling | BLOCKED / NOT RUN | No runtime trace to inspect. |
| Multi-fact answer and evidence attribution | BLOCKED / NOT RUN | No generation or retrieval execution trace. |
| Session continuity | BLOCKED / NOT RUN | No isolated candidate workflow endpoint. |
| User isolation | BLOCKED / NOT RUN | No isolated candidate runtime or controlled session store. |

No response-quality, retrieval, session, or isolation acceptance check is being claimed as passed. Embedding smoke evidence is limited to the earlier two-vector dimension check; no new vectors were stored.

## Change and safety record

This follow-up only generated local review artifacts. Original source files, databases, active workflows, credentials, WhatsApp state, and service routing were not changed. No records were imported, and no candidate workflow was activated. The earlier planner remains at 0 approved, 0 inserted, 0 updated, 0 unchanged, and 0 failed.

## Required before resuming acceptance

1. Obtain source-owner scope and currentness decisions and create a record-level approval manifest.
2. Resolve the generation process termination within a constrained candidate runtime, then capture a successful controlled generation trace.
3. Complete isolated workflow packaging, dedicated credentials, and network restrictions; validate the candidate database target as read-only.
4. Run the listed acceptance cases only through that isolated endpoint and retain retrieval IDs, scope, source attribution, and model context for review.
