#!/usr/bin/env python3
"""Plan or apply reviewed JSON FAQ records to an isolated NexaServe KB.

Application requires an explicit approval manifest and never deletes records.
All unverified, out-of-scope, incomplete, or duplicate records stay quarantined.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SOURCE_DIR = ROOT / "FAQs" / "converted"
DB_SCRIPTS = ROOT / "deployment" / "application" / "ingestion" / "scripts"


def canonical_hash(question: str, answer: str, language: str, program: str, category: str) -> str:
    value = {"answer": answer.strip(), "category": category.strip(), "language": language.strip().lower(),
             "program": program.strip().upper(), "question": question.strip()}
    canonical = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def gather() -> tuple[list[dict[str, Any]], Counter[str]]:
    candidates: list[dict[str, Any]] = []
    counts: Counter[str] = Counter()
    seen_content: set[str] = set()
    for path in sorted(SOURCE_DIR.rglob("*.json")):
        try:
            root = json.loads(path.read_text(encoding="utf-8-sig"))
        except (OSError, UnicodeError, json.JSONDecodeError):
            counts["failed"] += 1
            continue
        if not isinstance(root, dict):
            counts["skipped"] += 1
            continue
        records = next((root.get(k) for k in ("records", "faqs", "items", "tickets") if isinstance(root.get(k), list)), [])
        if not records:
            counts["skipped"] += 1
            continue
        for index, record in enumerate(records):
            if not isinstance(record, dict):
                counts["quarantined"] += 1
                continue
            record_id = str(record.get("id") or index)
            source_status = str(record.get("source_status") or "unverified").lower()
            scope_label = str(record.get("program_scope") or record.get("program") or "AMBIGUOUS").upper()
            q = str(record.get("question") or record.get("question_ar") or "").strip()
            a = str(record.get("answer") or record.get("answer_ar") or "").strip()
            rtype = str(record.get("record_type") or ("ticket" if "tickets" in root else "faq")).lower()
            content_hash = canonical_hash(q, a, str(record.get("language") or "und"), scope_label, str(record.get("category") or "general"))
            source_duplicate = bool(record.get("is_duplicate") or record.get("duplicate_of"))
            exact_duplicate = bool(q and a and content_hash in seen_content)
            if q and a:
                seen_content.add(content_hash)
            if source_duplicate or exact_duplicate:
                reason = "duplicate_record"
                counts["duplicated"] += 1
            elif not q or not a or rtype != "faq":
                reason = "incomplete_or_non_faq"
                counts["quarantined"] += 1
            elif scope_label not in {"DEPI", "GENERAL_SUPPORT"}:
                reason = "scope_unverified_or_out_of_scope"
                counts["quarantined"] += 1
            elif source_status != "verified":
                reason = "source_unverified"
                counts["quarantined"] += 1
            else:
                reason = "awaiting_approval_manifest"
                counts["skipped"] += 1
            candidates.append({
                "source_file": path.relative_to(ROOT).as_posix(),
                "source_record_id": record_id,
                "source_index": index,
                "record_type": rtype,
                "program_label": scope_label,
                "retrieval_scope": "DEPI_AUTHORITATIVE" if scope_label == "DEPI" else "GENERAL_SUPPORT",
                "language": str(record.get("language") or "und"),
                "question": q,
                "answer": a,
                "category": str(record.get("category") or "general")[:50],
                "source_url": record.get("source_url"),
                "source_status": source_status,
                "disposition": reason,
                "content_hash": content_hash,
            })
    return candidates, counts


def approved(candidates: list[dict[str, Any]], approval_path: Path | None) -> list[dict[str, Any]]:
    if approval_path is None:
        return []
    data = json.loads(approval_path.read_text(encoding="utf-8-sig"))
    entries = data.get("approved_records", []) if isinstance(data, dict) else []
    approvals = {(str(x.get("source_file")), str(x.get("source_record_id")), str(x.get("retrieval_scope")))
                 for x in entries if isinstance(x, dict) and x.get("reviewer")}
    return [r for r in candidates if r["disposition"] in {"awaiting_approval_manifest", "duplicate_record"}
            and r["source_status"] == "verified"
            and (r["source_file"], r["source_record_id"], r["retrieval_scope"]) in approvals]


def apply_records(records: list[dict[str, Any]], db_name: str, model: str, ollama_url: str) -> dict[str, int]:
    if not records:
        return {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    os.environ["CS_DB_NAME"] = db_name
    os.environ["EMBED_MODEL"] = model
    os.environ["OLLAMA_EMBED_URL"] = ollama_url
    sys.path.insert(0, str(DB_SCRIPTS))
    import requests  # type: ignore
    import db_config  # type: ignore
    from psycopg2.extras import Json  # type: ignore

    conn = db_config.get_db_connection()
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "failed": 0}
    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute("""CREATE TABLE IF NOT EXISTS knowledge_base_source_map (
                    knowledge_base_id INTEGER NOT NULL REFERENCES knowledge_base(id),
                    source_file TEXT NOT NULL, source_record_id TEXT NOT NULL,
                    content_hash CHAR(64) NOT NULL, source_file_sha256 CHAR(64) NOT NULL,
                    source_metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
                    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                    PRIMARY KEY (source_file, source_record_id), UNIQUE (knowledge_base_id, source_file, source_record_id)
                )""")
                cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name='knowledge_base'")
                columns = {row[0] for row in cur.fetchall()}
                required = {"id", "program", "category", "question", "answer", "question_ar", "answer_ar", "source_attribution", "source_url", "content_hash", "embedding", "is_active", "retrieval_scope"}
                if not required.issubset(columns):
                    raise RuntimeError("Target knowledge_base schema is missing required columns")
                for r in records:
                    try:
                        cur.execute("SELECT knowledge_base_id FROM knowledge_base_source_map WHERE source_file=%s AND source_record_id=%s", (r["source_file"], r["source_record_id"]))
                        mapped = cur.fetchone()
                        cur.execute("SELECT id FROM knowledge_base WHERE content_hash=%s", (r["content_hash"],))
                        existing = cur.fetchone()
                        if mapped and existing and mapped[0] == existing[0]:
                            counts["unchanged"] += 1
                            continue
                        response = requests.post(ollama_url, json={"model": model, "input": r["question"] + "\n" + r["answer"]}, timeout=90)
                        response.raise_for_status()
                        payload = response.json()
                        vector = (payload.get("embeddings") or [payload.get("embedding")])[0]
                        if not vector or len(vector) != db_config.EMBED_DIMENSION:
                            raise RuntimeError("Embedding response has an invalid dimension")
                        if existing:
                            kb_id = existing[0]
                            counts["unchanged"] += 1
                        else:
                            program = "DEPI" if r["retrieval_scope"] == "DEPI_AUTHORITATIVE" else "COMMON"
                            attribution = f"{r['source_file']}#{r['source_record_id']}"
                            cur.execute("""INSERT INTO knowledge_base
                                (program, category, question, answer, question_ar, answer_ar,
                                 source_attribution, source_url, content_hash, embedding, is_active, retrieval_scope)
                                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,TRUE,%s) RETURNING id""",
                                (program, r["category"], r["question"], r["answer"], r["question"], r["answer"],
                                 attribution, r["source_url"], r["content_hash"], vector, r["retrieval_scope"]))
                            kb_id = cur.fetchone()[0]
                            counts["inserted"] += 1
                        cur.execute("""INSERT INTO knowledge_base_source_map
                            (knowledge_base_id, source_file, source_record_id, content_hash, source_file_sha256, source_metadata)
                            VALUES (%s,%s,%s,%s,%s,%s)
                            ON CONFLICT (source_file, source_record_id) DO UPDATE SET
                            knowledge_base_id=EXCLUDED.knowledge_base_id, content_hash=EXCLUDED.content_hash,
                            source_file_sha256=EXCLUDED.source_file_sha256, source_metadata=EXCLUDED.source_metadata""",
                            (kb_id, r["source_file"], r["source_record_id"], r["content_hash"],
                             hashlib.sha256((ROOT / r["source_file"]).read_bytes()).hexdigest(),
                             Json({"language": r["language"], "category": r["category"], "source_url": r["source_url"]})))
                    except Exception:
                        counts["failed"] += 1
                        raise
    finally:
        conn.close()
    return counts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", default="nexaserve_final", help="Candidate database; default is nexaserve_final.")
    parser.add_argument("--approval-file", type=Path, help="Reviewed JSON with approved_records and reviewer fields.")
    parser.add_argument("--apply", action="store_true", help="Apply approved records transactionally; default is a read-only plan.")
    parser.add_argument("--embedding-model", default=os.getenv("EMBED_MODEL", "nomic-embed-text"))
    parser.add_argument("--ollama-embed-url", default=os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11434/api/embed"))
    parser.add_argument("--report", type=Path, default=ROOT / "docs" / "knowledge_ingestion" / "ingestion_summary.json")
    args = parser.parse_args()
    if args.database not in {"nexaserve_final", "test_uat_candidate"}:
        parser.error("Only isolated candidate databases are allowed; customerservice is prohibited.")
    if args.apply and args.approval_file is None:
        parser.error("--apply requires --approval-file with explicit reviewer approvals.")
    records, counts = gather()
    ready = approved(records, args.approval_file)
    result: dict[str, Any] = {
        "source_directory": "FAQs/converted", "target_database": args.database,
        "mode": "apply" if args.apply else "plan", "embedding_model": args.embedding_model,
        "embedding_dimension_expected": 768, "counts": dict(counts),
        "approved_records": len(ready), "inserted": 0, "updated": 0, "unchanged": 0,
        "duplicated": counts["duplicated"], "skipped": counts["skipped"],
        "quarantined": counts["quarantined"], "failed": counts["failed"],
        "source_record_decisions": [{k: v for k, v in r.items() if k not in {"question", "answer"}} for r in records],
        "database_write_performed": False,
    }
    if args.apply and ready:
        result.update(apply_records(ready, args.database, args.embedding_model, args.ollama_embed_url))
        result["database_write_performed"] = True
        result["approved_records"] = len(ready)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in result.items() if k != "source_record_decisions"}, ensure_ascii=False, indent=2))
    return 1 if result["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
