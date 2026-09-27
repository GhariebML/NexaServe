# Runtime forensic checkpoint

Checkpoint captured 2026-09-27 22:02 Africa/Cairo (UTC+03:00), before runtime or knowledge-base mutations.

## Repository state

- Repository root: `E:\NexaServe`.
- Branch: `master` at `72f6e68` (`feat: enterprise readme overhaul, high-fidelity visual assets, and full whatsapp live gateway sync`).
- The worktree was already substantially dirty, including changes to compose, workflow JSON, PostgreSQL schema, WhatsApp bridge, scripts, and numerous untracked files. No commit/reset was made so existing work would be preserved.

## Docker state

- Docker Desktop 4.89.0 / Engine 29.7.2 was responding.
- All five Compose containers were healthy: `cs-n8n`, `cs-ollama`, `cs-postgres`, `cs-redis`, and `cs-whatsapp`.
- The WhatsApp bridge health endpoint reported connected. This records the bridge status only; no real WhatsApp test message was sent.

## n8n state

- 38 workflow records existed, with 17 active records. Several names have multiple historical/duplicate rows; canonical-use review remains open.
- Active core IDs: `CSWF000000000001` through `CSWF000000000008`, with the agent bridge `RWLCadRzOPjTHXVo` and output dispatcher `F7kjakLJXmzBDsvS`.
- The live full export of all 38 workflows is preserved under `backups/runtime_forensic_20260927_220221/live_n8n_workflows/`.

## Database and knowledge base state

- `customerservice.knowledge_base`: 66 rows; all 66 active and all 66 have a non-null 768-dimensional embedding.
- 29 rows are categorized `scraped_faq`; their `source_attribution` is only `scraped`, not a source URL.
- 36 rows have no `content_hash`; none lack an embedding. No `content_hash` duplicates were found.
- Tables and counts were inspected read-only; no production rows were deleted or reset.

## Checkpoint files

`backups/runtime_forensic_20260927_220221/` contains copies of the repository workflow JSON, `.env`, `docker-compose.yml`, PostgreSQL schema/init script, and RAG ingestion/embed/diagnostic scripts. It also contains all 38 live n8n workflow exports, a CSV snapshot of the 66-row knowledge base including vector values, and the five existing scraper output files. The `.env` copy contains secrets and must remain local; secrets are not included in this document or diagnostic reports.

## First live execution finding

A synthetic webchat FAQ request reached the active gateway, session manager, intent workflow, knowledge workflow, output dispatcher, and logger. It retrieved the expected DEBI conditions row (KB id 91) and returned that row's answer. However, the RAG Qwen HTTP node returned HTTP 400 because its request body was encoded as an array; the formatter then used the curated top-row answer. The retrieval formatter also consumed only the first of five PostgreSQL result items. See `logs/runtime_forensic/replay_01.json` and `logs/runtime_forensic/execution_5317.json`.

## Runtime execution state at checkpoint

The execution table contained many successful runs, 64 error runs, four crashed runs, and several running executions at the capture time. Recent intent subworkflow executions repeatedly lasted approximately 45 seconds and returned an Axios `ECONNABORTED` timeout from the Ollama request, after which the parser defaulted some requests to `general_support`. Details are recorded in `docs/n8n_runtime_execution_audit.md` after the controlled replay set is complete.
