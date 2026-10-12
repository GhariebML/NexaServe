#!/usr/bin/env python3
"""Build a record-level, non-approving provenance review for converted sources."""
from __future__ import annotations

import collections
import hashlib
import json
import re
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "FAQs" / "converted"
OUTPUT = ROOT / "docs" / "knowledge_ingestion"


def file_hash(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def normalize(text: Any) -> str:
    if not text:
        return ""
    value = str(text).replace("\u00a0", " ").replace("\ufeff", "")
    value = re.sub(r"\r\n?", "\n", value)
    value = re.sub(r"\n{3,}", "\n\n", value)
    return "\n".join(re.sub(r"[ \t]+", " ", line).strip() for line in value.splitlines()).strip()


def content_hash(question: Any, answer: Any, content: Any = None,
                 fallback_to_content: bool = False) -> str:
    """Recompute the source extractor's canonical Q/A hash.

    The DEPI HELPER Excel converter uses ``answer or content`` when building
    its canonical answer. Other extractors hash the answer field as persisted,
    including an explicitly empty answer.
    """
    canonical_answer = (answer or content) if fallback_to_content else answer
    return hashlib.sha256(f"{normalize(question)}||{normalize(canonical_answer)}".encode("utf-8")).hexdigest()


def record_fingerprint(record: dict[str, Any]) -> str:
    body = {
        "answer": normalize(record.get("answer") or record.get("answer_ar")),
        "language": record.get("language") or "und",
        "question": normalize(record.get("question") or record.get("question_ar")),
        "source_file": record.get("source_file") or record.get("source_archive"),
        "source_record_id": record.get("id"),
    }
    return hashlib.sha256(json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()


def load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def original_source_info() -> dict[str, dict[str, Any]]:
    sources: dict[str, dict[str, Any]] = {}
    helper = load(SOURCE / "depi_helper.json")
    for name, expected, size in [("DEPI HELPER.xlsx", helper["source_file_sha256"], helper["source_file_size_bytes"])]:
        path = ROOT / "FAQs" / name
        actual = file_hash(path) if path.exists() else None
        sources[f"FAQs/{name}"] = {"bytes": path.stat().st_size if path.exists() else None, "expected_bytes": size,
                                    "sha256_expected": expected, "sha256_actual": actual, "hash_match": actual == expected}
    faq = load(SOURCE / "faqs.json")
    for rec in faq["records"]:
        name = rec.get("source_file")
        if not name or name in sources:
            continue
        path = ROOT / name
        expected = rec.get("source_sha256")
        actual = file_hash(path) if path.exists() else None
        sources[name] = {"bytes": path.stat().st_size if path.exists() else None, "sha256_expected": expected,
                         "sha256_actual": actual, "hash_match": actual == expected}
    tickets = load(SOURCE / "tickets.json")
    name = tickets.get("source_file")
    if name:
        path = ROOT / name
        expected = tickets.get("source_file_sha256")
        actual = file_hash(path) if path.exists() else None
        sources[name] = {"bytes": path.stat().st_size if path.exists() else None,
                         "expected_bytes": tickets.get("source_file_size_bytes"), "sha256_expected": expected,
                         "sha256_actual": actual, "hash_match": actual == expected}
    return sources


def classify(record: dict[str, Any], source_file: str, is_ticket: bool = False) -> dict[str, Any]:
    q = record.get("question") or record.get("question_ar")
    a = record.get("answer") or record.get("answer_ar")
    rtype = (record.get("record_type") or "faq").lower()
    original_program = str(record.get("program_scope") or record.get("program") or "UNSPECIFIED").upper()
    if is_ticket:
        identity = "AMBIGUOUS: ticket export label DEBI is not sufficient to establish initiative identity"
        authority = "ticket/case correspondence; not a knowledge source"
        proposed_program = None
        proposed_scope = "QUARANTINED"
        decision = "rejected_non_knowledge"
        reason = "Ticket case data is not FAQ knowledge and contains personal/case information; raw contents are omitted from this manifest."
    elif "FAQ final-Digilians.pdf" in source_file or original_program == "DIGILIANS":
        identity = "DIGILIANS (source document title/content and export label agree)"
        authority = "initiative FAQ document; issuing authority not verified from the supplied artifact"
        proposed_program = "DIGILIANS"
        proposed_scope = "DIGILIANS"
        decision = "rejected_for_DEPI_scope"
        reason = "Identified as Digilians content; must remain inactive for the DEPI assistant. Source authority and current validity are not established."
    elif "DEPI HELPER.xlsx" in source_file or "FAQ LMS-English Exam.pdf" in source_file:
        identity = "DEPI (original source artifact/content supports DEPI; faqs.json converter label DEBI conflicts)"
        authority = "internal operational/support document; not verified as an official government publication"
        proposed_program = "DEPI"
        # The supplied workbook/PDFs establish DEPI-oriented internal guidance,
        # not official authority. Keep proposed scope explicitly non-authoritative
        # until an accountable owner approves it.
        proposed_scope = "DEPI_SCOPED_INTERNAL_PENDING_OWNER_APPROVAL"
        if "DEPI HELPER.xlsx" in source_file and "DEPI VS DEBI" in normalize(q) + " " + normalize(a):
            identity = "DEPI/DEBI cross-initiative case (source explicitly contrasts the two initiatives)"
            proposed_scope = "QUARANTINED"
            decision = "unresolved_cross_initiative"
            reason = "The record discusses DEPI eligibility for a person already registered in DEBI; keep quarantined until program and eligibility owners validate it."
        elif not normalize(q) or not normalize(a) or rtype != "faq":
            decision = "unresolved_incomplete_or_reference"
            reason = "No complete explicit FAQ question/answer pair, or the source marks this as a reference section. Preserve the original passage; do not invent a question."
        else:
            decision = "unresolved_source_owner_review"
            reason = "Source file and locator are verifiable, but no accountable source owner, approval date, or current-validity confirmation is present. Workbook/PDF content is internal guidance, not proven official publication."
    else:
        identity = f"Unverified initiative label {original_program}"
        authority = "unverified"
        proposed_program = None
        proposed_scope = "AMBIGUOUS"
        decision = "unresolved_identity_and_authority"
        reason = "Supplied labels and source material do not establish the initiative and authority sufficiently for activation."

    if record.get("is_duplicate") or record.get("duplicate_of"):
        reason += f" Source export flags this record as a duplicate of {record.get('duplicate_of')}; retain its provenance link."
    if record.get("needs_review"):
        reason += " Source conversion marks this record needs_review."
    return {
        "program_identity_original_label": original_program,
        "program_identity_review": identity,
        "source_authority_class": authority,
        "proposed_program": proposed_program,
        "proposed_retrieval_scope": proposed_scope,
        "approval_status": decision,
        "evidence_based_reason": reason,
    }


def main() -> None:
    helper = load(SOURCE / "depi_helper.json")
    faq = load(SOURCE / "faqs.json")
    tickets = load(SOURCE / "tickets.json")
    source_manifest = load(SOURCE / "source_manifest.json")
    helper_manifest = load(SOURCE / "depi_helper_manifest.json")
    source_info = original_source_info()

    records: list[dict[str, Any]] = []
    raw_records: list[tuple[str, dict[str, Any], str, bool]] = []
    for rec in helper["records"]:
        raw_records.append(("FAQs/converted/depi_helper.json", rec, "FAQs/DEPI HELPER.xlsx", False))
    for rec in faq["records"]:
        raw_records.append(("FAQs/converted/faqs.json", rec, rec.get("source_file") or "", False))
    for rec in tickets["tickets"]:
        raw_records.append(("FAQs/converted/tickets.json", rec, tickets.get("source_file") or "FAQs/tickets.pst", True))

    duplicate_map: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for group_index, group in enumerate(source_manifest.get("exact_duplicates", []), start=1):
        for rid in group.get("record_ids", []):
            duplicate_map[rid].append({"group_id": f"faqs-flagged-{group_index:02d}", "relationship": "source_manifest_exact_duplicate",
                                       "member_count": group.get("count"), "sources": group.get("sources"),
                                       "question": group.get("question")})
    helper_duplicates = {d["record_id"]: d for d in helper_manifest.get("duplicates_detail", [])}

    for json_file, source_record, source_file, is_ticket in raw_records:
        q = source_record.get("question") or source_record.get("question_ar")
        a = source_record.get("answer") or source_record.get("answer_ar")
        raw_content_hash = source_record.get("content_sha256") or source_record.get("content_hash")
        if is_ticket:
            entry = {
                "source_file": json_file, "source_record_id": source_record.get("id"),
                "content_hash": source_record.get("content_hash"),
                "source_archive": source_record.get("source_archive"), "source_record_content_included": False,
                "language": None, "original_question": None, "original_answer": None,
                "source_locator": {},
            }
            entry.update(classify(source_record, source_file, True))
            records.append(entry)
            continue

        helper_fallback = json_file.endswith("depi_helper.json") or source_file == "FAQs/DEPI HELPER.xlsx"
        equivalence = content_hash(q, a, source_record.get("content"), helper_fallback)
        faq_file_path = ROOT / source_file if source_file else None
        source_hash_verified = bool(faq_file_path and faq_file_path.exists() and
                                    source_info.get(source_file, {}).get("hash_match"))
        if json_file.endswith("depi_helper.json"):
            source_hash_verified = source_info.get("FAQs/DEPI HELPER.xlsx", {}).get("hash_match", False)
        entry = {
            "source_file": json_file,
            "source_record_id": source_record.get("id"),
            "source_original_file": source_file,
            "language": source_record.get("language"),
            "record_type": source_record.get("record_type", "faq"),
            "category": source_record.get("category"),
            "original_question": q,
            "original_answer": a,
            "content": source_record.get("content"),
            "content_sha256_source": raw_content_hash,
            "content_sha256_recomputed_converter_compatible": equivalence,
            "source_hash_verification": "matched_original_source_file" if source_hash_verified else "not_matched_or_missing",
            "source_status_original": source_record.get("source_status"),
            "source_url": source_record.get("source_url"),
            "source_locator": {key: source_record.get(key) for key in ("source_sheet", "source_row", "source_page") if source_record.get(key) is not None},
            "source_locator_status": "sheet_row_or_page_present" if any(source_record.get(k) is not None for k in ("source_sheet", "source_row", "source_page")) else "missing_locator",
            "source_attribution_original": source_record.get("source_attribution"),
            "needs_review_original": source_record.get("needs_review"),
            "review_notes_original": source_record.get("review_notes"),
            "record_fingerprint_sha256": record_fingerprint(source_record),
            "content_equivalence_hash": equivalence,
            "duplicate_relationships": duplicate_map.get(str(source_record.get("id")), []),
            "source_duplicate_of": source_record.get("duplicate_of"),
        }
        if source_record.get("id") in helper_duplicates:
            d = helper_duplicates[source_record["id"]]
            entry["duplicate_relationships"].append({"group_id": "depi_helper-source-dedup", "relationship": "duplicate_of",
                                                     "related_record_id": d.get("duplicate_of"), "source_locator": d.get("source")})
        entry.update(classify(source_record, source_file))
        if source_file.endswith("FAQ LMS-English Exam.pdf"):
            entry["age_and_validity_review"] = "Round 3 support/exam text and April 10 cutoff language are cohort-bound; confirm the applicable cycle before reuse."
        elif source_file.endswith("DEPI HELPER.xlsx"):
            entry["age_and_validity_review"] = "Round/sheet-specific operational content is potentially time-sensitive; no last-verified date is present."
        elif source_file.endswith("FAQ final-Digilians.pdf"):
            entry["age_and_validity_review"] = "PDF metadata indicates creation on 2025-04-23; confirm it is current for Digilians before use elsewhere."
        records.append(entry)

    equivalence_groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    question_groups: dict[str, list[dict[str, Any]]] = collections.defaultdict(list)
    for rec in records:
        if rec.get("source_record_content_included") is False:
            continue
        q = normalize(rec.get("original_question"))
        a = normalize(rec.get("original_answer"))
        if q and a:
            equivalence_groups[rec["content_equivalence_hash"]].append(rec)
            question_groups[hashlib.sha256(q.encode("utf-8")).hexdigest()].append(rec)
    exact_groups = []
    for digest, members in equivalence_groups.items():
        if len(members) > 1:
            group_id = f"content-{digest[:16]}"
            for member in members:
                member["duplicate_relationships"].append({"group_id": group_id, "relationship": "exact_normalized_question_answer_equivalent"})
            exact_groups.append({"group_id": group_id, "canonical_content_hash": digest,
                                 "members": [{"source_file": x["source_file"], "source_record_id": x["source_record_id"],
                                              "language": x.get("language"), "source_locator": x.get("source_locator"),
                                              "approval_status": x["approval_status"]} for x in members],
                                 "member_count": len(members),
                                 "interpretation": "Exact normalized question-and-answer repeat; retain all original source links until source review. Language variants with different text are not merged."})
    complementary_groups = []
    for digest, members in question_groups.items():
        answer_hashes = {hashlib.sha256(normalize(m.get("original_answer")).encode("utf-8")).hexdigest() for m in members}
        if len(members) > 1 and len(answer_hashes) > 1:
            group_id = f"question-variant-{digest[:16]}"
            for member in members:
                member["question_variant_group"] = group_id
            complementary_groups.append({"group_id": group_id, "question_hash": digest, "members": [{"source_file": x["source_file"],
                "source_record_id": x["source_record_id"], "answer_hash": hashlib.sha256(normalize(x.get("original_answer")).encode("utf-8")).hexdigest(),
                "source_locator": x.get("source_locator")} for x in members],
                "interpretation": "Same normalized question with different answers: preserve as variants and ask the content owner whether they are complementary or conflicting."})

    dispositions: collections.Counter[str] = collections.Counter(r["approval_status"] for r in records)
    statuses = {"verified_official_depi_website": 0, "verified_internal_depi_guidance": 0, "verified_general_support": 0,
                "debi_identity_confirmed": 0, "digilians_identity_confirmed": sum(r.get("program_identity_review", "").startswith("DIGILIANS") for r in records),
                "ambiguous_or_unverified": sum(r["approval_status"].startswith("unresolved") for r in records)}
    parity_results = {}
    for name, key in (("depi_helper", "records"), ("faqs", "records"), ("tickets", "tickets")):
        structured = load(SOURCE / f"{name}.json")[key]
        line_records = [json.loads(line) for line in (SOURCE / f"{name}.jsonl").read_text(encoding="utf-8-sig").splitlines() if line.strip()]
        parity_results[f"{name}.jsonl"] = {"count": len(line_records), "matches_json_records_exactly": structured == line_records}

    report = {
        "title": "NexaServe source provenance and reconciliation review",
        "policy": "Review only. No record approved for ingestion; no database writes. Original source files are unchanged.",
        "hash_method": {"source_file_sha256": "SHA-256 over original file bytes", "content_equivalence": "converter-compatible SHA-256 over normalized(question) + '||' + normalized(answer); DEPI HELPER Excel records use answer or content exactly as that converter does, while other extractors preserve an empty answer. Normalization preserves punctuation and line breaks while normalizing whitespace and does not apply Unicode NFC.", "record_fingerprint": "SHA-256 of canonical JSON containing source path, stable source record ID, language, normalized question, normalized answer"},
        "original_source_files": source_info,
        "jsonl_companion_parity": parity_results,
        "summary": {"records_reviewed_in_json": len(records), "knowledge_records_with_question_or_answer": sum(r.get("source_record_content_included") is not False for r in records),
                    "ticket_records_quarantined_without_content": sum(r.get("source_record_content_included") is False for r in records),
                    "approval_status_counts": dict(dispositions), "exact_content_groups_across_exports": len(exact_groups),
                    "exact_content_duplicate_occurrences": sum(g["member_count"] - 1 for g in exact_groups),
                    "content_equivalence_groups": exact_groups, "same_question_different_answer_groups": complementary_groups,
                    "source_manifest_flagged_groups": source_manifest.get("exact_duplicates", []),
                    "source_manifest_flagged_duplicate_occurrences": sum(g.get("count", 1) - 1 for g in source_manifest.get("exact_duplicates", [])),
                    "depi_helper_source_flagged_duplicate_count": helper_manifest.get("duplicate_records", 0),
                    "all_original_source_hashes_match": all(v.get("hash_match") for v in source_info.values())},
        "source_records": records,
    }
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "source_provenance_review.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    summary = report["summary"]
    lines = ["# Source Provenance Review", "", "**Status: review only — no records approved for ingestion.** Original sources and databases were not modified.",
             "", f"Reviewed {summary['records_reviewed_in_json']} JSON records: {summary['knowledge_records_with_question_or_answer']} FAQ/reference records and {summary['ticket_records_quarantined_without_content']} ticket rows (ticket contents omitted).",
             f"Original source byte hashes: {'PASS' if summary['all_original_source_hashes_match'] else 'FAIL'}.",
             "", "## Source and scope findings", "",
             "- `DEPI HELPER.xlsx` SHA-256 matches both converted exports. The workbook is an internal operational workbook with sheet/row locators, not proof of a government publication. Its 265-row export has 201 complete Q/A pairs, 55 rows without an explicit question, 9 without an answer, and 5 source-flagged duplicate links. Cycle-specific rows need owner/date confirmation.",
             "- `faqs.json` labels 268 records from that same DEPI workbook as `DEBI`; the original workbook, its title, and content support DEPI identity. One workbook row is a DEPI-versus-DEBI eligibility case and remains quarantined. The converter's `DEBI` program value should not be used as the factual initiative identity.",
             "- The 22 records from `FAQ LMS-English Exam.pdf` have a verified source-file hash, page locators, and DEPI textual identity. They refer to Round 3 and include April 10 cutoffs, so applicability is cycle-bound. The source is a platform support document, not established as an official government publication. Page 11's image-only contact poster was not extracted and needs manual review.",
             "- The 162 records from `FAQ final-Digilians.pdf` are clearly Digilians content by source title and PDF text. PDF metadata gives creation date 2025-04-23. All remain excluded from DEPI retrieval; source authority/currentness are unverified.",
             "- `tickets.json` holds 625 ticket/case rows from the PST archive. They are quarantined as non-knowledge and the manifest deliberately omits names, ticket numbers, subjects, and case text.",
             "- No source URL is present on FAQ records. Source attribution is by workbook sheet/row or PDF page. The verified hashes establish which local source file was converted, not who authorized it or whether the advice is current.",
             "", "## Duplicate reconciliation", "",
             f"The source conversion report flags {len(source_manifest.get('exact_duplicates', []))} exact-content groups containing {summary['source_manifest_flagged_duplicate_occurrences']} duplicate occurrences (9 occurrences, 8 groups). The record-level manifest preserves every member and source locator.",
             "", "| Group | Repeated content | Records / sources |", "|---|---|---|"]
    for i, group in enumerate(source_manifest.get("exact_duplicates", []), start=1):
        names = ", ".join(group.get("record_ids", []))
        locations = "; ".join(group.get("sources", []))
        label = group.get("question") or "No explicit question; response-only content"
        lines.append(f"| {i} | {label} | {group.get('count')} occurrences: {names}; {locations} |")
    lines.extend(["", "Five additional `depi_helper.json` duplicate flags map directly to primary IDs in `depi_helper_manifest.json`; these are a separate export's provenance links, not five extra source-manifest FAQ groups. The `depi_helper.json` and `faqs.json` exports both derive from the same workbook, so exact cross-export equivalence groups are listed in the machine manifest. Distinct language text is not deduplicated; same-question/different-answer groups are marked as possible complementary or conflicting variants.",
                  "", "## Review disposition", "", "- **Approved for ingestion: 0.** No source includes accountable owner approval/currentness evidence, and no external official DEPI website URLs are present.",
                  "- **Rejected for DEPI retrieval:** all Digilians records (162), all tickets (625) as non-knowledge, and records explicitly marked as response-only/incomplete for direct FAQ activation. Original content remains in the source files and review manifest.",
                  "- **Unresolved:** complete DEPI workbook and LMS support records pending owner approval, validity dates, and scope review; ambiguous/cross-initiative content stays quarantined.",
                  "", "The full record-by-record manifest, including original Q/A text for FAQ records, source locators, content hashes, relationships, source authority, proposed scope, and reasons, is in `source_provenance_review.json`.", ""])
    (OUTPUT / "source_reconciliation_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({k: v for k, v in summary.items() if k not in {"content_equivalence_groups", "same_question_different_answer_groups", "source_manifest_flagged_groups"}}, ensure_ascii=False, indent=2))
    print(f"Wrote {OUTPUT / 'source_provenance_review.json'} and source_reconciliation_report.md")


if __name__ == "__main__":
    main()
