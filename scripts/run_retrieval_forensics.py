"""Replay the active 04B scoring query directly, without invoking generation."""
import json
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from db_config import get_db_connection  # noqa: E402

cases = json.loads((ROOT / "tests" / "response_quality_cases.json").read_text(encoding="utf-8"))
output = ROOT / "logs" / "runtime_forensic" / "rag_top10_all_30_after_fix.jsonl"
query_sql = """WITH words AS (
 SELECT lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) AS word
 FROM unnest(string_to_array(%s, ' ')) w
 WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2
), scored AS (
 SELECT id,program,category,question_ar,answer_ar,question,answer,source_attribution,source_url,
  (SELECT count(*)*10 FROM words WHERE question_ar ILIKE '%%'||word||'%%' OR question ILIKE '%%'||word||'%%')
 +(SELECT count(*)*5 FROM words WHERE EXISTS(SELECT 1 FROM unnest(keywords_ar) kw WHERE kw=word) OR EXISTS(SELECT 1 FROM unnest(keywords) kw WHERE kw=word))
 +(SELECT count(*)*2 FROM words WHERE EXISTS(SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%%'||word||'%%') OR EXISTS(SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%%'||word||'%%'))
 +(SELECT count(*) FROM words WHERE answer_ar ILIKE '%%'||word||'%%' OR answer ILIKE '%%'||word||'%%') AS lexical_score,
 (1-(embedding <=> %s::vector))*50 AS semantic_score,
 (SELECT count(*) FROM words WHERE EXISTS(SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%%'||word||'%%') OR EXISTS(SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%%'||word||'%%')) AS keyword_match_count,
  (SELECT count(*) FROM words WHERE question_ar ILIKE '%%'||word||'%%' OR answer_ar ILIKE '%%'||word||'%%') AS content_match_count,
  CASE WHEN category = '{topic_category}' THEN 35 ELSE 0 END AS topic_boost
 FROM knowledge_base WHERE is_active AND 
 {program_filter}
)
SELECT id,program,category,source_attribution,source_url,question_ar,answer_ar,
 lexical_score,semantic_score,keyword_match_count,content_match_count,
 lexical_score+COALESCE(semantic_score,0)+topic_boost AS relevance_score
FROM scored WHERE lexical_score+COALESCE(semantic_score,0)>20
ORDER BY relevance_score DESC,keyword_match_count DESC,id ASC LIMIT 10"""

STOP_WORDS = "'the','what','who','which','when','where','why','how','are','is','does','did','do','and','for','with','from','about','after','before','between','into','your','please','ignore','previous','instructions','reveal','system','prompt','depi','debi','digilians'"
query_sql = query_sql.replace(
    "WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2",
    "WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2 AND lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) NOT IN (" + STOP_WORDS + ")",
).replace("FROM scored WHERE lexical_score+COALESCE(semantic_score,0)>20", "FROM scored")

def filter_for(program):
    return {
        "DEBI": "program IN ('DEBI','COMMON') AND category NOT IN ('disambiguation','comparison')",
        "DIGILIANS": "program IN ('DIGILIANS','COMMON') AND category NOT IN ('disambiguation','comparison')",
        "COMPARISON": "program IN ('DIGILIANS','DEBI','COMMON')",
        "AMBIGUOUS": "category IN ('disambiguation','comparison')",
        "COMMON": "program IN ('DIGILIANS','DEBI','COMMON')",
    }.get(program, "program IN ('DIGILIANS','DEBI','COMMON')")

def topic_for(program, query):
    q = query.lower()
    prefix = "debi_" if program == "DEBI" else "depi_"
    if program not in ("DEBI", "DIGILIANS"):
        return ""
    if program == "DEBI" and ("من المؤهل" in q or "who is eligible" in q):
        return ""
    if any(x in q for x in ["شروط", "شرط", "اهلية", "أهلية", "التقديم", "قبول", "التقدير", "معدل", "السن", "عمر", "مؤهلة", "المؤهلة", "المطلوب", "مطلوب", "مستوى", "gpa", "grade", "age", "required", "requirements", "requirement", "eligibility", "eligible", "apply", "admission", "who can", "من يستطيع", "لغير خريجي"]):
        return prefix + "conditions"
    if any(x in q for x in ["منحة", "منح", "المنح", "مزايا", "تمويل", "scholarship", "grant", "benefit", "funding"]):
        return prefix + "benefits"
    if any(x in q for x in ["مسار", "مسارات", "تخصص", "تخصصات", "track", "specialization"]):
        return prefix + "tracks"
    if any(x in q for x in ["أونلاين", "اونلاين", "عن بعد", "online", "remote"]):
        return "debi_training" if program == "DEBI" else "depi_study_system"
    return ""

retrieval_cases = cases + [{
    "id": "official-source-trace-01", "program": "DEBI",
    "query": "من المؤهل للتدريب في DEPI؟",
}]
with output.open("w", encoding="utf-8") as out:
    for case in retrieval_cases:
        emb = requests.post(
            "http://127.0.0.1:11434/api/embed",
            json={"model": "nomic-embed-text", "input": case["query"]},
            timeout=30,
        )
        emb.raise_for_status()
        vector = emb.json()["embeddings"][0]
        topic_category = topic_for(case["program"], case["query"])
        sql = query_sql.format(program_filter=filter_for(case["program"]), topic_category=topic_category)
        conn = get_db_connection()
        try:
            with conn.cursor() as cur:
                cur.execute(sql, (case["query"], vector))
                rows = cur.fetchall()
        finally:
            conn.close()
        record = {
            "case_id": case["id"], "query": case["query"],
            "program_filter_scope": case["program"], "top10": [
                {"rank": rank, "id": row[0], "program": row[1], "category": row[2],
                 "source": row[3], "source_url": row[4], "question": row[5],
                 "answer": row[6], "lexical_score": float(row[7]),
                 "semantic_score": float(row[8]), "keyword_match_count": row[9],
                 "content_match_count": row[10], "score": float(row[11])}
                for rank, row in enumerate(rows, 1)
            ]
        }
        top = record["top10"][0] if record["top10"] else None
        record["topic_category"] = topic_category
        record["evidence_gate"] = bool(top and (
            top["lexical_score"] >= 15
            or (top["keyword_match_count"] >= 1 and top["content_match_count"] >= 2)
            or (topic_category and top["category"] == topic_category)
            or (case["program"] == "COMPARISON" and top["program"] == "COMMON" and top["category"] == "comparison")
        ))
        out.write(json.dumps(record, ensure_ascii=False) + "\n")
        out.flush()
        print(json.dumps({"case_id": case["id"], "count": len(rows), "top_id": top and top["id"], "top_program": top and top["program"], "top_category": top and top["category"], "score": top and round(top["score"],1), "evidence_gate": record["evidence_gate"]}, ensure_ascii=False), flush=True)
print(f"saved={output} query_count={len(retrieval_cases)} ({len(cases)} quality cases plus official-source replay)")
