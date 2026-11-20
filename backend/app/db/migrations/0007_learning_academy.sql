CREATE TABLE IF NOT EXISTS academy_activity_progress (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    activity_id TEXT NOT NULL,
    track_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('started', 'completed')),
    score REAL,
    result_json TEXT,
    started_at TEXT NOT NULL,
    completed_at TEXT,
    updated_at TEXT NOT NULL,
    PRIMARY KEY(user_id, activity_id)
);
CREATE INDEX IF NOT EXISTS ix_academy_activity_user
    ON academy_activity_progress(user_id, track_id, status);

CREATE TABLE IF NOT EXISTS academy_assessments (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id TEXT NOT NULL,
    answers_json TEXT NOT NULL,
    result_json TEXT NOT NULL,
    score REAL NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_assessments_user
    ON academy_assessments(user_id, track_id, created_at);

CREATE TABLE IF NOT EXISTS academy_roadmaps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    target_role TEXT NOT NULL,
    roadmap_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_roadmaps_user
    ON academy_roadmaps(user_id, updated_at);

CREATE TABLE IF NOT EXISTS academy_projects (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    project_url TEXT,
    evaluation_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_projects_user
    ON academy_projects(user_id, updated_at);

CREATE TABLE IF NOT EXISTS academy_skill_evidence (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    skill TEXT NOT NULL,
    evidence_type TEXT NOT NULL CHECK (evidence_type IN ('portfolio', 'project', 'external_certificate', 'platform_assessment')),
    evidence_description TEXT NOT NULL,
    evidence_url TEXT,
    verification_status TEXT NOT NULL CHECK (verification_status IN ('user_submitted', 'assessment_verified')),
    assessment_id TEXT REFERENCES academy_assessments(id) ON DELETE SET NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_skill_evidence_user
    ON academy_skill_evidence(user_id, skill COLLATE NOCASE, created_at);

CREATE TABLE IF NOT EXISTS academy_certificates (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    track_id TEXT NOT NULL,
    serial_number TEXT NOT NULL UNIQUE,
    issued_at TEXT NOT NULL,
    score REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_certificates_user
    ON academy_certificates(user_id, issued_at);

CREATE TABLE IF NOT EXISTS academy_chat_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_academy_chat_history
    ON academy_chat_messages(user_id, created_at);
