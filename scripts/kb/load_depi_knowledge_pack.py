"""Loads infra/knowledge/depi_knowledge_pack_r5.json into knowledge_base with fresh embeddings.

Idempotent: pack rows are matched by (pack attribution, English question); unchanged rows are
skipped, changed rows are re-embedded and versioned, and pack rows no longer in the file are
deactivated. The official depi.gov.eg FAQ rows stay active as the audited source records; the
pack entries restate them as complete answers and outrank them in retrieval.

Usage:  python scripts/kb/load_depi_knowledge_pack.py [--dry-run]
"""
import argparse
import json
import os
import sys
from pathlib import Path

import psycopg2
import requests

ROOT = Path(__file__).resolve().parents[2]
PACK_FILE = ROOT / "infra" / "knowledge" / "depi_knowledge_pack_r5.json"
EMBED_URL = os.getenv("OLLAMA_EMBED_URL", "http://127.0.0.1:11435/api/embed")
EMBED_MODEL = os.getenv("EMBED_MODEL", "nomic-embed-text")

def load_env():
    env = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        key, sep, value = line.strip().partition("=")
        if sep and not key.startswith("#"):
            env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def embed(e):
    text = "\n".join([e["question_ar"], e["question"], " ".join(e["keywords_ar"] + e["keywords"]), e["answer_ar"]])[:6000]
    r = requests.post(EMBED_URL, json={"model": EMBED_MODEL, "input": text}, timeout=120)
    r.raise_for_status()
    vector = r.json()["embeddings"][0]
    if len(vector) != 768:
        raise RuntimeError(f"unexpected embedding dimension {len(vector)}")
    return "[" + ",".join(f"{v:.7f}" for v in vector) + "]"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    pack = json.loads(PACK_FILE.read_text(encoding="utf-8"))
    prefix = pack["pack"] + " |%"
    env = load_env()
    conn = psycopg2.connect(host="127.0.0.1", port=int(env.get("POSTGRES_PORT", 5432)), dbname="nexaserve_final",
                            user=env["POSTGRES_USER"], password=env["POSTGRES_PASSWORD"])
    counts = {"inserted": 0, "updated": 0, "unchanged": 0, "retired": 0}
    try:
        with conn, conn.cursor() as cur:
            cur.execute("SELECT id, question, content_hash FROM knowledge_base WHERE source_attribution LIKE %s", (prefix,))
            existing = {q: (i, h) for i, q, h in cur.fetchall()}
            seen = set()
            for e in pack["entries"]:
                seen.add(e["question"])
                row = existing.get(e["question"])
                if row and row[1] == e["content_hash"]:
                    cur.execute("UPDATE knowledge_base SET is_active = TRUE WHERE id = %s", (row[0],))
                    counts["unchanged"] += 1
                    continue
                vector = embed(e)
                fields = (e["category"], e["question"], e["answer"], e["keywords"], e["question_ar"], e["answer_ar"],
                          e["keywords_ar"], e["program"], e["source_attribution"], e["content_hash"], vector,
                          e["source_url"], e["retrieval_scope"])
                if row:
                    cur.execute("""UPDATE knowledge_base SET category=%s, question=%s, answer=%s, keywords=%s, question_ar=%s,
                                   answer_ar=%s, keywords_ar=%s, program=%s, source_attribution=%s, content_hash=%s,
                                   embedding=%s::vector, source_url=%s, retrieval_scope=%s, is_active=TRUE,
                                   last_verified_at=NOW() WHERE id=%s""", fields + (row[0],))
                    cur.execute("""INSERT INTO knowledge_base_versions (article_id, version, changed_fields, changed_by)
                                   SELECT %s, COALESCE(MAX(version), 0) + 1, %s::jsonb, 'depi_knowledge_pack'
                                   FROM knowledge_base_versions WHERE article_id = %s""",
                                (row[0], json.dumps({"content_hash": e["content_hash"]}), row[0]))
                    counts["updated"] += 1
                else:
                    cur.execute("""INSERT INTO knowledge_base (category, question, answer, keywords, question_ar, answer_ar,
                                   keywords_ar, program, source_attribution, content_hash, embedding, source_url,
                                   retrieval_scope, is_active, last_verified_at)
                                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::vector,%s,%s,TRUE,NOW())""", fields)
                    counts["inserted"] += 1
            for question, (row_id, _) in existing.items():
                if question not in seen:
                    cur.execute("UPDATE knowledge_base SET is_active = FALSE WHERE id = %s AND is_active", (row_id,))
                    counts["retired"] += cur.rowcount
            if args.dry_run:
                raise KeyboardInterrupt
    except KeyboardInterrupt:
        conn.rollback()
        print("dry run - rolled back")
    finally:
        conn.close()
    print(json.dumps(counts))
    return 0


if __name__ == "__main__":
    sys.exit(main())
