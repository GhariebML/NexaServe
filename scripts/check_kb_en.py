import sys
import os
sys.path.append(os.path.dirname(__file__))
from db_config import get_db_connection

conn = get_db_connection()
cur = conn.cursor()
cur.execute("""
    SELECT id, program, question, answer, question_ar 
    FROM knowledge_base 
    WHERE program IN ('DEBI', 'COMMON') 
      AND (question ILIKE '%Digital Egypt%' OR question ILIKE '%initiative%' OR question ILIKE '%pioneer%')
    LIMIT 10;
""")
rows = cur.fetchall()
print(f"Found {len(rows)} matching rows:")
for r in rows:
    print(f"ID: {r[0]} | Prog: {r[1]}")
    print(f"  Q: {r[2]}")
    print(f"  A: {r[3][:120]}...")
conn.close()
