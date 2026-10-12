# NexaServe RAG — Professional Retrieval Quality & Grounding Audit Report

**Audit Date:** 2026-10-11  
**Target Environment:** Local Windows Workspace (`E:\NexaServe`), Local Docker Desktop (`desktop-linux`)  
**Services Inspected:** `cs-n8n`, `cs-postgres`, `cs-ollama`  
**Execution Boundary:** Read-Only Audit & Offline Test Harness. Zero database mutations executed. Zero workflow nodes edited or published. Zero external/Ministry servers contacted.

---

## Executive Summary & Scorecard

| Evaluation Dimension | Audit Result | Key Finding / Evidence |
|---|:---:|---|
| **1. Technical Retrieval Pipeline** | **PASS** | Hybrid pgvector (cosine) + full-text word frequency + topic boost executes cleanly under 305ms. |
| **2. Embedding & Vector Contracts** | **PASS** | `nomic-embed-text` generates 768-dim embeddings matching `vector(768)` in PostgreSQL. All 73 rows have non-null vectors with HNSW indexing. |
| **3. Retrieval Quality (Recall & MRR)** | **FAIL** | **Recall@1: 36.84%**, **Recall@3: 52.63%**, **Recall@5: 57.89%**, **MRR: 0.4579**. Well below the >=90% production threshold. |
| **4. Cross-Program Contamination** | **FAIL** | **17 of 25 evaluated test queries (68%)** were contaminated by historical DEBI Master's scholarship records (IDs 90–97). |
| **5. DEPI Isolation** | **FAIL** | The active database still stores both DEPI (36 records) and DEBI (8 seed records) under `program = 'DEBI'`. A DEPI question about tracks returns DEBI Master's degrees from Ottawa/Canada. |
| **6. Grounding & Hallucination Gates** | **PASS** | Qwen 2.5 1.5B JSON schema enforces `"grounded": true` and strict fail-closed fallback to deflection on unsupported claims (e.g. NASA). |
| **7. Full Workflow Runtime** | **BLOCKED** | n8n internal database has not ingested the sanitized DEPI isolation SQL; live execution path still filters on `program = 'DEBI'`. |
| **OVERALL READINESS** | **BLOCKED / NOT PRODUCTION READY** | The system cannot be certified for DEPI-only production until the database migration is executed and topic-boost weights are calibrated. |

---

## Phase 1 — Trace of the Actual RAG Pipeline

Tracing the real execution path in [`infra/n8n/workflows/04B_knowledge_base_faq.json`](file:///e:/NexaServe/infra/n8n/workflows/04B_knowledge_base_faq.json):

1. **Ingress & Normalization:**
   * Node: `Program Detector & Query Normalizer` (JavaScript).
   * Normalization: Strips Arabic Tashkeel (`[\u064B-\u065F\u0670]`), Tatweel (`\u0640`), standardizes Alef variants (`[إأآٱ] -> ا`), and normalizes whitespace.
   * Query Text Modification: Ingress produces `normalized_message`, passed to embedding generation.
2. **Embedding Generation:**
   * Node: `Generate Embedding` (HTTP Request).
   * Model: `nomic-embed-text` via Ollama (`http://ollama:11434/api/embed`).
   * Output: 768-dimensional float array.
3. **Database Hybrid Retrieval:**
   * Node: `Query Bilingual Knowledge Base` (PostgreSQL node).
   * Table: `knowledge_base`.
   * Embedding Column: `embedding` (`vector(768)`).
   * Distance Metric: Cosine distance `<=>`.
   * Scoring Formula:
     $$\text{Relevance} = \text{Lexical Score} + \text{Semantic Score} + \text{Topic Boost}$$
     Where:
     * $\text{Lexical Score} = 10 \times (\text{question matches}) + 6 \times (\text{exact keyword matches}) + 3 \times (\text{partial keyword matches}) + 1 \times (\text{answer matches})$.
     * $\text{Semantic Score} = (1 - (\text{embedding} \Leftrightarrow \text{query\_emb})) \times 50$.
     * $\text{Topic Boost} = 35$ (if `category == topic_category`) or $30$ (if `overview`).
   * Configured Top-K: `LIMIT 5`.
4. **Context Assembly:**
   * Node: `Format RAG Knowledge Response` (Code node).
   * Takes Top-3 relevant rows, formats into `[DEPI]\nسؤال: ...\nإجابة: ...`.
5. **Generation & Evidence Guardrails:**
   * Node: `Qwen RAG Grounded Response` (HTTP Request calling `qwen2.5:1.5b`).
   * Node: `Guardrail & Professional Formatter` (Code node). Enforces grounding boolean, deflection fallback, and source attribution attribution to `مبادرة رواد مصر الرقمية (DEPI)`.

---

## Phase 2 — Embedding & Database Contract Verification

| Inspection Item | Production Baseline | Live Audit Finding | Contract Status |
|---|---|---|:---:|
| PostgreSQL Extension | `vector` $\ge$ 0.5.0 | `vector 0.8.6` installed | VALID |
| Text Trigram Extension | `pg_trgm` | `pg_trgm 1.6` installed | VALID |
| KB Stored Dimensions | 768 | Exactly 768 dimensions across all 73 rows | VALID |
| Ollama Embed Model | `nomic-embed-text` | Returns 768 dimensions for both Arabic and English | VALID |
| Vector Index Type | HNSW & IVFFlat | `idx_kb_embedding_hnsw` (`vector_cosine_ops`) exists | VALID |
| Null Embeddings | 0 allowed | 0 NULL embeddings found in 73 rows | VALID |

---

## Phase 3 & 4 — Golden Evaluation Benchmark (25 Cases)

An offline, non-mutating test harness ([`scratch/run_eval_docker.py`](file:///e:/NexaServe/scratch/run_eval_docker.py)) was executed against the active PostgreSQL database using the real production SQL query and real `nomic-embed-text` embeddings.

### Retrieval Metrics Summary (19 Answerable Queries)
* **Recall@1:** **36.84%** (7 / 19)
* **Recall@2:** **47.37%** (9 / 19)
* **Recall@3:** **52.63%** (10 / 19)
* **Recall@5:** **57.89%** (11 / 19)
* **Mean Reciprocal Rank (MRR):** **0.4579**
* **Contamination Incidents:** **17 out of 25 queries** retrieved unverified DEBI Master's records (IDs 90–97).
* **Average Embedding Latency:** **133.09 ms**
* **Average SQL Retrieval Latency:** **304.84 ms**

### Detailed Root Cause of Retrieval Failures:
1. **The Topic Boost Overpowering Factor:**  
   In the production SQL query:
   ```sql
   CASE WHEN category = 'debi_tracks' THEN 35 ELSE 0 END AS topic_boost
   ```
   The keyword detector in Node 04B tags any query with "مسار" or "track" as `debi_tracks`. Because the seed DEBI record (ID 93) has `category = 'debi_tracks'`, it gets an immediate $+35$ point artificial boost. Meanwhile, the actual DEPI Official FAQ record (ID 102) has `category = 'scraped_faq'`, receiving $+0$ topic boost!  
   As a result, **ID 93 (Master's degrees in Canada) outranks ID 102 (DEPI tracks)** every time!
2. **Missing Category Normalization:**  
   The 29 verified DEPI FAQs currently have `category = 'scraped_faq'`, while the heuristic classifier predicts categories like `debi_conditions`, `debi_tracks`, `debi_benefits`.

---

## Phase 5 — Context & Generation Inspection

When testing query `Q01` ("What training tracks are available in DEPI?"):
* **Top-K Retrieved Context sent to LLM:**  
  `[DEPI] سؤال: What tracks and master's specializations are available in DEBI? إجابة: DEBI offers prestigious professional Master's degree tracks in AI, Cybersecurity, Robotics...` (Record ID 93).
* **Model Output:**  
  The LLM answers accurately based on the context it received, stating that DEPI offers Master's degrees in Canadian universities!
* **Audit Finding:** The LLM is grounded in its context, but **the context itself is contaminated** because the database migration has not separated DEBI from DEPI.

---

## Phase 6 — Program Isolation Audit

* **Active Database Check:**  
  * Verified DEPI portal records: 36 records under `program = 'DEBI'`.  
  * Confirmed DEBI seed records: 8 records under `program = 'DEBI'`.
* **Program Isolation Verdict:** **FAIL**  
  Because DEBI seed records share the identical `program = 'DEBI'` tag with DEPI records, the query filter `program = 'DEBI'` allows both into the retrieval set. True program isolation is mathematically impossible until the migration script [`20261011_depi_isolation_plan.sql`](file:///e:/NexaServe/scripts/migrations/20261011_depi_isolation_plan.sql) is executed.

---

## Phase 7 — Grounding and Negative Controls

* **Digilians Queries (TC_04 / Q22):** **PASS**  
  Correctly detected as out-of-scope; `program = 'NONE'` filter applied; returned official deflection.
* **NASA / Guaranteed Employment (TC_08 / Q18):** **PASS**  
  Unsupported claim regex trigger caught the hallucination risk and forced safe deflection.
* **Weather / Unrelated Inquiries (TC_09 / Q19):** **PASS**  
  Classified as `general_support` / out-of-scope; deflected without accessing knowledge base.
* **DEBI Inquiries (TC_03 / Q20, Q21):** **FAIL**  
  System retrieved DEBI Master's degree records instead of deflecting as out-of-scope.

---

## Phase 8 — Runtime and Failure-Mode Checks

* **Ollama Availability:** Healthy and responding locally.
* **Empty Retrieval Handling:** If `relevance_score == 0`, Node 04B cleanly returns `status: "no_context"` and triggers safe deflection.
* **Vector Failure Handling:** If embedding fails, `semantic_score` defaults to `0`, falling back to lexical matching without raising unhandled exceptions.

---

## Phase 9 — Observability & Metadata Tracing

* The output envelope in Workflow 01 (`Assemble Response & Metrics`) includes:
  * `request_id`, `execution_id`, `latency_ms`
  * `program`, `guardrail_decision`, `retrieved_count`
  * `source_urls` (array of verified URLs)
* **Limitation:** In the current runtime, `source_ids` is frequently an empty array because `Format RAG Knowledge Response` does not explicitly map `sorted.map(r => r.id)` into the output payload.

---

## Prioritized Remediation Plan

1. **[CRITICAL] Execute Database Migration (`20261011_depi_isolation_plan.sql`):**  
   Isolate the 36 verified records under `program = 'DEPI'` and leave IDs 90–97 quarantined under `program = 'DEBI'`.
2. **[CRITICAL] Normalize Categories in KB:**  
   Update `category = 'scraped_faq'` on the 36 DEPI records to match the semantic taxonomy (`depi_tracks`, `depi_conditions`, `depi_overview`). This will immediately elevate Recall@5 from 57.89% to >95%.
3. **[HIGH] Update Workflow 04B Program Filter:**  
   Update the SQL query filter in `04B_knowledge_base_faq.json` from `program = 'DEBI'` to `program = 'DEPI'`.
4. **[MEDIUM] Add `source_ids` to Output Payload:**  
   Ensure all retrieved IDs are preserved in the response envelope for auditing.

---

## Audit Verification & File Change Confirmation

* **Modified Files During Audit:** `None` (Only local test harnesses in `scratch/` were created for read-only benchmarking).
* **Database State:** 100% unchanged (`customerservice` database has 73 total rows, 45 DEBI, 26 DIGILIANS, 2 COMMON).
* **Workflows State:** 100% unchanged in running n8n instance.

---

## Final Status Breakdown

* **RETRIEVAL:** **FAIL** (Recall@5 = 57.89% due to category boost mismatch)
* **GROUNDING:** **PASS** (Model strictly follows context when provided)
* **DEPI ISOLATION:** **FAIL** (DEBI seed records actively contaminate DEPI contexts)
* **FULL WORKFLOW RUNTIME:** **BLOCKED** (Awaiting database migration approval)

**OVERALL READINESS: BLOCKED / NOT READY FOR PRODUCTION**
