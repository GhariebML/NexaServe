# Knowledge Base Quality Report

Snapshot after scraped-only DEPI ingestion: 2026-09-27, `customerservice.knowledge_base`.

| Metric | Count |
|---|---:|
| Total | 73 |
| Active | 73 |
| Non-null embeddings | 73 |
| 768-dimensional embeddings | 73 |
| Source URL present | 36 |
| Content hash present | 37 |
| Empty question | 0 |
| Empty answer | 0 |
| Replacement characters detected | 0 |
| Exact duplicate Q/A pairs | 0 |
| DEBI | 45 |
| DIGILIANS | 26 |
| COMMON | 2 |
| Scraped FAQ | 29 |
| Scraped page/RAG sections | 7 |
| Local PDF-labeled records | 1 |
| XLSX rows ingested from DEPI HELPER | 0 |

The count composition is 36 DEPI scraped website records, eight DEBI curated/PDF records, 26 Digilians records, and two common records. These are all embedded, but the presence of a vector alone does not prove it matches current source text.

Row-level public content/provenance/embedding metadata is preserved in [knowledge_base_traceability.csv](../logs/runtime_forensic/knowledge_base_traceability.csv).

## Quality findings

- The 29 scraped FAQ source Q/A pairs match the current scrape and their stored hashes (29/29); 7 scraped page sections include source URLs and hashes.
- Thirty-six other active rows have no `content_hash` or `source_url`. This includes all 26 Digilians rows and both common records. Their exact embedding-to-content lineage is unprovable from existing columns.
- Digilians categories are named `depi_*`. Current filtering uses `program`, and the sample DEBI retrieval did not include DIGILIANS, but category naming risks confusion in future reporting/admin flows.
- The COMMON comparison record is not traceable to official source metadata; it contains unverified program claims. Do not treat its labels as authoritative evidence without source review.
- An exact duplicate normalized Q/A query found zero duplicate pairs. Hash duplicate count was also zero at baseline.
- The previous DB had 66 rows; this audit added seven DEPI web page chunks and backfilled URL/source attribution on the 29 existing scraped FAQ rows. No existing production rows were deleted.
