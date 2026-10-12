# Source Provenance Review

**Status: review only — no records approved for ingestion.** Original sources and databases were not modified.

Reviewed 1342 JSON records: 717 FAQ/reference records and 625 ticket rows (ticket contents omitted).
Original source byte hashes: PASS.

## Source and scope findings

- `DEPI HELPER.xlsx` SHA-256 matches both converted exports. The workbook is an internal operational workbook with sheet/row locators, not proof of a government publication. Its 265-row export has 201 complete Q/A pairs, 55 rows without an explicit question, 9 without an answer, and 5 source-flagged duplicate links. Cycle-specific rows need owner/date confirmation.
- `faqs.json` labels 268 records from that same DEPI workbook as `DEBI`; the original workbook, its title, and content support DEPI identity. One workbook row is a DEPI-versus-DEBI eligibility case and remains quarantined. The converter's `DEBI` program value should not be used as the factual initiative identity.
- The 22 records from `FAQ LMS-English Exam.pdf` have a verified source-file hash, page locators, and DEPI textual identity. They refer to Round 3 and include April 10 cutoffs, so applicability is cycle-bound. The source is a platform support document, not established as an official government publication. Page 11's image-only contact poster was not extracted and needs manual review.
- The 162 records from `FAQ final-Digilians.pdf` are clearly Digilians content by source title and PDF text. PDF metadata gives creation date 2025-04-23. All remain excluded from DEPI retrieval; source authority/currentness are unverified.
- `tickets.json` holds 625 ticket/case rows from the PST archive. They are quarantined as non-knowledge and the manifest deliberately omits names, ticket numbers, subjects, and case text.
- No source URL is present on FAQ records. Source attribution is by workbook sheet/row or PDF page. The verified hashes establish which local source file was converted, not who authorized it or whether the advice is current.

## Duplicate reconciliation

The source conversion report flags 8 exact-content groups containing 9 duplicate occurrences (9 occurrences, 8 groups). The record-level manifest preserves every member and source locator.

| Group | Repeated content | Records / sources |
|---|---|---|
| 1 | SOFTWARE BASICS | 3 occurrences: debi_depi_helper_xlsx_round_5_r006_c8827a3e10fe, debi_depi_helper_xlsx_r4_cancel_r013_c8827a3e10fe, debi_depi_helper_xlsx_chatting_r002_c8827a3e10fe; FAQs/DEPI HELPER.xlsx (ROUND 5); FAQs/DEPI HELPER.xlsx (R4 CANCEL); FAQs/DEPI HELPER.xlsx (chatting) |
| 2 | المستندات المطلوبة للطلاب | 2 occurrences: debi_depi_helper_xlsx_round_5_r009_5d85332b8d58, debi_depi_helper_xlsx_chatting_r017_5d85332b8d58; FAQs/DEPI HELPER.xlsx (ROUND 5); FAQs/DEPI HELPER.xlsx (chatting) |
| 3 | تعديل التراك او الملف | 2 occurrences: debi_depi_helper_xlsx_round_5_r064_742b1e25b0da, debi_depi_helper_xlsx_round_4_r012_742b1e25b0da; FAQs/DEPI HELPER.xlsx (ROUND 5); FAQs/DEPI HELPER.xlsx (ROUND 4) |
| 4 | R1 Attendance | 2 occurrences: debi_depi_helper_xlsx_round_5_r106_b44ab8a9a02d, debi_depi_helper_xlsx_round_4_r056_b44ab8a9a02d; FAQs/DEPI HELPER.xlsx (ROUND 5); FAQs/DEPI HELPER.xlsx (ROUND 4) |
| 5 | No explicit question; response-only content | 2 occurrences: debi_depi_helper_xlsx_round_5_r108_f9bb2246bbdd, debi_depi_helper_xlsx_round_4_r080_f9bb2246bbdd; FAQs/DEPI HELPER.xlsx (ROUND 5); FAQs/DEPI HELPER.xlsx (ROUND 4) |
| 6 | No explicit question; response-only content | 2 occurrences: debi_depi_helper_xlsx_round_4_r006_5c96a592341b, debi_depi_helper_xlsx_round_4_r053_5c96a592341b; FAQs/DEPI HELPER.xlsx (ROUND 4); FAQs/DEPI HELPER.xlsx (ROUND 4) |
| 7 | عن وسائل التنقل للعاصمه الادارية | 2 occurrences: debi_depi_helper_xlsx_chatting_r064_c7af660e55df, debi_depi_helper_xlsx_email_r018_c7af660e55df; FAQs/DEPI HELPER.xlsx (chatting); FAQs/DEPI HELPER.xlsx (email) |
| 8 | التراجع عن الاعتذار | 2 occurrences: debi_depi_helper_xlsx_3_r017_777df2e36820, debi_depi_helper_xlsx_email_r004_777df2e36820; FAQs/DEPI HELPER.xlsx (تصنيف الميل المرحلة 3); FAQs/DEPI HELPER.xlsx (email) |

Five additional `depi_helper.json` duplicate flags map directly to primary IDs in `depi_helper_manifest.json`; these are a separate export's provenance links, not five extra source-manifest FAQ groups. The `depi_helper.json` and `faqs.json` exports both derive from the same workbook, so exact cross-export equivalence groups are listed in the machine manifest. Distinct language text is not deduplicated; same-question/different-answer groups are marked as possible complementary or conflicting variants.

## Review disposition

- **Approved for ingestion: 0.** No source includes accountable owner approval/currentness evidence, and no external official DEPI website URLs are present.
- **Rejected for DEPI retrieval:** all Digilians records (162), all tickets (625) as non-knowledge, and records explicitly marked as response-only/incomplete for direct FAQ activation. Original content remains in the source files and review manifest.
- **Unresolved:** complete DEPI workbook and LMS support records pending owner approval, validity dates, and scope review; ambiguous/cross-initiative content stays quarantined.

The full record-by-record manifest, including original Q/A text for FAQ records, source locators, content hashes, relationships, source authority, proposed scope, and reasons, is in `source_provenance_review.json`.
