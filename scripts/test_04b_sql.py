import sys
import os
sys.path.append(os.path.dirname(__file__))
from db_config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()

query_text = "What is the Digital Egypt Pioneers Initiative?"
program_filter = "program IN ('DEBI', 'COMMON') AND category != 'disambiguation'"

sql = f"""
WITH words AS (
  SELECT lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) AS word
  FROM unnest(string_to_array('{query_text}', ' ')) w
  WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2
), scored AS (
  SELECT id, program, category, question, answer, question_ar, answer_ar, source_attribution,
    (SELECT count(*) * 10 FROM words WHERE question_ar ILIKE '%' || word || '%' OR question ILIKE '%' || word || '%')
    + (SELECT count(*) * 5 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw = word) OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw = word))
    + (SELECT count(*) * 2 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%'))
    + (SELECT count(*) FROM words WHERE answer_ar ILIKE '%' || word || '%' OR answer ILIKE '%' || word || '%') AS lexical_score,
    (SELECT count(*) FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%')) AS keyword_match_count,
    (SELECT count(*) FROM words WHERE question_ar ILIKE '%' || word || '%' OR answer_ar ILIKE '%' || word || '%') AS content_match_count
  FROM knowledge_base
  WHERE is_active = TRUE AND {program_filter}
)
SELECT id, program, category, question, answer, lexical_score
FROM scored
WHERE lexical_score > 20
ORDER BY lexical_score DESC, keyword_match_count DESC, id ASC
LIMIT 5;
"""

cur.execute(sql)
rows = cur.fetchall()
print(f"Returned {len(rows)} rows with lexical_score > 20:")
for r in rows:
    print(f"ID: {r[0]} | Score: {r[5]} | Q: {r[3][:60]} | A: {r[4][:80]}...")
conn.close()
