import subprocess
import sys

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

def run_query(query_text, program_filter="program IN ('DIGILIANS', 'COMMON')"):
    cleaned_query = query_text.replace("'", "''")
    sql = f"""
    WITH words AS (
      SELECT lower(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) AS word
      FROM unnest(string_to_array('{cleaned_query}', ' ')) w
      WHERE length(regexp_replace(w, '[[:punct:][:space:]]', '', 'g')) > 2
    ), scored AS (
      SELECT id, program, category, question_ar, question,
        (SELECT count(*) * 10 FROM words WHERE question_ar ILIKE '%' || word || '%' OR question ILIKE '%' || word || '%')
        + (SELECT count(*) * 5 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw = word) OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw = word))
        + (SELECT count(*) * 2 FROM words WHERE EXISTS (SELECT 1 FROM unnest(keywords_ar) kw WHERE kw ILIKE '%' || word || '%') OR EXISTS (SELECT 1 FROM unnest(keywords) kw WHERE kw ILIKE '%' || word || '%'))
        + (SELECT count(*) FROM words WHERE answer_ar ILIKE '%' || word || '%' OR answer ILIKE '%' || word || '%') AS relevance_score
      FROM knowledge_base
      WHERE is_active = TRUE AND {program_filter}
    )
    SELECT id, program, category, question_ar, relevance_score
    FROM scored
    WHERE relevance_score > 0
    ORDER BY relevance_score DESC, id ASC
    LIMIT 3;
    """
    cmd = ["docker", "exec", "-i", "cs-postgres", "psql", "-U", "postgres", "-d", "customerservice"]
    p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8")
    out, err = p.communicate(sql)
    if err:
        print("ERR:", err)
    return out

print("--- Query 1: Digilians Tracks ---")
print(run_query("ما هي المسارات والتخصصات المتاحة في مبادرة الرواد الرقميون (Digilians)؟", "program IN ('DIGILIANS', 'COMMON')"))

print("--- Query 2: DEBI English Criteria ---")
print(run_query("What are the eligibility criteria for Digital Egypt Builders Initiative (DEBI)?", "program IN ('DEBI', 'COMMON')"))

print("--- Query 3: DEBI Age 32 ---")
print(run_query("هل يشترط السن حتى 32 سنة في مبادرة DEBI؟", "program IN ('DEBI', 'COMMON') AND category != 'disambiguation'"))
