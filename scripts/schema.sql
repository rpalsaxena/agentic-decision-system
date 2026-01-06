-- ============================================
-- EVENTS TABLE
-- Stores raw events from external systems
-- ============================================
CREATE TABLE events (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    timestamp TIMESTAMPTZ NOT NULL,
    source VARCHAR(255) NOT NULL,
    raw_payload JSONB NOT NULL,
    event_type VARCHAR(100) NOT NULL,
    severity VARCHAR(20) CHECK (severity IN ('low', 'medium', 'high', 'critical')),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Indexes for common queries
CREATE INDEX idx_events_timestamp ON events(timestamp DESC);
CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_source ON events(source);

-- ============================================
-- DECISIONS TABLE
-- Agent decisions for each event
-- ============================================
CREATE TABLE decisions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id) ON DELETE CASCADE,
    agent_type VARCHAR(50) NOT NULL,
    action VARCHAR(100) NOT NULL,
    reasoning TEXT,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    metadata JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up decisions by event
CREATE INDEX idx_decisions_event ON decisions(event_id);
CREATE INDEX idx_decisions_confidence ON decisions(confidence);
-- ============================================
-- CRITIQUES TABLE
-- Critic agent evaluations of decisions
-- ============================================
CREATE TABLE critiques (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    decision_id UUID NOT NULL REFERENCES decisions(id) ON DELETE CASCADE,
    verdict VARCHAR(20) NOT NULL CHECK (verdict IN ('approve', 'reject', 'defer')),
    risk_flags JSONB DEFAULT '[]',
    reasoning TEXT,
    confidence FLOAT CHECK (confidence >= 0 AND confidence <= 1),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for looking up critiques by decision
CREATE INDEX idx_critiques_decision ON critiques(decision_id);

-- ============================================
-- AUDIT LOGS TABLE
-- Complete decision trail for compliance
-- ============================================
CREATE TABLE audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    event_id UUID NOT NULL REFERENCES events(id),
    decision_id UUID NOT NULL REFERENCES decisions(id),
    critique_id UUID NOT NULL REFERENCES critiques(id),
    event_hash VARCHAR(64) NOT NULL,
    final_action VARCHAR(50) NOT NULL,
    blocked BOOLEAN DEFAULT FALSE,
    block_reason TEXT,
    latency_ms INTEGER,
    safety_checks JSONB DEFAULT '{}',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Index for audit queries
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_blocked ON audit_logs(blocked) WHERE blocked = TRUE;
CREATE INDEX idx_audit_hash ON audit_logs(event_hash);
