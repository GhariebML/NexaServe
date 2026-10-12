-- ====================================================================
-- NEXASERVE MIGRATION PLAN: ENFORCE CANONICAL DEPI PROGRAM IDENTIFIER
-- Target Database: customerservice
-- Status: REVIEW ONLY (DO NOT EXECUTE WITHOUT EXPLICIT AUTHORIZATION)
-- Scope: Exactly 36 verified DEPI records (IDs 101-129, 156-162)
--        1 ambiguous record deactivation (ID 100)
-- Preservation: Preserves original last_verified_at, embeddings, IDs, and metadata
-- ====================================================================

BEGIN;

DO $$
DECLARE
    v_total_count INTEGER;
    v_target_depi_count INTEGER;
    v_invalid_url_count INTEGER;
    v_faq_attr_count INTEGER;
    v_home_attr_count INTEGER;
    v_about_attr_count INTEGER;
    v_guidance_attr_count INTEGER;
    v_contact_attr_count INTEGER;
    v_debi_quarantine_count INTEGER;
    v_digilians_count INTEGER;
    v_common_count INTEGER;
    v_record_100_active BOOLEAN;
BEGIN
    -- 1. PRECONDITION CHECKS
    SELECT count(*) INTO v_total_count FROM knowledge_base;
    IF v_total_count <> 73 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Total KB records count is %, expected exactly 73.', v_total_count;
    END IF;

    -- Assert target 36 candidate records exist with program 'DEBI' and exact ID boundaries
    SELECT count(*) INTO v_target_depi_count
    FROM knowledge_base
    WHERE id IN (
        101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
        121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
    )
    AND program = 'DEBI';

    IF v_target_depi_count <> 36 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected exactly 36 candidate records in ID list with program DEBI, found %.', v_target_depi_count;
    END IF;

    -- Assert source URL validity: must not be NULL, must start with https://depi.gov.eg/
    SELECT count(*) INTO v_invalid_url_count
    FROM knowledge_base
    WHERE id IN (
        101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
        121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
    )
    AND (source_url IS NULL OR source_url NOT ILIKE 'https://depi.gov.eg/%');

    IF v_invalid_url_count <> 0 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: % candidate records have NULL or invalid source_url not matching https://depi.gov.eg/%%', v_invalid_url_count;
    END IF;

    -- Assert exact source attribution by record group
    -- Group A: IDs 101-129 (29 FAQ records)
    SELECT count(*) INTO v_faq_attr_count
    FROM knowledge_base
    WHERE id BETWEEN 101 AND 129
      AND source_attribution = 'DEPI Official FAQ'
      AND source_url = 'https://depi.gov.eg/content/faqs';

    IF v_faq_attr_count <> 29 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 29 FAQ records with attribution "DEPI Official FAQ", found %.', v_faq_attr_count;
    END IF;

    -- Group B: IDs 156-157 (2 Home page records)
    SELECT count(*) INTO v_home_attr_count
    FROM knowledge_base
    WHERE id IN (156, 157)
      AND source_attribution = 'DEPI Official Web Page (home)'
      AND source_url = 'https://depi.gov.eg/content/home';

    IF v_home_attr_count <> 2 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 2 Home page records, found %.', v_home_attr_count;
    END IF;

    -- Group C: IDs 158-160 (3 About DEPI records)
    SELECT count(*) INTO v_about_attr_count
    FROM knowledge_base
    WHERE id IN (158, 159, 160)
      AND source_attribution = 'DEPI Official Web Page (about_depi)'
      AND source_url = 'https://depi.gov.eg/content/aboutdepi';

    IF v_about_attr_count <> 3 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 3 About DEPI records, found %.', v_about_attr_count;
    END IF;

    -- Group D: ID 161 (1 Guidance record)
    SELECT count(*) INTO v_guidance_attr_count
    FROM knowledge_base
    WHERE id = 161
      AND source_attribution = 'DEPI Official Web Page (guidance)'
      AND source_url = 'https://depi.gov.eg/StaticContent/Guidance';

    IF v_guidance_attr_count <> 1 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 1 Guidance record (ID 161), found %.', v_guidance_attr_count;
    END IF;

    -- Group E: ID 162 (1 Contact Us record)
    SELECT count(*) INTO v_contact_attr_count
    FROM knowledge_base
    WHERE id = 162
      AND source_attribution = 'DEPI Official Web Page (contact_us)'
      AND source_url = 'https://depi.gov.eg/StaticContent/ContactUs';

    IF v_contact_attr_count <> 1 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 1 Contact Us record (ID 162), found %.', v_contact_attr_count;
    END IF;

    -- Assert the 8 confirmed DEBI seed records exist and remain untouched
    SELECT count(*) INTO v_debi_quarantine_count
    FROM knowledge_base
    WHERE id IN (90, 91, 92, 93, 94, 95, 96, 97)
      AND program = 'DEBI';

    IF v_debi_quarantine_count <> 8 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 8 confirmed DEBI seed records (IDs 90-97), found %.', v_debi_quarantine_count;
    END IF;

    -- Assert Digilians records remain intact (26 records)
    SELECT count(*) INTO v_digilians_count
    FROM knowledge_base
    WHERE program = 'DIGILIANS';

    IF v_digilians_count <> 26 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 26 DIGILIANS records, found %.', v_digilians_count;
    END IF;

    -- Assert Common records remain intact (2 records)
    SELECT count(*) INTO v_common_count
    FROM knowledge_base
    WHERE program = 'COMMON';

    IF v_common_count <> 2 THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Expected 2 COMMON records, found %.', v_common_count;
    END IF;

    -- Assert ambiguous record ID 100 exists and is currently active
    SELECT is_active INTO v_record_100_active
    FROM knowledge_base
    WHERE id = 100 
      AND program = 'DEBI'
      AND source_attribution = 'FAQ LMS-English Exam.pdf';

    IF v_record_100_active IS NOT TRUE THEN
        RAISE EXCEPTION 'PRECONDITION FAILED: Record ID 100 (FAQ LMS-English Exam.pdf) is not in expected active state.';
    END IF;

    RAISE NOTICE 'All migration pre-conditions verified successfully.';
END $$;

-- 2. SCHEMA CONSTRAINT UPDATE: Safely permit 'DEPI' while preserving 'DIGILIANS', 'DEBI', 'COMMON'
ALTER TABLE knowledge_base DROP CONSTRAINT IF EXISTS chk_kb_program;
ALTER TABLE knowledge_base ADD CONSTRAINT chk_kb_program 
  CHECK (program::text = ANY (ARRAY['DIGILIANS'::text, 'DEBI'::text, 'COMMON'::text, 'DEPI'::text]));

-- 3. MIGRATION: Migrate ONLY the exact 36 verified DEPI records with explicit double guard (IDs + URL match)
-- Note: Original last_verified_at, embeddings, source_attribution, and question/answer contents are preserved unmodified.
UPDATE knowledge_base
SET program = 'DEPI'
WHERE id IN (
    101,102,103,104,105,106,107,108,109,110,111,112,113,114,115,116,117,118,119,120,
    121,122,123,124,125,126,127,128,129,156,157,158,159,160,161,162
)
AND program = 'DEBI'
AND source_url ILIKE 'https://depi.gov.eg/%';

-- 4. AMBIGUOUS RECORD DEACTIVATION: Safely deactivate ID 100 while keeping program = 'DEBI'
-- Note: Original last_verified_at is preserved unmodified.
UPDATE knowledge_base
SET is_active = FALSE
WHERE id = 100 
  AND program = 'DEBI'
  AND source_attribution = 'FAQ LMS-English Exam.pdf'
  AND is_active = TRUE;

-- 5. POST-MIGRATION ASSERTIONS
DO $$
DECLARE
    v_updated_depi_count INTEGER;
    v_active_record_100 BOOLEAN;
    v_remaining_debi_count INTEGER;
BEGIN
    SELECT count(*) INTO v_updated_depi_count FROM knowledge_base WHERE program = 'DEPI';
    IF v_updated_depi_count <> 36 THEN
        RAISE EXCEPTION 'POST-MIGRATION ASSERTION FAILED: Expected 36 records with program DEPI, found %.', v_updated_depi_count;
    END IF;

    SELECT count(*) INTO v_remaining_debi_count FROM knowledge_base WHERE program = 'DEBI';
    IF v_remaining_debi_count <> 9 THEN
        RAISE EXCEPTION 'POST-MIGRATION ASSERTION FAILED: Expected 9 records with program DEBI (8 active seed + 1 deactivated), found %.', v_remaining_debi_count;
    END IF;

    SELECT is_active INTO v_active_record_100 FROM knowledge_base WHERE id = 100;
    IF v_active_record_100 IS NOT FALSE THEN
        RAISE EXCEPTION 'POST-MIGRATION ASSERTION FAILED: Record 100 is not marked is_active = FALSE.';
    END IF;

    RAISE NOTICE 'Migration executed and verified with 100%% integrity.';
END $$;

COMMIT;
