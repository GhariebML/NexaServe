#!/usr/bin/env python3
"""Audit JSON and JSONL artifacts under FAQs/converted without changing them."""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "FAQs" / "converted"
OUTPUT_DIR = ROOT / "docs" / "knowledge_ingestion"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_jsonl(path: Path) -> tuple[list[Any], int]:
    records: list[Any] = []
    malformed = 0
    with path.open(encoding="utf-8-sig") as stream:
        for line in stream:
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                malformed += 1
    return records, malformed


def get_records(value: Any) -> tuple[list[Any], str]:
    if isinstance(value, list):
        return value, "JSON array"
    if not isinstance(value, dict):
        return [], type(value).__name__
    for key in ("records", "tickets", "items", "faqs", "data"):
        if isinstance(value.get(key), list):
            return value[key], f"JSON object/{key}[]"
    return [], "JSON metadata object"


def profile(path: Path, value: Any, malformed: int = 0) -> dict[str, Any]:
    records, shape = get_records(value)
    if not isinstance(value, dict) and not isinstance(value, list):
        disposition = "rejected_invalid"
        reason = "Valid JSON, but the root value cannot be safely interpreted as a dataset."
    elif malformed:
        disposition = "rejected_invalid"
        reason = f"Contains {malformed} malformed JSONL line(s)."
    elif path.name in {"source_manifest.json", "depi_helper_manifest.json", "tickets_manifest.json"}:
        disposition = "skipped_metadata"
        reason = "Manifest/metadata artifact; it describes source files but is not knowledge content."
    elif path.name == "tickets.json":
        disposition = "quarantined_non_faq"
        reason = "Support-ticket archive export includes student/ticket personal and case data; it is not FAQ knowledge and is excluded from RAG."
    elif path.name.endswith(".jsonl"):
        disposition = "skipped_duplicate_export"
        reason = "Line-delimited companion export; inventory is counted from its structured JSON counterpart to prevent double ingestion."
    elif records:
        disposition = "quarantined_review"
        reason = "FAQ-like records require verified source provenance, scope confirmation, and record-level quality review before activation."
    else:
        disposition = "skipped_empty_or_metadata"
        reason = "No knowledge records are present in this JSON artifact."

    questions = answers = empty_qa = missing_questions = missing_answers = 0
    languages: collections.Counter[str] = collections.Counter()
    programs: collections.Counter[str] = collections.Counter()
    record_types: collections.Counter[str] = collections.Counter()
    hashes: collections.Counter[str] = collections.Counter()
    sources: collections.Counter[str] = collections.Counter()
    flags: collections.Counter[str] = collections.Counter()
    record_dispositions: collections.Counter[str] = collections.Counter()
    applicability: collections.Counter[str] = collections.Counter()
    duplicate_groups = 0
    if records:
        for record in records:
            if not isinstance(record, dict):
                flags["non_object_record"] += 1
                continue
            q = str(record.get("question") or record.get("question_ar") or "").strip()
            a = str(record.get("answer") or record.get("answer_ar") or "").strip()
            questions += bool(q)
            answers += bool(a)
            missing_questions += not bool(q)
            missing_answers += not bool(a)
            empty_qa += not (q and a)
            languages[str(record.get("language") or "unspecified")] += 1
            programs[str(record.get("program_scope") or record.get("program") or "unspecified")] += 1
            record_types[str(record.get("record_type") or record.get("dataset_type") or "unspecified")] += 1
            scope = str(record.get("program_scope") or record.get("program") or "").upper()
            verified = str(record.get("source_status") or "").lower() == "verified"
            if scope == "DEPI" and verified:
                applicability["DEPI_authoritative_candidate"] += 1
            elif scope in {"COMMON", "GENERAL_SUPPORT"} and verified:
                applicability["general_support_candidate"] += 1
            elif scope == "DIGILIANS":
                applicability["other_initiative_DIGILIANS"] += 1
            else:
                applicability["ambiguous_or_unverified"] += 1
            content_hash = str(record.get("content_sha256") or record.get("content_hash") or "").strip()
            if content_hash:
                hashes[content_hash] += 1
            source = record.get("source_file") or record.get("source_archive") or record.get("source_attribution")
            if source:
                sources[str(source)] += 1
            if record.get("source_status"):
                flags[f"source_status:{record['source_status']}"] += 1
            if record.get("needs_review"):
                flags["needs_review"] += 1
            if record.get("is_duplicate"):
                flags["marked_duplicate"] += 1
            if path.name == "tickets.json":
                record_dispositions["quarantined_non_faq_ticket"] += 1
            elif record.get("is_duplicate") or record.get("duplicate_of"):
                record_dispositions["duplicate_flagged"] += 1
            elif not q or not a or str(record.get("record_type") or "faq").lower() != "faq":
                record_dispositions["quarantined_incomplete_or_non_faq"] += 1
            elif str(record.get("source_status") or "unverified").lower() != "verified":
                record_dispositions["quarantined_unverified_source"] += 1
            elif str(record.get("program_scope") or record.get("program") or "").upper() not in {"DEPI", "GENERAL_SUPPORT"}:
                record_dispositions["quarantined_scope_review"] += 1
            else:
                record_dispositions["eligible_for_explicit_review_only"] += 1
        duplicate_groups = sum(n > 1 for n in hashes.values())

    if path.name == "depi_helper.json":
        reason += " Export contains no source URL/status; incomplete rows and duplicate flags are separately counted."
    if path.name == "faqs.json":
        reason += " All records currently declare source_status=unverified; program aliases include DEBI and DIGILIANS and have not been independently validated."

    return {
        "relative_path": path.relative_to(ROOT).as_posix(),
        "bytes": path.stat().st_size,
        "sha256": sha256(path),
        "format": "JSONL" if path.suffix.lower() == ".jsonl" else "JSON",
        "shape": shape,
        "schema_version": value.get("schema_version") if isinstance(value, dict) else None,
        "top_level_keys": list(value.keys()) if isinstance(value, dict) else None,
        "record_count": len(records),
        "question_count": questions,
        "answer_count": answers,
        "missing_question_count": missing_questions,
        "missing_answer_count": missing_answers,
        "empty_or_incomplete_qa_count": empty_qa,
        "duplicate_content_hash_record_count": sum(n - 1 for n in hashes.values() if n > 1),
        "duplicate_content_hash_group_count": duplicate_groups,
        "languages": dict(languages),
        "program_labels": dict(programs),
        "applicability_counts": dict(applicability),
        "record_types": dict(record_types),
        "source_labels": dict(sources),
        "quality_flags": dict(flags),
        "record_dispositions": dict(record_dispositions),
        "field_presence": {
            "question_or_question_ar": questions,
            "answer_or_answer_ar": answers,
            "language": sum(bool(isinstance(r, dict) and r.get("language")) for r in records),
            "source_file_or_archive_or_attribution": sum(bool(isinstance(r, dict) and (r.get("source_file") or r.get("source_archive") or r.get("source_attribution"))) for r in records),
            "source_url": sum(bool(isinstance(r, dict) and r.get("source_url")) for r in records),
            **{field: sum(bool(isinstance(r, dict) and r.get(field)) for r in records) for field in (
                "question", "question_ar", "answer", "answer_ar", "language", "program_scope", "program",
                "record_type", "category", "source_file", "source_page", "source_sheet", "source_row",
                "source_url", "source_status", "content_sha256", "content_hash")},
        },
        "malformed_json_lines": malformed,
        "disposition": disposition,
        "disposition_reason": reason,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=OUTPUT_DIR)
    args = parser.parse_args()
    entries: list[dict[str, Any]] = []
    parse_errors: list[dict[str, str]] = []
    for path in sorted((*SOURCE_DIR.rglob("*.json"), *SOURCE_DIR.rglob("*.jsonl"))):
        try:
            if path.suffix.lower() == ".jsonl":
                value, malformed = load_jsonl(path)
            else:
                with path.open(encoding="utf-8-sig") as stream:
                    value = json.load(stream)
                malformed = 0
            entry = profile(path, value, malformed)
            if path.suffix.lower() == ".jsonl":
                companion = path.with_suffix(".json")
                entry["companion_json"] = companion.relative_to(ROOT).as_posix()
                try:
                    with companion.open(encoding="utf-8-sig") as stream:
                        companion_value = json.load(stream)
                    companion_records, _ = get_records(companion_value)
                    entry["companion_record_parity"] = malformed == 0 and value == companion_records
                except (OSError, UnicodeError, json.JSONDecodeError):
                    entry["companion_record_parity"] = False
            entries.append(entry)
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            parse_errors.append({"relative_path": path.relative_to(ROOT).as_posix(), "error": str(error)})
            entries.append({
                "relative_path": path.relative_to(ROOT).as_posix(), "bytes": path.stat().st_size,
                "sha256": sha256(path), "format": path.suffix[1:].upper(),
                "disposition": "rejected_invalid", "disposition_reason": type(error).__name__,
                "record_count": 0, "malformed_json_lines": 0,
            })

    exact_file_groups: dict[str, list[str]] = {}
    for entry in entries:
        exact_file_groups.setdefault(entry["sha256"], []).append(entry["relative_path"])
    duplicates = [paths for paths in exact_file_groups.values() if len(paths) > 1]
    report = {
        "source_directory": "FAQs/converted",
        "scan_recursive": True,
        "encoding": "UTF-8 (BOM accepted)",
        "files": entries,
        "exact_duplicate_file_groups": duplicates,
        "parse_errors": parse_errors,
        "totals": {
            "files": len(entries),
            "json_files": sum(e["format"] == "JSON" for e in entries),
            "jsonl_files": sum(e["format"] == "JSONL" for e in entries),
            "records_in_json_datasets": sum(e["record_count"] for e in entries if e["format"] == "JSON"),
            "records_in_jsonl_companions": sum(e["record_count"] for e in entries if e["format"] == "JSONL"),
            "dispositions": dict(collections.Counter(e["disposition"] for e in entries)),
        },
        "policy": "Inventory is descriptive. No source is activated by this scan. Unverified, ambiguous, incomplete, and out-of-scope knowledge remains inactive/quarantined.",
    }
    args.output_dir.mkdir(parents=True, exist_ok=True)
    json_path = args.output_dir / "source_inventory.json"
    md_path = args.output_dir / "source_inventory_report.md"
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# Converted Source Inventory", "", "Source: `FAQs/converted` (recursive UTF-8 scan).",
        "", f"Files: {report['totals']['files']} ({report['totals']['json_files']} JSON, {report['totals']['jsonl_files']} JSONL).",
        f"JSON dataset records: {report['totals']['records_in_json_datasets']}; JSONL companion records: {report['totals']['records_in_jsonl_companions']}.",
        "", "| File | Bytes | Shape/schema | Records | Incomplete Q/A | Disposition |", "|---|---:|---|---:|---:|---|",
    ]
    for entry in entries:
        shape = entry.get("shape", "invalid")
        if entry.get("schema_version") is not None:
            shape += f" (schema {entry['schema_version']})"
        lines.append(f"| `{entry['relative_path']}` | {entry['bytes']} | {shape} | {entry.get('record_count',0)} | {entry.get('empty_or_incomplete_qa_count','—')} | {entry['disposition']} |")
    lines.extend(["", "## Dispositions", ""])
    for entry in entries:
        lines.append(f"- **{entry['relative_path']} — {entry['disposition']}:** {entry['disposition_reason']}")
    lines.extend([
        "", "## Quality and scope findings", "",
        "- `faqs.json` contains 452 records: 393 FAQ records and 59 reference sections; all declare `source_status=unverified`. The labels are 290 `DEBI` and 162 `DIGILIANS`, neither of which is silently promoted into DEPI-authoritative scope.",
        "- `depi_helper.json` contains 265 records, including incomplete question/answer rows and records flagged as duplicates; its source workbook is named but no source URL or verification status is present.",
        "- `tickets.json` contains ticket records, not FAQs, and includes student names, ticket identifiers, and case content. It is quarantined from RAG ingestion.",
        "- Manifest JSON files describe the source artifacts and have no knowledge record arrays. JSONL files are excluded from ingestion to avoid double counting; their machine inventory records exact record parity against their JSON companion.",
        "- No source records are approved for activation by this inventory. Source-owner review and provenance verification are required first.",
        "", "## Reproducibility", "", "Run `python scripts/inventory_converted_sources.py`. The command reads source files and writes only under `docs/knowledge_ingestion/`, outside the canonical source directory.", "",
    ])
    md_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Wrote {json_path.relative_to(ROOT)} and {md_path.relative_to(ROOT)}")
    return 1 if parse_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
