"""Attach synthetic webhook, source, database, and response evidence to a trace."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from db_config import get_db_connection  # noqa: E402

request_id = "forensic-official-faq-verify-01"
logs = ROOT / "logs" / "runtime_forensic"
trace = json.loads((logs / "official_faq_trace.json").read_text(encoding="utf-8-sig"))
replay = json.loads((logs / "official_faq_replay.json").read_text(encoding="utf-8"))
final_webchat = json.loads((logs / "final_live_ambiguous.json").read_text(encoding="utf-8"))
retrieval_after_fix = next(
    item for item in (
        json.loads(line) for line in (logs / "rag_top10_all_30_after_fix.jsonl").read_text(encoding="utf-8").splitlines()
    ) if item["case_id"] == "official-source-trace-01"
)
source_items = json.loads((ROOT / "DEPI_Web_Scraper" / "data" / "final" / "faqs.json").read_text(encoding="utf-8"))
source = next(item for item in source_items if item["question"] == "من المؤهل للتدريب؟")

conn = get_db_connection()
try:
    with conn.cursor() as cursor:
        cursor.execute(
            """SELECT id, program, category, question_ar, answer_ar, source_attribution,
                      source_url, content_hash, embedding IS NOT NULL, vector_dims(embedding)
                 FROM knowledge_base
                 WHERE program='DEBI' AND category='scraped_faq' AND question_ar=%s""",
            (source["question"],),
        )
        row = cursor.fetchone()
        if not row:
            raise RuntimeError("Scraped FAQ source record is absent from knowledge_base")
        cursor.execute(
            """SELECT sender_type, content, metadata
                 FROM messages WHERE metadata->>'request_id'=%s ORDER BY created_at""",
            (request_id,),
        )
        messages = cursor.fetchall()
        cursor.execute(
            """SELECT execution_id, event_type, payload
                 FROM audit_logs WHERE payload->>'request_id'=%s ORDER BY created_at""",
            (request_id,),
        )
        audit = cursor.fetchall()
finally:
    conn.close()

trace["source_fact"] = source
trace["database_record"] = {
    "id": row[0], "program": row[1], "category": row[2], "question": row[3],
    "answer": row[4], "source_attribution": row[5], "source_url": row[6],
    "content_hash": row[7], "embedding_present": row[8], "embedding_dimensions": row[9],
}
trace["webhook"] = replay
trace["retrieval_replay_after_fix"] = retrieval_after_fix
trace["final_live_correlation_probe"] = final_webchat
trace["logged_messages"] = [
    {"sender_type": sender, "content": content, "metadata": metadata}
    for sender, content, metadata in messages
]
trace["audit_events"] = [
    {"execution_id": execution_id, "event_type": event, "payload": payload}
    for execution_id, event, payload in audit
]
(logs / "official_faq_trace.json").write_text(
    json.dumps(trace, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
print(f"trace_saved request={request_id} db_id={row[0]} retrieval_rank=1 log_rows={len(messages)}")
