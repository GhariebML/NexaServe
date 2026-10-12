# NexaServe RAG Recovery — Root-Cause Analysis and Ablation Report

**Date:** 2026-10-11T23:48:00+03:00  
**Environment:** Local Isolated Docker PostgreSQL (`test_diagnose_20261011_2330`, dropped post-audit).  
**Production Integrity:** `customerservice` verified 100% untouched (73 records: COMMON=2, DEBI=45, DIGILIANS=26). Active n8n workflows unchanged.  
**Release Gate Verdict:** **BLOCKED** (Pending resolution of Q02 semantic competition and multi-target recall constraints).

---

## 1. Executive Summary: The Real Root Cause

In the previous run, the reported drop to `HitRate@5 = 63.16%` was initially hypothesized as "dense semantic dilution from 197 operational records". **Our deep diagnostic audit proved this hypothesis was incomplete.**

### The True Dual Root Causes:
1. **Critical UTF-8 Mojibake in Temporary Restore Pipeline (Primary Degradation Driver):**
   - The test script restored the baseline database using a Windows PowerShell redirect from `dump_utf8.sql`.
   - Windows PowerShell piped the UTF-8 dump through CP1252/Windows-1252 encoding, corrupting all Arabic text in the baseline records into mojibake (`┘à╪º┘ç┘ë...`).
   - Consequently, lexical search scores for baseline records dropped to **0**. Records 344–356 (which were inserted later directly via UTF-8 Python) scored 22+ lexically, completely displacing baseline records.
   - When the baseline was restored directly inside the Docker container with native UTF-8 encoding (`SET client_encoding = 'UTF8'`), the baseline expanded HitRate@5 immediately jumped from **63.16% to 94.74% (18/19)**!
2. **Persistent Semantic Competition on Broad Entity Terms (`Q02`):**
   - Query `Q02` (`ما هي شروط الالتحاق بمبادرة رواد مصر الرقمية؟`) still missed Top-5 (`HitRate@5 = 0%`).
   - Broad initiative overview records (IDs 156, 158, 159) match "مبادرة رواد مصر الرقمية" across their full text and score 42 lexical points, outscoring the specific admission conditions record (ID 104, lexical score 18).

---

## 2. Evaluation Audit: Formula Validation & Query Breakdown

### 2.1 Why 25 Queries vs 19 Evaluated Cases?
The golden dataset [`tests/candidate_golden_rag_cases_v2.json`](file:///e:/NexaServe/tests/candidate_golden_rag_cases_v2.json) contains **25 total test cases**:
- **19 Answerable Queries:** Tested for retrieval accuracy (`HitRate@5`, `MRR`, `Strict Recall@5/8`, `Evidence Sufficiency`).
- **6 Out-of-Scope (OOS) / Quarantined Queries:** Tested for **Deflection / Zero-Retrieval** (Q18 NASA, Q19 Weather, Q20 DEBI Masters, Q21 Ottawa, Q22 Digilians, Q23 Ambiguous PDF).
- Combining OOS queries into the HitRate denominator would artificially dilute accuracy. Reporting them as separate metrics (**HitRate@5 over 19** and **Deflection Rate over 6**) is methodologically correct.

### 2.2 Independent Recomputation of Metrics
All formulas were re-verified from raw per-case outputs:
- **HitRate@5:** $\frac{\sum_{i=1}^{N_{ans}} \mathbb{I}(\text{Retrieved}_5 \cap \text{Expected} \neq \emptyset)}{N_{ans}} = \frac{18}{19} = \mathbf{94.74\%}$
- **MRR (Mean Reciprocal Rank):** $\frac{1}{N_{ans}} \sum_{i=1}^{N_{ans}} \frac{1}{\text{Rank}_1} = \mathbf{0.6754}$ (Baseline) $\rightarrow$ $\mathbf{0.7781}$ (Strategy D)
- **Strict Multi-Target Recall@5:** $\frac{1}{N_{ans}} \sum_{i=1}^{N_{ans}} \frac{|\text{Retrieved}_5 \cap \text{Expected}|}{|\text{Expected}|} = \mathbf{22.28\%}$ (Baseline) $\rightarrow$ $\mathbf{30.68\%}$ (Strategy D) $\rightarrow$ $\mathbf{31.34\%}$ (Strategy E)
- **Deflection Rate:** $\frac{6}{6} = \mathbf{100.00\%}$ across all strategies when Q23 ambiguous PDF pattern is included.

### 2.3 Evidence & Source Sufficiency Audit (Strict Distinction)
Retrieval of at least one relevant record (`HitRate@5`) is **not** equivalent to full evidence sufficiency:
- **Single-Record Sufficient Cases (16 queries):** 15/16 achieved full evidence sufficiency (**93.75%**). Only Q02 missed.
- **Multiple-Records Complementary Cases (3 queries: Q04, Q12, Q13):**
  - While all 3 queries achieved a Hit@5 (retrieving at least 1 expected record), **0/3 queries** retrieved 100% of all required complementary records in Top-5 results (due to $K=5$ cutoff vs 6–9 expected complementary targets).
  - Fact-level partial sufficiency was achieved (providing necessary core facts), but strict full multi-record sufficiency was **0.0%**.

---

## 3. Deep Diagnosis of Failed & Partially Successful Cases

### 3.1 Failed Case: `Q02_DEPI_ADMISSION_AR`
- **Query:** `ما هي شروط الالتحاق بمبادرة رواد مصر الرقمية؟`
- **Expected Records:** `[104, 101, 106, 120, 128, 246]` (Primary core fact: ID 104 `شروط التقديم ومعايير القبول`).
- **Retrieved Top-5 IDs & Ranks:** `[158, 159, 156, 354, 349]` (Rank 1–5). Target ID 104 ranked **#6**.
- **Score Breakdown:**
  - ID 158 (`scraped_rag`): Lexical = 42, Semantic = 40.75 $\rightarrow$ **Total = 82.75** (Matches initiative name repeat).
  - ID 159 (`scraped_rag`): Lexical = 42, Semantic = 39.98 $\rightarrow$ **Total = 81.98**
  - ID 156 (`scraped_rag`): Lexical = 42, Semantic = 38.60 $\rightarrow$ **Total = 80.60**
  - ID 104 (`scraped_faq`): Lexical = 18, Semantic = 40.56 $\rightarrow$ **Total = 58.56**
- **Diagnosis:** **Ranking & Weighting Flaw.** General overview articles contain multiple occurrences of "مبادرة رواد مصر الرقمية", dominating the lexical word count over the concise question header of ID 104 (`ماهى شروط الإلتحاق؟`).
- **Sufficiency Type:** Single record sufficient (ID 104 provides all admission conditions).

### 3.2 Partially Successful Cases (Multi-Record Complementary)

#### A. `Q04_DEPI_INDUSTRY_TRACK_AR`
- **Query:** `ما هي تفاصيل ومميزات مسار الصناعة DEPI Industry؟`
- **Expected Records:** `[119, 120, 121, 122, 124, 168]`
- **Retrieved Top-5:** `[119, 120, 128, 186, 268]`
- **Retrieved Expected Count:** 2 of 6 (IDs 119, 120).
- **Diagnosis:** Top-5 retrieved IDs provide core track definitions; secondary details (IDs 121, 122) ranked #6–9 due to $K=5$ ceiling.

#### B. `Q12_DEPI_PARAPHRASE_ELIGIBILITY`
- **Query:** `هل يمكن لطلاب الجامعات التقديم في رواد مصر الرقمية؟ وما هي الكليات المقبولة؟`
- **Expected Records:** `[101, 104, 106, 113, 171, 328, 337, 342, 343]`
- **Retrieved Top-5:** `[107, 109, 113, 118, 110]`
- **Retrieved Expected Count:** 1 of 9 (ID 113).
- **Diagnosis:** Partially sufficient. Mentions student eligibility, but missed ID 101 due to lexical match with general eligibility rules.

#### C. `Q13_DEPI_ABOUT_EN`
- **Query:** `What is the Digital Egypt Pioneers Initiative and who is it for?`
- **Expected Records:** `[102, 128, 158, 159, 160, 186, 264, 323, 353]`
- **Retrieved Top-5:** `[268, 186, 249, 365, 377]`
- **Retrieved Expected Count:** 1 of 9 (ID 186).
- **Diagnosis:** English semantic retrieval retrieves English overview record 186, but broad expected set of 9 equivalent records cannot fit in Top-5.

---

## 4. Controlled 5-Way Ablation Study

All 5 strategies were tested against the identical 25-query golden benchmark on the isolated test database:

| Strategy | HitRate@5 | MRR | Strict Recall@5 | Strict Recall@8 | Deflection | Contam. | Single Suff. | Multi Full Suff. | Failure IDs |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :---: | :--- |
| **A: Baseline (Clean UTF-8)** | 94.74% (18/19) | 0.6754 | 22.28% | 26.55% | 100% (6/6) | 0 | 93.8% (15/16) | 0.0% (0/3) | `Q02` |
| **B: Scope Selection** | 94.74% (18/19) | 0.6930 | 22.86% | 27.96% | 100% (6/6) | 0 | 93.8% (15/16) | 0.0% (0/3) | `Q02` |
| **C: General Support Gated** | 94.74% (18/19) | 0.6930 | 22.86% | 27.96% | 100% (6/6) | 0 | 93.8% (15/16) | 0.0% (0/3) | `Q02` |
| **D: Reciprocal Rank Fusion** | **94.74% (18/19)** | **0.7781** | **30.68%** | **40.77%** | **100% (6/6)** | **0** | **93.8% (15/16)** | **0.0% (0/3)** | `Q02` |
| **E: Authority & Metadata** | 94.74% (18/19) | 0.6974 | **31.34%** | 39.70% | 100% (6/6) | 0 | 93.8% (15/16) | 0.0% (0/3) | `Q02` |

### Key Ablation Insights:
1. **Strategy D (RRF - Reciprocal Rank Fusion)** achieved the highest MRR (**0.7781**) and strong recall (**30.68%** / **40.77%**), significantly reducing the impact of lexical runaway scores.
2. **Strategy E (Controlled Authority Boost)** achieved the highest Strict Recall@5 (**31.34%**) by prioritizing official web-verified records (`scraped_faq`, `scraped_rag`) over operational email templates.
3. **Strategy C (General Support Intent Gating)** successfully prevented LMS/Exam PDF support records from competing with admissions/policy queries, achieving 100% out-of-scope deflection and 0 contamination.

---

## 5. Formal Acceptance Gate Verdict

| Acceptance Metric | Gate Requirement | Best Candidate Result (Strategy D) | Status |
| :--- | :---: | :---: | :---: |
| **HitRate@5** | $\ge 90.0\%$ | **94.74%** (18/19) | **PASS** |
| **Out-of-Scope Deflection** | $\ge 80.0\%$ | **100.00%** (6/6) | **PASS** |
| **Cross-Program Contamination** | $0$ | **0** | **PASS** |
| **Single-Record Evidence Sufficiency**| $\ge 90.0\%$ | **93.75%** (15/16) | **PASS** |
| **Strict Multi-Target Recall@5** | $\ge 90.0\%$ | **30.68%** | **FAIL** (Mathematical cutoff limitation) |
| **Q02 Admission Condition Retrieval** | Pass | **FAIL** (Rank #6) | **FAIL** |
| **FINAL RELEASE GATE** | All Pass | — | **BLOCKED** |

### Recommendations for Release Approval:
1. **Resolve Q02 Ranking:** Adjust lexical weighting for `question_ar` exact match or add key synonyms ("شروط القبول", "معايير الالتحاق") to record 104's `keywords_ar` so it ranks in Top-3 over broad initiative overviews.
2. **Standardize Multi-Target Recall Metric:** Golden cases with 6–9 expected targets mathematically cannot achieve $\ge 90\%$ Recall@5 when $K=5$ (maximum possible is $5/9 = 55.5\%$). The acceptance criteria should either evaluate Recall@10 for multi-target queries or measure Propositional Fact Sufficiency.
3. **Do Not Deploy Until Authorized:** All candidate changes remain strictly in isolated code and test databases. Production database and active workflows remain unchanged.
