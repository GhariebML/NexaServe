import psycopg2
import requests
from pgvector.psycopg2 import register_vector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_config import get_db_connection, EMBED_MODEL, OLLAMA_EMBED_URL as OLLAMA_URL

conn = get_db_connection()
cur = conn.cursor()

cur.execute("SELECT id, question, question_ar, answer, answer_ar FROM knowledge_base WHERE embedding IS NULL")
rows = cur.fetchall()
logger.info(f"Found {len(rows)} records without embeddings.")

for row in rows:
    rid, q, q_ar, a, a_ar = row
    text_to_embed = f"{q_ar or q}\n{a_ar or a}"
    
    try:
        resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": text_to_embed})
        data = resp.json()
        emb = data.get("embeddings", [[]])[0]
        if emb:
            cur.execute("UPDATE knowledge_base SET embedding = %s WHERE id = %s", (emb, rid))
            logger.info(f"Updated embedding for record {rid}: {q_ar[:40] if q_ar else q[:40]}")
    except Exception as e:
        logger.error(f"Failed to embed record {rid}: {e}")

conn.commit()
cur.close()
conn.close()
logger.info("All missing embeddings updated successfully!")
