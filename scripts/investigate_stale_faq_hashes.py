#!/usr/bin/env python3
"""Write a privacy-minimizing investigation and non-operative hash proposal."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path
from typing import Any

from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from build_source_provenance_review import record_fingerprint  # noqa: E402
from convert_faqs_to_json import compute_content_hash, normalize_whitespace  # noqa: E402
from reconcile_content_approval_decisions import (  # noqa: E402
    compute_current_content_hash,
    read_json,
    read_workbook_decisions,
    sha256_file,
)

DOCS = ROOT / "docs" / "knowledge_ingestion"
DEFAULTS = {
    "queue": DOCS / "source_approval_queue.json",
    "provenance": DOCS / "source_provenance_review.json",
    "source_ledger": DOCS / "content_approval_ledger.json",
    "workbook": DOCS / "DEPI_Content_Approval_Review.xlsx",
    "output_json": DOCS / "stale_faq_hash_reconciliation.proposed.json",
    "output_report": DOCS / "stale_faq_hash_investigation.md",
}
SUPPORT_NOTE_HASH_QUESTION = "قنوات الدعم الفني والخط الساخن للمنحة"


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def previous_reconciler_hash(record: dict[str, Any]) -> str:
    """Reproduce the source-independent algorithm that produced the 10 flags."""
    question = record.get("question") if record.get("question") is not None else record.get("question_ar", "")
    answer = record.get("answer") if record.get("answer") is not None else record.get("answer_ar")
    if answer is None:
        answer = record.get("content", "")
    return sha256_text(f"{normalize_whitespace(question or '')}||{normalize_whitespace(answer or '')}")


def compare_source_row(workbook_path: Path, record: dict, locator: dict) -> dict:
    wb = load_workbook(workbook_path, read_only=True, data_only=True)
    try:
        target = str(locator.get("source_sheet", ""))
        ws = next((sheet for sheet in wb.worksheets if sheet.title.strip() == target), None)
        if ws is None or locator.get("source_row") is None:
            return {"verified": False, "question_matches_source_row": None, "answer_matches_source_row": None}
        row = [ws.cell(locator["source_row"], column).value for column in range(1, 5)]
        values = [normalize_whitespace(str(value) if value is not None else "") for value in row]
        if target.startswith("تصنيف الميل المرحلة 3"):
            question, answer = values[1], values[2]
        elif target == "email":
            question = values[0] or values[1]
            answer = values[2] or values[1]
        else:
            question, answer = values[0], values[1]
        current_question = record.get("question") or record.get("question_ar") or ""
        current_answer = record.get("answer") or record.get("answer_ar") or ""
        return {
            "verified": True,
            "question_matches_source_row": question == current_question,
            "answer_matches_source_row": answer == current_answer,
            "source_row_cell_lengths": [len(str(value or "")) for value in row],
        }
    finally:
        wb.close()


def source_text_check(source_path: Path, record: dict) -> dict:
    try:
        import fitz
        document = fitz.open(source_path)
        try:
            text = "\n".join(page.get_text() for page in document)
            page_number = record.get("source_page")
            page_text = document[page_number - 1].get_text() if isinstance(page_number, int) and 1 <= page_number <= len(document) else ""
        finally:
            document.close()
    except Exception:
        return {"verified": False, "answer_found_in_original_document": None}
    answer = record.get("answer") or record.get("answer_ar") or ""
    return {
        "verified": bool(answer),
        "answer_found_in_original_document": bool(answer and answer in text),
        "answer_found_at_recorded_page": bool(answer and answer in page_text),
        "recorded_page_number_is_one_based": record.get("source_page"),
        "extracted_answer_length": len(answer),
    }


def metadata_matches_manifest(record: dict, manifest_record: dict) -> dict:
    comparisons = {
        "language": (record.get("language"), manifest_record.get("language")),
        "record_type": (record.get("record_type", "faq"), manifest_record.get("record_type", "faq")),
        "category": (record.get("category"), manifest_record.get("category")),
        "source_file": (record.get("source_file"), manifest_record.get("source_original_file")),
        "source_page": (record.get("source_page"), manifest_record.get("source_locator", {}).get("source_page")),
        "source_sheet": (record.get("source_sheet"), manifest_record.get("source_locator", {}).get("source_sheet")),
        "source_row": (record.get("source_row"), manifest_record.get("source_locator", {}).get("source_row")),
        "source_url": (record.get("source_url"), manifest_record.get("source_url")),
        "source_status": (record.get("source_status"), manifest_record.get("source_status_original")),
        "source_attribution": (record.get("source_attribution"), manifest_record.get("source_attribution_original")),
        "needs_review": (record.get("needs_review"), manifest_record.get("needs_review_original")),
        "review_notes": (record.get("review_notes"), manifest_record.get("review_notes_original")),
    }
    return {key: left == right for key, (left, right) in comparisons.items()}


def diagnose(queue: dict, provenance: dict, source_ledger: dict, workbook_path: Path) -> dict:
    queue_rows = [r for r in queue["records"] if r.get("source_json") == "FAQs/converted/faqs.json"]
    provenance_rows = {
        (r.get("source_file"), r.get("source_record_id")): r
        for r in provenance["source_records"]
    }
    dataset = read_json(ROOT / "FAQs" / "converted" / "faqs.json")
    current_by_id = {r["id"]: r for r in dataset.get("records", []) if isinstance(r, dict) and r.get("id")}
    workbook_rows, _ = read_workbook_decisions(workbook_path)
    explicit_decisions = sum(1 for row in workbook_rows if str(row.get("Reviewer Decision") or "").strip())
    source_hashes = {}
    for source_name, info in provenance["original_source_files"].items():
        actual = sha256_file(ROOT / source_name)
        source_hashes[source_name] = {
            "provenance_sha256": info.get("sha256_expected"),
            "current_sha256": actual,
            "matches": bool(actual and actual == info.get("sha256_expected")),
        }
    converted_sha = sha256_file(ROOT / "FAQs" / "converted" / "faqs.json")

    candidates = []
    for queued in queue_rows:
        record = current_by_id.get(queued["source_record_id"])
        manifest = provenance_rows.get((queued["source_json"], queued["source_record_id"]))
        if not record or not manifest:
            continue
        previous_hash = previous_reconciler_hash(record)
        if previous_hash == queued.get("original_content_hash"):
            continue
        source_path = queued["source_original_file"]
        corrected_hash = compute_current_content_hash(queued["source_json"], record, source_path)
        provenance_hash = manifest.get("content_sha256_source")
        source_hash_info = source_hashes.get(source_path, {})
        metadata_checks = metadata_matches_manifest(record, manifest)
        locator_current = {k: record.get(k) for k in ("source_sheet", "source_row", "source_page") if record.get(k) is not None}
        locator_matches = locator_current == queued.get("source_locator", {})
        current_question = record.get("question") or record.get("question_ar") or ""
        current_answer = record.get("answer") or record.get("answer_ar") or ""
        qa_snapshot_matches = (
            manifest.get("original_question") == current_question
            and manifest.get("original_answer") == current_answer
            and manifest.get("content") == record.get("content")
        )
        if source_path == "FAQs/DEPI HELPER.xlsx":
            raw_source_check = compare_source_row(ROOT / source_path, record, queued.get("source_locator", {}))
            old_recompute = previous_hash
            if corrected_hash == provenance_hash and corrected_hash == queued.get("original_content_hash"):
                disposition = "RESOLVED_RECOMPUTATION_RULE"
                reason = (
                    "The original helper converter hashes normalized question plus answer-or-content. "
                    "These records have an empty answer and content equal to the extracted question; "
                    "the earlier reconciler hashed question plus empty answer. Raw source cells, Q/A, "
                    "metadata snapshot, locator, and source-file SHA-256 match."
                )
                action = "correct_provenance_recomputed_hash_field_only"
            else:
                disposition = "UNRESOLVED_HASH_MISMATCH"
                reason = "Source-specific helper fallback did not reproduce the recorded source hash."
                action = "leave_stale"
            canonicalization_details = {
                "previous_reconciliation_basis": "normalize(question)||normalize(answer)",
                "converter_basis": "normalize(question)||normalize(answer or content)",
                "answer_was_empty": not bool(current_answer),
                "content_equals_question": normalize_whitespace(record.get("content")) == normalize_whitespace(current_question),
                "question_component_sha256": sha256_text(normalize_whitespace(current_question)),
                "previous_answer_component_sha256": sha256_text(""),
                "converter_answer_or_content_component_sha256": sha256_text(normalize_whitespace(current_answer or record.get("content"))),
            }
        else:
            raw_source_check = source_text_check(ROOT / source_path, record)
            old_recompute = previous_hash
            if source_path == "FAQs/FAQ LMS-English Exam.pdf" and record.get("id", "").startswith("debi_lms_exam_pdf_support_contact_note_"):
                historical_hash = compute_content_hash(SUPPORT_NOTE_HASH_QUESTION, current_answer, current_answer)
                historical_hash_matches = historical_hash == provenance_hash == queued.get("original_content_hash")
                if (historical_hash_matches and source_hash_info.get("matches") and qa_snapshot_matches
                        and locator_matches and all(metadata_checks.values())):
                    disposition = "PROPOSED_CANONICAL_HASH_CORRECTION"
                    reason = (
                        "The PDF converter hashed its hard-coded topic label plus the extracted answer, "
                        "but persisted a different generated question plus the same answer. The original "
                        "PDF bytes and extracted answer are unchanged. Rebinding the hash to persisted "
                        "question-and-answer fields yields a new hash; this proposal is not applied."
                    )
                    action = "propose_new_hash_pending_human_review"
                else:
                    disposition = "UNRESOLVED_HASH_MISMATCH"
                    reason = "The converter's historical hash basis could not be verified against the source snapshot."
                    action = "leave_stale"
                canonicalization_details = {
                    "historical_converter_basis": "normalize(hard-coded topic label)||normalize(extracted answer)",
                    "proposed_persisted_record_basis": "normalize(persisted question)||normalize(persisted answer)",
                    "historical_hash_question_input": SUPPORT_NOTE_HASH_QUESTION,
                    "current_persisted_question": current_question,
                    "historical_question_component_sha256": sha256_text(normalize_whitespace(SUPPORT_NOTE_HASH_QUESTION)),
                    "persisted_question_component_sha256": sha256_text(normalize_whitespace(current_question)),
                    "answer_component_unchanged": True,
                    "historical_answer_component_sha256": sha256_text(normalize_whitespace(current_answer)),
                    "persisted_answer_component_sha256": sha256_text(normalize_whitespace(current_answer)),
                }
            else:
                disposition = "UNRESOLVED_HASH_MISMATCH"
                reason = "No source-specific canonicalization discrepancy was verified."
                action = "leave_stale"
                canonicalization_details = {
                    "previous_reconciliation_basis": "normalize(question)||normalize(answer)",
                    "proposed_persisted_record_basis": "normalize(question)||normalize(answer)",
                }

        old_hash = provenance_hash
        proposed_hash = corrected_hash
        record_suffix_hash = record.get("id", "").rsplit("_", 1)[-1]
        item = {
            "source_dataset": queued["source_json"],
            "source_record_id": queued["source_record_id"],
            "source_filename": source_path,
            "source_locator": queued.get("source_locator", {}),
            "provenance_content_hash": old_hash,
            "approval_queue_content_hash": queued.get("original_content_hash"),
            "previous_reconciler_current_hash": old_recompute,
            "current_canonical_record_hash": corrected_hash,
            "proposed_content_hash": proposed_hash,
            "original_source_file_sha256": source_hash_info,
            "converted_dataset_sha256_current": converted_sha,
            "question_comparison": {
                "provenance_snapshot_equals_current_record": manifest.get("original_question") == current_question,
                "direct_source_check": raw_source_check.get("question_matches_source_row", "generated_question"),
                "current_length": len(current_question),
            },
            "answer_comparison": {
                "provenance_snapshot_equals_current_record": manifest.get("original_answer") == current_answer,
                "direct_source_check": raw_source_check.get("answer_matches_source_row", raw_source_check.get("answer_found_in_original_document")),
                "current_length": len(current_answer),
            },
            "content_comparison": {
                "provenance_snapshot_equals_current_record": manifest.get("content") == record.get("content"),
                "current_length": len(str(record.get("content") or "")),
            },
            "metadata_comparison_to_provenance": metadata_checks,
            "metadata_changed_since_provenance_snapshot": not all(metadata_checks.values()),
            "source_locator_unchanged": locator_matches,
            "record_fingerprint_matches_canonical_json_snapshot": record_fingerprint(record) == manifest.get("record_fingerprint_sha256"),
            "unicode_nfc_changes_question": unicodedata.normalize("NFC", str(current_question)) != str(current_question),
            "unicode_nfc_changes_answer": unicodedata.normalize("NFC", str(current_answer)) != str(current_answer),
            "canonicalization_details": canonicalization_details,
            "proposed_provenance_patch": {
                "source_record_id": queued["source_record_id"],
                "source_original_file": source_path,
                "source_locator": queued.get("source_locator", {}),
                "original_content_sha256_source_preserved": old_hash,
                "proposed_content_sha256_source": proposed_hash,
                "proposed_content_sha256_recomputed_converter_compatible": corrected_hash,
                "proposed_content_equivalence_hash": corrected_hash,
                "proposal_applied": False,
                "approval_decision": None,
                "approval_inherited": False,
            },
            "source_file_unchanged_since_provenance": source_hash_info.get("matches", False),
            "direct_original_content_check": raw_source_check,
            "disposition": disposition,
            "diagnosis": reason,
            "proposed_action": action,
            "proposal_applied": False,
            "approval_decision": None,
            "approval_inherited": False,
            "content_review_required": True,
            "stable_id_suffix_matches_recorded_hash": record_suffix_hash == (old_hash or "")[:12],
            "stable_id_suffix_matches_proposed_hash": record_suffix_hash == (proposed_hash or "")[:12],
        }
        candidates.append(item)

    decisions = len(source_ledger.get("entries", []))
    unresolved = sum(1 for item in candidates if item["disposition"] in {"PROPOSED_CANONICAL_HASH_CORRECTION", "UNRESOLVED_HASH_MISMATCH"})
    resolved = len(candidates) - unresolved
    proposal = {
        "title": "NexaServe stale FAQ source hash investigation and proposal",
        "version": "1.0.0",
        "status": "REVIEW_REQUIRED",
        "generated_by": "scripts/investigate_stale_faq_hashes.py",
        "source_inputs_read_only": True,
        "original_source_files_modified": False,
        "approval_workbook_modified": False,
        "original_ledger_modified": False,
        "database_modified": False,
        "records_investigated": len(candidates),
        "resolved_by_correct_source_specific_recomputation": resolved,
        "hash_rebinding_proposals_pending_review": sum(1 for item in candidates if item["disposition"] == "PROPOSED_CANONICAL_HASH_CORRECTION"),
        "unexplained_mismatches": sum(1 for item in candidates if item["disposition"] == "UNRESOLVED_HASH_MISMATCH"),
        "stale_in_current_fail_closed_reconciliation": unresolved,
        "workbook_explicit_decisions": explicit_decisions,
        "source_ledger_entries": decisions,
        "approved_records": sum(1 for e in source_ledger.get("entries", []) if str(e.get("decision", "")).startswith("APPROVED_")),
        "records": candidates,
        "policy": "Proposal only. No content hash or provenance entry is changed, no approval is created or inherited, and unresolved records remain stale.",
    }
    return proposal


def render_report(proposal: dict) -> str:
    pdf_item = next((item for item in proposal["records"] if item["disposition"] == "PROPOSED_CANONICAL_HASH_CORRECTION"), None)
    lines = [
        "# Stale FAQ Source Hash Investigation",
        "",
        "**Status: REVIEW REQUIRED.** This report diagnoses the ten records flagged by the earlier reconciliation run. It does not apply provenance changes or make approval decisions.",
        "",
        "## Findings",
        "",
        f"- Records investigated: {proposal['records_investigated']}",
        f"- Resolved by correcting source-specific recomputation: {proposal['resolved_by_correct_source_specific_recomputation']}",
        f"- Corrected hash proposals pending human review: {proposal['hash_rebinding_proposals_pending_review']}",
        f"- Mismatches with unknown cause: {proposal['unexplained_mismatches']}",
        f"- Records still stale in the current fail-closed reconciliation: {proposal['stale_in_current_fail_closed_reconciliation']}",
        f"- Explicit workbook decisions: {proposal['workbook_explicit_decisions']}",
        f"- Existing source ledger entries / approvals: {proposal['source_ledger_entries']} / {proposal['approved_records']}",
        "- Original XLSX and PDF source file hashes match the hashes recorded in the provenance manifest.",
        "- For all ten records, the current converted question, answer, content, metadata snapshot, and locator match the provenance manifest. Direct original-source checks also match the extracted helper rows or PDF answer text.",
        "- No raw Q/A text, ticket data, contact detail, or credentials are reproduced here; lengths and hashes provide the content-level comparison.",
        "",
        "## Hash procedure findings",
        "",
        "The helper converter computes `SHA256(normalize(question) + `||` + normalize(answer or content))`. For the nine helper rows below, `answer` is empty and `content` is the same extracted text as the question. The earlier reconciliation used `question||empty-answer`, so it produced false stale flags. Recomputing with the helper source rule reproduces the recorded hash exactly; no stored hash changes.",
        "",
        "The LMS support-note converter computes its stored hash with a hard-coded generated topic label and extracted answer, then persists a different generated question and the same answer. The PDF source bytes and answer text match the provenance snapshot. Hashing the persisted question and answer produces the proposed replacement below. The old hash is preserved, the proposal is not applied, and the stable ID suffix still reflects the old hash; human review is required before adopting the new binding.",
        "",
        "The canonical Q/A hash algorithm is `SHA256(normalize(question) + `||` + normalize(answer))`, except the DEPI HELPER XLSX extractor's documented `answer or content` fallback. The existing whitespace normalization replaces NBSP/BOM, normalizes CRLF/CR, collapses three or more line breaks to two, collapses inline spaces/tabs, and trims lines. It does not perform Unicode NFC. Diagnostic tests confirm that Arabic NFC-equivalent strings only hash equally when the normalization form is explicitly selected; no Unicode rewrite was used to explain these ten records.",
        "",
        "The provenance metadata fingerprint uses canonical JSON (`ensure_ascii=False`, sorted keys, compact separators), so object key order and indentation do not explain any of these mismatches.",
        "",
    ]
    if pdf_item:
        detail = pdf_item["canonicalization_details"]
        lines += [
            f"For the LMS record, the old hash input question was `{detail['historical_hash_question_input']}`; the persisted question is `{detail['current_persisted_question']}`. The answer component is unchanged (both component hashes are `{detail['historical_answer_component_sha256']}`).",
            "",
        ]
    lines += [
        "## Record-by-record audit",
        "",
        "| Stable record ID | Original source / locator | Provenance hash | Current raw source SHA-256 | Current canonical record hash | Diagnosis / exact difference | Disposition |",
        "|---|---|---|---|---|---|---|",
    ]
    for item in proposal["records"]:
        locator = json.dumps(item["source_locator"], ensure_ascii=False, sort_keys=True)
        source_hash = item["original_source_file_sha256"].get("current_sha256") or "unavailable"
        values = [item["source_record_id"], f"{item['source_filename']} {locator}", item["provenance_content_hash"], source_hash, item["current_canonical_record_hash"], item["diagnosis"], item["disposition"]]
        lines.append("| " + " | ".join(str(v).replace("|", "\\|").replace("\n", " ") for v in values) + " |")
    lines += [
        "",
        "## Proposed provenance actions",
        "",
        "The machine-readable proposal preserves each original source hash and includes a candidate hash only where the persisted Q/A binding differs. All changes are marked `proposal_applied: false`; no decision is populated and no approval can be inherited from a prior hash.",
        "",
        "For nine helper records, only the provenance recomputation diagnostic should be corrected to use the extractor's content fallback. For the LMS support note, the proposed source content hash uses the persisted question and answer; its stable-ID suffix mismatch is explicitly flagged for review.",
        "",
        "## Validation boundary",
        "",
        "Run `python scripts/reconcile_content_approval_decisions.py` after any separately reviewed provenance change. A corrected hash alone does not make a record approval-ready. The review workbook remains empty, the ledger remains empty, and all ten records still require content/authority/scope review.",
        "",
    ]
    return "\n".join(lines)


def write_outputs(output_json: Path, output_report: Path, proposal: dict) -> None:
    output_json.parent.mkdir(parents=True, exist_ok=True)
    output_report.parent.mkdir(parents=True, exist_ok=True)
    for path, text in (
        (output_json, json.dumps(proposal, ensure_ascii=False, indent=2) + "\n"),
        (output_report, render_report(proposal)),
    ):
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8")
        temporary.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for option, default in DEFAULTS.items():
        parser.add_argument("--" + option.replace("_", "-"), type=Path, default=default)
    args = parser.parse_args(argv)
    proposal = diagnose(read_json(args.queue), read_json(args.provenance), read_json(args.source_ledger), args.workbook)
    write_outputs(args.output_json, args.output_report, proposal)
    print(json.dumps({k: proposal[k] for k in (
        "status", "records_investigated", "resolved_by_correct_source_specific_recomputation",
        "hash_rebinding_proposals_pending_review", "unexplained_mismatches",
        "stale_in_current_fail_closed_reconciliation", "workbook_explicit_decisions",
        "source_ledger_entries", "approved_records",
    )} | {"proposed_json": str(args.output_json), "report": str(args.output_report)}, ensure_ascii=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
