# NEXASERVE — MASTER PRODUCTION ARCHITECTURE, HARDENING & DEPLOYMENT PLAN (V2)

**Document Version:** 2.0.0 (Production Engineering Review & Correction)  
**Date:** 2026-09-27  
**Project Path:** `E:\NexaServe`  
**Status:** Approved Target Plan for Immediate Systematic Execution  

---

## 1. Executive Summary & V1 Plan Review

The Phase 0 discovery and baseline audit in Plan V1 accurately identified critical technical debt, security exposures, and operational gaps in NexaServe. However, an engineering review of Plan V1 reveals several critical architectural flaws, naive assumptions, and arbitrary heuristics that would compromise system reliability if implemented as written.

This V2 Master Plan corrects those flaws, aligns priorities with production realities, formalizes strict contracts, and outlines a verified execution path without rebuilding or discarding working architecture.

### Critical Deficiencies Identified in Plan V1

1. **Naive Secret Remediation (Phase B):**  
   *V1 Flaw:* Assumed replacing passwords in `infra/n8n/credentials.json` with `${ENV_VAR}` syntax would work out of the box.  
   *Reality:* n8n does not perform bash-style parameter expansion inside static credential JSON files on disk; credentials in n8n are managed via its internal encrypted SQLite/Postgres database (`credentials_entity`) or via n8n's dedicated CLI/environment mechanisms. Blind string replacement would corrupt n8n's credential loading.
2. **Symptom Patching for RAG Leakage (Phase D):**  
   *V1 Flaw:* Proposed regex-stripping prefixes like `[DEBI]`, `[COMMON]`, `سؤال:`, `إجابة:` from the final string as the primary fix.  
   *Reality:* Regex stripping is only a last-mile defensive filter. The root cause is architectural: in `04B_knowledge_base_faq.json`, when the LLM node fails, times out, or produces low confidence, the workflow logic falls back to directly assigning `ragData.rag_context` to `finalReply`. Raw retrieval context must *never* be the customer-facing response.
3. **Destructive & Over-Aggressive Arabic Normalization (Phase F):**  
   *V1 Flaw:* Blindly proposed converting Taa Marbuta (`ة`) to Haa (`ه`).  
   *Reality:* This causes semantic collisions (e.g., `منحة` [scholarship] vs `منحه` [granted him], `مدرسة` [school] vs `مدرسه` [taught him], `خاصة` vs `خاصه`). Normalization must be conservative, non-destructive, and applied only to retrieval index/lookup projections, never mutating the immutable customer message.
4. **Arbitrary Evidence Gate Thresholds (Phase G):**  
   *V1 Flaw:* Proposed arbitrary cutoffs (`relevance_score < 20`).  
   *Reality:* In pgvector cosine distance, scores are in $[0, 2]$, where distance $\to 0$ means exact identity. In hybrid RAG combining lexical keyword weights with vector similarity, scores depend on specific weighting formulas. Thresholds must be calibrated against measured score distributions using a validation set.
5. **Uncontrolled Fallback in WhatsApp Gateway (Phase N):**  
   *V1 Flaw:* Acknowledged the issue but left room for an in-process direct LLM call.  
   *Reality:* `server.js` contained a 140-line `generateAutonomousResponse()` function that queried Ollama directly with zero RAG grounding, zero PII masking, zero prompt injection guardrails, and no audit trail. This must be eliminated in favor of deterministic, safe deflection and guaranteed webhook retry/queuing.
6. **Schema vs Runtime Embedding Dimension Contract (Phase C):**  
   *V1 Flaw:* Simply edited `vector(384)` to `vector(768)` in `schema.sql` without establishing a single source of truth across ingestion scripts, database migrations, pgvector HNSW/IVFFlat indexes, and clean bootstrap validation.

---

## 2. Comparative Matrix: Plan V1 vs Plan V2

| Dimension | Plan V1 (Questionable / Deficient) | Plan V2 (Corrected & Production-Grade) | Architectural Rationale |
| :--- | :--- | :--- | :--- |
| **Secret Management** | Naive string substitution (`${VAR}`) in static JSON & scripts | Environment-driven configuration via `.env`, Docker env pass-through, verified n8n credential import/CLI, and credential rotation | Ensures runtime stability; avoids crashing n8n credential deserialization. |
| **RAG Output Architecture** | Regex sanitization of raw chunks (`replace(/\[DEBI\]/)`) | Strict pipeline separation: `Retrieval Context` $\to$ `LLM Synthesis` $\to$ `Structured Output Validator` $\to$ `Sanitized Reply`. Fallback returns deterministic curated text, never raw context. | Fixes the root cause. Raw chunk dump is architecturally impossible. |
| **Program Disambiguation** | Broad keyword checks (`'depi'`, `'الرواد'` in Digilians list) | Deterministic Multi-Tier Entity Resolver: (1) Exact multi-word entities, (2) Known program aliases, (3) Program-specific phrases, (4) Specific keywords, (5) Disambiguation prompt. | Prevents cross-program leakage between Digilians and DEBI. |
| **Arabic Text Normalization** | Aggressive replacement (`ة` $\to$ `ه`, indiscriminate stripping) | Conservative, information-preserving normalization: Unicode NFKC, strip tashkeel/tatweel, normalize Alef variants (`أ/إ/آ` $\to$ `ا`), normalize whitespace. Keeps `ة` intact. Applied to search projections only. | Preserves semantic lexical identity and prevents false positive keyword collisions. |
| **Evidence Gate** | Arbitrary cutoff (`score < 20`) | Calibrated multi-factor confidence scoring: vector distance threshold + lexical keyword match + program scope alignment $\to$ `ANSWER`, `CLARIFY`, `DEFLECT`, or `ESCALATE`. | Prevents hallucinations when query has poor evidence grounding. |
| **WhatsApp Fallback** | Autonomous ungrounded Ollama query directly inside `server.js` | Elimination of uncontrolled LLM. Deterministic offline response + Redis/in-memory retry queue + structured audit log. | Closes the major security/grounding bypass. |
| **Embedding Contract** | In-place edit of `schema.sql` line | Canonical contract: `EMBEDDING_MODEL=nomic-embed-text`, `EMBEDDING_DIM=768`. Synchronized across `schema.sql`, migration script, ingestion, and clean bootstrap test. | Guarantees fresh cluster bootstrap and zero dimension mismatch. |
| **Customer Memory** | Generic key-value store, max 3 items | Relevance-filtered multi-tier memory: (1) Turn context, (2) Rolling summary, (3) Fact extraction with TTL & confidence. Memory cannot override verified KB. | Grounding hierarchy: Security Rules > Verified KB > Turn Context > Memory. |
| **Out-of-Scope Handling** | Static 4-word regex (`weather`, `sports`) | Intent engine deterministic classification + fast-path deflection before expensive RAG/LLM invocation. | Low latency for out-of-scope queries without brittle regex. |

---

## 3. Strict Priority Classification

Every planned task is categorized under operational definitions:

### P0 — Deployment Blockers (Must fix before any production traffic)
1. **P0-1:** Remove hardcoded credentials across all tracked scripts (`ingest_knowledge.py`, `seed_digilians_properly.py`, `embed_missing_knowledge.py`, `reset-n8n-password.ps1`). Rotate exposed passwords in Postgres and n8n.
2. **P0-2:** Eliminate uncontrolled autonomous Ollama LLM fallback in `infra/whatsapp/server.js`.
3. **P0-3:** Fix architectural RAG context leakage in `04B_knowledge_base_faq.json` (prevent raw chunks reaching customer; fallback to deterministic verified text).
4. **P0-4:** Synchronize schema embedding dimension: unify `schema.sql` and live DB to `vector(768)` for `nomic-embed-text`.
5. **P0-5:** Implement deterministic entity resolution in `04B` to stop cross-program contamination between DEBI and Digilians.
6. **P0-6:** Fix clean-bootstrap capability so a fresh `docker compose up -d` initializes cleanly without manual database intervention.

### P1 — Production Hardening Requirements (Required before go-live)
1. **P1-1:** Calibrated Evidence Gate in RAG pipeline (`ANSWER` / `CLARIFY` / `DEFLECT` / `ESCALATE`).
2. **P1-2:** Conservative Arabic normalization for retrieval and intent matching.
3. **P1-3:** Structured LLM JSON output contract with validator node in `04B`.
4. **P1-4:** Three-layer memory architecture (Recent turns + Rolling conversation summary + Extracted profile facts).
5. **P1-5:** End-to-end Human-In-The-Loop (HITL) ticket escalation, SLA assignment, and agent bridge verification.
6. **P1-6:** Idempotency & deduplication for WhatsApp incoming webhooks (prevent duplicate tickets/messages).
7. **P1-7:** Disaster Recovery validation (reproducible automated backup and isolated restore test).
8. **P1-8:** Golden test dataset (40+ curated evaluation cases) and automated regression test suite.

### P2 — Performance & Reliability Improvements
1. **P2-1:** Out-of-scope fast path in Intent Engine (deflect greeting/trivia/nonsense without RAG/LLM).
2. **P2-2:** Redis retrieval and embedding caching layer.
3. **P2-3:** Structured observability, request telemetry, and standard `/health` endpoints.
4. **P2-4:** pgvector index benchmarking (Flat vs IVFFlat vs HNSW on current dataset size).

### P3 — Operational Refinements (Non-blocking)
1. **P3-1:** Admin CLI utilities for memory inspection.
2. **P3-2:** Dashboard metrics visualization.

---

## 4. Target Architecture & Flow

```
+-----------------------------------------------------------------------------------+
|                            WhatsApp Channel (Baileys)                            |
+-----------------------------------------------------------------------------------+
                                         |
                                         | 1. Inbound Webhook (with Idempotency Key)
                                         v
+-----------------------------------------------------------------------------------+
|                        n8n 01 Gateway Dispatcher                                  |
|   - Webhook validation & idempotency check (Redis dedup)                          |
|   - PII Redaction (National ID, Phone, Email)                                     |
|   - Language Detection (ar / en)                                                  |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        n8n 02 Customer Session & Memory                           |
|   - Customer Upsert & Conversation State Registry                                 |
|   - Load 3-tier Context: Recent Turns + Conversation Summary + Verified Facts     |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        n8n 03 AI Intent Engine                                    |
|   - Security Guardrails (Prompt Injection / Jailbreak Filter)                     |
|   - Fast-Path Out-of-Scope Classifier (Greeting, System, Escalation, KB)          |
+-----------------------------------------------------------------------------------+
                                         |
         +-------------------------------+-------------------------------+
         | (faq_query / program_inquiry)                                 | (escalation / order)
         v                                                               v
+------------------------------------+                         +-------------------+
|  n8n 04B Hybrid RAG Sub-Workflow   |                         |  04A / 04C / 04D  |
|                                    |                         |  Order Lookup /   |
| 1. Multi-Tier Entity Resolver      |                         |  HITL Escalation  |
|    (DIGILIANS vs DEBI vs AMBIGUOUS)|                         +-------------------+
| 2. Conservative Arabic Normalizer  |
| 3. Hybrid Retrieval:               |
|    - pgvector Cosine (768-dim)     |
|    - Lexical Keyword Match (tsvector)
| 4. Calibrated Evidence Gate:       |
|    - Sufficient -> Pass to LLM     |
|    - Ambiguous  -> Clarification   |
|    - Deficient  -> Safe Deflection |
| 5. Grounded LLM Prompt (qwen2.5)   |
| 6. Structured JSON Validator       |
| 7. Last-Mile Shield (Anti-leakage) |
+------------------------------------+
                   |
                   v
+-----------------------------------------------------------------------------------+
|                        n8n 06 Output Dispatcher                                   |
|   - Customer Response Formatting (WhatsApp markdown)                              |
|   - Dispatch to WhatsApp HTTP Gateway (:8080/send)                                |
+-----------------------------------------------------------------------------------+
                                         |
                                         v
+-----------------------------------------------------------------------------------+
|                        n8n 05 Conversation Logger                                 |
|   - Masked Message Archival & Performance Telemetry (latency, confidence, tokens)  |
+-----------------------------------------------------------------------------------+
```

---

## 5. Detailed Execution Sequence (Phases 1 to 21)

```
Step 1: Security & Credential Hardening (P0)
Step 2: Database Schema & Clean Bootstrap Consistency (P0)
Step 3: WhatsApp Gateway Hardening (Remove Ollama Fallback) (P0)
Step 4: RAG Core Architectural Correction (Zero Raw Leakage) (P0)
Step 5: Multi-Tier Program Disambiguation Engine (P0)
Step 6: Conservative Arabic Normalization Engine (P1)
Step 7: Calibrated Evidence Gate (P1)
Step 8: Grounded Structured LLM Output Contract (P1)
Step 9: Three-Layer Customer Memory & Summary Architecture (P1)
Step 10: Human-in-the-Loop (HITL) Workflow Verification (P1)
Step 11: Idempotency & Webhook Deduplication (P1)
Step 12: Out-of-Scope Fast-Path Classification (P2)
Step 13: Caching & Performance Benchmark (P2)
Step 14: Structured Observability & Health Probes (P2)
Step 15: Backup & Disaster Recovery Verification (P1)
Step 16: Comprehensive Golden Dataset & Evaluation (P1)
Step 17: Clean Bootstrap Deployment Test (P0)
Step 18: Final Production Readiness Report (P0)
```

---

## 6. Acceptance Gates & Verification Evidence Checklist

Before claiming the system is "Production Ready", every gate below must be backed by a reproducible, automated test script or command output:

- [ ] **Gate 1 (Security):** `git grep` and codebase scans show 0 hardcoded DB/Redis/n8n passwords in tracked files.
- [ ] **Gate 2 (Bootstrap):** Database initialization script cleanly creates `vector(768)` tables and extensions.
- [ ] **Gate 3 (WhatsApp Fallback):** Simulating n8n outage results in a deterministic safe response or queueing, with 0 ungrounded Ollama calls.
- [ ] **Gate 4 (RAG Leakage):** 0 instances of `[DEBI]`, `[DIGILIANS]`, `[COMMON]`, `سؤال:`, or internal scores in customer output.
- [ ] **Gate 5 (Program Separation):** 100% isolation in golden tests: DEBI queries return DEBI facts; Digilians queries return Digilians facts.
- [ ] **Gate 6 (Evidence Gate):** Low-confidence or out-of-domain questions trigger safe deflection or clarification without LLM hallucination.
- [ ] **Gate 7 (Memory & Summary):** Conversation summaries and facts persist across turns without overriding verified KB content.
- [ ] **Gate 8 (Disaster Recovery):** `backup.ps1` produces a valid tar/sql archive, and `restore.ps1` successfully restores it in an isolated container.
- [ ] **Gate 9 (Golden Suite):** All categories in the golden test suite pass with precision $\ge 95\%$ and 0 hallucinations.
- [ ] **Gate 10 (Telemetry):** Every request generates a structured audit record with latency, program, and confidence.
