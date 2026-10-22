-- Migration 003: Ticket Management Lifecycle & Duplicate Prevention
-- Additive, backward-compatible extension to the customerservice database.
BEGIN;

-- 1. Extend tickets table with lifecycle & duplicate prevention fields
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='title') THEN
        ALTER TABLE tickets ADD COLUMN title VARCHAR(255);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='external_message_id') THEN
        ALTER TABLE tickets ADD COLUMN external_message_id VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='idempotency_key') THEN
        ALTER TABLE tickets ADD COLUMN idempotency_key VARCHAR(100);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='internal_notes') THEN
        ALTER TABLE tickets ADD COLUMN internal_notes TEXT;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='closed_at') THEN
        ALTER TABLE tickets ADD COLUMN closed_at TIMESTAMP WITH TIME ZONE;
    END IF;
END $$;

CREATE INDEX IF NOT EXISTS idx_tickets_ext_msg_id ON tickets(external_message_id);
CREATE INDEX IF NOT EXISTS idx_tickets_idempotency_key ON tickets(idempotency_key);

-- 2. Dedicated ticket event timeline table
CREATE TABLE IF NOT EXISTS ticket_events (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_id UUID NOT NULL REFERENCES tickets(id) ON DELETE CASCADE,
    ticket_number VARCHAR(30) NOT NULL,
    event_type VARCHAR(50) NOT NULL,
    actor_type VARCHAR(20) NOT NULL,
    actor_name VARCHAR(100),
    old_value VARCHAR(100),
    new_value VARCHAR(100),
    message TEXT,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket ON ticket_events(ticket_id);
CREATE INDEX IF NOT EXISTS idx_ticket_events_ticket_num ON ticket_events(ticket_number);
CREATE INDEX IF NOT EXISTS idx_ticket_events_created ON ticket_events(created_at);

COMMIT;
