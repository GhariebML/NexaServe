# RAG Retrieval Forensics

## Proven end-to-end request

Synthetic webchat: `من المؤهل للتدريب في DEPI؟`; master execution 6124; RAG child 6127; request ID `forensic-official-faq-verify-01`.

Program detector produced `DEBI` and SQL filter `program IN ('DEBI','COMMON') AND category != 'disambiguation'`. The exact official FAQ was rank 1. Source URL and exact answer are in the [runtime trace](../logs/runtime_forensic/official_faq_trace.json).

| Rank | KB id | Program | Category | Source | Score | Question | Assessment |
|---:|---:|---|---|---|---:|---|---|
| 1 | 101 | DEBI | scraped_faq | DEPI Official FAQ | 56.3129 | من المؤهل للتدريب؟ | Exact answer source; rank 1 |
| 2 | 128 | DEBI | scraped_faq | DEPI Official FAQ | 53.0052 | ما هي مدة تدريب DEPI Industry؟ | Related training wording, wrong fact for eligibility |
| 3 | 120 | DEBI | scraped_faq | DEPI Official FAQ | 52.0796 | ما الفرق بين مسار الصناعة والمسارات التقليدية في DEPI؟ | Wrong fact for eligibility |
| 4 | 119 | DEBI | scraped_faq | DEPI Official FAQ | 48.5444 | ما هو مسار الصناعة (DEPI Industry Track)؟ | Wrong fact for eligibility |
| 5 | 108 | DEBI | scraped_faq | DEPI Official FAQ | 41.2596 | ما هي وسائل التواصل مع المختصين بالمبادرة؟ | Irrelevant contact item |

## Interpretation

- The correct official document ranks first and survives into the context. The remaining four are semantically/lexically noisy; the formatter sends all five, including irrelevant course-duration, track, and contact material.
- The 04B SQL combines token/keyword lexical scores with cosine-derived semantic score, filters by program and active status, then returns top 5. `source_url` is selected. The active program filter correctly excludes DIGILIANS on a DEBI question.
- The comparison replay (`ما الفرق بين DEPI والرواد الرقميون؟`) set `program_scope=COMPARISON`, retrieved a COMMON comparison record plus records from both programs as expected. The intent classifier still returned `faq_query`, so the canonical classification contract is split between workflow 03 and the 04B resolver.
- Exact-query DEPI conditions replay in the earlier execution retrieved KB id 91 at relevance 82.06. The RAG output was correct because the guardrail returned the curated record after malformed LLM JSON caused HTTP 400.
- There is no evidence that the model authored the captured correct answers. In the latest official FAQ replay, Qwen failed with HTTP 500; the guardrail fallback answered exactly from row 101.

## Retrieval quality actions

The row handling and JSON body defects are fixed in active 04B. Further score/threshold tuning is deferred until Qwen can stay alive and fresh sequential quality tests can be run. Do not infer quality from HTTP 200 or fallback success.

## Post-fix offline scoring replay

`logs/runtime_forensic/rag_top10_all_30_after_fix.jsonl` records the active scoring/filter/evidence-gate logic against each of the 30 test queries plus the dedicated official-source query. It is retrieval-stage replay, not a claim that all 30 webhook workflows completed.

- The 30 cases produced 24 evidence-gate approvals; three ambiguous prompts use the explicit clarification fast path; no-answer, security injection, and out-of-scope cases fail the evidence gate.
- The no-answer NASA/employment query’s top candidate is a scraped FAQ record at score 32.3, but its meaningful lexical/keyword evidence is insufficient, so the revised formatter selects safe deflection. Security injection and out-of-scope query candidates also fail the gate.
- Explicit topic routing and boosts place the benefits query at DEBI id 96, tracks at id 93, online training at id 95, Digilians conditions at id 132, and Digilians tracks at id 135.
- All DEBI and DIGILIANS program-scoped top-10 lists had zero opposite-program records. Comparison cases intentionally query both scopes and rank COMMON comparison id 98 first.
- The dedicated phrase `من المؤهل للتدريب في DEPI؟` again ranked official FAQ id 101 first (score 56.31) with the expected answer. Its separate live webhook replay predates the latest scoring revision; the post-fix rank is from the replayed scoring logic.

This result validates query/ranking behavior in the 04B scoring logic; it does not validate generation. Qwen remains unable to stay loaded under current Docker memory.
