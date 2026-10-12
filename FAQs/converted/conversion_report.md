# 📄 NexaServe FAQ-to-JSON Conversion Report

**Generated At**: `2026-10-12T02:40:14.764083+00:00`  
**Discovered FAQ Directory**: `FAQs`  
**Total Source Files**: `6`  
**Total Records Extracted**: `1864`  

---

## 1. 📂 Source File Inventory

| File Name | Format | Size (Bytes) | SHA-256 (Truncated) | Status | Records Extracted |
| :--- | :---: | :---: | :---: | :---: | :---: |
| `DEPI HELPER.xlsx` | `XLSX` | 238,618 | `b754f154508b...` | **extracted** | 268 |
| `DEPI_Content_Approval_Review.xlsx` | `XLSX` | 354,144 | `b4729989c4fa...` | **extracted** | 1412 |
| `FAQ final-Digilians.pdf` | `PDF` | 405,865 | `e8bfdb2b3739...` | **extracted** | 162 |
| `FAQ LMS-English Exam.pdf` | `PDF` | 2,630,889 | `588de073bd28...` | **extracted** | 22 |
| `tickets.json` | `JSON` | 2,508,027 | `844ea1dec812...` | **supported** | 0 |
| `tickets.pst` | `PST` | 81,789,952 | `ab49532476d9...` | **unsupported_binary_format** | 0 |

---

## 2. 📊 Distribution Metrics

### By Program Scope

| Program Scope | Record Count | Notes |
| :--- | :---: | :--- |
| **DEBI** | 1702 | Digital Egypt Pioneers Initiative |
| **DIGILIANS** | 162 | Digilians Initiative |

### By Language

| Language | Record Count | Percentage |
| :--- | :---: | :---: |
| `ar` | 411 | 22.0% |
| `bilingual` | 17 | 0.9% |
| `en` | 1436 | 77.0% |

---

## 3. 🔍 Deduplication & Quality Analysis

- **Exact Content Duplicates**: 10 sets detected across files/sheets.
- **Records Flagged for Review**: 69 records.

### Duplicate Groups (Preserved with Review Flag)

- **Hash** `c8827a3e10fe...`: 3 occurrences of *"SOFTWARE BASICS"*
  - FAQs/DEPI HELPER.xlsx (ROUND 5)
  - FAQs/DEPI HELPER.xlsx (R4 CANCEL)
  - FAQs/DEPI HELPER.xlsx (chatting)
- **Hash** `5d85332b8d58...`: 2 occurrences of *"المستندات المطلوبة للطلاب"*
  - FAQs/DEPI HELPER.xlsx (ROUND 5)
  - FAQs/DEPI HELPER.xlsx (chatting)
- **Hash** `742b1e25b0da...`: 2 occurrences of *"تعديل التراك او الملف"*
  - FAQs/DEPI HELPER.xlsx (ROUND 5)
  - FAQs/DEPI HELPER.xlsx (ROUND 4)
- **Hash** `b44ab8a9a02d...`: 2 occurrences of *"R1 Attendance"*
  - FAQs/DEPI HELPER.xlsx (ROUND 5)
  - FAQs/DEPI HELPER.xlsx (ROUND 4)
- **Hash** `f9bb2246bbdd...`: 2 occurrences of *"N/A"*
  - FAQs/DEPI HELPER.xlsx (ROUND 5)
  - FAQs/DEPI HELPER.xlsx (ROUND 4)
- **Hash** `5c96a592341b...`: 2 occurrences of *"N/A"*
  - FAQs/DEPI HELPER.xlsx (ROUND 4)
  - FAQs/DEPI HELPER.xlsx (ROUND 4)
- **Hash** `c7af660e55df...`: 2 occurrences of *"عن وسائل التنقل للعاصمه الادارية"*
  - FAQs/DEPI HELPER.xlsx (chatting)
  - FAQs/DEPI HELPER.xlsx (email)
- **Hash** `777df2e36820...`: 2 occurrences of *"التراجع عن الاعتذار"*
  - FAQs/DEPI HELPER.xlsx (تصنيف الميل المرحلة 3)
  - FAQs/DEPI HELPER.xlsx (email)
- **Hash** `9cec2b4570aa...`: 4 occurrences of *"Review only. Reviewer fields are intentionally blank; no record is approved by this workbook."*
  - FAQs/DEPI_Content_Approval_Review.xlsx (Owner Approval Queue)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Manual Content Review)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Scope Decisions)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Out of Scope)
- **Hash** `889ea5a6c1a8...`: 4 occurrences of *"Stable Source Record ID"*
  - FAQs/DEPI_Content_Approval_Review.xlsx (Owner Approval Queue)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Manual Content Review)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Scope Decisions)
  - FAQs/DEPI_Content_Approval_Review.xlsx (Out of Scope)

---

## 4. ⚠️ Exceptions & Files Requiring Manual Review

### `FAQ LMS-English Exam.pdf`
- **Type**: `scanned_or_graphic_image`
  - **Details**: Page 11 contains graphical support contact numbers poster without embedded text layer.

### `tickets.pst`
- **Type**: `unsupported_outlook_pst`
  - **Details**: Microsoft Outlook Personal Storage Table (.pst) binary archive. Requires external pypff/libratom parser library or pre-conversion export. Retained as exception for review.


---

## 5. 🚀 RAG Compatibility & Next Steps

1. **Canonical Schema**: Records contain `id`, `program_scope`, `category`, `question`, `answer`, `content`, `source_file`, `source_page`, `source_sheet`, `content_sha256`.
2. **Ingestion Aliases**: Includes `program`, `question_ar`, `answer_ar`, `source_attribution`, and `content_hash` for 100% native compatibility with `deployment/application/ingestion/scripts/ingest_knowledge.py`.
3. **Local Testing Command**:
   ```bash
   python scripts/convert_faqs_to_json.py
   pytest tests/test_faq_conversion.py
   ```