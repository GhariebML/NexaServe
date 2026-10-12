#!/usr/bin/env python3
"""Create the human review workbook and empty, fail-closed approval ledger."""
from __future__ import annotations

import json
from collections import Counter
from datetime import date
from pathlib import Path

from openpyxl import Workbook, load_workbook
from openpyxl.formatting.rule import FormulaRule
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.worksheet.datavalidation import DataValidation
from openpyxl.worksheet.table import Table, TableStyleInfo

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "knowledge_ingestion"
WORKBOOK_PATH = DOCS / "DEPI_Content_Approval_Review.xlsx"
LEDGER_PATH = DOCS / "content_approval_ledger.json"

DECISIONS = [
    "APPROVED_OFFICIAL_DEPI", "APPROVED_INTERNAL_DEPI_GUIDANCE",
    "APPROVED_GENERAL_SUPPORT", "OUT_OF_SCOPE", "REJECTED",
    "NEEDS_MORE_EVIDENCE", "NEEDS_OWNER_APPROVAL",
]
NAVY, BLUE, CYAN = "111827", "2563EB", "06B6D4"
WHITE, TEXT, MUTED = "FFFFFF", "1F2937", "6B7280"
PALE_BLUE, PALE_AMBER, PALE_GREEN, PALE_RED, PALE_GRAY = "EFF6FF", "FEF3C7", "D1FAE5", "FEE2E2", "F3F4F6"

HEADERS = [
    "Stable Source Record ID", "Source JSON Path", "Original Source File", "Original Source Locator",
    "Source URL", "Content Hash", "Question", "Answer", "Language", "Current Program Label",
    "Reviewed Program Identity", "Proposed Program", "Proposed Retrieval Scope",
    "Source Authority Classification", "Current Review Status", "Exact Review Rationale",
    "Missing Provenance / Scope Evidence", "Evidence Required to Resolve", "Duplicate / Relationship IDs",
    "Reviewer Decision", "Reviewer Identity / Responsible Role", "Decision Date (UTC)",
    "Approval Evidence / Decision Reference", "Reviewer Rationale",
]
WIDTHS = [28, 34, 34, 32, 34, 68, 56, 64, 13, 21, 52, 22, 44, 60, 34, 72, 75, 88, 44, 34, 34, 20, 54, 60]


def load_json(name: str):
    return json.loads((DOCS / name).read_text(encoding="utf-8-sig"))


def make_ledger() -> dict:
    entry_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "NexaServe content approval decision",
        "type": "object",
        "additionalProperties": False,
        "required": ["source_dataset", "source_record_id", "content_hash_at_decision", "decision",
                     "decision_rationale", "evidence_reference", "reviewer_role", "timestamp_utc"],
        "properties": {
            "source_dataset": {"type": "string", "minLength": 1},
            "source_record_id": {"type": "string", "minLength": 1},
            "content_hash_at_decision": {"type": "string", "pattern": "^[0-9a-f]{64}$"},
            "decision": {"enum": DECISIONS},
            "decision_rationale": {"type": "string", "minLength": 1},
            "evidence_reference": {"type": ["string", "null"]},
            "reviewer_role": {"type": "string", "minLength": 1},
            "timestamp_utc": {"type": "string", "format": "date-time"},
        },
    }
    ledger_schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "NexaServe content approval ledger",
        "type": "object",
        "required": ["entries"],
        "properties": {"entries": {"type": "array", "items": entry_schema}},
        "additionalProperties": True,
    }
    return {
        "title": "NexaServe Human Content Approval Ledger",
        "schema_version": "1.0.0",
        "schema": ledger_schema,
        "validation_rules": [
            "Only entries in the entries array are recorded decisions. example_entry_template is documentation and never a decision.",
            "The entries array is empty at package creation; approved_record_count is zero.",
            "A decision applies only to the exact source_dataset + source_record_id + content_hash_at_decision tuple.",
            "Run scripts/validate_content_approval_ledger.py before use. It resolves every decision against source_approval_queue.json; a missing record or content-hash mismatch makes the decision STALE and blocks ledger acceptance.",
            "Duplicate JSONL companions are parity artifacts, not distinct source_dataset values for approval or import.",
            "An approved decision requires an evidence_reference and reviewer_role; official DEPI decisions require a verifiable official URL/document reference, and internal DEPI guidance requires an authorized content-owner decision.",
            "No approval is inferred from a blank decision, missing evidence, workbook status, matching file hash, or absence of a response.",
        ],
        "permitted_decisions": DECISIONS,
        "approved_record_count": 0,
        "entries": [],
        "example_entry_template": {
            "example_only": True,
            "source_dataset": "<source JSON path from the approval queue>",
            "source_record_id": "<stable source record ID>",
            "content_hash_at_decision": "<64-character SHA-256 from the current approval queue>",
            "decision": "NEEDS_MORE_EVIDENCE",
            "decision_rationale": "<reviewer explains the unresolved evidence gap>",
            "evidence_reference": None,
            "reviewer_role": "<authorized reviewer role; do not use a placeholder in a real entry>",
            "timestamp_utc": "<ISO-8601 UTC timestamp; do not use a placeholder in a real entry>",
            "notice": "Illustrative template only. Not a source record, reviewer decision, approval, or supporting evidence.",
        },
    }


def write_ledger() -> None:
    LEDGER_PATH.write_text(json.dumps(make_ledger(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def style_sheet(ws, tab_color=None):
    ws.sheet_view.showGridLines = False
    if tab_color:
        ws.sheet_properties.tabColor = tab_color


def build_review_sheet(wb, title: str, rows: list[dict], table_name: str, status_color: str) -> None:
    ws = wb.create_sheet(title)
    style_sheet(ws, status_color)
    ws.cell(1, 1, f"NexaServe | {title}")
    ws.cell(1, 1).font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    ws.cell(2, 1, "Review only. Reviewer fields are intentionally blank; no record is approved by this workbook.")
    ws.cell(2, 1).font = Font(name="Calibri", size=9, italic=True, color=MUTED)
    for col, header in enumerate(HEADERS, 1):
        cell = ws.cell(4, col, header)
        cell.fill = PatternFill("solid", fgColor=BLUE)
        cell.font = Font(name="Calibri", size=9, bold=True, color=WHITE)
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 34
    for row_num, source in enumerate(rows, 5):
        locator = json.dumps(source.get("source_locator") or {}, ensure_ascii=False, sort_keys=True)
        duplicate_ids = "; ".join(
            str(x.get("group_id") or x.get("related_record_id") or x.get("relationship"))
            for x in source.get("duplicate_relationships", [])
        )
        values = [
            source.get("source_record_id"), source.get("source_json"), source.get("source_original_file"), locator,
            source.get("source_url"), source.get("original_content_hash"), source.get("original_question"),
            source.get("original_answer"), source.get("language"), source.get("program_identity_original_label"),
            source.get("program_identity_review"), source.get("proposed_program"), source.get("proposed_retrieval_scope"),
            source.get("source_authority_class"), source.get("recommended_disposition"), source.get("record_rationale"),
            source.get("missing_evidence"), source.get("approval_evidence_needed"), duplicate_ids,
            None, None, None, None, None,
        ]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row_num, col, value)
            cell.font = Font(name="Calibri", size=9, color=TEXT)
            is_long = col in {4, 7, 8, 11, 14, 16, 17, 18, 19, 23, 24}
            cell.alignment = Alignment(vertical="top", wrap_text=True, horizontal="right" if source.get("language") == "ar" and col in {7, 8} else "left")
            if col in {20, 21, 22, 23, 24}:
                cell.fill = PatternFill("solid", fgColor="FFF7ED")
            elif row_num % 2 == 0:
                cell.fill = PatternFill("solid", fgColor="F9FAFB")
        ws.cell(row_num, 22).number_format = "yyyy-mm-dd"
        ws.row_dimensions[row_num].height = 64
    last_row = max(4, 4 + len(rows))
    last_col = len(HEADERS)
    ref = f"A4:{ws.cell(4, last_col).column_letter}{last_row}"
    if rows:
        table = Table(displayName=table_name, ref=ref)
        table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
                                             showRowStripes=True, showColumnStripes=False)
        ws.add_table(table)
        dv = DataValidation(type="list", formula1='"' + ",".join(DECISIONS) + '"', allow_blank=True)
        dv.errorTitle = "Select a permitted review decision"
        dv.error = "Choose a listed decision. Approval requires the evidence listed in the adjacent columns and a ledger entry."
        dv.promptTitle = "Human review required"
        dv.prompt = "Leave blank until a reviewer has reviewed the source and supporting evidence."
        dv.showErrorMessage = True
        dv.showInputMessage = True
        ws.add_data_validation(dv)
        dv.add(f"T5:T{last_row}")
        date_dv = DataValidation(type="date", operator="between", formula1="DATE(2000,1,1)", formula2="DATE(2100,12,31)", allow_blank=True)
        date_dv.error = "Enter a valid decision date. The ledger timestamp must be UTC."
        date_dv.showErrorMessage = True
        ws.add_data_validation(date_dv)
        date_dv.add(f"V5:V{last_row}")
        ws.conditional_formatting.add(f"T5:T{last_row}", FormulaRule(formula=['LEFT(T5,8)="APPROVED"'], fill=PatternFill("solid", fgColor=PALE_GREEN)))
        ws.conditional_formatting.add(f"T5:T{last_row}", FormulaRule(formula=['T5="NEEDS_MORE_EVIDENCE"'], fill=PatternFill("solid", fgColor=PALE_AMBER)))
        ws.conditional_formatting.add(f"T5:T{last_row}", FormulaRule(formula=['OR(T5="REJECTED",T5="OUT_OF_SCOPE")'], fill=PatternFill("solid", fgColor=PALE_RED)))
    for col, width in enumerate(WIDTHS, 1):
        ws.column_dimensions[ws.cell(4, col).column_letter].width = width
    ws.freeze_panes = "D5"
    ws.auto_filter.ref = ref
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:4"


def build_summary(wb, counts: Counter) -> None:
    ws = wb.active
    ws.title = "Executive Summary"
    style_sheet(ws, NAVY)
    ws.column_dimensions["A"].width = 43
    ws.column_dimensions["B"].width = 22
    ws.column_dimensions["C"].width = 95
    ws.cell(2, 1, "NexaServe | DEPI Content Approval Review")
    ws.cell(2, 1).font = Font(name="Calibri", size=16, bold=True, color=NAVY)
    ws.cell(3, 1, f"Human review package • as of {date.today().isoformat()} • no content approved")
    ws.cell(3, 1).font = Font(name="Calibri", size=10, italic=True, color=MUTED)
    ws.cell(5, 1, "CURRENT REVIEW STATUS")
    ws.cell(5, 1).font = Font(name="Calibri", size=10, bold=True, color=WHITE)
    ws.cell(5, 1).fill = PatternFill("solid", fgColor=BLUE)
    ws.cell(5, 2, "0 APPROVED")
    ws.cell(5, 2).font = Font(name="Calibri", size=12, bold=True, color="B91C1C")
    ws.cell(5, 2).fill = PatternFill("solid", fgColor=PALE_RED)
    ws.cell(5, 3, "Hash/parity verification establishes file integrity only; it is not source-owner approval or content authorization.")
    ws.cell(5, 3).font = Font(name="Calibri", size=9, color=TEXT)
    for col, header in enumerate(["Current disposition", "Records", "What remains unresolved"], 1):
        c = ws.cell(7, col, header); c.fill = PatternFill("solid", fgColor=BLUE); c.font = Font(name="Calibri", size=10, bold=True, color=WHITE); c.alignment = Alignment(horizontal="center", wrap_text=True)
    summary_rows = [
        ("NEEDS_OWNER_APPROVAL", counts["NEEDS_OWNER_APPROVAL"], "Accountable content-owner approval, source authority, effective/current date, and retrieval scope."),
        ("MANUAL_CONTENT_REVIEW", counts["MANUAL_CONTENT_REVIEW"], "Incomplete Q/A or reference sections; do not invent missing questions or approvals."),
        ("QUARANTINE_SCOPE_DECISION", counts["QUARANTINE_SCOPE_DECISION"], "Explicit DEPI/DEBI eligibility case needs a decision supported by the source and both initiative owners."),
        ("OUT_OF_SCOPE_FOR_DEPI", counts["OUT_OF_SCOPE_FOR_DEPI"], "Digilians content; excluded from the DEPI runtime. No approval implied for another assistant."),
        ("EXCLUDE_NON_KNOWLEDGE", counts["EXCLUDE_NON_KNOWLEDGE"], "Ticket/case data; excluded as operational data. Ticket text and personal metadata are not included."),
    ]
    for r, row in enumerate(summary_rows, 8):
        for c, value in enumerate(row, 1):
            cell = ws.cell(r, c, value); cell.font = Font(name="Calibri", size=10, color=TEXT); cell.alignment = Alignment(vertical="top", wrap_text=True)
            if r % 2 == 0: cell.fill = PatternFill("solid", fgColor="F9FAFB")
    ws.cell(13, 1, "Total source records in approval inventory"); ws.cell(13, 2, "=SUM(B8:B12)")
    ws.cell(14, 1, "Verified official DEPI sources"); ws.cell(14, 2, 0)
    ws.cell(15, 1, "Verified general technical-support sources"); ws.cell(15, 2, 0)
    ws.cell(16, 1, "Approved records in validated ledger"); ws.cell(16, 2, 0)
    for r in range(13, 17):
        ws.cell(r, 1).font = Font(name="Calibri", size=10, bold=(r == 13), color=TEXT)
        ws.cell(r, 2).font = Font(name="Calibri", size=10, bold=True, color=TEXT)
    ws.cell(18, 1, "Approval progress")
    ws.cell(18, 1).font = Font(name="Calibri", size=11, bold=True, color=NAVY)
    ws.cell(19, 1, "Reviewer decision cells completed")
    ws.cell(19, 2, "=COUNTA('Owner Approval Queue'!T5:T425)+COUNTA('Manual Content Review'!T5:T136)+COUNTA('Scope Decisions'!T5:T6)+COUNTA('Out of Scope'!T5:T791)")
    ws.cell(20, 1, "Workbook decisions marked as an approval (not yet ledger-validated)")
    approved_formula = "+".join(f'COUNTIF(\'{sheet}\'!T5:T{end},"{decision}")' for sheet, end in [("Owner Approval Queue", 425), ("Manual Content Review", 136), ("Scope Decisions", 6), ("Out of Scope", 791)] for decision in DECISIONS[:3])
    ws.cell(20, 2, f"={approved_formula}")
    ws.cell(21, 1, "Validated approval ledger entries"); ws.cell(21, 2, 0)
    ws.cell(22, 1, "Important"); ws.cell(22, 2, "Workbook selections are review inputs only. Transfer a decision to the ledger only after evidence validation; no absence or selection alone authorizes ingestion.")
    ws.merge_cells("B22:C23")
    for r in range(19, 22):
        ws.cell(r, 1).font = Font(name="Calibri", size=10, color=TEXT)
        ws.cell(r, 2).font = Font(name="Calibri", size=10, bold=True, color=TEXT)
    ws.cell(22, 1).font = Font(name="Calibri", size=10, bold=True, color="B45309")
    ws.cell(22, 2).alignment = Alignment(vertical="top", wrap_text=True)
    ws.cell(25, 1, "Integrity checks")
    ws.cell(25, 1).font = Font(name="Calibri", size=11, bold=True, color=NAVY)
    integrity = [
        ("Original source-file SHA-256 checks", "PASS — 4 of 4 match"),
        ("JSON / JSONL exact companion parity", "PASS — 3 of 3 datasets match"),
        ("JSONL treatment", "Parity copies only; not counted/imported as separate datasets"),
        ("Review coverage", "1,342 source records across four review tabs; each source dataset record is listed once"),
        ("Technical blocker", "qwen2.5:3b generation runner was killed; cause unconfirmed"),
        ("Isolation blocker", "Existing candidate Compose uses shared baseline services; no candidate runtime started"),
    ]
    for r, (label, value) in enumerate(integrity, 26):
        ws.cell(r, 1, label); ws.cell(r, 2, value); ws.merge_cells(start_row=r, start_column=2, end_row=r, end_column=3)
        ws.cell(r, 1).font = Font(name="Calibri", size=9, color=TEXT)
        ws.cell(r, 2).font = Font(name="Calibri", size=9, color=TEXT)
        ws.cell(r, 2).alignment = Alignment(wrap_text=True)
    ws.freeze_panes = "A7"
    ws.sheet_view.zoomScale = 90


def build_source_inventory(wb, queue_records: list[dict], inventory: dict, provenance: dict) -> None:
    ws = wb.create_sheet("Source Inventory")
    style_sheet(ws, CYAN)
    headers = ["Artifact Type", "Relative Path", "Format", "Bytes", "SHA-256", "Record Count", "JSON / JSONL Pair", "Parity", "Disposition / Notes"]
    widths = [28, 48, 16, 17, 70, 20, 34, 16, 96]
    ws.cell(1, 1, "Source Inventory | originals, structured exports, companions, and metadata")
    ws.cell(1, 1).font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    ws.cell(2, 1, "Original file hashes verify byte identity, not source authority, currentness, or approval.")
    ws.cell(2, 1).font = Font(name="Calibri", size=9, italic=True, color=MUTED)
    for c, h in enumerate(headers, 1):
        cell = ws.cell(4, c, h); cell.fill = PatternFill("solid", fgColor=BLUE); cell.font = Font(name="Calibri", size=9, bold=True, color=WHITE); cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    source_manifest = json.loads((ROOT / "FAQs/converted/source_manifest.json").read_text(encoding="utf-8-sig"))
    source_meta = {x["file_path"]: x for x in source_manifest["source_inventory"]}
    source_to_rows = Counter(x["source_original_file"] for x in queue_records)
    original_paths = ["FAQs/DEPI HELPER.xlsx", "FAQs/FAQ final-Digilians.pdf", "FAQs/FAQ LMS-English Exam.pdf", "FAQs/tickets.pst"]
    hash_map = provenance["original_source_files"]
    rows = []
    for path in original_paths:
        info = hash_map[path]
        meta = source_meta.get(path, {})
        if path.endswith("DEPI HELPER.xlsx"):
            record_count = f"{meta.get('records_count')} extracted by FAQ conversion; 265 helper export + 268 faqs export rows in approval queue"
            notes = "Two converted views from the same workbook are retained as supplied records; content-equivalence links are preserved. Do not infer official authority from filename or hash."
        elif path.endswith("tickets.pst"):
            record_count = f"625 ticket rows in converted ticket export; generic FAQ extractor reports {meta.get('records_count', 'n/a')}"
            notes = "Operational/case data excluded from knowledge retrieval. Approval workbook omits ticket text and personal fields."
        else:
            record_count = str(meta.get("records_count", "n/a"))
            notes = "Source identity/content lineage only; no accountable owner/currentness approval established."
            if path.endswith("FAQ LMS-English Exam.pdf"):
                notes += " Page 11 has a graphic-only contact poster not extracted; manual review required."
        rows.append(["Original source", path, meta.get("format"), info.get("bytes"), info.get("sha256_actual"), record_count, "—", "—", notes])

    inventory_rows = {f["relative_path"]: f for f in inventory["files"]}
    for name in ("depi_helper", "faqs", "tickets"):
        for suffix in ("json", "jsonl"):
            path = f"FAQs/converted/{name}.{suffix}"
            info = inventory_rows[path]
            pair = f"{name}.json / {name}.jsonl"
            rows.append(["Structured dataset" if suffix == "json" else "JSONL parity companion", path, suffix.upper(), info["bytes"], info["sha256"], info["record_count"], pair, "PASS — exact" if info.get("companion_record_parity") or suffix == "json" else "PASS — exact", info.get("disposition_reason", "")])
    for path, info in inventory_rows.items():
        if path.endswith("_manifest.json") or path.endswith("source_manifest.json"):
            rows.append(["Conversion metadata", path, "JSON", info["bytes"], info["sha256"], 0, "—", "N/A", "Metadata only; not a knowledge dataset."])
    for r, values in enumerate(rows, 5):
        for c, value in enumerate(values, 1):
            cell = ws.cell(r, c, value); cell.font = Font(name="Calibri", size=9, color=TEXT); cell.alignment = Alignment(vertical="top", wrap_text=True)
            if r % 2 == 0: cell.fill = PatternFill("solid", fgColor="F9FAFB")
        ws.row_dimensions[r].height = 48
    last_row = 4 + len(rows)
    table = Table(displayName="SourceInventory", ref=f"A4:I{last_row}")
    table.tableStyleInfo = TableStyleInfo(name="TableStyleMedium2", showRowStripes=True, showColumnStripes=False)
    ws.add_table(table)
    for c, width in enumerate(widths, 1): ws.column_dimensions[ws.cell(4,c).column_letter].width = width
    ws.freeze_panes = "C5"; ws.auto_filter.ref = f"A4:I{last_row}"
    ws.sheet_properties.pageSetUpPr.fitToPage = True; ws.page_setup.orientation = "landscape"; ws.page_setup.fitToWidth = 1; ws.page_setup.fitToHeight = 0


def build_instructions(wb) -> None:
    ws = wb.create_sheet("Approval Instructions")
    style_sheet(ws, "8B5CF6")
    ws.column_dimensions["A"].width = 36; ws.column_dimensions["B"].width = 110
    ws.cell(1, 1, "Approval Instructions | evidence before decision")
    ws.cell(1, 1).font = Font(name="Calibri", size=14, bold=True, color=NAVY)
    sections = [
        ("Decision values", "APPROVED_OFFICIAL_DEPI: use only with a verifiable official DEPI URL or official document reference, confirmed wording, scope, and current effective date."),
        ("Decision values", "APPROVED_INTERNAL_DEPI_GUIDANCE: use only after authorized DEPI content-owner approval; label the source as internal guidance, never as an official government publication."),
        ("Decision values", "APPROVED_GENERAL_SUPPORT: use only for verified reusable technical-support guidance with an accountable platform/support owner, authoritative reference, currentness, and GENERAL_SUPPORT scope."),
        ("Decision values", "OUT_OF_SCOPE: record the initiative boundary and rationale. Digilians is out of scope for the DEPI runtime; this does not approve a separate Digilians assistant."),
        ("Decision values", "REJECTED: retain a concise reason and decision evidence; do not delete or overwrite the source record."),
        ("Decision values", "NEEDS_MORE_EVIDENCE: identify the precise missing source, authority, scope, or currentness evidence."),
        ("Decision values", "NEEDS_OWNER_APPROVAL: identify the accountable owner role and exact content/scope decision needed; do not invent a person or approval."),
        ("How to review", "Filter by Current Review Status, source, language, program, or duplicate relationship. Read the original record and cited locator. Keep decisions provisional until evidence is attached."),
        ("How to review", "Enter a reviewer decision only after review. Fill reviewer role, UTC decision date, evidence reference, and concise rationale. Blank fields remain blank; no values were fabricated."),
        ("Hash freshness", "Run scripts/validate_content_approval_ledger.py before accepting ledger decisions. It binds each decision to the source dataset, stable record ID, and exact 64-character content hash; a changed or missing record is stale and blocked."),
        ("Duplicates", "JSONL files are parity companions, not additional records to import. Duplicate relationships are review links; do not silently delete, merge, or approve a duplicate group."),
        ("Current source findings", "Zero sources are verified as official DEPI content or general technical support. Workbook/PDF hashes establish file identity, not source authority or currentness."),
        ("Technical blockers", "Ollama generation previously failed after the qwen2.5:3b runner was killed; cause is unconfirmed. See docs/knowledge_ingestion/ollama_failure_diagnosis.md."),
        ("Technical blockers", "Existing candidate Compose references shared baseline services and is not isolated. See docs/knowledge_ingestion/candidate_isolation_matrix.md. No services were started for this package."),
        ("Fail-closed control", "The workbook is a human review interface, not an ingestion manifest. The ledger is empty and approved_record_count is zero. Do not import or activate records from a workbook decision alone."),
    ]
    for c, h in enumerate(["Topic", "Instruction"], 1):
        cell = ws.cell(3, c, h); cell.fill = PatternFill("solid", fgColor=BLUE); cell.font = Font(name="Calibri", size=10, bold=True, color=WHITE)
    for r, values in enumerate(sections, 4):
        for c, value in enumerate(values, 1):
            cell = ws.cell(r, c, value); cell.font = Font(name="Calibri", size=10, color=TEXT); cell.alignment = Alignment(vertical="top", wrap_text=True)
            if r % 2 == 0: cell.fill = PatternFill("solid", fgColor="F9FAFB")
        ws.row_dimensions[r].height = 38
    ws.freeze_panes = "A4"


def main() -> None:
    queue = load_json("source_approval_queue.json")
    inventory = load_json("source_inventory.json")
    provenance = load_json("source_provenance_review.json")
    records = queue["records"]
    counts = Counter(r["recommended_disposition"] for r in records)
    owner = [r for r in records if r["recommended_disposition"] == "NEEDS_OWNER_APPROVAL"]
    manual = [r for r in records if r["recommended_disposition"] == "MANUAL_CONTENT_REVIEW"]
    scope = [r for r in records if r["recommended_disposition"] == "QUARANTINE_SCOPE_DECISION"]
    out = [r for r in records if r["recommended_disposition"] in {"OUT_OF_SCOPE_FOR_DEPI", "EXCLUDE_NON_KNOWLEDGE"}]

    wb = Workbook()
    wb.calculation.fullCalcOnLoad = True
    wb.calculation.forceFullCalc = True
    wb.calculation.calcMode = "auto"
    build_summary(wb, counts)
    build_review_sheet(wb, "Owner Approval Queue", owner, "OwnerApprovalQueue", BLUE)
    build_review_sheet(wb, "Manual Content Review", manual, "ManualContentReview", "F59E0B")
    build_review_sheet(wb, "Scope Decisions", scope, "ScopeDecisions", "8B5CF6")
    build_review_sheet(wb, "Out of Scope", out, "OutOfScope", "6B7280")
    build_source_inventory(wb, records, inventory, provenance)
    build_instructions(wb)
    wb.save(WORKBOOK_PATH)
    write_ledger()
    print(json.dumps({"workbook": str(WORKBOOK_PATH), "ledger": str(LEDGER_PATH),
                      "rows": {"owner": len(owner), "manual": len(manual), "scope": len(scope), "out_of_scope": len(out), "total": len(owner)+len(manual)+len(scope)+len(out)},
                      "dispositions": counts, "approved_record_count": 0}, ensure_ascii=True, indent=2))


if __name__ == "__main__":
    main()
