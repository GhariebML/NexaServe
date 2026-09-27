"""
Migration script to upgrade live database schema to V2:
- Ensures extensions: uuid-ossp, vector, pg_trgm
- Ensures knowledge_base table has embedding vector(768) and indexes (trgm and hnsw)
- Creates customer_memory and conversation_summaries tables
- Idempotent and non-destructive.
"""

import sys
import os
import logging
from psycopg2 import sql

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from db_config import get_admin_db_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("schema_migrator")

MIGRATIONS = [
    ("Extensions", """
        CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
        CREATE EXTENSION IF NOT EXISTS vector;
        CREATE EXTENSION IF NOT EXISTS pg_trgm;
    """),
    ("Customer Memory Table", """
        CREATE TABLE IF NOT EXISTS customer_memory (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            memory_type VARCHAR(50) NOT NULL,
            content TEXT NOT NULL,
            source VARCHAR(50) DEFAULT 'conversation',
            confidence NUMERIC(3,2) DEFAULT 0.85,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            expires_at TIMESTAMP WITH TIME ZONE
        );
        CREATE INDEX IF NOT EXISTS idx_cust_mem_customer ON customer_memory(customer_id);
        CREATE INDEX IF NOT EXISTS idx_cust_mem_active ON customer_memory(customer_id, is_active);
    """),
    ("Conversation Summaries Table", """
        CREATE TABLE IF NOT EXISTS conversation_summaries (
            id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
            conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
            customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
            summary TEXT NOT NULL,
            unresolved_questions TEXT,
            topics TEXT[] DEFAULT '{}',
            turn_count INT DEFAULT 0,
            created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE INDEX IF NOT EXISTS idx_conv_sum_conversation ON conversation_summaries(conversation_id);
        CREATE INDEX IF NOT EXISTS idx_conv_sum_customer ON conversation_summaries(customer_id);
    """),
    ("Knowledge Base Trigram and HNSW Indexes", """
        CREATE INDEX IF NOT EXISTS idx_kb_question_ar_trgm ON knowledge_base USING gin (question_ar gin_trgm_ops);
        CREATE INDEX IF NOT EXISTS idx_kb_answer_ar_trgm ON knowledge_base USING gin (answer_ar gin_trgm_ops);
        -- Only create HNSW index if it does not already exist
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes WHERE indexname = 'idx_kb_embedding_hnsw'
            ) THEN
                CREATE INDEX idx_kb_embedding_hnsw ON knowledge_base USING hnsw (embedding vector_cosine_ops);
            END IF;
        END
        $$;
    """),
    ("App User Permissions", """
        GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cs_app_user;
        GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cs_app_user;
    """)
]

def run_migration():
    logger.info("Connecting to database for schema V2 migration...")
    conn = get_admin_db_connection()
    conn.commit()
    conn.autocommit = True
    cur = conn.cursor()
    
    try:
        for name, query in MIGRATIONS:
            logger.info(f"Applying migration: {name}")
            cur.execute(query)
            logger.info(f"  [OK] {name} applied successfully.")
            
        # Verify embedding dimension
        cur.execute("""
            SELECT atttypmod 
            FROM pg_attribute 
            WHERE attrelid = 'knowledge_base'::regclass 
              AND attname = 'embedding';
        """)
        dim = cur.fetchone()[0]
        logger.info(f"Verified knowledge_base.embedding vector dimension: {dim}")
        if dim != 768:
            logger.warning(f"Dimension mismatch! Expected 768, found {dim}")
        else:
            logger.info("Embedding contract satisfied: dimension = 768")
            
        logger.info("Schema V2 migration complete.")
    finally:
        cur.close()
        conn.close()

if __name__ == "__main__":
    run_migration()
