#!/usr/bin/env python3
"""Generate a non-approving, record-level source approval queue."""
from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "knowledge_ingestion"


def read_json(name: str):
    return json.loads((DOCS / name).read_text(encoding="utf-8-sig"))


def disposition(record: dict) -> tuple[str, str, str, str]:
    source = record.get("source_original_file") or record.get("source_file", "")
    status = record.get("approval_status", "")
    if record.get("source_record_content_included") is False:
        return ("EXCLUDE_NON_KNOWLEDGE", "Operational ticket/case correspondence, not an FAQ source.",
                "No FAQ approval can convert ticket records directly into a knowledge corpus.",
                "Keep outside RAG. Any separately curated technical-support article must be de-identified, rewritten, source-attributed, and approved by a support owner.")
    if "FAQ final-Digilians.pdf" in source or status == "rejected_for_DEPI_scope":
        return ("OUT_OF_SCOPE_FOR_DEPI", "Source identifies Digilians; the DEPI assistant must not retrieve it.",
                "No evidence is missing for the DEPI exclusion; authority and current validity remain unverified for any Digilians assistant.",
                "Exclude from DEPI. For a separate Digilians knowledge base, obtain accountable owner approval, official/current source evidence, effective date, and dedicated scope mapping.")
    if status == "unresolved_cross_initiative":
        return ("QUARANTINE_SCOPE_DECISION", "Explicit DEPI/DEBI cross-initiative eligibility content.",
                "Initiative boundary and eligibility owner decision are missing.",
                "Obtain written DEPI and DEBI owner decision on the exact question, eligibility rule, audience, effective period, and which assistant may retrieve it.")
    if status == "unresolved_incomplete_or_reference":
        return ("MANUAL_CONTENT_REVIEW", "Incomplete Q/A or reference-section record; preserve source passage without inventing a question.",
                "A complete approved question/answer and record type are missing; time-sensitive records also lack current-validity confirmation.",
                "Owner must supply or approve an explicit question, answer, FAQ/reference classification, effective dates, and the intended initiative/scope; otherwise exclude.")
    if status == "unresolved_source_owner_review":
        return ("NEEDS_OWNER_APPROVAL", "Complete FAQ-like source record, but supplied artifacts establish source identity rather than authority or current approval.",
                "Accountable owner, approval evidence, effective/expiry or last-verified date, and final retrieval scope are absent; no source URL is present.",
                "Owner must confirm wording, initiative/audience, authority, effective dates, and retrieval scope; provide a stable official URL or signed internal source reference and approval identity/date.")
    return ("UNRESOLVED_IDENTITY_AND_AUTHORITY", record.get("evidence_based_reason", "Identity and authority not established."),
            "Verified initiative, accountable authority, and intended retrieval scope are absent.",
            "Identify source owner and initiative; provide authoritative source reference, effective dates, and scope decision, or exclude.")


def main() -> None:
    provenance = read_json("source_provenance_review.json")
    inventory = read_json("source_inventory.json")
    output = []
    for rec in provenance["source_records"]:
        disposition_code, rationale, missing, evidence = disposition(rec)
        source = (rec.get("source_original_file") or rec.get("source_archive")
                  or rec.get("source_file", ""))
        content_hash = rec.get("content_sha256_source") or rec.get("content_hash")
        q, a = rec.get("original_question"), rec.get("original_answer")
        locator = rec.get("source_locator", {})
        if not locator and rec.get("source_archive"):
            # Ticket text and identifying metadata stay omitted; archive plus stable
            # converted record ID is sufficient to locate the quarantined item.
            locator = {"source_archive": rec["source_archive"], "source_record_id": rec.get("source_record_id")}
        duplicate_links = rec.get("duplicate_relationships", [])
        duplicate_flags = []
        if duplicate_links:
            duplicate_flags.append("duplicate_reconciliation_required")
        if rec.get("source_duplicate_of"):
            duplicate_flags.append("source_export_duplicate_pointer")
        row = {
            "source_json": rec.get("source_file"), "source_record_id": rec.get("source_record_id"),
            "source_original_file": source, "source_locator": locator,
            "original_content_hash": content_hash, "original_question": q,
            "original_answer": a, "question_available": bool(q), "answer_available": bool(a),
            "program_identity_original_label": rec.get("program_identity_original_label"),
            "program_identity_review": rec.get("program_identity_review"),
            "source_authority_class": rec.get("source_authority_class"),
            "proposed_retrieval_scope": rec.get("proposed_retrieval_scope"),
            "source_status_original": rec.get("source_status_original"),
            "source_url": rec.get("source_url"), "approval_status": rec.get("approval_status"),
            "recommended_disposition": disposition_code, "record_rationale": rationale,
            "missing_evidence": missing, "approval_evidence_needed": evidence,
            "additional_review_flags": duplicate_flags,
            "duplicate_relationships": duplicate_links,
            "content_sha256_source_vs_recomputed": {
                "source": rec.get("content_sha256_source"),
                "recomputed": rec.get("content_sha256_recomputed_converter_compatible"),
            },
        }
        output.append(row)

    counts = Counter(r["recommended_disposition"] for r in output)
    metadata = [
        {"path": f["relative_path"], "format": f["format"], "records": f["record_count"],
         "disposition": f["disposition"], "reason": f["disposition_reason"]}
        for f in inventory["files"] if f["disposition"] == "skipped_metadata"
    ]
    queue = {
        "title": "NexaServe source approval queue",
        "status": "review only; no records approved",
        "record_count": len(output), "recommended_disposition_counts": dict(counts),
        "metadata_files_skipped": metadata,
        "jsonl_policy": "JSONL companions are retained for parity verification and are not separate queue/import datasets.",
        "records": output,
    }
    (DOCS / "source_approval_queue.json").write_text(json.dumps(queue, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = ["# Record-Level Source Rationale and Approval Queue", "",
             "**Review only. No records are approved or imported.** This queue includes every structured source record; JSONL companions are used for parity checks and are not counted as additional import datasets.", "",
             f"Queue size: **{len(output)} records**. Recommended dispositions: " + "; ".join(f"`{k}` {v}" for k, v in sorted(counts.items())) + ".", "",
             "## Source groups and common evidence gaps", "",
             "| Original source | Record count | Identity and authority | Retrieval treatment | Evidence needed |", "|---|---:|---|---|---|"]
    group_rows = [
        ("FAQs/DEPI HELPER.xlsx", "265 helper export rows plus 268 overlapping workbook-origin rows in faqs.json", "DEPI-labelled workbook / internal operational support; workbook hash and sheet-row locators establish file lineage, not official status", "Complete explicit FAQ records are NEEDS_OWNER_APPROVAL; incomplete, cross-initiative, and duplicate rows stay separately gated", "Accountable DEPI owner, wording/scope approval, current/effective date, stable official or signed internal reference; determine each round-bound rule's currentness"),
        ("FAQs/FAQ LMS-English Exam.pdf", "22 records", "DEPI support/exam document; PDF hash and page locators establish lineage, not a government issuing authority", "Complete explicit FAQs NEEDS_OWNER_APPROVAL; reference sections/manual omissions need review", "LMS/platform owner approval, current cycle, effective dates; inspect image-only page 11 contact poster manually"),
        ("FAQs/FAQ final-Digilians.pdf", "162 records", "Digilians by document title/content; issuing authority not established", "OUT_OF_SCOPE_FOR_DEPI", "For a separate Digilians assistant only: owner, authority, currentness, and scope evidence"),
        ("FAQs/tickets.pst", "625 ticket rows", "Operational correspondence; ticket export label DEBI does not prove initiative identity", "EXCLUDE_NON_KNOWLEDGE; source contents withheld from this report", "Do not approve raw ticket rows. A separately curated, de-identified support article needs a support owner and verified platform source"),
        ("Converted manifests", "3 metadata files; zero knowledge rows", "Conversion metadata only", "Skip as non-knowledge metadata", "No knowledge approval applies"),
    ]
    lines.extend("| " + " | ".join(row) + " |" for row in group_rows)
    lines += ["", "## Category decisions", "",
              "- **Verified official DEPI content:** none established. A matching file hash and DEPI label prove neither issuing authority nor current approval.",
              "- **DEPI-specific internal operational guidance:** workbook and LMS PDF content are DEPI-oriented, but remain `NEEDS_OWNER_APPROVAL` when complete; round-bound items need effective dates and currentness decisions.",
              "- **Verified general technical support:** none established from the supplied knowledge sources. Ticket cases are operational data, not verified reusable support articles.",
              "- **DEBI content:** no source group is verified as DEBI knowledge. The DEBI field on workbook-derived faqs records conflicts with source content; the explicit DEPI-vs-DEBI eligibility case is quarantined pending both owners. Ticket labels are not treated as evidence.",
              "- **Digilians content:** 162 records are clearly Digilians and excluded from DEPI retrieval; this does not approve them for a Digilians assistant.",
              "- **Ambiguous/incomplete/stale/duplicate/unverified:** handled record by record below and in the machine-readable queue. Duplicate equivalence is a review relationship, not an approval or deletion.",
              "- **Metadata and operational data:** three manifests are metadata; 625 PST rows are excluded as case data. JSONL companions remain unchanged for parity verification.",
              "", "## Record-by-record rationale", "",
              "The table lists every structured record without reproducing ticket text or personal data. Hashes are converter-supplied original content hashes where available. The full structured Q/A text for FAQ rows, provenance fields, duplicate links, and all dispositions are in `source_approval_queue.json` and `source_provenance_review.json`.", "",
              "| Source | Record ID | Locator | Hash | Q/A | Identity / scope | Status and exact rationale | Missing evidence / approval decision |", "|---|---|---|---|---|---|---|---|"]
    def safe(value):
        if value is None: return "—"
        if isinstance(value, dict): value = ", ".join(f"{k}={v}" for k,v in value.items()) or "—"
        elif isinstance(value, list): value = "; ".join(str(x.get("group_id", x)) for x in value) or "—"
        return str(value).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
    for row in output:
        qa = f"Q:{'yes' if row['question_available'] else 'no'}, A:{'yes' if row['answer_available'] else 'no'}"
        identity_scope = f"{row['program_identity_review']} / {row['proposed_retrieval_scope']}"
        status = f"{row['recommended_disposition']}: {row['record_rationale']}"
        if row["additional_review_flags"]:
            status += " Additional hold: " + ", ".join(row["additional_review_flags"])
        missing = row["missing_evidence"] + " Approval: " + row["approval_evidence_needed"]
        lines.append("| " + " | ".join(safe(x) for x in (row["source_original_file"], row["source_record_id"], row["source_locator"], row["original_content_hash"], qa, identity_scope, status, missing)) + " |")
    lines += ["", "## Approval rule", "",
              "Only a human reviewer may move a record out of quarantine. Each approval must cite the queue's source record ID and locator, content hash, initiative and retrieval scope, owner decision, source reference, and effective/last-verified date. Incomplete records and duplicate members must be resolved explicitly. The existing ingestion planner remains fail-closed.", ""]
    (DOCS / "record_level_rationale_report.md").write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"records": len(output), "counts": counts, "report": str(DOCS / "record_level_rationale_report.md"), "queue": str(DOCS / "source_approval_queue.json")}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
