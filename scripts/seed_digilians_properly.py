import sys
import os
import psycopg2
import requests
from pgvector.psycopg2 import register_vector
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from seed_depi_faq import faqs
from db_config import get_db_connection, EMBED_MODEL, OLLAMA_EMBED_URL as OLLAMA_URL

conn = get_db_connection()
cur = conn.cursor()

# Delete old DIGILIANS entries so we have clean, curated, properly vectorized data
cur.execute("DELETE FROM knowledge_base WHERE program = 'DIGILIANS';")
logger.info("Cleared old DIGILIANS entries.")

inserted = 0
for item in faqs:
    q_ar = item.get("question_ar", "")
    a_ar = item.get("answer_ar", "")
    kws_ar = item.get("keywords_ar", [])
    q_en = item.get("question", "")
    a_en = item.get("answer", "")
    kws_en = item.get("keywords", [])
    cat = item.get("category", "digilians_faq")
    src = "مبادرة الرواد الرقميون (Digilians)"

    # Get embedding for Arabic + English
    text_to_embed = f"{q_ar}\n{a_ar}\n{q_en}\n{a_en}"
    try:
        resp = requests.post(OLLAMA_URL, json={"model": EMBED_MODEL, "input": text_to_embed})
        data = resp.json()
        emb = data.get("embeddings", [[]])[0]
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        emb = None

    cur.execute("""
        INSERT INTO knowledge_base (
            program, category, question_ar, answer_ar, keywords_ar,
            question, answer, keywords, source_attribution, is_active, embedding
        ) VALUES (
            'DIGILIANS', %s, %s, %s, %s, %s, %s, %s, %s, TRUE, %s
        )
    """, (cat, q_ar, a_ar, kws_ar, q_en, a_en, kws_en, src, emb))
    inserted += 1
    logger.info(f"Inserted Digilians FAQ: {q_ar[:40]}")

conn.commit()
cur.close()
conn.close()
logger.info(f"Successfully seeded and embedded {inserted} Digilians FAQs!")
