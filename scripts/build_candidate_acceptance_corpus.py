#!/usr/bin/env python3
"""
NexaServe Candidate Acceptance Corpus Builder
==============================================
Builds an isolated, verified candidate knowledge corpus for local acceptance testing,
preserving exact provenance, source hashes, canonical URLs, and strict scope tagging.

Outputs:
  data/acceptance_candidate_corpus/candidate_faqs.json
  data/acceptance_candidate_corpus/candidate_faqs.jsonl
  data/acceptance_candidate_corpus/candidate_manifest.json
  data/acceptance_candidate_corpus/candidate_approval_manifest.json

NEVER overwrites historical incident artifacts under FAQs/converted/.
All candidate records are explicitly marked CANDIDATE or REVIEW_REQUIRED,
never silently claiming production approval.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

# Ensure stdout supports UTF-8
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

from convert_faqs_to_json import (
    compute_content_hash,
    compute_sha256,
    detect_language,
    extract_depi_helper_excel,
    extract_digilians_pdf,
    extract_lms_exam_pdf,
    make_stable_id,
    normalize_whitespace,
)

CORPUS_VERSION = "2026.10-candidate-v1"


def build_candidate_corpus(
    output_dir: Path,
    repo_root: Path = ROOT,
) -> Dict[str, Any]:
    output_dir = output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    metrics = {
        "accepted_for_test": 0,
        "pending_review": 0,
        "rejected": 0,
        "empty_answer": 0,
        "duplicate": 0,
        "out_of_scope": 0,
        "by_program_scope": {},
        "by_retrieval_scope": {},
        "by_source": {},
    }

    candidate_records: List[Dict[str, Any]] = []
    quarantined_records: List[Dict[str, Any]] = []
    seen_hashes: Dict[str, str] = {}  # hash -> record_id

    # --------------------------------------------------------------------------
    # Source 1: Official Scraped DEPI FAQs (https://depi.gov.eg/content/faqs)
    # --------------------------------------------------------------------------
    scraped_faqs_path = repo_root / "DEPI_Web_Scraper" / "data" / "final" / "faqs.json"
    if scraped_faqs_path.exists():
        scraped_sha = compute_sha256(scraped_faqs_path)
        rel_path = str(scraped_faqs_path.relative_to(repo_root)).replace("\\", "/")
        try:
            raw_items = json.loads(scraped_faqs_path.read_text(encoding="utf-8-sig"))
            for idx, item in enumerate(raw_items, start=1):
                q = normalize_whitespace(item.get("question") or "")
                a = normalize_whitespace(item.get("answer") or "")
                url = item.get("source_url") or "https://depi.gov.eg/content/faqs"

                if not q or not a or a.lower() in ("nan", "none", ""):
                    metrics["empty_answer"] += 1
                    metrics["rejected"] += 1
                    quarantined_records.append({
                        "source": rel_path,
                        "locator": f"item_{idx}",
                        "reason": "empty_question_or_answer",
                    })
                    continue

                c_hash = compute_content_hash(q, a, None)
                if c_hash in seen_hashes:
                    metrics["duplicate"] += 1
                    metrics["rejected"] += 1
                    quarantined_records.append({
                        "source": rel_path,
                        "locator": f"item_{idx}",
                        "reason": f"duplicate_of_{seen_hashes[c_hash]}",
                    })
                    continue

                rec_id = f"depi_official_faq_{idx:03d}_{c_hash[:10]}"
                seen_hashes[c_hash] = rec_id

                rec = {
                    "id": rec_id,
                    "record_type": "faq",
                    "question": q,
                    "answer": a,
                    "question_ar": q,
                    "answer_ar": a,
                    "title": f"DEPI Official FAQ - {q[:40]}",
                    "content": f"{q}\n{a}",
                    "language": detect_language(f"{q} {a}"),
                    "program": "DEPI",
                    "program_scope": "DEPI",
                    "retrieval_scope": "DEPI_AUTHORITATIVE",
                    "category": "official_faq",
                    "source_file": rel_path,
                    "source_locator": f"item_{idx}",
                    "source_url": url,
                    "source_sha256": scraped_sha,
                    "content_sha256": c_hash,
                    "content_hash": c_hash,
                    "source_attribution": "DEPI Official FAQ",
                    "source_status": "verified",
                    "approval_status": "CANDIDATE",
                    "needs_review": False,
                    "review_notes": ["Scraped directly from official DEPI portal FAQ."],
                    "corpus_version": CORPUS_VERSION,
                }
                candidate_records.append(rec)
                metrics["accepted_for_test"] += 1
        except Exception as e:
            print(f"[WARN] Error reading scraped faqs: {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Source 2: Official Scraped DEPI Web Pages (Home, About, Guidance, Contact)
    # --------------------------------------------------------------------------
    scraped_rag_path = repo_root / "DEPI_Web_Scraper" / "data" / "final" / "depi_rag.json"
    if scraped_rag_path.exists():
        rag_sha = compute_sha256(scraped_rag_path)
        rel_path = str(scraped_rag_path.relative_to(repo_root)).replace("\\", "/")
        try:
            rag_items = json.loads(scraped_rag_path.read_text(encoding="utf-8-sig"))
            for idx, item in enumerate(rag_items, start=1):
                content = normalize_whitespace(item.get("content") or "")
                meta = item.get("metadata") or {}
                section = normalize_whitespace(meta.get("section") or "")
                url = meta.get("source_url") or "https://depi.gov.eg"
                page_type = meta.get("page_type") or "web_page"

                if not content or len(content) < 20:
                    metrics["rejected"] += 1
                    continue

                q = f"ما هي تفاصيل {section}؟" if section else f"معلومات رسمية عن مبادرة رواد مصر الرقمية ({page_type})"
                a = content
                c_hash = compute_content_hash(q, a, content)

                if c_hash in seen_hashes:
                    metrics["duplicate"] += 1
                    continue

                rec_id = f"depi_official_web_{page_type}_{idx:02d}_{c_hash[:10]}"
                seen_hashes[c_hash] = rec_id

                rec = {
                    "id": rec_id,
                    "record_type": "reference_section",
                    "question": q,
                    "answer": a,
                    "question_ar": q,
                    "answer_ar": a,
                    "title": f"DEPI Portal - {section or page_type}",
                    "content": f"{q}\n{a}",
                    "language": detect_language(content),
                    "program": "DEPI",
                    "program_scope": "DEPI",
                    "retrieval_scope": "DEPI_AUTHORITATIVE",
                    "category": f"official_{page_type}",
                    "source_file": rel_path,
                    "source_locator": f"block_{idx}",
                    "source_url": url,
                    "source_sha256": rag_sha,
                    "content_sha256": c_hash,
                    "content_hash": c_hash,
                    "source_attribution": f"DEPI Official Web Page ({page_type})",
                    "source_status": "verified",
                    "approval_status": "CANDIDATE",
                    "needs_review": False,
                    "review_notes": [f"Scraped official portal content from {url}"],
                    "corpus_version": CORPUS_VERSION,
                }
                candidate_records.append(rec)
                metrics["accepted_for_test"] += 1
        except Exception as e:
            print(f"[WARN] Error reading scraped rag: {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Source 3: DEPI HELPER Excel (Operational Guidance - REVIEW_REQUIRED)
    # --------------------------------------------------------------------------
    helper_path = repo_root / "FAQs" / "DEPI HELPER.xlsx"
    if helper_path.exists():
        try:
            helper_recs, _ = extract_depi_helper_excel(helper_path, repo_root)
            for r in helper_recs:
                q = r.get("question") or ""
                a = r.get("answer") or ""
                if not q or not a or a.strip().lower() in ("nan", "none", ""):
                    metrics["empty_answer"] += 1
                    metrics["rejected"] += 1
                    continue
                c_hash = r["content_sha256"]
                if c_hash in seen_hashes:
                    metrics["duplicate"] += 1
                    continue
                seen_hashes[c_hash] = r["id"]

                r["approval_status"] = "REVIEW_REQUIRED"
                r["corpus_version"] = CORPUS_VERSION
                r["source_locator"] = f"{r.get('source_sheet')}:row_{r.get('source_row')}"
                r["retrieval_scope"] = "DEPI_INTERNAL_GUIDANCE"
                r["source_url"] = "https://depi.gov.eg"
                candidate_records.append(r)
                metrics["pending_review"] += 1
        except Exception as e:
            print(f"[WARN] Error reading DEPI HELPER: {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Source 4: LMS Exam PDF (Safe Exam Browser / Platform Support)
    # --------------------------------------------------------------------------
    lms_path = repo_root / "FAQs" / "FAQ LMS-English Exam.pdf"
    if lms_path.exists():
        try:
            lms_recs, _ = extract_lms_exam_pdf(lms_path, repo_root)
            for r in lms_recs:
                c_hash = r["content_sha256"]
                if c_hash in seen_hashes:
                    metrics["duplicate"] += 1
                    continue
                seen_hashes[c_hash] = r["id"]
                r["approval_status"] = "CANDIDATE"
                r["corpus_version"] = CORPUS_VERSION
                r["source_locator"] = f"page_{r.get('source_page')}"
                r["retrieval_scope"] = "GENERAL_SUPPORT"
                r["program"] = "COMMON"
                r["program_scope"] = "COMMON"
                r["source_url"] = "https://depi.gov.eg"
                candidate_records.append(r)
                metrics["accepted_for_test"] += 1
        except Exception as e:
            print(f"[WARN] Error reading LMS PDF: {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Source 5: Digilians PDF (Isolated Digilians Scope - OUT_OF_SCOPE for DEPI)
    # --------------------------------------------------------------------------
    digi_path = repo_root / "FAQs" / "FAQ final-Digilians.pdf"
    if digi_path.exists():
        try:
            digi_recs, _ = extract_digilians_pdf(digi_path, repo_root)
            for r in digi_recs:
                c_hash = r["content_sha256"]
                if c_hash in seen_hashes:
                    metrics["duplicate"] += 1
                    continue
                seen_hashes[c_hash] = r["id"]
                r["approval_status"] = "OUT_OF_SCOPE"
                r["corpus_version"] = CORPUS_VERSION
                r["source_locator"] = f"page_{r.get('source_page')}"
                r["retrieval_scope"] = "DIGILIANS"
                r["program"] = "DIGILIANS"
                r["program_scope"] = "DIGILIANS"
                r["source_url"] = "https://digilians.gov.eg"
                candidate_records.append(r)
                metrics["out_of_scope"] += 1
        except Exception as e:
            print(f"[WARN] Error reading Digilians PDF: {e}", file=sys.stderr)

    # --------------------------------------------------------------------------
    # Compute Aggregations
    # --------------------------------------------------------------------------
    for r in candidate_records:
        prog = r.get("program_scope", "UNKNOWN")
        r_scope = r.get("retrieval_scope", "UNKNOWN")
        src = r.get("source_file", "UNKNOWN")
        metrics["by_program_scope"][prog] = metrics["by_program_scope"].get(prog, 0) + 1
        metrics["by_retrieval_scope"][r_scope] = metrics["by_retrieval_scope"].get(r_scope, 0) + 1
        metrics["by_source"][src] = metrics["by_source"].get(src, 0) + 1

    # Write candidate dataset files
    faqs_json = output_dir / "candidate_faqs.json"
    faqs_jsonl = output_dir / "candidate_faqs.jsonl"
    manifest_json = output_dir / "candidate_manifest.json"
    approval_queue = output_dir / "candidate_approval_queue.json"

    dataset_envelope = {
        "schema_version": "2.0-candidate",
        "corpus_version": CORPUS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "total_records": len(candidate_records),
        "metrics": metrics,
        "records": candidate_records,
    }

    with open(faqs_json, "w", encoding="utf-8") as f:
        json.dump(dataset_envelope, f, ensure_ascii=False, indent=2)

    with open(faqs_jsonl, "w", encoding="utf-8") as f:
        for r in candidate_records:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    manifest_envelope = {
        "pipeline_version": "2.0-acceptance",
        "corpus_version": CORPUS_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "output_directory": str(output_dir.relative_to(repo_root)).replace("\\", "/"),
        "total_candidate_records": len(candidate_records),
        "quarantined_records_count": len(quarantined_records),
        "quarantined_samples": quarantined_records[:10],
        "metrics": metrics,
    }
    with open(manifest_json, "w", encoding="utf-8") as f:
        json.dump(manifest_envelope, f, ensure_ascii=False, indent=2)

    approval_queue = output_dir / "candidate_approval_queue.json"

    # Build pending-approval queue (no approvals invented)
    pending = []
    for r in candidate_records:
        status = r.get("approval_status")
        if status in ("CANDIDATE", "REVIEW_REQUIRED", "OUT_OF_SCOPE"):
            pending.append({
                "source_file": r.get("source_file"),
                "source_record_id": r.get("id"),
                "content_hash": r.get("content_hash"),
                "program": r.get("program"),
                "retrieval_scope": r.get("retrieval_scope"),
                "approval_status": status,
                "evidence_reference": None,
                "decision": None,
                "reviewer_identity": None,
            })

    queue_doc = {
        "queue_version": "1.0-pending",
        "purpose": "Pending human review. No approvals are granted by this generator.",
        "pending_records_count": len(pending),
        "pending_records": pending,
    }
    with open(approval_queue, "w", encoding="utf-8") as f:
        json.dump(queue_doc, f, ensure_ascii=False, indent=2)

    return {
        "candidate_faqs_json": faqs_json,
        "candidate_faqs_jsonl": faqs_jsonl,
        "candidate_manifest_json": manifest_json,
        "candidate_approval_queue": approval_queue,
        "total_records": len(candidate_records),
        "metrics": metrics,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=ROOT / "data" / "acceptance_candidate_corpus",
        help="Target isolated candidate output directory.",
    )
    args = parser.parse_args()
    res = build_candidate_corpus(args.output_dir, ROOT)
    print(json.dumps(res["metrics"], indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


