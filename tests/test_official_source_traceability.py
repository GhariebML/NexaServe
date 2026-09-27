"""Audits the captured, synthetic DEPI official FAQ replay end to end.

The trace artifact is generated from a live synthetic webchat execution, not a mock.
The generation acceptance assertion intentionally fails when the captured trace
shows that Qwen errored and the answer came from the curated fallback.
"""
import hashlib
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from db_config import get_db_connection  # noqa: E402

TRACE_PATH = ROOT / "logs" / "runtime_forensic" / "official_faq_trace.json"
SOURCE_PATH = ROOT / "DEPI_Web_Scraper" / "data" / "final" / "faqs.json"
FACT_QUESTION = "من المؤهل للتدريب؟"
FACT_ANSWER = "طلاب و خريجو الكليات بالجامعات المصرية حسب المسار."


def _source_fact():
    records = json.loads(SOURCE_PATH.read_text(encoding="utf-8"))
    return next(item for item in records if item["question"] == FACT_QUESTION)


def _trace():
    return json.loads(TRACE_PATH.read_text(encoding="utf-8-sig"))


def test_official_faq_source_maps_to_active_db_record_and_embedding():
    source = _source_fact()
    expected_hash = hashlib.sha256(
        f"{source['question']}||{source['answer']}".encode("utf-8")
    ).hexdigest()
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, answer_ar, source_url, content_hash, is_active,
                          embedding IS NOT NULL, vector_dims(embedding)
                     FROM knowledge_base
                     WHERE program='DEBI' AND category='scraped_faq' AND question_ar=%s""",
                (source["question"],),
            )
            row = cur.fetchone()
    finally:
        conn.close()
    assert row is not None
    assert row[1] == source["answer"] == FACT_ANSWER
    assert row[2] == source["source_url"] == "https://depi.gov.eg/content/faqs"
    assert row[3] == expected_hash
    assert row[4] is True and row[5] is True and row[6] == 768


def test_official_faq_ranks_first_and_matches_live_context_and_final_response():
    source = _source_fact()
    embedding_response = requests.post(
        "http://127.0.0.1:11434/api/embed",
        json={"model": "nomic-embed-text", "input": "من المؤهل للتدريب في DEPI؟"},
        timeout=30,
    )
    embedding_response.raise_for_status()
    vector = embedding_response.json()["embeddings"][0]
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """WITH words AS (
                       SELECT lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) AS word
                         FROM unnest(string_to_array(%s, ' ')) w
                   WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2
                     AND lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) NOT IN
                       ('the','what','who','which','when','where','why','how','are','is','does','did','do','and','for','with','from','about','after','before','between','into','your','please','ignore','previous','instructions','reveal','system','prompt','depi','debi','digilians')
                   ), scored AS (
                       SELECT id, program, category, answer_ar, source_url,
                           (SELECT count(*)*10 FROM words WHERE question_ar ILIKE '%%'||word||'%%' OR question ILIKE '%%'||word||'%%')
                         + (SELECT count(*)*5 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw=word) OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw=word))
                         + (SELECT count(*)*2 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%%'||word||'%%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%%'||word||'%%'))
                         + (SELECT count(*) FROM words WHERE answer_ar ILIKE '%%'||word||'%%' OR answer ILIKE '%%'||word||'%%')
                         + (1-(embedding <=> %s::vector))*50 AS rank_score
                       FROM knowledge_base
                       WHERE is_active AND program IN ('DEBI','COMMON')
                         AND category NOT IN ('disambiguation','comparison')
                   )
                   SELECT id,program,category,answer_ar,source_url,rank_score
                     FROM scored ORDER BY rank_score DESC,id ASC LIMIT 10""",
                ("من المؤهل للتدريب في DEPI؟", vector),
            )
            results = cur.fetchall()
    finally:
        conn.close()

    assert results[0][1:5] == (
        "DEBI", "scraped_faq", source["answer"], source["source_url"]
    )
    trace = _trace()
    assert trace["database_record"]["id"] == results[0][0]
    assert trace["nodes"]["Query Bilingual Knowledge Base"][0]["retrieved"][0]["id"] == results[0][0]
    context = trace["nodes"]["Check if LLM Needed"][0]["context"]
    assert source["answer"] in context
    assert trace["nodes"]["Guardrail & Professional Formatter"][0]["final_reply"] == source["answer"]
    assert trace["webhook"]["response"]["response"] == source["answer"]
    ai_rows = [row for row in trace["logged_messages"] if row["sender_type"] == "ai"]
    assert len(ai_rows) == 1 and ai_rows[0]["content"] == source["answer"]


def test_final_answer_was_generated_by_qwen_not_a_fallback():
    """Do not pass readiness when an HTTP 200 concealed a failed LLM call."""
    trace = _trace()
    generation = trace["nodes"]["Qwen RAG Grounded Response"][0]
    assert generation["status"] == "success" and not generation.get("error"), (
        "Qwen did not generate this answer; active workflow returned a curated fallback: "
        f"{generation.get('error')}"
    )
