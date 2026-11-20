CREATE TABLE IF NOT EXISTS ats_analysis_progress_sessions (
    session_hash TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN ('pending', 'running', 'completed', 'failed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    duration_ms INTEGER,
    error_code TEXT,
    result_json TEXT
);

CREATE INDEX IF NOT EXISTS idx_ats_analysis_progress_sessions_expiry
    ON ats_analysis_progress_sessions(expires_at);

CREATE TABLE IF NOT EXISTS ats_analysis_progress_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_hash TEXT NOT NULL REFERENCES ats_analysis_progress_sessions(session_hash) ON DELETE CASCADE,
    layer_id TEXT NOT NULL,
    step_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('pending', 'in_progress', 'completed', 'failed', 'skipped')),
    details_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_ats_analysis_progress_events_session
    ON ats_analysis_progress_events(session_hash, id);
