-- Rollback for 004_whatsapp_message_lifecycle.sql.
-- Export any lifecycle values you need before running this: this removes the new fields.
BEGIN;
DROP INDEX IF EXISTS idx_messages_provider_reply;
DROP INDEX IF EXISTS uq_messages_one_reply_per_inbound;
DROP INDEX IF EXISTS uq_messages_provider_message_id;
DROP INDEX IF EXISTS idx_messages_conversation_created_id;
ALTER TABLE messages DROP CONSTRAINT IF EXISTS messages_delivery_status_check;
ALTER TABLE messages
    DROP COLUMN IF EXISTS reply_to_provider_message_id,
    DROP COLUMN IF EXISTS delivery_updated_at,
    DROP COLUMN IF EXISTS delivery_status,
    DROP COLUMN IF EXISTS provider_message_id,
    DROP COLUMN IF EXISTS provider;
COMMIT;
