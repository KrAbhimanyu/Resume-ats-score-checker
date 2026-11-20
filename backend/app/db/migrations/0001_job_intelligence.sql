CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS auth_sessions (
    token_hash TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_auth_sessions_user ON auth_sessions(user_id);

CREATE TABLE IF NOT EXISTS search_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    preferences_json TEXT NOT NULL DEFAULT '{}',
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS resume_profiles (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    resume_text TEXT NOT NULL,
    parsed_json TEXT NOT NULL,
    is_primary INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_resume_profiles_user ON resume_profiles(user_id, updated_at);

CREATE TABLE IF NOT EXISTS companies (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL COLLATE NOCASE UNIQUE,
    industry TEXT,
    website TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    source_job_id TEXT,
    company_id TEXT REFERENCES companies(id) ON DELETE SET NULL,
    owner_user_id TEXT REFERENCES users(id) ON DELETE CASCADE,
    visibility TEXT NOT NULL DEFAULT 'public',
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    location TEXT,
    country TEXT,
    remote_type TEXT,
    employment_type TEXT,
    salary_min REAL,
    salary_max REAL,
    salary_currency TEXT,
    salary_period TEXT,
    description TEXT NOT NULL,
    original_url TEXT NOT NULL,
    posted_at TEXT,
    expires_at TEXT,
    availability TEXT NOT NULL DEFAULT 'unknown',
    source_label TEXT NOT NULL,
    source_url TEXT NOT NULL,
    raw_json TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(source, source_job_id)
);
CREATE INDEX IF NOT EXISTS ix_jobs_posted ON jobs(posted_at);
CREATE INDEX IF NOT EXISTS ix_jobs_company ON jobs(company_id);
CREATE INDEX IF NOT EXISTS ix_jobs_availability ON jobs(availability);
CREATE INDEX IF NOT EXISTS ix_jobs_owner ON jobs(owner_user_id, visibility);

CREATE TABLE IF NOT EXISTS job_recommendations (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    resume_id TEXT REFERENCES resume_profiles(id) ON DELETE SET NULL,
    score REAL NOT NULL,
    explanation_json TEXT NOT NULL,
    state TEXT NOT NULL DEFAULT 'active',
    first_recommended_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_recommendations_user ON job_recommendations(user_id, state, score);

CREATE TABLE IF NOT EXISTS job_matches (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    resume_id TEXT REFERENCES resume_profiles(id) ON DELETE SET NULL,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    job_fingerprint TEXT NOT NULL,
    score REAL NOT NULL,
    result_json TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_job_matches_user ON job_matches(user_id, created_at);

CREATE TABLE IF NOT EXISTS skill_progress (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill TEXT NOT NULL COLLATE NOCASE,
    status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, skill)
);

CREATE TABLE IF NOT EXISTS saved_jobs (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    saved_at TEXT NOT NULL,
    PRIMARY KEY(user_id, job_id)
);
CREATE INDEX IF NOT EXISTS ix_saved_jobs_user ON saved_jobs(user_id, saved_at);

CREATE TABLE IF NOT EXISTS applications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    job_id TEXT REFERENCES jobs(id) ON DELETE SET NULL,
    title TEXT NOT NULL,
    company_name TEXT NOT NULL,
    location TEXT,
    original_url TEXT,
    description TEXT NOT NULL DEFAULT '',
    source TEXT NOT NULL DEFAULT 'manual',
    salary_json TEXT NOT NULL DEFAULT '{}',
    status TEXT NOT NULL,
    applied_at TEXT,
    resume_version_id TEXT,
    notes TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_applications_user_status ON applications(user_id, status, updated_at);
CREATE INDEX IF NOT EXISTS ix_applications_user_applied ON applications(user_id, applied_at);

CREATE TABLE IF NOT EXISTS application_events (
    id TEXT PRIMARY KEY,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    from_status TEXT,
    to_status TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_application_events_history ON application_events(user_id, application_id, created_at);

CREATE TABLE IF NOT EXISTS interviews (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    scheduled_at TEXT NOT NULL,
    timezone TEXT NOT NULL,
    interview_type TEXT NOT NULL,
    meeting_url TEXT,
    interviewer_details TEXT NOT NULL DEFAULT '',
    preparation_notes TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'scheduled',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_interviews_user_time ON interviews(user_id, scheduled_at, status);

CREATE TABLE IF NOT EXISTS reminders (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id TEXT REFERENCES applications(id) ON DELETE CASCADE,
    interview_id TEXT REFERENCES interviews(id) ON DELETE CASCADE,
    reminder_type TEXT NOT NULL,
    due_at TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'scheduled',
    snoozed_until TEXT,
    email_requested INTEGER NOT NULL DEFAULT 0,
    email_status TEXT NOT NULL DEFAULT 'not_requested',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_reminders_user_due ON reminders(user_id, status, due_at);

CREATE TABLE IF NOT EXISTS notifications (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    reminder_id TEXT REFERENCES reminders(id) ON DELETE SET NULL,
    message TEXT NOT NULL,
    created_at TEXT NOT NULL,
    read_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_notifications_user ON notifications(user_id, created_at);

CREATE TABLE IF NOT EXISTS salary_observations (
    id TEXT PRIMARY KEY,
    job_id TEXT NOT NULL REFERENCES jobs(id) ON DELETE CASCADE,
    source TEXT NOT NULL,
    minimum REAL NOT NULL,
    maximum REAL NOT NULL,
    currency TEXT NOT NULL,
    period TEXT NOT NULL,
    observed_at TEXT NOT NULL,
    UNIQUE(job_id, source)
);
CREATE INDEX IF NOT EXISTS ix_salary_observations_currency ON salary_observations(currency, period);

CREATE TABLE IF NOT EXISTS job_search_events (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    query_json TEXT NOT NULL,
    result_count INTEGER NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_job_search_events_user ON job_search_events(user_id, created_at);

CREATE TABLE IF NOT EXISTS provider_syncs (
    provider TEXT PRIMARY KEY,
    last_attempt_at TEXT,
    last_success_at TEXT,
    last_error_at TEXT,
    last_error_code TEXT,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS provider_search_cache (
    cache_key TEXT PRIMARY KEY,
    provider TEXT NOT NULL,
    response_json TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_provider_search_cache_expiry ON provider_search_cache(expires_at);

CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    applied_at TEXT NOT NULL
);
