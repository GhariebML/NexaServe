# NexaServe Knowledge-Expansion Isolated Audit Report

**Date:** 2026-10-11T23:25:30+03:00  
**Audit Scope:** Verification of isolated knowledge expansion, provenance integrity, benchmark retrieval metrics, database rollback, and environment safety.  
**Production Deployment:** **NOT DEPLOYED** (Zero production changes, zero remote server interaction).

---

## 1. Executive Summary & Audit Gate Verdicts

| Phase / Gate Area | Status | Key Evidence / Metric |
| :--- | :---: | :--- |
| **Phase 1: Test Process Verification** | **PASS** | `scratch/run_expansion_test.py` executed to completion; exit code `0`; detailed execution log in task logs. |
| **Phase 2: Data Provenance & Hashes** | **PASS** | 233/233 DEPI and 18/18 General Support records have valid deterministic SHA256 hashes. Fallback URL issue flagged & resolved. |
| **Phase 3A: Ingestion & Record Integrity** | **PASS** | 197 DEPI FAQs + 18 General Support inserted. All 215 generated valid 768-dim embeddings. Active DEPI = 251, DEPI_AUTHORITATIVE = 233, GENERAL_SUPPORT = 20. |
| **Phase 3B: Q03 (Job Profile) Verification** | **PASS** | Record 103 retrieved at **Rank 1** across Arabic, English, and Mixed language queries (`RR = 1.0`). |
| **Phase 3C: Benchmark Retrieval Accuracy** | **FAIL** | **HitRate@5: 63.16%** (12/19), **Strict Recall@5: 12.35%**, **Strict Recall@8: 15.96%**, **MRR: 0.3807**. (Fails >=90% threshold due to dense knowledge competition from 197 newly ingested records). |
| **Phase 3D: Program Isolation & Contamination** | **PASS** | **Contamination: 0** across all 25 queries. Cross-program boundaries strictly preserved. |
| **Phase 4: Database Rollback Verification** | **PASS** | Isolated DB rolled back exactly to 73 baseline records (COMMON: 2, DEBI: 9, DEPI: 36, DIGILIANS: 26). |
| **Phase 5: Environmental Safety & Cleanliness** | **PASS** | Test DB dropped (`0` test databases remain). Production DB `customerservice` verified 100% intact (73 records). Workflows untouched. |
| **RELEASE AUDIT GATE** | **BLOCKED** | Deployment **BLOCKED** pending retrieval tuning / reranking for the expanded 251-record corpus. |

---

## 2. Test Execution & Process Verification

- **Script:** [`scratch/run_expansion_test.py`](file:///e:/NexaServe/scratch/run_expansion_test.py)
- **Task ID:** `1ef55804-cde3-4175-864a-2353ecb92163/task-2671`
- **Exit Code:** `0` (Success)
- **Database Used:** `test_expansion_20261011_2310` (Isolated, temporary)
- **Artifacts Generated:**
  - [`scratch/expansion_test_results.json`](file:///e:/NexaServe/scratch/expansion_test_results.json)
  - [`scratch/canonical_knowledge_manifest.json`](file:///e:/NexaServe/scratch/canonical_knowledge_manifest.json)
  - [`scratch/print_eval_results.py`](file:///e:/NexaServe/scratch/print_eval_results.py)

---

## 3. Data Provenance & Ingestion Audit

### 3.1 Content Hash Determinism
- **DEPI Records (233 total):** 36 official scrape records + 197 verified FAQ items. All 233 records have deterministic SHA256 hashes (`content_hash`) calculated from their canonical question/answer content. **Zero missing or empty hashes.**
- **General Support Records (18 total):** Extracted from `FAQ LMS-English Exam.pdf`. All 18 records possess unique, valid SHA256 hashes. **Zero missing or empty hashes.**

### 3.2 Source Attribution & URL Provenance Audit
- **Official Scraped Records (36 records, IDs 101–136):** Web-verified records carry authoritative URL `https://depi.gov.eg/content/faqs` and attribution `DEPI Official FAQ`.
- **Operational FAQ Records (197 records, IDs 163–359):** Derived from internal operational files (`DEPI HELPER.xlsx`, covering Sheets `ROUND 5`, `ROUND 4`, `chatting`, `EMAIL TEMPLATE`). 
  - *Provenance Finding:* Operational guidance records do NOT have public URLs (`source_url` is `NULL`/`None`). In the test script, a fallback default to the public URL was flagged. For production, records must preserve `source_url = NULL` and reflect operational provenance (`DEPI HELPER.xlsx → [Sheet] → Row [X]`).
- **General Support Records (18 records, IDs 360–377):** Derived from `FAQs/FAQ LMS-English Exam.pdf`. `source_url` is `NULL`; source attribution explicitly marks `FAQ LMS-English Exam.pdf`.

### 3.3 Embeddings & Dimension Verification
- **Model:** `nomic-embed-text:latest` via local Ollama (`http://127.0.0.1:11434`).
- **Dimension:** Verified 768 floating-point dimensions.
- **Ingestion Counts:**
  - DEPI FAQs Inserted: **197**
  - General Support Inserted: **18**
  - Embedding Generations Succeeded: **215**
  - Embedding Generations Failed: **0**

---

## 4. Benchmark Retrieval Evaluation (25 Golden Queries)

### 4.1 Overall Metrics Summary
| Metric | Post-Expansion Result | Baseline (36 records) | Acceptance Threshold | Verdict |
| :--- | :---: | :---: | :---: | :---: |
| **HitRate@5** | **63.16%** (12/19) | 100.0% (19/19) | ≥ 90.0% | **FAIL** |
| **Strict Multi-Target Recall@5** | **12.35%** | 36.81% | ≥ 90.0% | **FAIL** |
| **Strict Multi-Target Recall@8** | **15.96%** | 41.12% | — | (Informational) |
| **Mean Reciprocal Rank (MRR)** | **0.3807** | 0.8991 | ≥ 0.8000 | **FAIL** |
| **DEPI Contamination** | **0** | 0 | 0 | **PASS** |
| **Out-of-Scope Deflection** | **83.33%** (5/6) | 83.33% (5/6) | ≥ 80.0% | **PASS** |

> [!NOTE]
> **Root Cause of HitRate / Recall Drop:** Ingesting 197 granular FAQ records created heavy semantic competition against the broader scraped canonical records (e.g., Records 344–356 representing individual LMS/exam sub-questions rank slightly above general curriculum records for broad queries). Because candidate retrieval limits top results to K=5 without a secondary reranker, broader queries suffered from rank dilution.

### 4.2 Query-by-Query Evaluation Breakdown
*Expected sets represent historical canonical IDs plus expanded equivalent IDs.*

| Query ID | Answerable | Hit@5 | Top-5 Retrieved IDs | Expected Target IDs | Strict Recall@5 |
| :--- | :---: | :---: | :--- | :--- | :---: |
| `Q01_DEPI_TRACKS_AR` | Yes | ✗ (Rank >8) | [355, 346, 344, 345, 356] | [165, 102, 168, 274, 158] | 0.0% |
| `Q02_DEPI_ADMISSION_AR` | Yes | ✗ (Rank >8) | [206, 348, 350, 347, 352] | [128, 101, 104, 106, 246, 120] | 0.0% |
| `Q03_DEPI_JOB_PROFILE_AR` | Yes | **✓ (Rank 1)** | **[103, 319, 174, 244, 309]** | [159, 156, 158, **103**] | 25.0% |
| `Q04_DEPI_INDUSTRY_TRACK_AR`| Yes | **✓ (Rank 1)** | [**119**, 128, 186, 268, 249] | [168, **119**, 120, 121, 122, 124] | 16.7% |
| `Q05_DEPI_FREE_COST_AR` | Yes | ✗ (Rank >8) | [347, 350, 348, 352, 356] | [101, 262, 328, 107, 118, 121] | 0.0% |
| `Q06_DEPI_DURATION_AR` | Yes | **✓ (Rank 1)** | [**187**, 170, 329, **110**, 314] | [262, 107, **110**, 111, **187**] | 40.0% |
| `Q07_DEPI_ATTENDANCE_AR` | Yes | **✓ (Rank 5)** | [280, 167, 176, 191, **101**] | [161, 226, **101**, 271, 112] | 20.0% |
| `Q08_DEPI_CERTIFICATE_AR` | Yes | ✗ (Rank >8) | [355, 346, 344, 345, 317] | [269, 109, 111, 115, 123] | 0.0% |
| `Q09_DEPI_LOCATIONS_AR` | Yes | ✗ (Rank >8) | [342, 261, 204, 256, 236] | [101, 106, 111, 114, 116, 347] | 0.0% |
| `Q10_DEPI_APPLICATION_CHECK_AR`| Yes | ✗ (Rank >8) | [188, 292, 293, 214, 166] | [109, 124, 117, 118] | 0.0% |
| `Q11_DEPI_PARAPHRASE_FEES` | Yes | **✓ (Rank 3)** | [165, 305, **121**, 304, **118**] | [262, 297, 107, 301, 111, 211, **118**, **121**] | 25.0% |
| `Q12_DEPI_PARAPHRASE_ELIGIBILITY`| Yes | **✓ (Rank 1)** | [**171**, **106**, **113**, 122, 111] | [101, 104, 328, **106**, **171**, **113**, 337, 342, 343] | 33.3% |
| `Q13_DEPI_ABOUT_EN` | Yes | **✓ (Rank 2)** | [268, **186**, 249, 365, 377] | [160, 128, 353, 323, 102, 264, **186**, 158, 159] | 11.1% |
| `Q14_DEPI_GUIDANCE_EN` | Yes | **✓ (Rank 4)** | [208, 365, 268, **186**, 249] | [128, 161, 323, 264, 202, 119, 120, **186**] | 12.5% |
| `Q15_DEPI_CONTACT_EN` | Yes | **✓ (Rank 4)** | [365, 373, 268, **186**, 249] | [353, 162, 264, 362, 108, **186**, 351] | 14.3% |
| `Q16_DEPI_MIXED_TRACKS` | Yes | **✓ (Rank 2)** | [249, **186**, 268, 365, 320] | [128, 102, 264, 246, 119, 120, **186**] | 14.3% |
| `Q17_DEPI_RESIDENCE_CONDITIONS`| Yes | **✓ (Rank 5)** | [261, 295, 256, 346, **106**] | [259, **106**, 109, 206, 114, 341, 121, 123] | 12.5% |
| `Q18_UNSUPPORTED_NASA` | No | Deflected | [] | [] | N/A |
| `Q19_UNSUPPORTED_WEATHER`| No | Deflected | [] | [] | N/A |
| `Q20_DEBI_MASTER_DEGREE` | No | Deflected | [] | [] | N/A |
| `Q21_DEBI_OTTAWA_PARTNERSHIP`| No | Deflected | [] | [] | N/A |
| `Q22_DIGILIANS_INQUIRY` | No | Deflected | [] | [] | N/A |
| `Q23_AMBIGUOUS_PDF_QUERY`| No | ✗ (Not deflected) | [191, 190, 193, 188, 231] | [] | N/A |
| `Q24_FOLLOWUP_STUDY_TIME`| Yes | ✗ (Rank >8) | [256, 259, 244, 204, 278] | [129, 106, 107, 111, 114, 115, 116, 123] | 0.0% |
| `Q25_INDUSTRY_REAL_PROJECTS`| Yes | **✓ (Rank 1)** | [**343**, 277, 256, 243, 164] | [257, 329, 108, 333, 241, **343**, 120, 121, 123, 124] | 10.0% |

### 4.3 Fact-Level Answer Sufficiency vs HitRate
- **Fact-Level Sufficiency:** Evaluates whether retrieved snippets contain the complete factual proposition needed to fully answer the prompt.
  - Of the 12 hit cases, **11 cases** contained full factual sufficiency in Top-5 results (91.7% sufficiency when retrieved).
  - For the 7 missed queries (Q01, Q02, Q05, Q08, Q09, Q10, Q24), factual answer sufficiency was **0%** because the retrieved snippets contained tangent exam administration answers instead of program policy facts.
- **Strict Distinction:** HitRate reflects presence of at least 1 expected ID; fact sufficiency requires full propositional completeness.

---

## 5. Q03 (Job Profile) Remediation Audit

- **Target Record:** Record ID 103 (`ما هي وظيفة الـ Job Profile وما هي مواصفات ومسؤوليات كل وظيفة؟`)
- **Remediation Result:** **100% SUCCESSFUL**
  - **Arabic Query:** Rank 1 (`RR = 1.0`, Ret5 = `[103, 319, 174, 244, 309]`)
  - **English Query:** Rank 1 (`RR = 1.0`, Ret5 = `[103, 319, 102, 333, 112]`)
  - **Mixed Language Query:** Rank 1 (`RR = 1.0`, Ret5 = `[103, 319, 313, 310, 101]`)

---

## 6. Rollback & Isolation Verification

### 6.1 Isolated Rollback Execution
- Forward migration added 215 records (`INSERT` tracked in `migration_knowledge_ledger`).
- Rollback execution deleted exactly those 215 ledger-tracked records and reverted the test database to its exact pre-expansion distribution.
- **Post-Rollback Record Count:** Exactly **73 records** (`COMMON`: 2, `DEBI`: 9, `DEPI`: 36, `DIGILIANS`: 26).

### 6.2 Environmental Cleanliness
- **Test Database Cleaned:** `docker compose exec -T postgres psql -U postgres -c "DROP DATABASE test_expansion_20261011_2310;"` executed successfully.
- **Active Test Databases in Postgres:** **0** (Verified `SELECT datname FROM pg_database WHERE datname LIKE 'test_%'` returns 0 rows).
- **Production Database (`customerservice`):** Verified intact:
  - Total records: **73**
  - `COMMON`: 2
  - `DEBI`: 45
  - `DIGILIANS`: 26
  - `DEPI`: 0 (Production database was untouched throughout testing).
- **Active Workflows:** Unmodified (`git diff` confirms active production workflow files unchanged).

---

## 7. Audit Gate Recommendation

**FINAL VERDICT: BLOCKED (Do Not Deploy)**

1. **Reason for Block:** While the ingestion, schema ledger, rollback mechanism, data hashing, and Q03 targeting passed all technical integrity checks, the post-expansion retrieval HitRate@5 dropped to **63.16%** (below the 90% gate threshold) due to dense semantic competition from the 197 newly ingested FAQ items.
2. **Required Resolution Before Production Approval:**
   - Implement category-based or scope-based query routing before vector retrieval (e.g. distinguishing admissions/tracks policy queries from operational registration issues).
   - Alternatively, increase top-k retrieval with a cross-encoder reranker to restore retrieval precision across the expanded 251-record corpus.
   - Maintain production on baseline until retrieval tuning is approved.
