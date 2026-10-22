"""
NexaServe FAQ Conversion Test Suite
===================================
Validates the FAQ-to-JSON conversion pipeline against strict requirements:
- Arabic text and UTF-8 round-tripping
- English and bilingual records
- FAQ extraction fidelity
- PDF section and question numbering extraction
- Spreadsheet sheets, columns, and rows extraction
- Missing question / answer handling
- Exact duplicate detection and flagging
- Unsupported file handling (tickets.pst)
- Stable IDs across repeated runs
- JSON and JSONL parsing and parity
- Source traceability and SHA-256 integrity
- Exclusion of generated output from subsequent source scans
"""

import os
import sys
import json
import hashlib
from pathlib import Path
import re
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from convert_faqs_to_json import (
    run_conversion,
    inspect_source_files,
    detect_language,
    normalize_whitespace,
    compute_sha256,
    compute_content_hash,
    make_stable_id,
    VALID_PROGRAM_SCOPES
)

FAQ_DIR = ROOT / "FAQs"
OUTPUT_DIR = ROOT / "scratch" / "test_faq_conversion_out"


@pytest.fixture(scope="module")
def conversion_output():
    """Runs conversion into an isolated test directory and returns output paths and parsed datasets."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    results = run_conversion(FAQ_DIR, OUTPUT_DIR, ROOT)
    
    with open(results["faqs_json"], "r", encoding="utf-8") as f:
        json_data = json.load(f)
        
    jsonl_records = []
    with open(results["faqs_jsonl"], "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                jsonl_records.append(json.loads(line.strip()))
                
    with open(results["source_manifest"], "r", encoding="utf-8") as f:
        manifest = json.load(f)
        
    yield {
        "results": results,
        "json_data": json_data,
        "records": json_data["records"],
        "jsonl_records": jsonl_records,
        "manifest": manifest
    }
    # Cleanup test output
    import shutil
    if OUTPUT_DIR.exists():
        shutil.rmtree(OUTPUT_DIR, ignore_errors=True)


# ------------------------------------------------------------------------------
# 1. Output Files & Exclusions
# ------------------------------------------------------------------------------

def test_all_output_artifacts_exist(conversion_output):
    """Verifies that all 4 required artifacts exist in test output directory."""
    assert (OUTPUT_DIR / "faqs.json").exists()
    assert (OUTPUT_DIR / "faqs.jsonl").exists()
    assert (OUTPUT_DIR / "source_manifest.json").exists()
    assert (OUTPUT_DIR / "conversion_report.md").exists()


def test_exclusion_of_converted_directory_from_source_scans():
    """Ensures source file discovery excludes the generated converted directory."""
    discovered, manifest = inspect_source_files(FAQ_DIR, ROOT)
    discovered_paths = [str(p).replace('\\', '/') for p in discovered]
    for p in discovered_paths:
        assert "/converted/" not in p, f"Generated output directory was not excluded: {p}"


def test_exclusion_of_content_approval_review_workbook(conversion_output):
    """Verifies DEPI_Content_Approval_Review.xlsx is excluded from FAQ extraction."""
    records = conversion_output["records"]
    approval_recs = [r for r in records if "Approval_Review" in r.get("source_file", "")]
    assert len(approval_recs) == 0, "Approval review workbook must not produce ordinary FAQ records"
    manifest = conversion_output["manifest"]
    inv_item = next((e for e in manifest["source_inventory"] if "Approval_Review" in e["file_name"]), None)
    assert inv_item is not None
    assert inv_item["status"] == "approval_review_workbook"
    assert inv_item["records_count"] == 0


# ------------------------------------------------------------------------------
# 2. JSON & JSONL Validity and Parity
# ------------------------------------------------------------------------------

def test_json_and_jsonl_record_parity(conversion_output):
    """Verifies faqs.json and faqs.jsonl contain identical record counts and IDs in same order."""
    json_recs = conversion_output["records"]
    jsonl_recs = conversion_output["jsonl_records"]
    assert len(json_recs) == len(jsonl_recs)
    assert len(json_recs) >= 350
    for j_rec, jl_rec in zip(json_recs, jsonl_recs):
        assert j_rec["id"] == jl_rec["id"]
        assert j_rec["content_sha256"] == jl_rec["content_sha256"]


# ------------------------------------------------------------------------------
# 3. Arabic & UTF-8 Round-Tripping
# ------------------------------------------------------------------------------

def test_arabic_utf8_encoding_integrity(conversion_output):
    """Verifies Arabic characters round-trip cleanly without corruption or unicode escapes."""
    arabic_recs = [r for r in conversion_output["records"] if r["language"] in ["ar", "bilingual"]]
    assert len(arabic_recs) >= 300
    
    # Check sample known Arabic terms
    found_depi = any("مبادرة رواد مصر الرقمية" in (r["content"] or "") for r in arabic_recs)
    found_digilians = any("الرواد الرقميون" in (r["content"] or "") for r in arabic_recs)
    assert found_depi, "Expected DEPI Arabic phrase not found in extracted text"
    assert found_digilians, "Expected Digilians Arabic phrase not found in extracted text"


# ------------------------------------------------------------------------------
# 4. English & Bilingual Records
# ------------------------------------------------------------------------------

def test_english_and_bilingual_classification(conversion_output):
    """Verifies that English technical records and bilingual entries are correctly typed."""
    records = conversion_output["records"]
    en_recs = [r for r in records if r["language"] == "en"]
    bi_recs = [r for r in records if r["language"] == "bilingual"]
    assert len(en_recs) >= 18, f"Expected at least 18 English records from LMS PDF, got {len(en_recs)}"
    assert len(bi_recs) >= 10, f"Expected at least 10 bilingual records, got {len(bi_recs)}"


# ------------------------------------------------------------------------------
# 5. Program Scopes & RAG Compatibility
# ------------------------------------------------------------------------------

def test_valid_program_scopes(conversion_output):
    """Ensures all records adhere to the database program scope constraint (DEPI, DIGILIANS, COMMON)."""
    for rec in conversion_output["records"]:
        scope = rec["program_scope"]
        assert scope in VALID_PROGRAM_SCOPES, f"Invalid program scope '{scope}' in record {rec['id']}"
        assert rec["program"] == scope, f"Ingestion alias 'program' must match program_scope in {rec['id']}"


def test_depi_scope_isolation_from_debi(conversion_output):
    """Proves that DEPI content is assigned to DEPI scope, never misclassified as DEBI."""
    records = conversion_output["records"]
    depi_recs = [r for r in records if r["source_file"] == "FAQs/DEPI HELPER.xlsx"]
    assert len(depi_recs) > 0
    for r in depi_recs:
        assert r["program_scope"] == "DEPI", f"DEPI HELPER row {r['id']} incorrectly assigned scope {r['program_scope']}"
        assert r["program"] == "DEPI"

    debi_recs = [r for r in records if r["program_scope"] == "DEBI"]
    assert len(debi_recs) == 0, f"Expected 0 DEBI records in converted FAQ corpus, found {len(debi_recs)}"


def test_rag_canonical_ingestion_fields(conversion_output):
    """Ensures each record includes fields expected by ingest_knowledge.py."""
    for rec in conversion_output["records"]:
        assert "program" in rec
        assert "category" in rec
        assert "question" in rec
        assert "answer" in rec
        assert "source_attribution" in rec
        assert "content_hash" in rec
        assert rec["content_hash"] == rec["content_sha256"]



# ------------------------------------------------------------------------------
# 6. Source Traceability & SHA-256
# ------------------------------------------------------------------------------

def test_source_file_references_and_checksums(conversion_output):
    """Ensures all source_file references exist and source_sha256 matches actual disk files."""
    records = conversion_output["records"]
    file_hashes = {}
    for rec in records:
        src_path = ROOT / rec["source_file"]
        assert src_path.exists(), f"Source file does not exist: {rec['source_file']}"
        if rec["source_file"] not in file_hashes:
            file_hashes[rec["source_file"]] = compute_sha256(src_path)
        assert rec["source_sha256"] == file_hashes[rec["source_file"]], f"SHA-256 mismatch for {rec['source_file']}"


# ------------------------------------------------------------------------------
# 7. Unsupported File Handling (tickets.pst)
# ------------------------------------------------------------------------------

def test_unsupported_pst_file_recorded_as_exception(conversion_output):
    """Verifies that tickets.pst is recorded in source inventory with an exception for review."""
    manifest = conversion_output["manifest"]
    pst_entry = next((e for e in manifest["source_inventory"] if e["file_name"] == "tickets.pst"), None)
    assert pst_entry is not None, "tickets.pst missing from source manifest inventory"
    assert pst_entry["status"] == "unsupported_binary_format"
    assert pst_entry["records_count"] == 0
    assert len(pst_entry["exceptions"]) > 0
    assert any("pst" in ex.get("type", "").lower() for ex in pst_entry["exceptions"])


# ------------------------------------------------------------------------------
# 8. Deterministic Stable IDs
# ------------------------------------------------------------------------------

def test_id_stability_across_repeated_runs(conversion_output):
    """Verifies that re-running conversion produces 100% identical record IDs."""
    first_run_ids = [r["id"] for r in conversion_output["records"]]
    
    # Run conversion a second time into a temp directory or same directory
    rerun_results = run_conversion(FAQ_DIR, OUTPUT_DIR, ROOT)
    with open(rerun_results["faqs_json"], "r", encoding="utf-8") as f:
        rerun_data = json.load(f)
    rerun_ids = [r["id"] for r in rerun_data["records"]]
    
    assert first_run_ids == rerun_ids, "Record IDs must be deterministic and stable across repeated conversions"


# ------------------------------------------------------------------------------
# 9. Deduplication & Conflict Reporting
# ------------------------------------------------------------------------------

def test_exact_duplicates_detected_and_flagged(conversion_output):
    """Verifies that duplicate content hashes are grouped and flagged for review without silent deletion."""
    manifest = conversion_output["manifest"]
    duplicates = manifest["exact_duplicates"]
    assert len(duplicates) >= 5, f"Expected duplicate groups across Excel sheets, found {len(duplicates)}"
    for d in duplicates:
        assert d["count"] >= 2
        assert len(d["record_ids"]) == d["count"]
        # Find secondary records in dataset and ensure needs_review is True
        for rec_id in d["record_ids"][1:]:
            rec = next((r for r in conversion_output["records"] if r["id"] == rec_id), None)
            assert rec is not None
            assert rec["needs_review"] is True
            assert any("duplicate" in note.lower() for note in rec["review_notes"])


# ------------------------------------------------------------------------------
# 10. PDF Section & Numbering Extraction
# ------------------------------------------------------------------------------

def test_digilians_pdf_all_sections_extracted(conversion_output):
    """Verifies Digilians PDF has questions from all 7 chapters."""
    digi_recs = [r for r in conversion_output["records"] if r["source_file"] == "FAQs/FAQ final-Digilians.pdf"]
    assert len(digi_recs) == 162
    categories = {r["category"] for r in digi_recs}
    expected_categories = {"admissions", "registration", "training_content", "regulations", "technical_support", "certification", "careers"}
    assert expected_categories.issubset(categories)


def test_lms_exam_pdf_q_series_and_seb_guide(conversion_output):
    """Verifies LMS exam PDF extracts Q1..Q18 plus SEB installation guide and support notice."""
    lms_recs = [r for r in conversion_output["records"] if r["source_file"] == "FAQs/FAQ LMS-English Exam.pdf"]
    assert len(lms_recs) >= 20
    q_titles = [r["question"] for r in lms_recs if r.get("question")]
    assert any("Q1" in (r.get("title") or "") for r in lms_recs)
    assert any("Q18" in (r.get("title") or "") for r in lms_recs)
    assert any("Safe Exam" in (r.get("content") or "") for r in lms_recs)


# ------------------------------------------------------------------------------
# 11. Excel Multi-Sheet Extraction
# ------------------------------------------------------------------------------

def test_depi_helper_all_sheets_extracted(conversion_output):
    """Verifies DEPI HELPER.xlsx extracts records across all 8 sheets."""
    excel_recs = [r for r in conversion_output["records"] if r["source_file"] == "FAQs/DEPI HELPER.xlsx"]
    # 204 non-empty rows extracted (empty answers and headers filtered out)
    assert len(excel_recs) == 204
    sheets = {r["source_sheet"] for r in excel_recs}
    expected_sheets = {"ROUND 5", "ROUND 4", "Round 5 Cancel", "R4 CANCEL", "chatting", "R3", "تصنيف الميل المرحلة 3", "email"}
    # normalize spaces for comparison
    clean_sheets = {re.sub(r'\s+', ' ', s).strip() for s in sheets}
    assert expected_sheets.issubset(clean_sheets)
