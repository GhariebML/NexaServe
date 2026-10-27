-- Additive: per-user token version so password changes, logout and deactivation
-- revoke previously issued dashboard JWTs. Existing users start at version 0.
-- Also reconciles installs whose admin_users predates 002 and lacks updated_at
-- (002's CREATE TABLE IF NOT EXISTS was skipped there, breaking password changes).
BEGIN;

ALTER TABLE admin_users
    ADD COLUMN IF NOT EXISTS token_version INTEGER NOT NULL DEFAULT 0,
    ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP;

COMMIT;
