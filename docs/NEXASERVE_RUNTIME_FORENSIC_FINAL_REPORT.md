# NEXASERVE RUNTIME FORENSIC FINAL REPORT

**Audit date:** 2026-09-27 (Africa/Cairo)  
**Decision:** **NOT READY**

## 1. Current Runtime State

All five Docker Compose services currently report healthy, including n8n, PostgreSQL, Redis, WhatsApp bridge, and Ollama. n8n `/healthz` returned 200. The Ollama tag health check does not exercise model generation: the `qwen2.5:3b` llama-server was killed by OOM, and `/api/generate` returned HTTP 500. Container memory events currently show 31 OOM kills. HTTP 200 from the customer webhook can therefore conceal an LLM failure.

Live n8n has 38 workflow records, 17 active. Current database has 73 active KB rows, all with 768-dimensional vectors. Latest execution counts: 5,175 success, 75 error, seven crashed, zero running. These aggregates include synthetic audit activity and ambient traffic.

## 2. What Was Actually Broken

- RAG generation request body was serialized as an array and rejected by Ollama with HTTP 400.
- RAG formatting consumed only the first of five Postgres rows, silently dropping four results.
- Generic program names/stopwords inflated retrieval scores. Scholarship queries ranked training-duration content; no-answer and security queries still produced candidate rows.
- Common comparison content could enter single-program retrieval.
- Anonymous webchat users all shared the same `web-anon` customer/session identity.
- n8n error/retry behavior allowed failed LLM generation to appear as a successful customer response because the validator returned a curated fallback.
- The Windows scraper attempted unavailable packaged Chromium and returned no rendered sections on its first run.
- Ingestion’s default host Ollama URL did not expose the `nomic-embed-text` model used in Docker.
- A concurrent 30-case load attempt produced 26 HTTP 503 `Database is not ready!` responses.

## 3. Root Causes

**INFRASTRUCTURE:** current Docker Desktop memory ceiling is insufficient for the deployed Qwen generation process with the active service set.  
**RETRIEVAL / CONTEXT_BUILDING:** weak lexical tokenization, generic-token matches, cross-scope COMMON comparison row, uncalibrated answer gate, and all five candidates passed to context.  
**CONFIGURATION:** invalid JSON body and embedding endpoint default.  
**MEMORY / LOGGING:** shared anonymous user ID and missing request/master execution correlation.  
**SOURCE_FRESHNESS:** no current Digilians official URL lineage and incomplete metadata for legacy rows.

## 4. Broken Nodes

See [broken_nodes_fixed.md](broken_nodes_fixed.md). The key active nodes were 04B `Qwen RAG Grounded Response`, 04B formatter/SQL output, 03 intent fallback, gateway normalization, logger, and scraper browser launch. Final live test caught a duplicate `topicCategory` declaration (execution 6133); it was fixed and the revised workflow completed execution 6134.

## 5. RAG Retrieval Findings

The exact official DEPI eligibility FAQ ranks first in the official source trace. Before the retrieval-gate change, a scholarship question ranked a DEPI training-duration FAQ first, and the fallback could have used that unrelated answer. Post-fix retrieval replay used topic boosts, stopword/program-token suppression, single-program filters without comparison COMMON rows, and a lexical/keyword/topic evidence gate. Across the 30 planned query cases, 24 passed that retrieval evidence gate; three ambiguous requests were intentionally handled by clarification; no-answer, injection, and out-of-scope requests failed the gate. All DEBI and DIGILIANS top-10 lists had zero opposite-program rows.

These are retrieval-stage checks, not end-to-end LLM acceptance. Detailed pre/post top-10 records are under `logs/runtime_forensic/rag_top10_all_30_*.jsonl`.

## 6. Official FAQ Traceability

Verified chain: `DEPI_Web_Scraper/data/final/faqs.json` → `scripts/ingest_knowledge.py` → active DB row 101 → `nomic-embed-text` 768-D vector → rank 1 → exact fact in RAG context → final answer in webhook and AI message log.

Fact: `من المؤهل للتدريب؟` → `طلاب و خريجو الكليات بالجامعات المصرية حسب المسار.` Source URL: `https://depi.gov.eg/content/faqs`. Current source file, DB row, hash, vector, rank, context, validator, logger, and response are captured in [official_faq_trace.json](../logs/runtime_forensic/official_faq_trace.json). Qwen failed; the exact final answer was the curated fallback.

## 7. Official Scraped Website Traceability

The DEPI scraper produced seven pages, 29 FAQs, seven RAG page chunks, and zero discovered PDFs in the latest manual crawl. All 29 FAQ records match their source Q/A and hashes; all 36 DEPI scraped records have official source URLs. The browser fallback now prefers installed Edge on Windows. This verifies DEPI only; no current official Digilians crawl/source URL was established.

## 8. Knowledge Base Quality

73 total / 73 active / 73 embedded / all vector dimensions 768; 36 have source URLs; 37 have content hashes; zero empty questions/answers; zero replacement characters; zero exact normalized duplicate Q/A pairs. The 36 legacy records without URL/hash cannot be fully source- or embedding-synchronized. Twenty-six Digilians records use `depi_*` categories, which are misleading despite the `program=DIGILIANS` filter. One local PDF row and two COMMON rows lack authoritative URL lineage. See [knowledge_base_quality_report.md](knowledge_base_quality_report.md).

## 9. Arabic Quality

The verified Arabic source answer and Arabic ambiguity clarification were exact. However, the 30-case webhook run was not a valid full-quality sample: the concurrent run returned 26 service-unavailable errors, and a DEPI scholarship request returned an irrelevant duration answer. The final Arabic model generation remains unverified due OOM.

## 10. Program Isolation

The post-fix 30-query retrieval-stage replay had zero DEBI↔DIGILIANS opposite-program entries in single-program top-10s. A comparison query intentionally retrieves both plus the COMMON comparison record. This does not yet prove zero leakage in generated customer answers because model generation did not complete.

## 11. LLM Prompt / Context Analysis

The exact scraped FAQ answer entered the context. The earlier context contained all five retrieved rows, including unrelated duration, industry-track, and contact information. The final formatter now limits non-comparison context to three and applies a stronger evidence gate. The actual production prompt includes language, grounding, and isolation rules. Generation failed before a valid model response; prompt quality cannot be signed off from fallback results.

## 12. Memory

Before correction, anonymous requests shared `web-anon`, allowing unrelated webchat users to share session history. The active gateway now uses a stable supplied session/user ID, or request-scoped identity when none is supplied. The latter prevents cross-user sharing but cannot maintain memory across turns without a stable client session ID. A full memory follow-up test is still outstanding.

## 13. WhatsApp

The bridge and container health checks were healthy; baseline history included a live WhatsApp inbound execution. No controlled real outbound WhatsApp message was sent, so WhatsApp delivery is **not verified end to end**. Synthetic tests used only `channel=webchat`.

## 14. Logs / Correlation

After the correlation patch, synthetic request `forensic-live-ambiguous-final-02` returned parent execution ID 6134. Both customer and AI `messages.metadata` rows and the audit row contain that request ID and parent execution ID. The logged clarification exactly equals the webhook response. See `logs/runtime_forensic/final_live_ambiguous.json`.

## 15. Fixes Applied

- Corrected generation request JSON type and formatter item handling.
- Added safe zero-row output behavior, source URL selection, and topic-aware retrieval/evidence gating.
- Removed comparison rows from single-program scopes; excluded nondiscriminative stopwords and program names.
- Added deterministic intent fallback after classifier timeout.
- Added request/session/master-execution correlation to gateway response and logger.
- Fixed scraper browser selection and Ollama embedding endpoint defaults.
- Added official scraped FAQ/page records only; no existing KB rows or Docker volumes were deleted.

## 16. Before vs After Response Examples

| Query | Before | After evidence check | Status |
|---|---|---|---|
| `ما هي المنح المتاحة في DEPI؟` | Top candidate was a training-duration FAQ; an accepted fallback answered “four months.” | Post-fix scorer ranks DEBI benefits row 96. | Retrieval fixed in direct scoring replay; full model response unverified. |
| `ما هي مسارات DEPI؟` | Industry comparison text ranked above the tracks record. | Post-fix scorer ranks DEBI tracks row 93. | Retrieval-stage success. |
| `Does DEPI guarantee a job at NASA?` | Similar DEPI rows scored high enough to enter the answer path. | Candidate fails the explicit evidence gate. | Safe deflection logic verified in scoring replay; not a full live LLM test. |
| `ما هي المسارات؟` | Shared anonymous identity and unclear scope. | Post-fix live request returned an explicit DEPI-vs-Digilians clarification; logger matched. | Live webchat verified. |
| Official FAQ eligibility | RAG retrieved official FAQ row 101, but Qwen failed. | Exact source answer preserved through fallback, with source→DB→retrieval→context→webhook/log proof. | Grounded fallback verified; LLM generation failed. |

## 17. Tests

- **Thirty webhook cases:** attempted synthetically; concurrent run yielded 4 HTTP 200 and 26 HTTP 503. The raw JSONL is interleaved by overlapping runners, so detailed row bodies are not fully recoverable. Aggregate results are in `parallel_attempt_b_summary.json`.
- **Post-fix retrieval replay:** 30 cases plus one official-source query; correct topic rows and zero opposite-program top-10 leakage; no-answer/security/out-of-scope evidence gates rejected.
- **Official source trace pytest:** 2 passed, 1 failed. The failed generation acceptance test correctly reports that Qwen was killed and the final answer came from fallback.
- **Final live webchat clarification:** execution 6134 passed through session, intent, RAG, output, logger, and webhook with matching correlation IDs.
- **WhatsApp real E2E:** not run.

## 18. Remaining Issues

1. Allocate sufficient runtime memory or benchmark alternatives before changing the deployed model. Keep qwen2.5:3b until a controlled accuracy/Arabic/groundedness/latency/memory comparison is available.
2. Repeat 30 sequential webhook tests with stable model availability and preserve each execution’s nodes, retrieval, prompt, output, validator, and logged response.
3. Verify official Digilians source lineage; source-map historical records; repair category labels; validate the COMMON comparison row.
4. Establish stable browser session IDs and run a memory follow-up case.
5. Run controlled WhatsApp delivery with an approved test target and end-to-end correlation.
6. Add per-row embedding model/content hash/freshness metadata for future ingestion and backfill only where provenance is proven.

## 19. Final Readiness

**NOT READY.** Correct official DEPI evidence can be retrieved and preserved, program-scoped retrieval was improved, and webchat logging now correlates. The model generation process still fails under the current memory ceiling; a customer query returned an irrelevant fallback; load tests produced 503s; Digilians and legacy KB source lineage is incomplete; WhatsApp delivery and memory continuity remain unverified. Docker health and HTTP 200 are not sufficient evidence of customer-ready quality.
