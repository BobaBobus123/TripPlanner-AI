CREATE TABLE IF NOT EXISTS users (
    id UUID PRIMARY KEY,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    email_verified BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
ALTER TABLE users ADD COLUMN IF NOT EXISTS email_verified BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE IF NOT EXISTS email_verification_tokens (
    token_hash TEXT PRIMARY KEY,
    user_id UUID NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS email_verification_tokens_expires_idx
    ON email_verification_tokens (expires_at);

CREATE TABLE IF NOT EXISTS sessions (
    token_hash TEXT PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    csrf_token TEXT NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS sessions_expires_at_idx ON sessions (expires_at);

CREATE TABLE IF NOT EXISTS login_attempts (
    attempt_key TEXT PRIMARY KEY,
    window_started_at TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS login_attempts_window_idx ON login_attempts (window_started_at);

CREATE TABLE IF NOT EXISTS app_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS jobs (
    id UUID PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    request_json JSONB NOT NULL,
    request_fingerprint TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN ('queued', 'preparing', 'generating', 'validating', 'completed',
                   'failed', 'cancel_requested', 'cancelled', 'interrupted')
    ),
    stage_message TEXT NOT NULL,
    error_code TEXT,
    worker_id TEXT,
    lease_until TIMESTAMPTZ,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS jobs_queue_idx ON jobs (created_at)
    WHERE status = 'queued';
CREATE INDEX IF NOT EXISTS jobs_lease_idx ON jobs (lease_until)
    WHERE status IN ('preparing', 'generating', 'validating');

CREATE TABLE IF NOT EXISTS job_events (
    id BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    job_id UUID NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    status TEXT NOT NULL,
    message TEXT NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS job_events_job_id_idx ON job_events (job_id, id);

CREATE TABLE IF NOT EXISTS plans (
    id UUID PRIMARY KEY,
    job_id UUID NOT NULL UNIQUE REFERENCES jobs(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    version INTEGER NOT NULL DEFAULT 1,
    parent_plan_id UUID REFERENCES plans(id) ON DELETE SET NULL,
    plan_json JSONB NOT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS plans_user_created_idx ON plans (user_id, created_at DESC);

ALTER TABLE sessions ADD COLUMN IF NOT EXISTS csrf_token TEXT;
DELETE FROM sessions WHERE csrf_token IS NULL;
ALTER TABLE sessions ALTER COLUMN csrf_token SET NOT NULL;
ALTER TABLE sessions DROP COLUMN IF EXISTS csrf_token_hash;
DELETE FROM sessions WHERE expires_at <= now();
