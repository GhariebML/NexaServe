# Content Approval Ledger Reconciliation

**Status:** NO_DECISIONS — zero records approved.

## Decision summary

- Workbook review rows read: 1342
- Source queue records: 1342
- Decisions found: 0 (None)
- Decisions validated and written to proposed ledger: 0 (None)
- Approved records: 0 (None)
- Explicit rejected decisions: 0
- Explicit out-of-scope decisions: 0
- Rejected decisions written to ledger: 0
- Out-of-scope decisions written to ledger: 0
- Baseline Digilians records out of DEPI scope: 162
- Baseline ticket records excluded as operational data: 625
- Rows with no review input: 1342

## Fail-closed checks

- Incomplete decisions: 0
- Invalid statuses or modified source cells: 0
- Unknown source records: 0
- Ambiguous source identities: 0
- Conflicting or duplicated decisions: 0
- Stale source hashes: 3
- Resulting proposed ledger schema validation: PASS
- JSONL companion files are checked as parity artifacts and are not treated as decision records or import datasets.
- Question/answer content and ticket details are omitted from this report; the source workbook remains unchanged.

## Missing decision evidence

No reviewer decisions were entered. The 421 owner-approval, 132 manual-review, and 2 scope-decision records retain their existing evidence requirements; none was promoted.

## Incomplete and stale items

### Incomplete decisions

None.

### Stale hashes

| source_dataset | source_record_id | reason |
|---|---|---|
| FAQs/converted/faqs.json | digilians_digilians_pdf_s1_q20_1633aae2e9bd | content hash or original source file hash mismatch |
| FAQs/converted/faqs.json | digilians_digilians_pdf_s1_q32_d5cd43088680 | content hash or original source file hash mismatch |
| FAQs/converted/faqs.json | debi_lms_exam_pdf_support_contact_note_f0057b3ff593 | content hash or original source file hash mismatch |

### Conflicting or duplicated identities

None.

### Unknown records

None.

### Ambiguous identities

None.

### Invalid decisions/source fields

None.

## Decision identity and evidence rules

The workbook reviewer field must use `Reviewer identity: <name>; Role: <role>`. A full UTC timestamp must include a time; a date-only Excel value is incomplete. Every explicit decision requires reviewer identity/role, timestamp, rationale, and evidence reference.

Official DEPI approval requires an HTTPS `.gov.eg` source URL, source authority explicitly classified as verified official DEPI, and an authorized DEPI owner role. Internal guidance requires DEPI scope, internal classification, an authorized DEPI content-owner role, and an `OWNER_APPROVAL:` reference. General support requires `GENERAL_SUPPORT` scope, verified support authority, HTTPS source URL, an authorized support/platform owner, and a `SUPPORT_SOURCE:` or `SUPPORT_APPROVAL:` reference.

These checks validate evidence fields and structure; they do not fetch external URLs or independently certify a human's source/content assessment. No Ministry server was contacted.

## Reproducibility

Rerun `python scripts/reconcile_content_approval_decisions.py` to rebuild the proposed ledger and this report. The source workbook, original ledger, provenance manifest, databases, workflows, services, credentials, and WhatsApp state are read-only inputs or were not accessed.
