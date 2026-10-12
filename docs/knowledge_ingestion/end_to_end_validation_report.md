# Canonical Knowledge Ingestion and Candidate RAG Validation

**Run date:** 2026-10-12 (local workspace)  
**Scope:** Local-only inspection and candidate artifact updates. No ingestion writes, workflow activation, credential changes, source-file changes, or Ministry-server access.

## Result

The canonical source inventory and a fail-closed ingestion planner are in place. The planner found **0 records eligible for ingestion** because the supplied FAQ records are unverified or scope-ambiguous, incomplete, or explicitly duplicates. It therefore made **no database writes**. The full end-to-end RAG acceptance is **not passed**: the candidate workflow is staged but not deployed to an isolated runtime, and there is no candidate chat endpoint to exercise safely.

## Source-to-database reconciliation

See [source_inventory_report.md](source_inventory_report.md) and [source_inventory.json](source_inventory.json). The recursive scan found 9 files: 6 JSON and 3 JSONL. The JSON datasets contain 1,342 entries; their JSONL companions contain the same 1,342 records and compare exactly record-for-record. The companions are excluded from ingestion to avoid double counting.

| Source | Records | Disposition | Reason |
|---|---:|---|---|
| `depi_helper.json` | 265 | Quarantined for review | 64 entries lack a complete question/answer pair; 5 are duplicate-flagged; the workbook is named but records lack source URL and verification status. |
| `faqs.json` | 452 | Quarantined for review | All 452 carry `source_status=unverified`; 59 are reference sections, 66 lack a complete question/answer pair, and the program labels require source-owner confirmation. |
| `tickets.json` | 625 | Quarantined as non-FAQ | Ticket/student/case content is not approved FAQ knowledge. |
| Three manifest JSON files | 0 | Skipped as metadata | Descriptive metadata only; no knowledge-record arrays. |
| Three JSONL files | 1,342 | Skipped as duplicate exports | Exact line-for-line companion datasets of the JSON files above. |

There are 9 repeated canonical content hashes in the ingestion plan. Language is part of the canonical hash, so Arabic and English variants are preserved as distinct records. The planner reports **1,333 quarantined, 9 duplicated, 3 skipped, 0 approved, 0 inserted, 0 updated, 0 unchanged, and 0 failed**. Because there are no approved source records, source-to-new-database reconciliation is **0/0 attempted**, not a claim that the supplied corpus is searchable.

## Current local database state

Read-only PostgreSQL inspection found:

| Database | Rows | Active | Embeddings | Notes |
|---|---:|---:|---:|---|
| `nexaserve_final` | 474 | 253 | 474 | Intended final database exists. It has no separate original-JSON source mapping table. |
| `test_uat_candidate` | 474 | 253 | 474 | Its program/scope counts match `nexaserve_final`; it is not selected as the intended final store. |
| `customerservice` | 73 | 73 | 73 | Left unchanged. |

Active rows in `nexaserve_final` are 233 `DEPI / DEPI_AUTHORITATIVE` and 20 `COMMON / GENERAL_SUPPORT`. All 253 active rows have 768-dimensional vectors, nonempty source attribution and URL, valid 64-character hashes, and no duplicate active hash. No active row has an unapproved retrieval scope or a program/scope pair outside the two allowed pairs. This validates the stored schema and vector shape, but not the authority or correctness of historical source claims; source attribution does not provide a stable source-record mapping for those rows. `nexaserve_final` and `test_uat_candidate` had identical aggregate fingerprints during this read-only inspection.

Inactive rows by program/scope: `COMMON / AMBIGUOUS` 4, `COMMON / GENERAL_SUPPORT` 2, `DEBI / DEBI` 9, `DEBI / QUARANTINED` 9, `DEPI / AMBIGUOUS` 9, `DIGILIANS / DIGILIANS` 162, and `DIGILIANS / QUARANTINED` 26. No historical classification was changed.

## Runtime and candidate workflow

- Local containers are running for PostgreSQL, n8n, Ollama, dashboard, Redis, and WhatsApp. Ollama lists `nomic-embed-text:latest` and `qwen2.5:3b`.
- A direct local embedding smoke test produced two 768-dimensional vectors for Arabic and English input. A harmless `qwen2.5:3b` generation smoke test failed with HTTP 500: `llama-server process has terminated: signal: killed`; the Ollama container reports `oom_killed=true`. No answer-generation/RAG test is accepted as passing.
- The checked-in active workflow export `infra/n8n/workflows/04B_knowledge_base_faq.json` references credential `CS_PG_CRED_01` / `CustomerService Postgres` and filters `program = 'DEBI'`. The actual runtime credential target was not exposed or changed; based on the export and deployment config, this is not verified as `nexaserve_final`.
- The staged candidate workflow references `CS_PG_FINAL_01` / `CustomerService Postgres Final`, but its live credential binding and target database could not be verified. The candidate workflow is not active in n8n.
- The staged candidate query now filters on `retrieval_scope` and allows only `DEPI_AUTHORITATIVE` with program `DEPI`, or `GENERAL_SUPPORT` with program `COMMON`. Its response formatter retains both eligible scopes, and source attribution, URL, and scope are included in the evidence text passed to the generation node.
- `docker-compose.candidate.yml` currently points its dashboard at `test_uat_candidate` and sends chat to the shared n8n service. That is not an isolated candidate RAG endpoint, so it was not used for acceptance requests.

## Acceptance checks

| Check | Result | Evidence / limitation |
|---|---|---|
| Every JSON source file receives a disposition | PASS | 6 JSON files inventoried; 3 metadata, 2 FAQ-like quarantines, 1 ticket quarantine. |
| JSONL companions accounted for | PASS | 3 exact record-for-record companions; excluded from ingestion. |
| Source/database record reconciliation | BLOCKED | 0 eligible source records; no database write was attempted. Existing 474-row store is historical and lacks source-record mapping. |
| Hash and embedding validation | PASS for existing active rows | 253 active hashes valid and unique; all active vectors are 768-dimensional. No source-record embeddings were generated or stored. |
| Configured embedding endpoint | PASS | `nomic-embed-text` returned 768 dimensions for one Arabic and one English input. Vectors were not stored. |
| Configured generation endpoint | FAIL | `qwen2.5:3b` returned HTTP 500 because the local llama-server process was killed; Ollama reports `oom_killed=true`. |
| Active program/scope validation | PASS for stored rows | 233 DEPI-authoritative and 20 General Support active; no other active scope/program combinations. Authority of historical provenance remains unverified. |
| Arabic DEPI admission and eligibility | NOT RUN | No candidate chat endpoint. |
| DEPI tracks and industry tracks | NOT RUN | No candidate chat endpoint. |
| English DEPI vision and objectives | NOT RUN | No candidate chat endpoint. |
| General Support / Safe Exam Browser | NOT RUN | No candidate chat endpoint. |
| DEBI and Digilians deflection | NOT RUN | No candidate chat endpoint. |
| Retrieved evidence passed to generation model | STRUCTURAL CHECK ONLY | Staged workflow JSON includes retrieved text and source metadata in the generation context; no runtime execution trace is available. |
| Idempotent second ingestion | NOT RUN | No records were eligible and no apply run was performed. |
| `customerservice`, active workflows, WhatsApp state unchanged | PASS for this run | No DB writes, workflow imports/activations, credential edits, or chat calls were made. `customerservice` remains at 73 rows; WhatsApp container remained running. |

## Deliverables and reproducibility

- [Machine-readable source inventory](source_inventory.json)
- [Human-readable source inventory](source_inventory_report.md)
- [Machine-readable ingestion plan and counts](ingestion_summary.json)
- [Inventory script](../../scripts/inventory_converted_sources.py)
- [Fail-closed ingestion script](../../scripts/ingest_converted_knowledge.py)
- [Staged candidate 04B workflow](../../deployment/candidate_workflows/04B_knowledge_base_faq.candidate.json)

Run `python scripts/inventory_converted_sources.py` and `python scripts/ingest_converted_knowledge.py` for a fresh read-only inventory and ingestion plan. Applying requires `--apply` plus an explicit reviewer approval manifest; only the isolated `nexaserve_final` or `test_uat_candidate` databases are accepted. The source directory is never used as an output directory.

## Unresolved items before local cutover

1. A source owner must verify each DEPI record, clarify whether the conversion's `DEBI` label is a misclassification or another initiative, and approve only complete FAQ records with traceable provenance.
2. General Support records need verified platform-support provenance and explicit approval. Ticket records require a separate privacy and knowledge review and are not part of this FAQ pipeline.
3. The existing 474-row final store needs a reviewed mapping/reconciliation from row IDs to source file and source record before it can be treated as a complete canonical ingestion result.
4. Resolve the local Qwen generation process termination and repeat a real generation smoke test; retain the current configured model until its failure cause is understood.
5. Provision an isolated candidate n8n/dashboard configuration whose Postgres credential is confirmed to target `nexaserve_final`; do not reuse the shared active credential/workflow. The current candidate dashboard points at `test_uat_candidate` and shared n8n.
6. After those prerequisites, apply the reviewed records, capture DB and workflow execution traces, run the required Arabic/English/scope tests through the candidate endpoint, repeat ingestion to prove idempotency, and compare `customerservice`, active workflow versions, and WhatsApp state before and after.

## Controlled local cutover steps

After review approval: (1) create a record-level approval manifest and verify source status/scope; (2) take a local backup of `nexaserve_final`; (3) run the ingestion script first in plan mode, review counts and diffs, then apply only approved records; (4) run the isolated candidate n8n workflow against the final database; (5) capture retrieval IDs, scopes, citations, model context, and answers for every acceptance case; (6) repeat ingestion and verify zero new rows; and (7) present the evidence for approval before routing any active dashboard or WhatsApp traffic to the candidate.
