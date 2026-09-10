-- ==============================================================================
-- Enterprise Migration: Add Multi-Channel, Bilingual & SLA Columns
-- ==============================================================================

-- 1. Customers Table
ALTER TABLE customers ADD COLUMN IF NOT EXISTS telegram_id VARCHAR(100) UNIQUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS whatsapp_id VARCHAR(100) UNIQUE;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS national_id_hash VARCHAR(128);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_language VARCHAR(10) DEFAULT 'ar';

CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram_id);
CREATE INDEX IF NOT EXISTS idx_customers_whatsapp ON customers(whatsapp_id);

-- 2. Conversations Table
ALTER TABLE conversations ADD COLUMN IF NOT EXISTS language VARCHAR(10) DEFAULT 'ar';
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(channel);

-- 3. Messages Table
ALTER TABLE messages ADD COLUMN IF NOT EXISTS pii_detected BOOLEAN DEFAULT FALSE;

-- 4. Orders Table
ALTER TABLE orders ADD COLUMN IF NOT EXISTS service_type VARCHAR(100) DEFAULT 'standard';

-- 5. Knowledge Base Table
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS question_ar TEXT;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS answer_ar TEXT;
ALTER TABLE knowledge_base ADD COLUMN IF NOT EXISTS keywords_ar TEXT[] DEFAULT '{}';

-- 6. Tickets Table
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS assigned_team VARCHAR(100) DEFAULT 'Citizen Support Tier-1';
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS escalation_channel VARCHAR(50) DEFAULT 'internal_portal';
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS resolution_notes TEXT;
ALTER TABLE tickets ADD COLUMN IF NOT EXISTS sla_due_at TIMESTAMP WITH TIME ZONE;
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);

-- 7. Audit Logs Table
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS channel VARCHAR(30) DEFAULT 'unknown';
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS client_ip VARCHAR(50);
ALTER TABLE audit_logs ADD COLUMN IF NOT EXISTS pii_masked BOOLEAN DEFAULT FALSE;
CREATE INDEX IF NOT EXISTS idx_audit_channel ON audit_logs(channel);

-- Re-grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cs_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cs_app_user;
