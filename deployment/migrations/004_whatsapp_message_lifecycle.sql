-- Additive, reversible WhatsApp message identity and delivery lifecycle fields.
-- Existing message rows remain unchanged; new fields are nullable.
BEGIN;

ALTER TABLE messages
    ADD COLUMN IF NOT EXISTS provider VARCHAR(32),
    ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(255),
    ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(24),
    ADD COLUMN IF NOT EXISTS delivery_updated_at TIMESTAMPTZ,
    ADD COLUMN IF NOT EXISTS reply_to_provider_message_id VARCHAR(255);

DO $$ BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint
        WHERE conname = 'messages_delivery_status_check'
          AND conrelid = 'messages'::regclass
    ) THEN
        ALTER TABLE messages ADD CONSTRAINT messages_delivery_status_check
            CHECK (delivery_status IS NULL OR delivery_status IN
                ('received', 'queued', 'sent', 'delivered', 'read', 'failed', 'undelivered'));
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS uq_messages_provider_message_id
    ON messages (provider, provider_message_id)
    WHERE provider IS NOT NULL AND provider_message_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS idx_messages_provider_reply
    ON messages (provider, reply_to_provider_message_id)
    WHERE reply_to_provider_message_id IS NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uq_messages_one_reply_per_inbound
    ON messages (provider, reply_to_provider_message_id)
    WHERE provider = 'whatsapp' AND reply_to_provider_message_id IS NOT NULL
      AND sender_type IN ('ai', 'agent');

CREATE INDEX IF NOT EXISTS idx_messages_conversation_created_id
    ON messages (conversation_id, created_at, id);

COMMIT;
