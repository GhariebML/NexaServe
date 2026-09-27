import argparse
import os
import json
import hashlib
import psycopg2
import pandas as pd
import fitz  # PyMuPDF
import requests
from psycopg2.extras import execute_values
from pgvector.psycopg2 import register_vector
import logging
import re

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Config imported from central secure config
from db_config import get_db_connection, EMBED_MODEL, OLLAMA_EMBED_URL as OLLAMA_URL

# Paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXCEL_PATH = os.path.join(BASE_DIR, "FAQs", "DEPI HELPER.xlsx")
LMS_FAQ_PATH = os.path.join(BASE_DIR, "FAQs", "FAQ LMS-English Exam.pdf")
DIGILIANS_FAQ_PATH = os.path.join(BASE_DIR, "FAQs", "FAQ final-Digilians.pdf")
SCRAPED_FAQS_PATH = os.path.join(BASE_DIR, "DEPI_Web_Scraper", "data", "final", "faqs.json")
SCRAPED_RAG_PATH = os.path.join(BASE_DIR, "DEPI_Web_Scraper", "data", "final", "depi_rag.json")

def hash_content(q, a):
    return hashlib.sha256(f"{q}||{a}".encode('utf-8')).hexdigest()

def extract_excel():
    logger.info("Extracting Excel FAQs...")
    if not os.path.exists(EXCEL_PATH):
        logger.warning(f"File not found: {EXCEL_PATH}")
        return []
    
    df = pd.read_excel(EXCEL_PATH)
    items = []
    
    col_q, col_a = None, None
    for c in df.columns:
        c_str = str(c).lower()
        if 'question' in c_str or 'سؤال' in c_str: col_q = c
        elif 'answer' in c_str or 'إجابة' in c_str or 'اجابة' in c_str or 'جواب' in c_str: col_a = c
    
    if col_q and col_a:
        for idx, row in df.iterrows():
            q = str(row[col_q]).strip()
            a = str(row[col_a]).strip()
            if q and a and q != 'nan' and a != 'nan':
                program = 'DEBI' if 'رواد' in q or 'depi' in q.lower() else 'COMMON'
                items.append({
                    'program': program,
                    'category': 'general_faq',
                    'question_ar': q,
                    'answer_ar': a,
                    'question': q,
                    'answer': a,
                    'source': 'DEPI HELPER.xlsx'
                })
    return items

def extract_pdf(path, program_default):
    logger.info(f"Extracting PDF: {path}")
    if not os.path.exists(path):
        logger.warning(f"File not found: {path}")
        return []
    
    items = []
    doc = fitz.open(path)
    filename = os.path.basename(path)
    for page_number, page in enumerate(doc, start=1):
        text = re.sub(r'\s+', ' ', page.get_text()).strip()
        if len(text) <= 30:
            continue

        sentences = re.split(r'(?<=[.!?؟])\s+', text)
        chunks = []
        current = ''
        for sentence in sentences:
            words = sentence.split()
            segments = []
            segment = ''
            for word in words:
                if segment and len(segment) + len(word) + 1 > 1100:
                    segments.append(segment)
                    segment = word
                else:
                    segment = f'{segment} {word}'.strip()
            if segment:
                segments.append(segment)

            for part in segments:
                if current and len(current) + len(part) + 1 > 1100:
                    chunks.append(current)
                    current = part
                else:
                    current = f'{current} {part}'.strip()
        if current:
            chunks.append(current)

        for part_number, chunk in enumerate(chunks, start=1):
            if len(chunk) > 30:
                question = f'Excerpt from {filename}, page {page_number}, part {part_number}'
                items.append({
                    'program': program_default,
                    'category': 'pdf_document',
                    'question': question,
                    'answer': chunk,
                    'question_ar': f'مقتطف من {filename}، صفحة {page_number}، جزء {part_number}',
                    'answer_ar': chunk,
                    'source': filename
                })
    return items

def extract_scraped():
    logger.info("Extracting scraped FAQ and RAG records...")
    items = []
    if os.path.exists(SCRAPED_FAQS_PATH):
        with open(SCRAPED_FAQS_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                source_url = item.get('source_url') or item.get('url')
                items.append({
                    'program': 'DEBI',
                    'category': 'scraped_faq',
                    'question_ar': item.get('question', ''),
                    'answer_ar': item.get('answer', ''),
                    'question': item.get('question', ''),
                    'answer': item.get('answer', ''),
                    'source': 'DEPI Official FAQ',
                    'source_url': source_url
                })
    
    if os.path.exists(SCRAPED_RAG_PATH):
        with open(SCRAPED_RAG_PATH, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for item in data:
                metadata = item.get('metadata') or {}
                # FAQ records are ingested from faqs.json with their structured Q/A fields.
                # Keep only page-section records from the combined RAG export here.
                if metadata.get('page_type') == 'faq':
                    continue
                content = (item.get('content') or '').strip()
                section = (metadata.get('section') or item.get('title') or item.get('id') or '').strip()
                source_url = item.get('source_url') or metadata.get('source_url') or item.get('url')
                if not content:
                    logger.warning("Skipping empty scraped RAG record: %s", item.get('id', 'unknown'))
                    continue
                items.append({
                    'program': 'DEBI',
                    'category': 'scraped_rag',
                    'question': section[:180] or content[:180],
                    'answer': content,
                    'question_ar': section[:180] or content[:180],
                    'answer_ar': content,
                    'source': f"DEPI Official Web Page ({metadata.get('page_type') or 'scraped section'})",
                    'source_url': source_url
                })
    return items

def get_embedding(text):
    try:
        response = requests.post(OLLAMA_URL, json={
            "model": EMBED_MODEL,
            "input": text
        }, timeout=60)
        response.raise_for_status()
        data = response.json()
        if 'embeddings' in data and data['embeddings']:
            return data['embeddings'][0]
        elif 'embedding' in data:
            return data['embedding']
        else:
            logger.error(f"Unexpected embedding response: {data}")
            return []
    except Exception as e:
        logger.error(f"Error getting embedding: {e}")
        return []

def main():
    parser = argparse.ArgumentParser(description="Ingest NexaServe FAQ and RAG knowledge sources.")
    parser.add_argument(
        "--scraped-only",
        action="store_true",
        help="Ingest only the current DEPI website scrape; skip PDFs and the local workbook.",
    )
    args = parser.parse_args()
    logger.info("Starting ingestion...")
    
    all_items = []
    if not args.scraped_only:
        all_items.extend(extract_excel())
        all_items.extend(extract_pdf(LMS_FAQ_PATH, 'DEBI'))
        all_items.extend(extract_pdf(DIGILIANS_FAQ_PATH, 'DIGILIANS'))
    all_items.extend(extract_scraped())
    
    logger.info(f"Total items extracted: {len(all_items)}")
    
    logger.info("Connecting to DB...")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    records_to_insert = []
    
    for item in all_items:
        q = item.get('question', '') or item.get('question_ar', '')
        a = item.get('answer', '') or item.get('answer_ar', '')
        if not q or not a:
            continue
            
        c_hash = hash_content(q, a)
        
        cursor.execute("SELECT id FROM knowledge_base WHERE content_hash = %s", (c_hash,))
        existing = cursor.fetchone()
        if existing:
            if item.get('source_url'):
                cursor.execute(
                    """UPDATE knowledge_base
                       SET source_url = COALESCE(NULLIF(source_url, ''), %s),
                           source_attribution = CASE
                               WHEN source_attribution = 'scraped' THEN %s
                               ELSE source_attribution
                           END
                       WHERE id = %s""",
                    (item['source_url'], item.get('source'), existing[0])
                )
            continue
            
        doc_text = f"{q}\n{a}"
        embedding = get_embedding(doc_text)
        
        if not embedding:
            continue
            
        records_to_insert.append((
            item['program'],
            item['category'],
            item.get('question', q),
            item.get('answer', a),
            item.get('question_ar', q),
            item.get('answer_ar', a),
            item['source'],
            item.get('source_url'),
            c_hash,
            embedding
        ))
    
    if records_to_insert:
        logger.info(f"Inserting {len(records_to_insert)} new records...")
        insert_query = """
            INSERT INTO knowledge_base (program, category, question, answer, question_ar, answer_ar, source_attribution, source_url, content_hash, embedding)
            VALUES %s
        """
        execute_values(cursor, insert_query, records_to_insert)
        conn.commit()
        logger.info("Insertion complete.")
    else:
        logger.info("No new records to insert.")

    # Commit verified provenance backfills even when every content hash already existed.
    conn.commit()
        
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
