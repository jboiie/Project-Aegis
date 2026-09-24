-- Supabase Table Setup for Project Aegis

CREATE TABLE IF NOT EXISTS aegis_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT now() NOT NULL,
    prompt_hash TEXT NOT NULL,
    blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_reason TEXT DEFAULT '',
    guardrail_checks JSONB DEFAULT '[]'::jsonb,
    latency_ms REAL DEFAULT 0.0,
    model TEXT DEFAULT '',
    errored BOOLEAN NOT NULL DEFAULT false
);

-- Idempotent add for existing tables created before `errored` existed - a
-- request/API failure (dead model, timeout, target 500) is a separate
-- outcome from blocked/allowed, previously either crashed before any row
-- was logged at all (router.py had no try/except around forward_to_llm)
-- or, in the red-team runner, got silently folded into "blocked". See
-- PROJECT_DESC.md's error-handling audit.
ALTER TABLE aegis_events ADD COLUMN IF NOT EXISTS errored BOOLEAN NOT NULL DEFAULT false;

CREATE INDEX IF NOT EXISTS idx_aegis_timestamp ON aegis_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_aegis_blocked ON aegis_events (blocked);

ALTER TABLE aegis_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow insert for anon" ON aegis_events FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow read for anon" ON aegis_events FOR SELECT TO anon USING (true);
