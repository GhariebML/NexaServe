-- ====================================================================
-- NEXASERVE ROLLBACK SCRIPT: REVERT DEPI ISOLATION MIGRATION
-- Target Database: customerservice
-- Status: REVIEW ONLY (DO NOT EXECUTE WITHOUT EXPLICIT AUTHORIZATION)
-- Scope: Exactly reverts the 36 DEPI records (IDs 101-129, 156-162)
--        and reactivates record ID 100
-- Preservation: Preserves original last_verified_at, embeddings, IDs, and metadata
-- ====================================================================

BEGIN;

DO $$
DECLARE
    v_current_depi_count INTEGER;
    v_target_revert_count INTEGER;
    v_record_100_state BOOLEAN;
    v_invalid_provenance_count INTEGER;
BEGIN
    -- 1. ROLLBACK PRECONDITION CHECKS
    -- Assert that exactly the expected 36 records have program = 'DEPI'
    SELECT count(*) INTO v_current_depi_count
    FROM knowledge_base
    WHERE program = 'DEPI';

    IF v_current_depi_count <> 36 THEN
        RAISE EXCEPTION 'ROLLBACK PRECONDITION FAILED: Total DEPI records is %, expected exactly 36. Possible unexpected external changes detected. Aborting rollback.', v_current_depi_count;
    END IF;

    -- Assert that all 36 records match our exact reviewed ID list and verified provenance
    SELECT count(*) INTO v_target_revert_count
    FROM knowledge_base
    WHERE id IN (
        101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
        121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
    )
    AND program = 'DEPI'
    AND source_url ILIKE 'https://depi.gov.eg/%';

    IF v_target_revert_count <> 36 THEN
        RAISE EXCEPTION 'ROLLBACK PRECONDITION FAILED: Target ID list did not match expected 36 DEPI records with valid provenance. Found %, expected 36. Aborting rollback.', v_target_revert_count;
    END IF;

    -- Assert no unexpected records were modified with program = 'DEPI' outside the reviewed list
    SELECT count(*) INTO v_invalid_provenance_count
    FROM knowledge_base
    WHERE program = 'DEPI'
      AND id NOT IN (
        101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
        121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
      );

    IF v_invalid_provenance_count <> 0 THEN
        RAISE EXCEPTION 'ROLLBACK PRECONDITION FAILED: % records exist with program DEPI outside reviewed ID scope. Aborting rollback to prevent unintended data loss.', v_invalid_provenance_count;
    END IF;

    -- Assert record 100 exists and is currently inactive with expected attribution
    SELECT is_active INTO v_record_100_state
    FROM knowledge_base
    WHERE id = 100 
      AND program = 'DEBI'
      AND source_attribution = 'FAQ LMS-English Exam.pdf';

    IF v_record_100_state IS NOT FALSE THEN
        RAISE EXCEPTION 'ROLLBACK PRECONDITION FAILED: Record ID 100 is not in expected inactive state. Aborting rollback.';
    END IF;

    RAISE NOTICE 'Rollback pre-conditions verified successfully.';
END $$;

-- 2. REVERT MIGRATED RECORDS: Revert ONLY the reviewed 36 records with strict ID & provenance filter
-- Note: Original last_verified_at is preserved unmodified.
UPDATE knowledge_base
SET program = 'DEBI'
WHERE id IN (
    101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
    121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
)
AND program = 'DEPI'
AND source_url ILIKE 'https://depi.gov.eg/%';

-- 3. REACTIVATE AMBIGUOUS RECORD: Restore ID 100 to is_active = TRUE
-- Note: Original last_verified_at is preserved unmodified.
UPDATE knowledge_base
SET is_active = TRUE
WHERE id = 100 
  AND program = 'DEBI'
  AND source_attribution = 'FAQ LMS-English Exam.pdf'
  AND is_active = FALSE;

-- 4. RESTORE ORIGINAL CONSTRAINT: Remove 'DEPI' and restore ['DIGILIANS', 'DEBI', 'COMMON']
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS chk_kb_program;
ALTER TABLE knowledge_base ADD CONSTRAINT chk_kb_program 
  CHECK (program::text = ANY (ARRAY['DIGILIANS'::text, 'DEBI'::text, 'COMMON'::text]));

-- 5. POST-ROLLBACK INTEGRITY ASSERTIONS
DO $$
DECLARE
    v_remaining_depi INTEGER;
    v_restored_debi INTEGER;
    v_record_100_restored BOOLEAN;
BEGIN
    SELECT count(*) INTO v_remaining_depi FROM knowledge_base WHERE program = 'DEPI';
    IF v_remaining_depi <> 0 THEN
        RAISE EXCEPTION 'POST-ROLLBACK ASSERTION FAILED: Found % remaining DEPI records, expected 0.', v_remaining_depi;
    END IF;

    SELECT count(*) INTO v_restored_debi FROM knowledge_base WHERE program = 'DEBI';
    IF v_restored_debi <> 45 THEN
        RAISE EXCEPTION 'POST-ROLLBACK ASSERTION FAILED: Found % DEBI records, expected 45.', v_restored_debi;
    END IF;

    SELECT is_active INTO v_record_100_restored FROM knowledge_base WHERE id = 100;
    IF v_record_100_restored IS NOT TRUE THEN
        RAISE EXCEPTION 'POST-ROLLBACK ASSERTION FAILED: Record ID 100 is not reactivated.';
    END IF;

    RAISE NOTICE 'Rollback completed and validated successfully.';
END $$;

COMMIT;
