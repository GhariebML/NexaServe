#!/usr/bin/env python3
"""Reconcile explicit Excel review decisions into a fail-closed ledger proposal.

This script reads the review workbook, source approval queue, current converted
JSON datasets, original-source hashes, and the original ledger schema. It never
imports data into a database and never edits the workbook or input ledger.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import re
import sys
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker
from openpyxl import load_workbook

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "knowledge_ingestion"
DEFAULTS = {
    "workbook": DOCS / "DEPI_Content_Approval_Review.xlsx",
    "queue": DOCS / "source_approval_queue.json",
    "source_ledger": DOCS / "content_approval_ledger.json",
    "provenance": DOCS / "source_provenance_review.json",
    "output_ledger": DOCS / "content_approval_ledger.reviewed.json",
    "report": DOCS / "content_approval_ledger_reconciliation.md",
}
REVIEW_SHEETS = ["Owner Approval Queue", "Manual Content Review", "Scope Decisions", "Out of Scope"]
REQUIRED_HEADERS = [
    "Stable Source Record ID", "Source JSON Path", "Original Source File", "Original Source Locator",
    "Source URL", "Content Hash", "Question", "Answer", "Language", "Current Program Label",
    "Reviewed Program Identity", "Proposed Program", "Proposed Retrieval Scope",
    "Source Authority Classification", "Current Review Status", "Exact Review Rationale",
    "Missing Provenance / Scope Evidence", "Evidence Required to Resolve", "Duplicate / Relationship IDs",
    "Reviewer Decision", "Reviewer Identity / Responsible Role", "Decision Date (UTC)",
    "Approval Evidence / Decision Reference", "Reviewer Rationale",
]
DECISION_HEADER = "Reviewer Decision"
REVIEW_METADATA_HEADERS = [
    "Reviewer Identity / Responsible Role", "Decision Date (UTC)",
    "Approval Evidence / Decision Reference", "Reviewer Rationale",
]
APPROVED = {"APPROVED_OFFICIAL_DEPI", "APPROVED_INTERNAL_DEPI_GUIDANCE", "APPROVED_GENERAL_SUPPORT"}
NON_APPROVALS = {"OUT_OF_SCOPE", "REJECTED", "NEEDS_MORE_EVIDENCE", "NEEDS_OWNER_APPROVAL"}
DECISIONS = APPROVED | NON_APPROVALS


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def safe_workspace_path(relative_path: str) -> Path:
    path = (ROOT / relative_path).resolve()
    try:
        path.relative_to(ROOT.resolve())
    except ValueError as exc:
        raise ValueError("A source dataset path resolves outside the NexaServe workspace") from exc
    return path


def sha256_file(path: Path) -> str | None:
    if not path.is_file():
        return None
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def normalize_faq_whitespace(value: Any) -> str:
    if not value:
        return ""
    text = str(value).replace("\u00a0", " ").replace("\ufeff", "")
    text = re.sub(r"\r\n?", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    lines = [re.sub(r"[ \t]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(lines).strip()


def compute_current_content_hash(dataset: str, record: dict[str, Any],
                                 source_original_file: str | None = None) -> str | None:
    """Recompute hashes using the converter rule for the record's original source.

    FAQ exports contain records from multiple extractors. DEPI HELPER Excel
    hashes ``question||answer-or-content``; PDF and Digilians FAQ extractors
    hash the persisted question and answer fields, including an empty answer.
    """
    if dataset.endswith("depi_helper.json"):
        content = record.get("content")
        if content is None:
            return None
        basis = str(content)
    elif dataset.endswith("faqs.json"):
        question = record.get("question") if record.get("question") is not None else record.get("question_ar", "")
        answer = record.get("answer") if record.get("answer") is not None else record.get("answer_ar")
        if source_original_file == "FAQs/DEPI HELPER.xlsx":
            answer = answer or record.get("content", "")
        elif answer is None:
            answer = ""
        basis = f"{normalize_faq_whitespace(question)}||{normalize_faq_whitespace(answer)}"
    elif dataset.endswith("tickets.json"):
        basis = "||".join(str(record.get(key) or "") for key in ("ticket_number", "subject", "description", "student_name"))
    else:
        return None
    return hashlib.sha256(basis.encode("utf-8")).hexdigest()


def load_current_source_index(queue_records: list[dict], provenance: dict) -> tuple[dict, dict]:
    dataset_refs: dict[str, list[dict]] = defaultdict(list)
    for item in queue_records:
        dataset_refs[item["source_json"]].append(item)
    original_file_hashes = {}
    for original_path, info in provenance.get("original_source_files", {}).items():
        actual = sha256_file(safe_workspace_path(original_path))
        original_file_hashes[original_path] = {
            "expected": info.get("sha256_expected"),
            "actual": actual,
            "matches": bool(actual and actual == info.get("sha256_expected")),
        }

    index: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for dataset, references in dataset_refs.items():
        data = read_json(safe_workspace_path(dataset))
        record_key = "tickets" if dataset.endswith("tickets.json") else "records"
        current_records = data.get(record_key)
        if not isinstance(current_records, list):
            raise ValueError(f"Current dataset has no expected record list: {dataset}")
        by_id: dict[str, list[dict]] = defaultdict(list)
        for record in current_records:
            if isinstance(record, dict) and record.get("id") is not None:
                by_id[str(record["id"])].append(record)
        for ref in references:
            identity = (dataset, str(ref["source_record_id"]))
            for record in by_id.get(identity[1], []):
                original_file = ref.get("source_original_file")
                current_hash = compute_current_content_hash(dataset, record, original_file)
                source_digest = original_file_hashes.get(original_file, {}).get("matches", False)
                source_sha = record.get("source_sha256")
                if dataset.endswith("depi_helper.json"):
                    source_sha = data.get("source_file_sha256")
                elif dataset.endswith("tickets.json"):
                    source_sha = data.get("source_file_sha256")
                source_sha_matches = True if source_sha is None else source_sha == original_file_hashes.get(original_file, {}).get("actual")
                index[identity].append({
                    "content_hash": current_hash,
                    "original_source_file": original_file,
                    "source_file_hash_matches": source_digest and source_sha_matches,
                    "question": record.get("question") or record.get("question_ar"),
                    "answer": record.get("answer") or record.get("answer_ar"),
                    "language": record.get("language"),
                    "source_locator": {
                        key: record.get(key) for key in ("source_sheet", "source_row", "source_page")
                        if record.get(key) is not None
                    },
                })
    return index, original_file_hashes


def read_workbook_decisions(path: Path) -> tuple[list[dict], list[dict]]:
    wb = load_workbook(path, read_only=True, data_only=False)
    try:
        missing_sheets = [name for name in REVIEW_SHEETS if name not in wb.sheetnames]
        if missing_sheets:
            raise ValueError(f"Workbook missing expected review sheet(s): {', '.join(missing_sheets)}")
        rows: list[dict] = []
        layout_errors: list[dict] = []
        for sheet_name in REVIEW_SHEETS:
            ws = wb[sheet_name]
            # Sequential iteration is essential for openpyxl's read-only mode;
            # random cell access repeatedly reparses the worksheet XML.
            header_values = next(ws.iter_rows(min_row=4, max_row=4, values_only=True), ())
            headers = list(header_values)
            duplicate_headers = sorted({h for h in headers if h and headers.count(h) > 1})
            missing_headers = [h for h in REQUIRED_HEADERS if h not in headers]
            if duplicate_headers or missing_headers:
                layout_errors.append({"sheet": sheet_name, "missing_headers": missing_headers, "duplicate_headers": duplicate_headers})
                continue
            col_index = {h: headers.index(h) for h in REQUIRED_HEADERS}
            for row_number, values in enumerate(ws.iter_rows(min_row=5, values_only=True), start=5):
                cells = {header: values[col] if col < len(values) else None for header, col in col_index.items()}
                if not any(value is not None and value != "" for value in cells.values()):
                    continue
                cells["_sheet"] = sheet_name
                cells["_row"] = row_number
                rows.append(cells)
        return rows, layout_errors
    finally:
        wb.close()


def parse_reviewer_identity_role(value: Any) -> tuple[str | None, str | None]:
    if not isinstance(value, str):
        return None, None
    match = re.fullmatch(r"\s*Reviewer identity:\s*(.+?)\s*;\s*Role:\s*(.+?)\s*", value, flags=re.IGNORECASE)
    if not match:
        return None, None
    identity, role = match.group(1).strip(), match.group(2).strip()
    return (identity or None), (role or None)


def parse_utc_timestamp(value: Any) -> str | None:
    if isinstance(value, datetime):
        if value.tzinfo is None:
            # Workbook header explicitly says UTC; naive datetimes are interpreted as UTC.
            parsed = value.replace(tzinfo=timezone.utc)
        else:
            parsed = value.astimezone(timezone.utc)
        if parsed.hour == parsed.minute == parsed.second == parsed.microsecond == 0:
            return None
        return parsed.isoformat(timespec="seconds").replace("+00:00", "Z")
    if isinstance(value, date):
        return None
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        parsed = datetime.fromisoformat(text[:-1] + "+00:00" if text.endswith("Z") else text)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None or parsed.utcoffset().total_seconds() != 0:
        return None
    return parsed.astimezone(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def clean_cell(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def source_row_integrity(row: dict, queue_record: dict, current: dict) -> list[str]:
    mismatches = []
    comparisons = [
        ("Original Source File", queue_record.get("source_original_file")),
        ("Question", queue_record.get("original_question")),
        ("Answer", queue_record.get("original_answer")),
        ("Language", queue_record.get("language")),
    ]
    for header, expected in comparisons:
        actual = row.get(header)
        if actual != expected:
            mismatches.append(header)
    try:
        locator = json.loads(row.get("Original Source Locator") or "{}")
    except (TypeError, json.JSONDecodeError):
        locator = None
    if locator != (queue_record.get("source_locator") or {}):
        mismatches.append("Original Source Locator")
    if row.get("Source JSON Path") != queue_record.get("source_json"):
        mismatches.append("Source JSON Path")
    if current:
        if row.get("Question") != current.get("question"):
            mismatches.append("current source Question")
        if row.get("Answer") != current.get("answer"):
            mismatches.append("current source Answer")
        if row.get("Language") != current.get("language"):
            mismatches.append("current source Language")
    return mismatches


def official_https_url(value: Any) -> bool:
    if not isinstance(value, str):
        return False
    parsed = urlparse(value.strip())
    host = (parsed.hostname or "").lower().rstrip(".")
    return parsed.scheme.lower() == "https" and bool(host) and (host == "gov.eg" or host.endswith(".gov.eg"))


def approval_evidence_errors(row: dict, decision: str, role: str | None) -> list[str]:
    errors = []
    program = (clean_cell(row.get("Proposed Program")) or "").upper()
    identity = (clean_cell(row.get("Reviewed Program Identity")) or "").upper()
    authority = (clean_cell(row.get("Source Authority Classification")) or "").casefold()
    scope = (clean_cell(row.get("Proposed Retrieval Scope")) or "").upper()
    source_status = (clean_cell(row.get("Current Review Status")) or "").upper()
    reviewer_role = (role or "").casefold()
    source_url = clean_cell(row.get("Source URL"))
    evidence_ref = clean_cell(row.get("Approval Evidence / Decision Reference")) or ""

    if decision in APPROVED and source_status == "EXCLUDE_NON_KNOWLEDGE":
        errors.append("ticket/case data cannot be directly approved as knowledge")
    if decision == "APPROVED_OFFICIAL_DEPI":
        if program != "DEPI" or "DEPI" not in identity:
            errors.append("verified DEPI program identity is required")
        if not official_https_url(source_url):
            errors.append("Source URL must be a verifiable HTTPS official .gov.eg URL")
        if "official" not in authority or "verified" not in authority:
            errors.append("Source Authority Classification must explicitly state verified official DEPI content")
        if not ("authorized" in reviewer_role and "depi" in reviewer_role and "owner" in reviewer_role):
            errors.append("reviewer role must identify an authorized DEPI owner")
        if not evidence_ref:
            errors.append("official-source verification evidence reference is required")
    elif decision == "APPROVED_INTERNAL_DEPI_GUIDANCE":
        if program != "DEPI" or "DEPI" not in identity:
            errors.append("DEPI program identity is required")
        if "internal" not in authority:
            errors.append("source must be explicitly classified as internal guidance, not official publication")
        if not ("authorized" in reviewer_role and "depi" in reviewer_role and "owner" in reviewer_role):
            errors.append("reviewer role must identify an authorized DEPI content owner")
        if not evidence_ref.casefold().startswith("owner_approval:"):
            errors.append("evidence reference must identify the explicit owner approval (OWNER_APPROVAL:...)")
        if not ("DEPI_SCOPED" in scope or scope == "DEPI_AUTHORITATIVE"):
            errors.append("DEPI retrieval scope must be explicit")
    elif decision == "APPROVED_GENERAL_SUPPORT":
        if scope != "GENERAL_SUPPORT":
            errors.append("proposed retrieval scope must be GENERAL_SUPPORT")
        if "verified" not in authority or "support" not in authority:
            errors.append("source authority must identify verified general technical support")
        if not official_https_url(source_url) and not (source_url and source_url.lower().startswith("https://")):
            errors.append("Source URL must be an HTTPS source for the supported platform")
        if not ("authorized" in reviewer_role and "owner" in reviewer_role and ("support" in reviewer_role or "platform" in reviewer_role)):
            errors.append("reviewer role must identify an authorized support or platform owner")
        if not evidence_ref.casefold().startswith(("support_source:", "support_approval:")):
            errors.append("evidence reference must identify verified support evidence (SUPPORT_SOURCE:... or SUPPORT_APPROVAL:...)")
    return errors


def _schema_parts(source_ledger: dict) -> tuple[dict, set[str]]:
    schema = source_ledger["schema"]
    item_schema = schema["properties"]["entries"]["items"]
    enum = set(item_schema["properties"]["decision"]["enum"])
    return schema, enum


def reconcile_decisions(rows: list[dict], queue_records: list[dict], current_index: dict,
                        allowed_decisions: set[str]) -> dict:
    queue_by_id: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for record in queue_records:
        queue_by_id[(record["source_json"], str(record["source_record_id"]))].append(record)
    workbook_by_id: dict[tuple[str | None, str | None], list[dict]] = defaultdict(list)
    for row in rows:
        key = (clean_cell(row.get("Source JSON Path")), clean_cell(row.get("Stable Source Record ID")))
        if key[0] or key[1]:
            workbook_by_id[key].append(row)

    found = Counter()
    explicit_rejected = 0
    explicit_out_of_scope = 0
    validated = Counter()
    approved = Counter()
    rejected = 0
    out_of_scope = 0
    incomplete: list[dict] = []
    invalid: list[dict] = []
    unknown: list[dict] = []
    ambiguous: list[dict] = []
    stale: dict[tuple[str, str], dict] = {}
    duplicates: list[dict] = []
    missing_evidence: list[dict] = []
    ledger_entries = []
    unreviewed = 0
    source_integrity_mismatch: set[str] = set()

    # Detect source drift for every queued record, whether reviewed or not.
    for key, candidates in queue_by_id.items():
        current_candidates = current_index.get(key, [])
        if len(candidates) != 1 or len(current_candidates) != 1:
            if current_candidates or len(candidates) > 1:
                stale[key] = {"source_dataset": key[0], "source_record_id": key[1], "reason": "ambiguous current source identity"}
            continue
        expected = candidates[0].get("original_content_hash")
        actual = current_candidates[0].get("content_hash")
        source_file_matches = current_candidates[0].get("source_file_hash_matches")
        if not expected or actual != expected or not source_file_matches:
            if not expected or actual != expected:
                reason = "current source content hash differs from the review snapshot"
            elif not source_file_matches:
                reason = "original source file SHA-256 differs from the provenance snapshot"
            else:
                reason = "current source integrity could not be verified"
            stale[key] = {
                "source_dataset": key[0], "source_record_id": key[1],
                "workbook_queue_hash": expected, "current_source_hash": actual,
                "reason": reason,
            }
            source_integrity_mismatch.add(key[0])

    for key, matches in workbook_by_id.items():
        if len(matches) > 1:
            touched = any(clean_cell(row.get(DECISION_HEADER)) or any(clean_cell(row.get(h)) for h in REVIEW_METADATA_HEADERS) for row in matches)
            if touched:
                duplicates.append({"source_dataset": key[0], "source_record_id": key[1], "rows": [f"{r['_sheet']}!{r['_row']}" for r in matches]})

    for row in rows:
        decision_raw = row.get(DECISION_HEADER)
        decision = clean_cell(decision_raw)
        meta_present = any(clean_cell(row.get(h)) for h in REVIEW_METADATA_HEADERS)
        if not decision and not meta_present:
            unreviewed += 1
            continue
        identity = clean_cell(row.get("Source JSON Path"))
        record_id = clean_cell(row.get("Stable Source Record ID"))
        key = (identity or "", record_id or "")
        if decision:
            found[decision] += 1
        if not decision:
            incomplete.append({"source_dataset": identity, "source_record_id": record_id, "row": f"{row['_sheet']}!{row['_row']}", "missing_fields": [DECISION_HEADER]})
            continue
        if decision not in allowed_decisions:
            invalid.append({"source_dataset": identity, "source_record_id": record_id, "decision": decision, "row": f"{row['_sheet']}!{row['_row']}", "reason": "decision is not in the existing ledger schema enum"})
            continue
        if decision == "REJECTED":
            explicit_rejected += 1
        elif decision == "OUT_OF_SCOPE":
            explicit_out_of_scope += 1
        candidates = queue_by_id.get(key, [])
        if len(candidates) == 0:
            unknown.append({"source_dataset": identity, "source_record_id": record_id, "row": f"{row['_sheet']}!{row['_row']}"})
            continue
        if len(candidates) != 1 or len(current_index.get(key, [])) != 1:
            ambiguous.append({"source_dataset": identity, "source_record_id": record_id, "row": f"{row['_sheet']}!{row['_row']}"})
            continue
        if len(workbook_by_id.get(key, [])) > 1:
            continue  # every repeated identity is withheld, including identical duplicate decisions
        source = candidates[0]
        current = current_index[key][0]
        row_hash = clean_cell(row.get("Content Hash"))
        queue_hash = source.get("original_content_hash")
        if key in stale or row_hash != queue_hash:
            if key not in stale:
                stale[key] = {"source_dataset": identity, "source_record_id": record_id, "workbook_hash": row_hash, "current_source_hash": current.get("content_hash"), "reason": "workbook content hash differs from current source"}
            continue
        mismatch_fields = source_row_integrity(row, source, current)
        if mismatch_fields:
            invalid.append({"source_dataset": identity, "source_record_id": record_id, "row": f"{row['_sheet']}!{row['_row']}", "reason": "source identity/content cells changed: " + ", ".join(mismatch_fields)})
            continue

        reviewer_identity, reviewer_role = parse_reviewer_identity_role(row.get("Reviewer Identity / Responsible Role"))
        timestamp = parse_utc_timestamp(row.get("Decision Date (UTC)"))
        rationale = clean_cell(row.get("Reviewer Rationale"))
        evidence = clean_cell(row.get("Approval Evidence / Decision Reference"))
        missing = []
        if not reviewer_identity:
            missing.append("Reviewer identity/role must use `Reviewer identity: <name>; Role: <role>`")
        if not reviewer_role:
            missing.append("Reviewer role")
        if not timestamp:
            missing.append("Decision Timestamp (UTC, including time; date-only values are incomplete)")
        if not rationale:
            missing.append("Reviewer Rationale")
        if not evidence:
            missing.append("Approval Evidence / Decision Reference")
        evidence_errors = approval_evidence_errors(row, decision, reviewer_role)
        if evidence_errors:
            missing.extend(evidence_errors)
        if missing:
            incomplete.append({"source_dataset": identity, "source_record_id": record_id, "row": f"{row['_sheet']}!{row['_row']}", "decision": decision, "missing_fields": missing})
            missing_evidence.append({"source_dataset": identity, "source_record_id": record_id, "decision": decision, "required": missing})
            continue

        entry = {
            "source_dataset": identity,
            "source_record_id": record_id,
            "content_hash_at_decision": queue_hash,
            "decision": decision,
            "decision_rationale": rationale,
            "evidence_reference": evidence,
            "reviewer_role": reviewer_role,
            "reviewer_identity": reviewer_identity,
            "timestamp_utc": timestamp,
        }
        ledger_entries.append(entry)
        validated[decision] += 1
        if decision in APPROVED:
            approved[decision] += 1

    # A duplicate identity invalidates all rows under that identity, even if only one carried a decision.
    duplicated_keys = {(d["source_dataset"], d["source_record_id"]) for d in duplicates}
    if duplicated_keys:
        ledger_entries = [e for e in ledger_entries if (e["source_dataset"], e["source_record_id"]) not in duplicated_keys]
        for key in duplicated_keys:
            if any((e["source_dataset"], e["source_record_id"]) == key for e in ledger_entries):
                continue
    ledger_entries.sort(key=lambda x: (x["source_dataset"], x["source_record_id"]))

    baseline_dispositions = Counter(r["recommended_disposition"] for r in queue_records)
    return {
        "decision_counts_found": dict(found),
        "decision_counts_validated": dict(validated),
        "approved_by_category": dict(approved),
        "approved_record_count": len([e for e in ledger_entries if e["decision"] in APPROVED]),
        "explicit_rejected_decisions": explicit_rejected,
        "explicit_out_of_scope_decisions": explicit_out_of_scope,
        "baseline_out_of_scope_digilians": baseline_dispositions["OUT_OF_SCOPE_FOR_DEPI"],
        "baseline_excluded_ticket_records": baseline_dispositions["EXCLUDE_NON_KNOWLEDGE"],
        "unreviewed_rows": unreviewed,
        "incomplete_decisions": incomplete,
        "invalid_decisions_or_source_cells": invalid,
        "unknown_source_records": unknown,
        "ambiguous_source_identities": ambiguous,
        "conflicting_or_duplicated_decisions": duplicates,
        "stale_source_hashes": list(stale.values()),
        "source_integrity_mismatch_datasets": sorted(source_integrity_mismatch),
        "missing_evidence": missing_evidence,
        "ledger_entries": ledger_entries,
        "queue_record_count": len(queue_records),
        "workbook_record_count": len(rows),
    }


def create_proposed_ledger(source_ledger: dict, result: dict) -> dict:
    ledger = copy.deepcopy(source_ledger)
    ledger["schema_version"] = "1.1.0"
    ledger["parent_schema_version"] = source_ledger.get("schema_version")
    schema = ledger["schema"]
    item_schema = schema["properties"]["entries"]["items"]
    item_schema["properties"]["reviewer_identity"] = {"type": "string", "minLength": 1}
    if "reviewer_identity" not in item_schema["required"]:
        item_schema["required"].append("reviewer_identity")
    ledger["entries"] = result["ledger_entries"]
    ledger["approved_record_count"] = result["approved_record_count"]
    ledger["reconciliation_status"] = reconciliation_status(result)
    ledger["source_schema_decision_enum_unchanged"] = True
    ledger["validation_rules"] = list(ledger.get("validation_rules", [])) + [
        "The source ledger decision enum is preserved. reviewer_identity is added to this proposed schema because the workbook captures it and it must not be lost during reconciliation.",
        "Only explicit, complete, non-conflicting, current-hash decisions are written to entries. Incomplete or stale decisions remain only in the reconciliation report.",
    ]
    # The template remains clearly non-operative; it is never part of entries.
    return ledger


def reconciliation_status(result: dict) -> str:
    flagged = any(result[k] for k in (
        "incomplete_decisions", "invalid_decisions_or_source_cells", "unknown_source_records",
        "ambiguous_source_identities", "conflicting_or_duplicated_decisions", "stale_source_hashes",
    ))
    if flagged:
        return "REVIEW_REQUIRED"
    return "NO_DECISIONS" if not result["decision_counts_found"] else "RECONCILED"


def render_report(result: dict, schema_valid: bool) -> str:
    def count_map(values: dict) -> str:
        if not values:
            return "None"
        return "; ".join(f"{key}: {value}" for key, value in sorted(values.items()))

    lines = [
        "# Content Approval Ledger Reconciliation",
        "",
        "**Status:** " + ("NO_DECISIONS — zero records approved." if reconciliation_status(result) == "NO_DECISIONS" else "REVIEW REQUIRED — inspect all flagged decisions before using the proposed ledger." if reconciliation_status(result) == "REVIEW_REQUIRED" else "RECONCILED — all explicit decisions passed the checks."),
        "",
        "## Decision summary",
        "",
        f"- Workbook review rows read: {result['workbook_record_count']}",
        f"- Source queue records: {result['queue_record_count']}",
        f"- Decisions found: {sum(result['decision_counts_found'].values())} ({count_map(result['decision_counts_found'])})",
        f"- Decisions validated and written to proposed ledger: {sum(result['decision_counts_validated'].values())} ({count_map(result['decision_counts_validated'])})",
        f"- Approved records: {result['approved_record_count']} ({count_map(result['approved_by_category'])})",
        f"- Explicit rejected decisions: {result['explicit_rejected_decisions']}",
        f"- Explicit out-of-scope decisions: {result['explicit_out_of_scope_decisions']}",
        f"- Rejected decisions written to ledger: {result['decision_counts_validated'].get('REJECTED', 0)}",
        f"- Out-of-scope decisions written to ledger: {result['decision_counts_validated'].get('OUT_OF_SCOPE', 0)}",
        f"- Baseline Digilians records out of DEPI scope: {result['baseline_out_of_scope_digilians']}",
        f"- Baseline ticket records excluded as operational data: {result['baseline_excluded_ticket_records']}",
        f"- Rows with no review input: {result['unreviewed_rows']}",
        "",
        "## Fail-closed checks",
        "",
        f"- Incomplete decisions: {len(result['incomplete_decisions'])}",
        f"- Invalid statuses or modified source cells: {len(result['invalid_decisions_or_source_cells'])}",
        f"- Unknown source records: {len(result['unknown_source_records'])}",
        f"- Ambiguous source identities: {len(result['ambiguous_source_identities'])}",
        f"- Conflicting or duplicated decisions: {len(result['conflicting_or_duplicated_decisions'])}",
        f"- Stale source hashes: {len(result['stale_source_hashes'])}",
        f"- Resulting proposed ledger schema validation: {'PASS' if schema_valid else 'FAIL'}",
        "- JSONL companion files are checked as parity artifacts and are not treated as decision records or import datasets.",
        "- Question/answer content and ticket details are omitted from this report; the source workbook remains unchanged.",
        "",
        "## Missing decision evidence",
        "",
    ]
    if result["missing_evidence"]:
        lines.append("| Source dataset | Record ID | Decision | Required field/evidence |")
        lines.append("|---|---|---|---|")
        for item in result["missing_evidence"]:
            for requirement in item["required"]:
                lines.append(f"| {item['source_dataset']} | {item['source_record_id']} | {item['decision']} | {requirement.replace('|', '\\|')} |")
    elif not result["decision_counts_found"]:
        lines.append("No reviewer decisions were entered. The 421 owner-approval, 132 manual-review, and 2 scope-decision records retain their existing evidence requirements; none was promoted.")
    else:
        lines.append("No missing evidence was recorded for the validated decisions.")
    lines += ["", "## Incomplete and stale items", ""]
    def add_detail(title: str, items: list[dict], fields: list[str]) -> None:
        lines.append(f"### {title}")
        lines.append("")
        if not items:
            lines.append("None.")
        else:
            lines.append("| " + " | ".join(fields) + " |")
            lines.append("|" + "|".join("---" for _ in fields) + "|")
            for item in items:
                vals = [str(item.get(f, "")) for f in fields]
                lines.append("| " + " | ".join(v.replace("|", "\\|") for v in vals) + " |")
        lines.append("")
    add_detail("Incomplete decisions", result["incomplete_decisions"], ["source_dataset", "source_record_id", "decision", "missing_fields"])
    add_detail("Stale hashes", result["stale_source_hashes"], ["source_dataset", "source_record_id", "reason"])
    add_detail("Conflicting or duplicated identities", result["conflicting_or_duplicated_decisions"], ["source_dataset", "source_record_id", "rows"])
    add_detail("Unknown records", result["unknown_source_records"], ["source_dataset", "source_record_id", "row"])
    add_detail("Ambiguous identities", result["ambiguous_source_identities"], ["source_dataset", "source_record_id", "row"])
    add_detail("Invalid decisions/source fields", result["invalid_decisions_or_source_cells"], ["source_dataset", "source_record_id", "decision", "reason"])
    lines += [
        "## Decision identity and evidence rules",
        "",
        "The workbook reviewer field must use `Reviewer identity: <name>; Role: <role>`. A full UTC timestamp must include a time; a date-only Excel value is incomplete. Every explicit decision requires reviewer identity/role, timestamp, rationale, and evidence reference.",
        "",
        "Official DEPI approval requires an HTTPS `.gov.eg` source URL, source authority explicitly classified as verified official DEPI, and an authorized DEPI owner role. Internal guidance requires DEPI scope, internal classification, an authorized DEPI content-owner role, and an `OWNER_APPROVAL:` reference. General support requires `GENERAL_SUPPORT` scope, verified support authority, HTTPS source URL, an authorized support/platform owner, and a `SUPPORT_SOURCE:` or `SUPPORT_APPROVAL:` reference.",
        "",
        "These checks validate evidence fields and structure; they do not fetch external URLs or independently certify a human's source/content assessment. No Ministry server was contacted.",
        "",
        "## Reproducibility",
        "",
        "Rerun `python scripts/reconcile_content_approval_decisions.py` to rebuild the proposed ledger and this report. The source workbook, original ledger, provenance manifest, databases, workflows, services, credentials, and WhatsApp state are read-only inputs or were not accessed.",
        "",
    ]
    return "\n".join(lines)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8")
    temporary.replace(path)


def reconcile_files(workbook_path: Path, queue_path: Path, source_ledger_path: Path,
                    provenance_path: Path, output_ledger_path: Path, report_path: Path) -> dict:
    protected = {workbook_path.resolve(), queue_path.resolve(), source_ledger_path.resolve(), provenance_path.resolve()}
    if output_ledger_path.resolve() in protected or report_path.resolve() in protected:
        raise ValueError("Output path must not overwrite the workbook or an input manifest")
    queue = read_json(queue_path)
    source_ledger = read_json(source_ledger_path)
    provenance = read_json(provenance_path)
    rows, layout_errors = read_workbook_decisions(workbook_path)
    if layout_errors:
        raise ValueError("Workbook layout mismatch; no output was written")
    current_index, original_hashes = load_current_source_index(queue["records"], provenance)
    source_schema, allowed = _schema_parts(source_ledger)
    result = reconcile_decisions(rows, queue["records"], current_index, allowed)
    # Surface source file drift explicitly even if it affects a dataset with no review decisions.
    failed_originals = [p for p, item in original_hashes.items() if not item["matches"]]
    if failed_originals:
        result["stale_source_hashes"].extend({"source_dataset": "original source file", "source_record_id": p, "reason": "original source file SHA-256 differs from the provenance snapshot"} for p in failed_originals)
    proposed = create_proposed_ledger(source_ledger, result)
    Draft202012Validator.check_schema(proposed["schema"])
    Draft202012Validator(proposed["schema"], format_checker=FormatChecker()).validate({"entries": proposed["entries"]})
    report = render_report(result, True)
    atomic_write(output_ledger_path, json.dumps(proposed, ensure_ascii=False, indent=2) + "\n")
    atomic_write(report_path, report)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for key, path in DEFAULTS.items():
        parser.add_argument("--" + key.replace("_", "-"), type=Path, default=path)
    args = parser.parse_args(argv)
    try:
        result = reconcile_files(args.workbook, args.queue, args.source_ledger, args.provenance, args.output_ledger, args.report)
    except Exception as exc:
        # Avoid printing source content or exception payloads that might contain record data.
        print(f"Reconciliation failed closed: {type(exc).__name__}", file=sys.stderr)
        return 2
    summary = {
        "status": reconciliation_status(result),
        "decisions_found": sum(result["decision_counts_found"].values()),
        "decisions_validated": sum(result["decision_counts_validated"].values()),
        "approved_records": result["approved_record_count"],
        "incomplete": len(result["incomplete_decisions"]),
        "stale_hashes": len(result["stale_source_hashes"]),
        "output_ledger": str(args.output_ledger),
        "report": str(args.report),
    }
    print(json.dumps(summary, ensure_ascii=True, indent=2))
    return 0 if summary["status"] in {"NO_DECISIONS", "RECONCILED"} else 1


if __name__ == "__main__":
    sys.exit(main())
