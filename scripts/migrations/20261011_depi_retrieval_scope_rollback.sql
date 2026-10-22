-- REVIEW ONLY rollback.

DROP INDEX IF EXISTS idx_kb_retrieval_scope;
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS chk_kb_retrieval_scope;
ALTER TABLE knowledge_base DROP COLUMN IF EXISTS retrieval_scope;

COMMIT;
