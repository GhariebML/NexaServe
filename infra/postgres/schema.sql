-- ==============================================================================
-- Customer Service AI Platform - Database Schema (DEPI Professional Support)
-- Database: customerservice
-- Owner: cs_app_user
-- DEPI/Egyptian Data Protection Compliant Specification
-- Includes: Core schema (v1) + Professional Support extensions (v2)
-- ==============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Customers Table (Multi-Channel Identity Registry)
CREATE TABLE IF NOT EXISTS customers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    phone_number VARCHAR(30) UNIQUE,
    email VARCHAR(255) UNIQUE,
    telegram_id VARCHAR(100) UNIQUE,
    whatsapp_id VARCHAR(100) UNIQUE,
    national_id_hash VARCHAR(128),
    full_name VARCHAR(100) NOT NULL,
    preferred_language VARCHAR(10) DEFAULT 'ar', -- 'ar' or 'en'
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_customers_phone ON customers(phone_number);
CREATE INDEX IF NOT EXISTS idx_customers_email ON customers(email);
CREATE INDEX IF NOT EXISTS idx_customers_telegram ON customers(telegram_id);
CREATE INDEX IF NOT EXISTS idx_customers_whatsapp ON customers(whatsapp_id);

-- 2. Conversations (Sessions) Table
CREATE TABLE IF NOT EXISTS conversations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    channel VARCHAR(30) NOT NULL DEFAULT 'web', -- 'whatsapp', 'telegram', 'webchat', 'email'
    status VARCHAR(30) NOT NULL DEFAULT 'active', -- 'active', 'closed', 'handed_off', 'resolved'
    current_intent VARCHAR(50),
    language VARCHAR(10) DEFAULT 'ar',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    closed_at TIMESTAMP WITH TIME ZONE
);

CREATE INDEX IF NOT EXISTS idx_conversations_customer ON conversations(customer_id);
CREATE INDEX IF NOT EXISTS idx_conversations_status ON conversations(status);
CREATE INDEX IF NOT EXISTS idx_conversations_channel ON conversations(channel);

-- 3. Messages Table (Turn-by-turn history with PII audit)
CREATE TABLE IF NOT EXISTS messages (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    sender_type VARCHAR(20) NOT NULL, -- 'customer', 'ai', 'agent', 'system'
    content TEXT NOT NULL,
    intent VARCHAR(50),
    confidence NUMERIC(4, 3),
    pii_detected BOOLEAN DEFAULT FALSE,
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_messages_created ON messages(created_at);

-- 4. Orders / Citizen E-Services Table
CREATE TABLE IF NOT EXISTS orders (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    order_number VARCHAR(50) UNIQUE NOT NULL, -- or Service Request No e.g. SRV-2026-901
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    status VARCHAR(50) NOT NULL, -- 'processing', 'in_review', 'approved', 'shipped', 'delivered', 'cancelled'
    total_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
    currency VARCHAR(10) NOT NULL DEFAULT 'SAR',
    carrier VARCHAR(50),
    tracking_number VARCHAR(100),
    estimated_delivery DATE,
    items JSONB NOT NULL DEFAULT '[]'::jsonb,
    service_type VARCHAR(100) DEFAULT 'standard',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_orders_number ON orders(order_number);
CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);

-- 5. Bilingual Knowledge Base (MCIT Services, FAQs & Enterprise Policies)
CREATE TABLE IF NOT EXISTS knowledge_base (
    id SERIAL PRIMARY KEY,
    program VARCHAR(20) NOT NULL DEFAULT 'DIGILIANS' CHECK (program IN ('DIGILIANS', 'DEBI', 'COMMON')),
    category VARCHAR(50) NOT NULL, -- 'citizen_services', 'digital_identity', 'policies', 'telecom_complaints', 'technical_support'
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    keywords TEXT[] DEFAULT '{}',
    question_ar TEXT,
    answer_ar TEXT,
    keywords_ar TEXT[] DEFAULT '{}',
    source_attribution TEXT,
    is_active BOOLEAN NOT NULL DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_kb_category ON knowledge_base(category);
CREATE INDEX IF NOT EXISTS idx_kb_program_category ON knowledge_base(program, category, is_active);

-- 6. Support Tickets (SLA-governed Human-in-the-Loop Escalation)
CREATE TABLE IF NOT EXISTS tickets (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_number VARCHAR(30) UNIQUE NOT NULL,
    customer_id UUID NOT NULL REFERENCES customers(id) ON DELETE CASCADE,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    priority VARCHAR(20) NOT NULL DEFAULT 'medium', -- 'low', 'medium', 'high', 'urgent'
    status VARCHAR(30) NOT NULL DEFAULT 'open', -- 'open', 'assigned', 'in_progress', 'resolved', 'closed'
    reason TEXT NOT NULL,
    assigned_team VARCHAR(100) DEFAULT 'Citizen Support Tier-1',
    assigned_agent VARCHAR(100),
    escalation_channel VARCHAR(50) DEFAULT 'internal_portal',
    resolution_notes TEXT,
    sla_due_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_tickets_status ON tickets(status);
CREATE INDEX IF NOT EXISTS idx_tickets_customer ON tickets(customer_id);
CREATE INDEX IF NOT EXISTS idx_tickets_priority ON tickets(priority);

-- 7. Audit Logs Table (Full Observability & Regulatory Data Sovereignty)
CREATE TABLE IF NOT EXISTS audit_logs (
    id BIGSERIAL PRIMARY KEY,
    workflow_name VARCHAR(100) NOT NULL,
    execution_id VARCHAR(100),
    event_type VARCHAR(50) NOT NULL, -- 'request_received', 'intent_classified', 'rag_retrieved', 'hitl_escalated', 'agent_replied', 'turn_completed', 'error'
    channel VARCHAR(30) DEFAULT 'unknown',
    client_ip VARCHAR(50),
    pii_masked BOOLEAN DEFAULT FALSE,
    payload JSONB DEFAULT '{}'::jsonb,
    latency_ms INT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_audit_event ON audit_logs(event_type);
CREATE INDEX IF NOT EXISTS idx_audit_created ON audit_logs(created_at);
CREATE INDEX IF NOT EXISTS idx_audit_channel ON audit_logs(channel);

-- Grant privileges to dedicated app user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO cs_app_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO cs_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON TABLES TO cs_app_user;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT ALL ON SEQUENCES TO cs_app_user;
