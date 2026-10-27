BEGIN;

ALTER TABLE admin_users DROP COLUMN IF EXISTS token_version;

COMMIT;
