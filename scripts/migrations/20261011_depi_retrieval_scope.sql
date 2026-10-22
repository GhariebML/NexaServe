-- REVIEW ONLY: do not execute against customerservice without explicit authorization.
-- Target: isolated DB only (test_uat_candidate / nexaserve_final).

ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS retrieval_scope VARCHAR(32);

UPDATE knowledge_base
SET retrieval_scope = CASE program
    WHEN 'DEPI' THEN 'DEPI_AUTHORITATIVE'
    WHEN 'COMMON' THEN 'GENERAL_SUPPORT'
    WHEN 'DIGILIANS' THEN 'DIGILIANS'
    WHEN 'DEBI' THEN 'DEBI_QUARANTINE'
END
WHERE retrieval_scope IS NULL;

ALTER TABLE knowledge_base ADD CONSTRAINT chk_kb_retrieval_scope
    CHECK (retrieval_scope IN ('DEPI_AUTHORITATIVE','DEPI_INTERNAL_GUIDANCE','GENERAL_SUPPORT','DIGILIANS','DEBI_QUARANTINE'));

CREATE INDEX IF NOT EXISTS idx_kb_retrieval_scope ON knowledge_base (retrieval_scope, is_active);

COMMIT;
