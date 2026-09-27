# Knowledge Source Traceability

## Verified official DEPI website FAQ path

| Stage | Evidence |
|---|---|
| Official source | Current configured page: `https://depi.gov.eg/content/faqs`; direct Python HTTP request returned 200 during the audit. |
| File | `DEPI_Web_Scraper/data/final/faqs.json`; 29 question/answer records, each with `source_url`. Fresh scrape generated at 2026-09-27 22:20 Africa/Cairo. |
| Ingestion | `scripts/ingest_knowledge.py`, `extract_scraped()`; `--scraped-only` avoids importing unverified local PDFs/workbook. Ingestion log: `logs/runtime_forensic/ingest_scraped_only_20260927.txt`. |
| Database | 29 records have `program=DEBI`, `category=scraped_faq`, `source_attribution=DEPI Official FAQ`, and `source_url=https://depi.gov.eg/content/faqs`. All 29 hashes matched source Q/A on the audit comparison. |
| Embedding | All 29 have non-null 768-dimensional vectors. Active embed endpoint/model: Ollama `nomic-embed-text`; exact per-row model/version is not stored, so historical rows cannot be independently proven to use that model. |
| RAG retrieval | Query `من المؤهل للتدريب في DEPI؟` retrieved official row id 101 at rank 1, relevance 56.3129. A direct vector search ranked it first at cosine similarity 0.8983. |
| LLM context | The exact question and answer were in `rag_context` sent to the Qwen node; see trace JSON. Four lower-ranked FAQ items were also included. |
| Final answer | The webhook and logged AI message both returned the exact source answer. Qwen failed with process-killed HTTP 500; this final response was guardrail fallback, not a generated answer. |

The current source fact is `من المؤهل للتدريب؟` → `طلاب و خريجو الكليات بالجامعات المصرية حسب المسار.` The database record stores its source URL, hash, and embedding.

The non-secret per-row snapshot of all 73 records (including source URL/hash, active/embedding flags/dimensions, created timestamp, and public question/answer text) is [knowledge_base_traceability.csv](../logs/runtime_forensic/knowledge_base_traceability.csv). `updated_at` and per-row embedding-model metadata columns do not exist, so those fields are explicitly reported unavailable rather than inferred.

## Remaining knowledge provenance gaps

- The DB now has 73 active embedded rows, but only 36 have source URLs and only 37 have content hashes. The other 36 rows lack reliable source URL/hash linkage.
- Twenty-six `DIGILIANS` rows use categories named `depi_*`; the program field is `DIGILIANS`, so the live program filter keeps them isolated, but category naming is misleading. Their source attribution says Digilians, yet there is no source URL or per-record content hash. The local `FAQs/FAQ final-Digilians.pdf` exists but exact row-to-page provenance has not been proven.
- The single `DEBI/pdf_document` row points to `FAQ LMS-English Exam.pdf`, with a local file label and no source URL. It is not an official online source verification.
- The `FAQs/DEPI HELPER.xlsx` workbook contains rows but the existing header mapping yielded no ingested records. It was intentionally not force-ingested because content includes operational/support scripts and no reliable question/answer schema was identified.
- `COMMON/comparison` and `COMMON/disambiguation` each lack URLs and hashes. The comparison record contains broad claims that were not traced to official records in this audit.
- No source precedence beyond the verified scraped DEPI FAQ was implemented. Existing metadata is insufficient to rank all historical records as official vs curated.
- Post-fix retrieval replay still ranks row 101 first for the dedicated source query; this updated scoring evidence is attached under `retrieval_replay_after_fix` in the trace artifact.
