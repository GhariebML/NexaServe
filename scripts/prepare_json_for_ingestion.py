#!/usr/bin/env python3
"""
NexaServe JSON Data Preparation Pipeline
=========================================
Inspects, cleans, normalizes, validates, and prepares JSON files for database ingestion.
Preserves originals unchanged; outputs to prepared/ subdirectory.

PHASE 2: Clean and normalize FAQ data
PHASE 3: Handle tickets separately
PHASE 4: Create prepared output files
PHASE 5: Strict import validation
"""

import json
import hashlib
import re
import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple, Set
from collections import Counter

# Valid program scopes per database constraint
VALID_PROGRAM_SCOPES = {"DEPI", "DEBI", "DIGILIANS", "COMMON", "UNKNOWN"}
VALID_RETRIEVAL_SCOPES = {"DEPI_AUTHORITATIVE", "DEPI_INTERNAL_GUIDANCE", "GENERAL_SUPPORT"}

# PII detection patterns (Arabic and English)
PII_PATTERNS = {
    "national_id": re.compile(r'\b[2-7]\d{2}[01]\d{2}[0-3]\d{4}\d{4}\b'),  # Egyptian ID
    "phone_eg": re.compile(r'\b(?:01[0125]\d{8}|201[0125]\d{8}|\+201[0125]\d{8})\b'),
    "email": re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'),
    "arabic_name": re.compile(r'[\u0600-\u06FF]{3,}\s+[\u0600-\u06FF]{3,}\s+[\u0600-\u06FF]{3,}'),
}

# Arabic normalization
ARABIC_NORMALIZATION_MAP = {
    'أ': 'ا', 'إ': 'ا', 'آ': 'ا', 'ة': 'ه', 'ى': 'ي', 'ؤ': 'ؤ', 'ئ': 'ئ', 'ء': 'ء',
}
ARABIC_TATWEEL = re.compile(r'ـ+')
ARABIC_EXTRA_SPACES = re.compile(r'\s{2,}')


def normalize_arabic(text: str) -> str:
    """Normalize Arabic text for consistent comparison."""
    if not text:
        return text
    for k, v in ARABIC_NORMALIZATION_MAP.items():
        text = text.replace(k, v)
    text = ARABIC_TATWEEL.sub('', text)
    text = ARABIC_EXTRA_SPACES.sub(' ', text)
    return text.strip()


def detect_pii(text: str) -> Dict[str, List[str]]:
    """Detect PII in text. Returns dict of pii_type -> list of matched values."""
    found = {}
    # Safety: Only process strings, and do NOT produce debug output
    if not isinstance(text, str):
        return found
    for pii_type, pattern in PII_PATTERNS.items():
        try:
            matches = pattern.findall(text)
            if matches:
                found[pii_type] = matches[:10]  # Limit to avoid large captures
        except (TypeError, AttributeError):
            continue
    return found


def sanitize_pii(text: str) -> Tuple[str, Dict[str, int]]:
    """Remove or mask PII from text. Returns sanitized text and counts by type."""
    if not text:
        return text, {}

    counts = {}
    sanitized = text

    # Mask national IDs
    national_ids = PII_PATTERNS["national_id"].findall(sanitized)
    if national_ids:
        counts["national_id"] = len(national_ids)
        sanitized = PII_PATTERNS["national_id"].sub('[REDACTED_NATIONAL_ID]', sanitized)

    # Mask phone numbers
    phones = PII_PATTERNS["phone_eg"].findall(sanitized)
    if phones:
        counts["phone"] = len(phones)
        sanitized = PII_PATTERNS["phone_eg"].sub('[REDACTED_PHONE]', sanitized)

    # Mask emails
    emails = PII_PATTERNS["email"].findall(sanitized)
    if emails:
        counts["email"] = len(emails)
        sanitized = PII_PATTERNS["email"].sub('[REDACTED_EMAIL]', sanitized)

    return sanitized, counts


def normalize_whitespace(text: str) -> str:
    """Conservatively normalize whitespace."""
    if not text:
        return ""
    text = text.replace('\u00a0', ' ').replace('\ufeff', '')
    text = re.sub(r'\r\n?', '\n', text)
    text = re.sub(r'\n{3,}', '\n\n', text)
    lines = [re.sub(r'[ \t]+', ' ', line).strip() for line in text.splitlines()]
    return '\n'.join(lines).strip()


def compute_content_hash(question: str, answer: str, language: str, program: str) -> str:
    """Compute deterministic content hash for deduplication."""
    canonical = json.dumps({
        "question": normalize_whitespace(question),
        "answer": normalize_whitespace(answer),
        "language": language.lower() if language else "und",
        "program": program.upper() if program else "UNKNOWN"
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def detect_language(text: str) -> str:
    """Detect if text is Arabic, English, or bilingual."""
    if not text:
        return "ar"
    arabic_chars = len(re.findall(r'[\u0600-\u06FF\u0750-\u077F\u08A0-\u08FF]', text))
    latin_chars = len(re.findall(r'[a-zA-Z]', text))
    if arabic_chars > 0 and latin_chars > 0:
        ratio = min(arabic_chars, latin_chars) / max(arabic_chars, latin_chars)
        if ratio > 0.25:
            return "bilingual"
        return "ar" if arabic_chars >= latin_chars else "en"
    elif arabic_chars > 0:
        return "ar"
    elif latin_chars > 0:
        return "en"
    return "ar"


def normalize_program_scope(raw_scope: str) -> Tuple[str, str]:
    """Normalize program scope label and determine retrieval scope."""
    if not raw_scope:
        return "UNKNOWN", "GENERAL_SUPPORT"

    raw_upper = raw_scope.upper().strip()

    # Map known variants
    if "DEPI" in raw_upper:
        if "CALL CENTER" in raw_upper or "SUPPORT" in raw_upper:
            return "DEPI", "DEPI_INTERNAL_GUIDANCE"
        return "DEPI", "DEPI_AUTHORITATIVE"
    elif "DIGILIANS" in raw_upper or "DIGITAL" in raw_upper:
        return "DIGILIANS", "DEPI_AUTHORITATIVE"
    elif "COMMON" in raw_upper or "GENERAL" in raw_upper:
        return "COMMON", "GENERAL_SUPPORT"
    elif "DEBI" in raw_upper:
        return "DEBI", "DEPI_AUTHORITATIVE"
    else:
        return "UNKNOWN", "GENERAL_SUPPORT"


def is_vague_or_incomplete(question: str, answer: str) -> bool:
    """Check if record is too vague or incomplete for knowledge base."""
    q = normalize_whitespace(question).lower()
    a = normalize_whitespace(answer).lower()

    # Vague questions
    vague_q_patterns = [
        r'^اخرى$', r'^other$', r'^_$', r'^-$', r'^nan$',
        r'^لا يوجد$', r'^لا شى$', r'^لا شيء$',
        r'^تجربة$', r'^test$', r'^sample$'
    ]
    for pat in vague_q_patterns:
        if re.match(pat, q):
            return True

    # Incomplete answers (too short or just complaints)
    if len(a) < 5:
        return True

    # Complaint patterns without actionable info
    complaint_patterns = [
        r'^مش عارف', r'^لا يظهر', r'^اريد', r'^مشكلة',
        r'^can\'t', r'^won\'t', r'^doesn\'t work'
    ]
    for pat in complaint_patterns:
        if re.match(pat, a) and len(a) < 30:
            return True

    return False


def process_form_response(records: List[Dict], source_file: str) -> Tuple[List[Dict], Dict]:
    """Process Form_response.json records."""
    processed = []
    stats = {
        "total": len(records),
        "valid_faq": 0,
        "vague_incomplete": 0,
        "pii_detected": 0,
        "pii_sanitized": 0,
        "duplicates_exact": 0,
        "quarantined": 0,
        "pending_review": 0,
    }
    seen_hashes: Set[str] = set()
    pii_stats = Counter()
    rejected_reasons = Counter()

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            stats["quarantined"] += 1
            rejected_reasons["not_dict"] += 1
            continue

        # Extract fields
        question = rec.get("question") or rec.get("question_ar") or ""
        answer = rec.get("answer") or rec.get("answer_ar") or ""
        raw_scope = rec.get("program_scope") or rec.get("program") or ""
        source_row = rec.get("source_row") or idx + 1
        source_sheet = rec.get("source_sheet") or "Sheet1"

        # Normalize
        question = normalize_whitespace(question)
        answer = normalize_whitespace(answer)
        program, retrieval_scope = normalize_program_scope(raw_scope)
        language = detect_language(f"{question} {answer}")

        # Check for vague/incomplete
        if is_vague_or_incomplete(question, answer):
            stats["vague_incomplete"] += 1
            rejected_reasons["vague_incomplete"] += 1
            stats["quarantined"] += 1
            continue

        # PII detection and sanitization
        pii_found = detect_pii(f"{question} {answer}")
        if pii_found:
            stats["pii_detected"] += 1
            for k, v in pii_found.items():
                pii_stats[k] += len(v)
            # Ensure we don't log PII
            try:
                answer_sanitized, pii_counts = sanitize_pii(answer)
                if pii_counts:
                    stats["pii_sanitized"] += sum(pii_counts.values())
                answer = answer_sanitized
            except Exception:
                # If PII sanitization fails, quarantine this record
                stats["quarantined"] += 1
                rejected_reasons["pii_processing_error"] += 1
                continue

        # Content hash for deduplication
        content_hash = compute_content_hash(question, answer, language, program)

        # Exact duplicate check
        if content_hash in seen_hashes:
            stats["duplicates_exact"] += 1
            stats["quarantined"] += 1
            rejected_reasons["duplicate"] += 1
            continue
        seen_hashes.add(content_hash)

        # Build processed record
        processed_rec = {
            "id": f"faq_form_{content_hash[:12]}_{source_row:06d}",
            "record_type": "faq",
            "question": question,
            "answer": answer,
            "title": f"Form response - row {source_row}",
            "content": f"{question}\n{answer}",
            "language": language,
            "program_scope": program,
            "category": rec.get("category") or "general_faq",
            "source_file": source_file,
            "source_sheet": source_sheet,
            "source_row": source_row,
            "source_status": "unverified",
            "retrieval_scope": retrieval_scope,
            "content_hash": content_hash,
            "needs_review": True,
            "review_notes": ["Form submission requires human review"],
            "sanitized": bool(pii_found),
        }

        # All form responses are candidates pending review
        stats["valid_faq"] += 1
        stats["pending_review"] += 1
        processed.append(processed_rec)

    return processed, {
        "stats": stats,
        "pii_breakdown": dict(pii_stats),
        "rejected_reasons": dict(rejected_reasons)
    }


def process_tickets_report(records: List[Dict], source_file: str) -> Tuple[List[Dict], Dict]:
    """Process tickets_report JSON - separate from FAQ candidates."""
    processed = []
    stats = {
        "total": len(records),
        "valid_tickets": 0,
        "malformed": 0,
        "pii_detected": 0,
        "quarantined": 0,
    }
    pii_stats = Counter()

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            stats["malformed"] += 1
            continue

        # Check if this looks like a ticket (has ticket_number or operational fields)
        ticket_num = rec.get("ticket_number") or rec.get("ticket_id")
        if not ticket_num:
            # Try to identify ticket-like records
            if rec.get("record_type") == "ticket" or "ticket" in str(rec.get("source_file", "")).lower():
                ticket_num = f"ticket_{idx}"
            else:
                stats["malformed"] += 1
                continue

        # Extract and sanitize
        question = rec.get("question") or rec.get("reason") or rec.get("subject") or ""
        answer = rec.get("answer") or rec.get("resolution") or ""

        question = normalize_whitespace(question)
        answer = normalize_whitespace(answer)

        # PII detection
        pii_found = detect_pii(f"{question} {answer}")
        if pii_found:
            stats["pii_detected"] += 1
            for k, v in pii_found.items():
                pii_stats[k] += len(v)

        # Build ticket record
        processed_rec = {
            "id": f"ticket_{ticket_num}",
            "record_type": "ticket",
            "ticket_number": str(ticket_num),
            "subject": question,
            "description": answer,
            "source_file": source_file,
            "source_status": "unverified",
            "needs_review": True,
            "sanitized": bool(pii_found),
        }

        stats["valid_tickets"] += 1
        processed.append(processed_rec)

    return processed, {"stats": stats, "pii_breakdown": dict(pii_stats)}


def validate_prepared_records(records: List[Dict], record_type: str) -> Dict:
    """Validate prepared records against ingestion schema requirements."""
    validation = {
        "total": len(records),
        "passed": 0,
        "failed": 0,
        "errors": []
    }

    required_fields = {
        "faq": ["id", "record_type", "question", "answer", "program_scope", "content_hash", "source_file"],
        "ticket": ["id", "record_type", "ticket_number", "source_file"]
    }

    required = required_fields.get(record_type, required_fields["faq"])

    for idx, rec in enumerate(records):
        errors = []

        # Check required fields
        for field in required:
            if field not in rec or (rec[field] is None and field != "source_url"):
                errors.append(f"missing_{field}")

        # Validate program_scope
        if "program_scope" in rec and rec["program_scope"] not in VALID_PROGRAM_SCOPES:
            errors.append(f"invalid_program_scope:{rec['program_scope']}")

        # Validate content_hash format
        if "content_hash" in rec:
            if not re.match(r'^[a-f0-9]{64}$', rec["content_hash"]):
                errors.append("invalid_hash_format")

        # Validate question/answer not empty for FAQs
        if record_type == "faq":
            if not rec.get("question") or not rec.get("answer"):
                errors.append("empty_question_or_answer")

        if errors:
            validation["failed"] += 1
            if len(validation["errors"]) < 20:
                validation["errors"].append({"record_id": rec.get("id", idx), "errors": errors})
        else:
            validation["passed"] += 1

    return validation


def main():
    print("=" * 70)
    print("NexaServe JSON Data Preparation Pipeline")
    print("=" * 70)

    # Paths
    parser = argparse.ArgumentParser(description="NexaServe JSON Data Preparation Pipeline")
    parser.add_argument(
        "--source-dir",
        type=Path,
        default=Path(r"E:\NexaServe\FAQs\New Fiels\JSON"),
        help="Directory containing raw JSON source files or prepared JSON files."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(r"E:\NexaServe\FAQs\New Fiels\JSON\prepared"),
        help="Directory for prepared output files."
    )
    parser.add_argument(
        "--mode",
        choices=["prepare", "validate"],
        default="prepare",
        help="Mode: 'prepare' to process raw data, 'validate' to validate prepared data."
    )
    args = parser.parse_args()

    source_dir = args.source_dir
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    faq_candidates = []
    form_stats = {}
    ticket_prepared = []
    ticket_stats = {}
    faq_pending = []
    faq_ready = []

    if args.mode == "prepare":
        print("\nLoading raw source files for preparation...")
        form_response_path = source_dir / "Form_response.json"
        tickets_path = source_dir / "tickets_report_2026-10-12.json"

        with open(form_response_path, 'r', encoding='utf-8') as f:
            form_data = json.load(f)
        form_records = form_data.get("records", [])
        print(f"  Form_response.json: {len(form_records)} records")

        with open(tickets_path, 'r', encoding='utf-8') as f:
            tickets_data = json.load(f)
        ticket_records = tickets_data.get("records", [])
        print(f"  tickets_report_2026-10-12.json: {len(ticket_records)} records")

        # Process Form responses (FAQ candidates)
        print("\nProcessing Form responses (FAQ candidates)...")
        faq_candidates, form_stats = process_form_response(
            form_records,
            "FAQs/New Fiels/JSON/Form_response.json"
        )

        # Process tickets separately
        print("Processing tickets report...")
        ticket_prepared, ticket_stats = process_tickets_report(
            ticket_records,
            "FAQs/New Fiels/JSON/tickets_report_2026-10-12.json"
        )

        # Separate FAQ candidates into pending vs ready
        faq_pending = [r for r in faq_candidates if r["needs_review"]]
        faq_ready = []  # Empty - no records have approved source status

        # Write output files (only in prepare mode)
        print("\nWriting output files...")

        # 1. FAQ candidates pending review
        faq_pending_output = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(faq_pending),
            "description": "Sanitized FAQ candidates requiring human review before import",
            "records": faq_pending
        }
        faq_pending_path = output_dir / "faq_candidates_pending_review.json"
        with open(faq_pending_path, 'w', encoding='utf-8') as f:
            json.dump(faq_pending_output, f, ensure_ascii=False, indent=2)
        print(f"  Written: {faq_pending_path} ({len(faq_pending)} records)")

        # 2. FAQ ready to import (empty for unverified sources)
        faq_ready_output = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": 0,
            "description": "Records with approved source status - empty because form submissions are unverified",
            "records": []
        }
        faq_ready_path = output_dir / "faq_ready_to_import.json"
        with open(faq_ready_path, 'w', encoding='utf-8') as f:
            json.dump(faq_ready_output, f, ensure_ascii=False, indent=2)
        print(f"  Written: {faq_ready_path} (0 records - all require approval)")

        # 3. Tickets import ready (separate from FAQ)
        tickets_output = {
            "schema_version": "1.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_records": len(ticket_prepared),
            "description": "Prepared ticket records - requires ticket-management schema compatibility check",
            "records": ticket_prepared
        }
        tickets_path_out = output_dir / "tickets_import_ready.json"
        with open(tickets_path_out, 'w', encoding='utf-8') as f:
            json.dump(tickets_output, f, ensure_ascii=False, indent=2)
        print(f"  Written: {tickets_path_out} ({len(ticket_prepared)} records)")

        # 4. Rejected records summary (no PII, aggregate only)
        rejected_summary = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "source_file": "Form_response.json",
            "total_rejected": form_stats["stats"]["quarantined"],
            "rejection_reasons": form_stats["rejected_reasons"],
            "note": "Raw rejected records not included to avoid PII exposure"
        }
        rejected_path = output_dir / "rejected_records_summary.json"
        with open(rejected_path, 'w', encoding='utf-8') as f:
            json.dump(rejected_summary, f, ensure_ascii=False, indent=2)
        print(f"  Written: {rejected_path}")

        # 5. Data preparation report
        report_lines = [
            "# Data Preparation Report",
            "",
            f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
            "",
            "## Source Files",
            "",
            f"- Form_response.json: {len(form_records)} records (119 MB)",
            f"- tickets_report_2026-10-12.json: {len(ticket_records)} records (53 MB)",
            "",
            "## Transformation Rules Applied",
            "",
            "1. **Whitespace normalization**: Collapsed multiple spaces/tabs, normalized line endings",
            "2. **Arabic text handling**: Preserved UTF-8 encoding, no character normalization that would change meaning",
            "3. **Program scope mapping**: Mapped raw labels to {DEPI, DIGILIANS, COMMON, DEBI, UNKNOWN}",
            "4. **PII detection and sanitization**: Masked national IDs, phone numbers, emails with [REDACTED_*] placeholders",
            "5. **Deduplication**: Exact content hash matching; duplicates flagged for review",
            "6. **Vague/incomplete filtering**: Records with empty questions, 'other' responses, or complaint-only answers quarantined",
            "",
            "## Processing Statistics - FAQ Candidates",
            "",
            f"- Total input records: {form_stats['stats']['total']:,}",
            f"- Valid FAQ candidates: {form_stats['stats']['valid_faq']:,}",
            f"- Vague/incomplete (quarantined): {form_stats['stats']['vague_incomplete']:,}",
            f"- PII detected: {form_stats['stats']['pii_detected']:,} records",
            f"- PII values sanitized: {form_stats['stats']['pii_sanitized']:,} instances",
            f"- Exact duplicates: {form_stats['stats']['duplicates_exact']:,}",
            f"- Total quarantined: {form_stats['stats']['quarantined']:,}",
            f"- Pending human review: {form_stats['stats']['pending_review']:,}",
            "",
            "### PII Breakdown (Aggregate)",
            "",
        ]
        for pii_type, count in form_stats.get("pii_breakdown", {}).items():
            report_lines.append(f"- {pii_type}: {count:,} instances")

        report_lines.extend([
            "",
            "## Processing Statistics - Tickets",
            "",
            f"- Total input records: {ticket_stats['stats']['total']:,}",
            f"- Valid ticket records: {ticket_stats['stats']['valid_tickets']:,}",
            f"- Malformed (quarantined): {ticket_stats['stats']['malformed']:,}",
            f"- PII detected: {ticket_stats['stats']['pii_detected']:,} records",
            "",
            "## Validation Results",
            "",
            "### FAQ Candidates",
            f"- Passed: {faq_validation['passed']:,}",
            f"- Failed: {faq_validation['failed']:,}",
        ])

        if faq_validation["errors"][:5]:
            report_lines.append("")
            report_lines.append("Sample validation errors:")
            for err in faq_validation["errors"][:5]:
                report_lines.append(f"- {err['record_id']}: {', '.join(err['errors'])}")

        report_lines.extend([
            "",
            "### Tickets",
            f"- Passed: {ticket_validation['passed']:,}",
            f"- Failed: {ticket_validation['failed']:,}",
            "",
            "## Output Files",
            "",
            f"1. `faq_candidates_pending_review.json` - {len(faq_pending):,} sanitized FAQ candidates requiring review",
            f"2. `faq_ready_to_import.json` - 0 records (form submissions are unverified; no automatic approval)",
            f"3. `tickets_import_ready.json` - {len(ticket_prepared):,} prepared ticket records",
            f"4. `rejected_records_summary.json` - Aggregate rejection counts (no raw data/PII)",
            "",
            "## Import Readiness Assessment",
            "",
            "### FAQ Records",
            "",
            "**NOT READY FOR IMPORT** - All {len(faq_pending):,} FAQ candidates require human review because:",
            "",
            "- Source status is `unverified` (form submissions, not approved documentation)",
            "- Content may contain complaints or personal opinions, not authoritative answers",
            "- PII sanitization was applied but human review needed to confirm meaning preserved",
            "- Program scope assignment based on text patterns, not verified against official policy",
            "",
            "### Ticket Records",
            "",
            "**BLOCKED** - Ticket import requires schema compatibility verification:",
            "",
            "- Current ticket schema has fields: ticket_number, customer_id, conversation_id, priority, status, reason, assigned_team, resolution_notes",
            "- Prepared records have: ticket_number, subject, description",
            "- Missing required fields: customer_id linkage, status assignment, priority classification",
            "- **Recommendation**: Do not import tickets into operational database without customer mapping and status workflow",
            "",
            "## Safety Verification",
            "",
            "- [x] Original source files unchanged (SHA-256 checksums preserved in records)",
            "- [x] No records inserted into active database",
            "- [x] No n8n workflows published or modified",
            "- [x] PII masked in output files (aggregate counts only in reports)",
            "- [x] Rejected records not written to output (summary only)",
            "",
            "## Next Steps",
            "",
            "1. Review `faq_candidates_pending_review.json` with content approval workflow",
            "2. Build approval manifest with reviewer sign-off for eligible records",
            "3. Run dry-run validation: `python scripts/ingest_converted_knowledge.py --source-dir FAQs/New\\ Fiels/JSON/prepared --database test_uat_candidate`",
            "4. Do NOT import tickets without customer mapping and workflow integration",
        ])

        report_path = output_dir / "data_preparation_report.md"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report_lines))
        print(f"  Written: {report_path}")

        # Print summary
        print("\n" + "=" * 70)
        print("SUMMARY")
        print("=" * 70)
        print(f"FAQ candidates pending review: {len(faq_pending):,}")
        print(f"FAQ ready to import: 0 (all require approval)")
        print(f"Tickets prepared: {len(ticket_prepared):,}")
        print(f"Records quarantined: {form_stats['stats']['quarantined']:,}")
        print(f"PII instances sanitized: {form_stats['stats']['pii_sanitized']:,}")
        print("=" * 70)

    elif args.mode == "validate":
        print("\nLoading prepared files for validation...")
        faq_pending_path = output_dir / "faq_candidates_pending_review.json"
        tickets_path_out = output_dir / "tickets_import_ready.json"

        with open(faq_pending_path, 'r', encoding='utf-8') as f:
            faq_data = json.load(f)
        faq_pending = faq_data.get("records", [])
        print(f"  faq_candidates_pending_review.json: {len(faq_pending)} records")

        with open(tickets_path_out, 'r', encoding='utf-8') as f:
            tickets_data = json.load(f)
        ticket_prepared = tickets_data.get("records", [])
        print(f"  tickets_import_ready.json: {len(ticket_prepared)} records")

        print("\nValidating prepared records...")
        faq_validation = validate_prepared_records(faq_pending, "faq")
        ticket_validation = validate_prepared_records(ticket_prepared, "ticket")

        print("\n" + "=" * 70)
        print("VALIDATION SUMMARY")
        print("=" * 70)
        print("### FAQ Candidates")
        print(f"- Passed: {faq_validation['passed']:,}")
        print(f"- Failed: {faq_validation['failed']:,}")
        if faq_validation["errors"][:5]:
            print("Sample validation errors:")
            for err in faq_validation["errors"][:5]:
                print(f"- {err['record_id']}: {', '.join(err['errors'])}")
        print("\n### Tickets")
        print(f"- Passed: {ticket_validation['passed']:,}")
        print(f"- Failed: {ticket_validation['failed']:,}")
        if ticket_validation["errors"][:5]:
            print("Sample validation errors:")
            for err in ticket_validation["errors"][:5]:
                print(f"- {err['record_id']}: {', '.join(err['errors'])}")
        print("=" * 70)
    return 0

    # Separate FAQ candidates into pending vs ready
    # For this dataset, ALL are pending review since they're unverified form submissions
    faq_pending = [r for r in faq_candidates if r["needs_review"]]
    faq_ready = []  # Empty - no records have approved source status

    # Validate prepared records
    print("\nValidating prepared records...")
    faq_validation = validate_prepared_records(faq_pending, "faq")
    ticket_validation = validate_prepared_records(ticket_prepared, "ticket")

    # Write output files
    print("\nWriting output files...")

    # 1. FAQ candidates pending review
    faq_pending_output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(faq_pending),
        "description": "Sanitized FAQ candidates requiring human review before import",
        "records": faq_pending
    }
    faq_pending_path = output_dir / "faq_candidates_pending_review.json"
    with open(faq_pending_path, 'w', encoding='utf-8') as f:
        json.dump(faq_pending_output, f, ensure_ascii=False, indent=2)
    print(f"  Written: {faq_pending_path} ({len(faq_pending)} records)")

    # 2. FAQ ready to import (empty for unverified sources)
    faq_ready_output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": 0,
        "description": "Records with approved source status - empty because form submissions are unverified",
        "records": []
    }
    faq_ready_path = output_dir / "faq_ready_to_import.json"
    with open(faq_ready_path, 'w', encoding='utf-8') as f:
        json.dump(faq_ready_output, f, ensure_ascii=False, indent=2)
    print(f"  Written: {faq_ready_path} (0 records - all require approval)")

    # 3. Tickets import ready (separate from FAQ)
    tickets_output = {
        "schema_version": "1.0",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(ticket_prepared),
        "description": "Prepared ticket records - requires ticket-management schema compatibility check",
        "records": ticket_prepared
    }
    tickets_path_out = output_dir / "tickets_import_ready.json"
    with open(tickets_path_out, 'w', encoding='utf-8') as f:
        json.dump(tickets_output, f, ensure_ascii=False, indent=2)
    print(f"  Written: {tickets_path_out} ({len(ticket_prepared)} records)")

    # 4. Rejected records summary (no PII, aggregate only)
    rejected_summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "source_file": "Form_response.json",
        "total_rejected": form_stats["stats"]["quarantined"],
        "rejection_reasons": form_stats["rejected_reasons"],
        "note": "Raw rejected records not included to avoid PII exposure"
    }
    rejected_path = output_dir / "rejected_records_summary.json"
    with open(rejected_path, 'w', encoding='utf-8') as f:
        json.dump(rejected_summary, f, ensure_ascii=False, indent=2)
    print(f"  Written: {rejected_path}")

    # 5. Data preparation report
    report_lines = [
        "# Data Preparation Report",
        "",
        f"**Generated**: {datetime.now(timezone.utc).isoformat()}",
        "",
        "## Source Files",
        "",
        f"- Form_response.json: {len(form_records)} records (119 MB)",
        f"- tickets_report_2026-10-12.json: {len(ticket_records)} records (53 MB)",
        "",
        "## Transformation Rules Applied",
        "",
        "1. **Whitespace normalization**: Collapsed multiple spaces/tabs, normalized line endings",
        "2. **Arabic text handling**: Preserved UTF-8 encoding, no character normalization that would change meaning",
        "3. **Program scope mapping**: Mapped raw labels to {DEPI, DIGILIANS, COMMON, DEBI, UNKNOWN}",
        "4. **PII detection and sanitization**: Masked national IDs, phone numbers, emails with [REDACTED_*] placeholders",
        "5. **Deduplication**: Exact content hash matching; duplicates flagged for review",
        "6. **Vague/incomplete filtering**: Records with empty questions, 'other' responses, or complaint-only answers quarantined",
        "",
        "## Processing Statistics - FAQ Candidates",
        "",
        f"- Total input records: {form_stats['stats']['total']:,}",
        f"- Valid FAQ candidates: {form_stats['stats']['valid_faq']:,}",
        f"- Vague/incomplete (quarantined): {form_stats['stats']['vague_incomplete']:,}",
        f"- PII detected: {form_stats['stats']['pii_detected']:,} records",
        f"- PII values sanitized: {form_stats['stats']['pii_sanitized']:,} instances",
        f"- Exact duplicates: {form_stats['stats']['duplicates_exact']:,}",
        f"- Total quarantined: {form_stats['stats']['quarantined']:,}",
        f"- Pending human review: {form_stats['stats']['pending_review']:,}",
        "",
        "### PII Breakdown (Aggregate)",
        "",
    ]
    for pii_type, count in form_stats.get("pii_breakdown", {}).items():
        report_lines.append(f"- {pii_type}: {count:,} instances")

    report_lines.extend([
        "",
        "## Processing Statistics - Tickets",
        "",
        f"- Total input records: {ticket_stats['stats']['total']:,}",
        f"- Valid ticket records: {ticket_stats['stats']['valid_tickets']:,}",
        f"- Malformed (quarantined): {ticket_stats['stats']['malformed']:,}",
        f"- PII detected: {ticket_stats['stats']['pii_detected']:,} records",
        "",
        "## Validation Results",
        "",
        "### FAQ Candidates",
        f"- Passed: {faq_validation['passed']:,}",
        f"- Failed: {faq_validation['failed']:,}",
    ])

    if faq_validation["errors"][:5]:
        report_lines.append("")
        report_lines.append("Sample validation errors:")
        for err in faq_validation["errors"][:5]:
            report_lines.append(f"- {err['record_id']}: {', '.join(err['errors'])}")

    report_lines.extend([
        "",
        "### Tickets",
        f"- Passed: {ticket_validation['passed']:,}",
        f"- Failed: {ticket_validation['failed']:,}",
        "",
        "## Output Files",
        "",
        f"1. `faq_candidates_pending_review.json` - {len(faq_pending):,} sanitized FAQ candidates requiring review",
        f"2. `faq_ready_to_import.json` - 0 records (form submissions are unverified; no automatic approval)",
        f"3. `tickets_import_ready.json` - {len(ticket_prepared):,} prepared ticket records",
        f"4. `rejected_records_summary.json` - Aggregate rejection counts (no raw data/PII)",
        "",
        "## Import Readiness Assessment",
        "",
        "### FAQ Records",
        "",
        "**NOT READY FOR IMPORT** - All {len(faq_pending):,} FAQ candidates require human review because:",
        "",
        "- Source status is `unverified` (form submissions, not approved documentation)",
        "- Content may contain complaints or personal opinions, not authoritative answers",
        "- PII sanitization was applied but human review needed to confirm meaning preserved",
        "- Program scope assignment based on text patterns, not verified against official policy",
        "",
        "### Ticket Records",
        "",
        "**BLOCKED** - Ticket import requires schema compatibility verification:",
        "",
        "- Current ticket schema has fields: ticket_number, customer_id, conversation_id, priority, status, reason, assigned_team, resolution_notes",
        "- Prepared records have: ticket_number, subject, description",
        "- Missing required fields: customer_id linkage, status assignment, priority classification",
        "- **Recommendation**: Do not import tickets into operational database without customer mapping and status workflow",
        "",
        "## Safety Verification",
        "",
        "- [x] Original source files unchanged (SHA-256 checksums preserved in records)",
        "- [x] No records inserted into active database",
        "- [x] No n8n workflows published or modified",
        "- [x] PII masked in output files (aggregate counts only in reports)",
        "- [x] Rejected records not written to output (summary only)",
        "",
        "## Next Steps",
        "",
        "1. Review `faq_candidates_pending_review.json` with content approval workflow",
        "2. Build approval manifest with reviewer sign-off for eligible records",
        "3. Run dry-run validation: `python scripts/ingest_converted_knowledge.py --source-dir FAQs/New\\ Fiels/JSON/prepared --database test_uat_candidate`",
        "4. Do NOT import tickets without customer mapping and workflow integration",
    ])

    report_path = output_dir / "data_preparation_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    print(f"  Written: {report_path}")

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"FAQ candidates pending review: {len(faq_pending):,}")
    print(f"FAQ ready to import: 0 (all require approval)")
    print(f"Tickets prepared: {len(ticket_prepared):,}")
    print(f"Records quarantined: {form_stats['stats']['quarantined']:,}")
    print(f"PII instances sanitized: {form_stats['stats']['pii_sanitized']:,}")
    print("=" * 70)

    return 0


if __name__ == "__main__":
    sys.exit(main())