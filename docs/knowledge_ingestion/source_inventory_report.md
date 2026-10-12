# Converted Source Inventory

Source: `FAQs/converted` (recursive UTF-8 scan).

Files: 9 (6 JSON, 3 JSONL).
JSON dataset records: 1342; JSONL companion records: 1342.

| File | Bytes | Shape/schema | Records | Incomplete Q/A | Disposition |
|---|---:|---|---:|---:|---|
| `FAQs/converted/depi_helper.json` | 612223 | JSON object/records[] (schema 2.0) | 265 | 64 | quarantined_review |
| `FAQs/converted/depi_helper.jsonl` | 567240 | JSON array | 265 | 64 | skipped_duplicate_export |
| `FAQs/converted/depi_helper_manifest.json` | 4042 | JSON metadata object | 0 | 0 | skipped_metadata |
| `FAQs/converted/faqs.json` | 1019688 | JSON object/records[] (schema 1.0) | 452 | 66 | quarantined_review |
| `FAQs/converted/faqs.jsonl` | 936697 | JSON array | 452 | 66 | skipped_duplicate_export |
| `FAQs/converted/source_manifest.json` | 6429 | JSON metadata object | 0 | 0 | skipped_metadata |
| `FAQs/converted/tickets.json` | 2508027 | JSON object/tickets[] (schema 1.0) | 625 | 625 | quarantined_non_faq |
| `FAQs/converted/tickets.jsonl` | 2246673 | JSON array | 625 | 625 | skipped_duplicate_export |
| `FAQs/converted/tickets_manifest.json` | 1454 | JSON metadata object | 0 | 0 | skipped_metadata |

## Dispositions

- **FAQs/converted/depi_helper.json — quarantined_review:** FAQ-like records require verified source provenance, scope confirmation, and record-level quality review before activation. Export contains no source URL/status; incomplete rows and duplicate flags are separately counted.
- **FAQs/converted/depi_helper.jsonl — skipped_duplicate_export:** Line-delimited companion export; inventory is counted from its structured JSON counterpart to prevent double ingestion.
- **FAQs/converted/depi_helper_manifest.json — skipped_metadata:** Manifest/metadata artifact; it describes source files but is not knowledge content.
- **FAQs/converted/faqs.json — quarantined_review:** FAQ-like records require verified source provenance, scope confirmation, and record-level quality review before activation. All records currently declare source_status=unverified; program aliases include DEBI and DIGILIANS and have not been independently validated.
- **FAQs/converted/faqs.jsonl — skipped_duplicate_export:** Line-delimited companion export; inventory is counted from its structured JSON counterpart to prevent double ingestion.
- **FAQs/converted/source_manifest.json — skipped_metadata:** Manifest/metadata artifact; it describes source files but is not knowledge content.
- **FAQs/converted/tickets.json — quarantined_non_faq:** Support-ticket archive export includes student/ticket personal and case data; it is not FAQ knowledge and is excluded from RAG.
- **FAQs/converted/tickets.jsonl — skipped_duplicate_export:** Line-delimited companion export; inventory is counted from its structured JSON counterpart to prevent double ingestion.
- **FAQs/converted/tickets_manifest.json — skipped_metadata:** Manifest/metadata artifact; it describes source files but is not knowledge content.

## Quality and scope findings

- `faqs.json` contains 452 records: 393 FAQ records and 59 reference sections; all declare `source_status=unverified`. The labels are 290 `DEBI` and 162 `DIGILIANS`, neither of which is silently promoted into DEPI-authoritative scope.
- `depi_helper.json` contains 265 records, including incomplete question/answer rows and records flagged as duplicates; its source workbook is named but no source URL or verification status is present.
- `tickets.json` contains ticket records, not FAQs, and includes student names, ticket identifiers, and case content. It is quarantined from RAG ingestion.
- Manifest JSON files describe the source artifacts and have no knowledge record arrays. JSONL files are excluded from ingestion to avoid double counting; their machine inventory records exact record parity against their JSON companion.
- No source records are approved for activation by this inventory. Source-owner review and provenance verification are required first.

## Reproducibility

Run `python scripts/inventory_converted_sources.py`. The command reads source files and writes only under `docs/knowledge_ingestion/`, outside the canonical source directory.
