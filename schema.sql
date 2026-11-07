-- 1. Workspaces table
CREATE TABLE IF NOT EXISTS workspaces (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    description TEXT,
    tone TEXT
);

-- 2. Rules table
CREATE TABLE IF NOT EXISTS rules (
    id TEXT PRIMARY KEY,
    category TEXT NOT NULL,
    text TEXT NOT NULL,
    severity TEXT NOT NULL,
    version INT NOT NULL DEFAULT 1,
    is_mandatory BOOLEAN NOT NULL DEFAULT FALSE
);

-- 3. Facts table
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY,
    approved_text TEXT NOT NULL,
    source TEXT NOT NULL,
    owner TEXT NOT NULL,
    valid_from DATE,
    expires_on DATE,
    status TEXT NOT NULL
);

-- 4. Submissions table
CREATE TABLE IF NOT EXISTS submissions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title TEXT NOT NULL,
    channel TEXT NOT NULL,
    audience TEXT NOT NULL,
    creator TEXT NOT NULL,
    status TEXT NOT NULL,
    current_version INT NOT NULL DEFAULT 1
);

-- 5. Versions table
CREATE TABLE IF NOT EXISTS versions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    version_no INT NOT NULL,
    body TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 6. Findings table
CREATE TABLE IF NOT EXISTS findings (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    version_id UUID NOT NULL REFERENCES versions(id) ON DELETE CASCADE,
    category TEXT NOT NULL,
    severity TEXT NOT NULL,
    confidence FLOAT NOT NULL,
    excerpt TEXT NOT NULL,
    rule_or_fact_id TEXT NOT NULL,
    source_ref TEXT,
    explanation TEXT NOT NULL,
    fix_1 TEXT NOT NULL,
    fix_2 TEXT NOT NULL,
    needs_human BOOLEAN DEFAULT FALSE, -- ADDED THIS LINE HERE
    evidence_valid BOOLEAN NOT NULL DEFAULT TRUE,
    decision TEXT NOT NULL DEFAULT 'pending',
    decision_reason TEXT
);

-- 7. Comments table
CREATE TABLE IF NOT EXISTS comments (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- 8. Audit Log table
CREATE TABLE IF NOT EXISTS audit_log (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    submission_id UUID NOT NULL REFERENCES submissions(id) ON DELETE CASCADE,
    role TEXT NOT NULL,
    action TEXT NOT NULL,
    detail TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);