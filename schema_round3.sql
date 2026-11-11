-- =====================================================================
-- MOHAR ROUND 3 MIGRATION  (safe to run more than once)
-- Run in: Supabase dashboard -> SQL Editor -> New query -> paste -> Run
-- =====================================================================

-- 1. Who is who: one row per signed-in user (filled by scripts/create_demo_users.py)
CREATE TABLE IF NOT EXISTS user_roles (
    user_id UUID PRIMARY KEY,
    email   TEXT,
    role    TEXT NOT NULL CHECK (role IN ('creator', 'manager', 'reviewer'))
);

-- 2. Every submission knows its owner (creators only see their own posts)
ALTER TABLE submissions ADD COLUMN IF NOT EXISTS creator_id UUID;

-- 3. Every audit entry is tied to a real person
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_id UUID;
ALTER TABLE audit_log ADD COLUMN IF NOT EXISTS actor_email TEXT;

-- 4. Fact lifecycle: versions, topic, who changed it
ALTER TABLE facts ADD COLUMN IF NOT EXISTS version INT NOT NULL DEFAULT 1;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS topic TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS updated_by TEXT;
ALTER TABLE facts ADD COLUMN IF NOT EXISTS updated_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS fact_versions (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    fact_id       TEXT NOT NULL,
    version       INT  NOT NULL,
    approved_text TEXT NOT NULL,
    source        TEXT,
    owner         TEXT,
    valid_from    DATE,
    expires_on    DATE,
    status        TEXT,
    topic         TEXT,
    changed_by    TEXT,
    change_note   TEXT,
    archived_at   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS fact_versions_fact_idx ON fact_versions (fact_id, version DESC);

-- 5. Topics for the existing facts (used for conflict detection)
UPDATE facts SET topic = 'upi_fee'             WHERE id = 'F-001' AND topic IS NULL;
UPDATE facts SET topic = 'upi_daily_limit'     WHERE id = 'F-002' AND topic IS NULL;
UPDATE facts SET topic = 'cashback_first_bill' WHERE id = 'F-003' AND topic IS NULL;
UPDATE facts SET topic = 'diwali_offer'        WHERE id = 'F-004' AND topic IS NULL;
UPDATE facts SET topic = 'merchant_fee'        WHERE id = 'F-005' AND topic IS NULL;
UPDATE facts SET topic = 'support_hours'       WHERE id = 'F-006' AND topic IS NULL;
UPDATE facts SET topic = 'card_annual_fee'     WHERE id = 'F-007' AND topic IS NULL;
UPDATE facts SET topic = 'savings_rate'        WHERE id = 'F-008' AND topic IS NULL;
UPDATE facts SET topic = 'upi_lite_limit'      WHERE id = 'F-009' AND topic IS NULL;

-- 6. Rules for the visual checker (the evidence validator needs them to exist)
UPDATE rules SET text = 'Every image must have alt text' WHERE id = 'AC-001';
INSERT INTO rules (id, category, text, severity, version, is_mandatory) VALUES
  ('AC-002', 'accessibility', 'Alt text must describe the image (at least 5 words, not a file name)', 'low', 1, FALSE),
  ('AC-003', 'accessibility', 'Text must have at least 4.5:1 contrast against its background (WCAG 2.2)', 'medium', 1, FALSE),
  ('VC-001', 'visual_brand',  'Dominant image colours must match the approved brand palette', 'medium', 1, FALSE)
ON CONFLICT (id) DO NOTHING;

-- 7. OPTIONAL but recommended: lock the tables so only your backend can read them.
--    ONLY run this block if SUPABASE_KEY on Render is the SERVICE ROLE key
--    (the service role key bypasses these locks; the anon key would be blocked!).
-- ALTER TABLE user_roles    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE fact_versions ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE workspaces    ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE rules         ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE facts         ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE submissions   ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE versions      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE findings      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE comments      ENABLE ROW LEVEL SECURITY;
-- ALTER TABLE audit_log     ENABLE ROW LEVEL SECURITY;
