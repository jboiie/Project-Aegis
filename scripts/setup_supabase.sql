-- Supabase Table Setup for Project Aegis

CREATE TABLE IF NOT EXISTS aegis_events (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    timestamp TIMESTAMPTZ DEFAULT now() NOT NULL,
    prompt_hash TEXT NOT NULL,
    blocked BOOLEAN NOT NULL DEFAULT false,
    blocked_reason TEXT DEFAULT '',
    guardrail_checks JSONB DEFAULT '[]'::jsonb,
    latency_ms REAL DEFAULT 0.0,
    model TEXT DEFAULT ''
);

CREATE INDEX IF NOT EXISTS idx_aegis_timestamp ON aegis_events (timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_aegis_blocked ON aegis_events (blocked);

ALTER TABLE aegis_events ENABLE ROW LEVEL SECURITY;

CREATE POLICY "Allow insert for anon" ON aegis_events FOR INSERT TO anon WITH CHECK (true);
CREATE POLICY "Allow read for anon" ON aegis_events FOR SELECT TO anon USING (true);
