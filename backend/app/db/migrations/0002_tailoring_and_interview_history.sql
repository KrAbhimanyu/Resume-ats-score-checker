ALTER TABLE resume_profiles ADD COLUMN structured_json TEXT;

CREATE TABLE IF NOT EXISTS tailoring_sessions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id TEXT NOT NULL REFERENCES resume_profiles(id) ON DELETE CASCADE,
    analysis_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'review',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_tailoring_user ON tailoring_sessions(user_id, created_at);

CREATE TABLE IF NOT EXISTS interview_events (
    id TEXT PRIMARY KEY,
    interview_id TEXT NOT NULL REFERENCES interviews(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    event_type TEXT NOT NULL,
    event_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_interview_events_history ON interview_events(user_id, interview_id, created_at);

CREATE TABLE IF NOT EXISTS auth_rate_limits (
    rate_key TEXT NOT NULL,
    operation TEXT NOT NULL,
    window_started_at TEXT NOT NULL,
    attempts INTEGER NOT NULL,
    PRIMARY KEY(rate_key, operation)
);
