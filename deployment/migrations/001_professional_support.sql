-- Derived from the repository professional-support migration; seed/demo INSERT statements are intentionally excluded.
BEGIN;
-- SECTION 1: New Tables
-- ============================================================================

-- Table: agents (Agent profiles and status)
CREATE TABLE IF NOT EXISTS agents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(100) NOT NULL,
    email VARCHAR(255) UNIQUE,
    role VARCHAR(50) DEFAULT 'tier1',
    team VARCHAR(100) DEFAULT 'DEPI Citizen Support',
    status VARCHAR(20) DEFAULT 'available',
    metadata JSONB DEFAULT '{}'::jsonb,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_agents_status ON agents(status);
CREATE INDEX IF NOT EXISTS idx_agents_team ON agents(team);
CREATE INDEX IF NOT EXISTS idx_agents_role ON agents(role);

-- Table: ticket_categories
CREATE TABLE IF NOT EXISTS ticket_categories (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    description TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE UNIQUE INDEX IF NOT EXISTS idx_ticket_categories_name ON ticket_categories(LOWER(name));
CREATE INDEX IF NOT EXISTS idx_ticket_categories_active ON ticket_categories(is_active);

-- Table: ticket_tags
CREATE TABLE IF NOT EXISTS ticket_tags (
    id SERIAL PRIMARY KEY,
    tag VARCHAR(50) NOT NULL UNIQUE,
    color VARCHAR(7) DEFAULT '#000000'
);

-- Table: ticket_tag_assignments (many-to-many: ticket <-> tags)
CREATE TABLE IF NOT EXISTS ticket_tag_assignments (
    ticket_number VARCHAR(30) NOT NULL,
    tag_id INT NOT NULL REFERENCES ticket_tags(id) ON DELETE CASCADE,
    PRIMARY KEY (ticket_number, tag_id)
);

CREATE INDEX IF NOT EXISTS idx_tta_ticket ON ticket_tag_assignments(ticket_number);
CREATE INDEX IF NOT EXISTS idx_tta_tag ON ticket_tag_assignments(tag_id);

-- Table: csat_surveys (Customer satisfaction ratings)
CREATE TABLE IF NOT EXISTS csat_surveys (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticket_number VARCHAR(30) REFERENCES tickets(ticket_number) ON DELETE SET NULL,
    conversation_id UUID REFERENCES conversations(id) ON DELETE SET NULL,
    customer_id UUID REFERENCES customers(id) ON DELETE SET NULL,
    rating INT CHECK (rating BETWEEN 1 AND 5),
    feedback TEXT,
    channel VARCHAR(30),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_csat_ticket ON csat_surveys(ticket_number);
CREATE INDEX IF NOT EXISTS idx_csat_customer ON csat_surveys(customer_id);
CREATE INDEX IF NOT EXISTS idx_csat_created ON csat_surveys(created_at);

-- Table: agent_performance (Agent activity tracking)
CREATE TABLE IF NOT EXISTS agent_performance (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    agent_id UUID NOT NULL REFERENCES agents(id) ON DELETE CASCADE,
    ticket_number VARCHAR(30),
    event_type VARCHAR(50) NOT NULL,
    response_time_ms INT,
    resolution_time_ms INT,
    notes TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ap_agent ON agent_performance(agent_id);
CREATE INDEX IF NOT EXISTS idx_ap_ticket ON agent_performance(ticket_number);
CREATE INDEX IF NOT EXISTS idx_ap_created ON agent_performance(created_at);

-- Table: automation_rules (Configurable auto-rules)
CREATE TABLE IF NOT EXISTS automation_rules (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    name_ar VARCHAR(100) NOT NULL,
    trigger_condition JSONB NOT NULL DEFAULT '{}'::jsonb,
    action_type VARCHAR(50) NOT NULL,
    action_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    is_active BOOLEAN DEFAULT TRUE,
    last_executed_at TIMESTAMP WITH TIME ZONE,
    execution_count INT DEFAULT 0,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_ar_active ON automation_rules(is_active);

-- Table: knowledge_base_versions (Change history for KB articles)
CREATE TABLE IF NOT EXISTS knowledge_base_versions (
    id SERIAL PRIMARY KEY,
    article_id INT NOT NULL REFERENCES knowledge_base(id) ON DELETE CASCADE,
    version INT NOT NULL,
    changed_fields JSONB,
    changed_by VARCHAR(100),
    changed_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(article_id, version)
);

CREATE INDEX IF NOT EXISTS idx_kbv_article ON knowledge_base_versions(article_id);

-- ============================================================================
-- SECTION 2: Extend Existing Tables (Non-destructive, all NULLABLE)
-- ============================================================================

-- Extend tickets table
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='category_id') THEN
        ALTER TABLE tickets ADD COLUMN category_id INT REFERENCES ticket_categories(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='assigned_agent_id') THEN
        ALTER TABLE tickets ADD COLUMN assigned_agent_id UUID REFERENCES agents(id);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='csat_score') THEN
        ALTER TABLE tickets ADD COLUMN csat_score INT CHECK (csat_score BETWEEN 1 AND 5);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='tags') THEN
        ALTER TABLE tickets ADD COLUMN tags TEXT[] DEFAULT '{}'::text[];
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='first_response_at') THEN
        ALTER TABLE tickets ADD COLUMN first_response_at TIMESTAMP WITH TIME ZONE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='tickets' AND column_name='source_channel') THEN
        ALTER TABLE tickets ADD COLUMN source_channel VARCHAR(30);
    END IF;
END $$;

-- Extend customers table
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='customers' AND column_name='total_tickets') THEN
        ALTER TABLE customers ADD COLUMN total_tickets INT DEFAULT 0;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='customers' AND column_name='csat_avg') THEN
        ALTER TABLE customers ADD COLUMN csat_avg NUMERIC(3,2);
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='customers' AND column_name='last_activity_at') THEN
        ALTER TABLE customers ADD COLUMN last_activity_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;
    END IF;
END $$;

-- Extend conversations table
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='conversations' AND column_name='satisfaction_offered') THEN
        ALTER TABLE conversations ADD COLUMN satisfaction_offered BOOLEAN DEFAULT FALSE;
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_name='conversations' AND column_name='agent_id') THEN
        ALTER TABLE conversations ADD COLUMN agent_id UUID REFERENCES agents(id);
    END IF;
END $$;

-- ============================================================================
COMMIT;
