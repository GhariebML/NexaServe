#!/usr/bin/env python3
"""Read-only schema, identity, and stale-hash checks for the human approval ledger."""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs" / "knowledge_ingestion"
APPROVED = {"APPROVED_OFFICIAL_DEPI", "APPROVED_INTERNAL_DEPI_GUIDANCE", "APPROVED_GENERAL_SUPPORT"}


def evaluate_entries(entries: list[dict], current: dict[tuple[str, str], str]) -> tuple[list[dict], list[dict]]:
    seen: set[tuple[str, str]] = set()
    stale = []
    invalid_approvals = []
    for entry in entries:
        key = (entry["source_dataset"], entry["source_record_id"])
        if key in seen:
            raise ValueError(f"Duplicate ledger identity: {key[0]} / {key[1]}")
        seen.add(key)
        current_hash = current.get(key)
        if current_hash is None or current_hash != entry["content_hash_at_decision"]:
            stale.append({"source_dataset": key[0], "source_record_id": key[1], "current_record_found": current_hash is not None})
        if entry["decision"] in APPROVED and (not entry["evidence_reference"] or not entry["reviewer_role"].strip()):
            invalid_approvals.append({"source_dataset": key[0], "source_record_id": key[1], "reason": "approval lacks evidence reference or reviewer role"})
    return stale, invalid_approvals


def main() -> int:
    ledger = json.loads((DOCS / "content_approval_ledger.json").read_text(encoding="utf-8-sig"))
    queue = json.loads((DOCS / "source_approval_queue.json").read_text(encoding="utf-8-sig"))
    Draft202012Validator.check_schema(ledger["schema"])
    Draft202012Validator(ledger["schema"], format_checker=FormatChecker()).validate({"entries": ledger["entries"]})

    current = {(r["source_json"], r["source_record_id"]): r["original_content_hash"] for r in queue["records"]}
    decisions = Counter()
    for entry in ledger["entries"]:
        decisions[entry["decision"]] += 1
    stale, invalid_approvals = evaluate_entries(ledger["entries"], current)

    result = {
        "schema_valid": True,
        "ledger_entries": len(ledger["entries"]),
        "approved_entries": sum(decisions[d] for d in APPROVED),
        "stale_entries": stale,
        "invalid_approvals": invalid_approvals,
        "duplicate_ledger_identities": "PASS — uniqueness enforced",
        "status": "PASS" if not stale and not invalid_approvals else "FAIL",
    }
    print(json.dumps(result, ensure_ascii=True, indent=2))
    return 0 if result["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
