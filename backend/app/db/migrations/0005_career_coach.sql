CREATE TABLE IF NOT EXISTS career_coach_settings (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    ai_data_consent INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS career_coach_goals (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_json TEXT NOT NULL,
    goal_type TEXT NOT NULL CHECK (goal_type IN ('short_term', 'long_term')),
    status TEXT NOT NULL DEFAULT 'active'
        CHECK (status IN ('active', 'completed', 'paused', 'archived')),
    progress REAL NOT NULL DEFAULT 0 CHECK (progress >= 0 AND progress <= 100),
    target_date TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_career_coach_goals_user
    ON career_coach_goals(user_id, status, updated_at);

CREATE TABLE IF NOT EXISTS career_coach_roadmaps (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    goal_id TEXT REFERENCES career_coach_goals(id) ON DELETE SET NULL,
    roadmap_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_career_coach_roadmaps_user
    ON career_coach_roadmaps(user_id, updated_at);

CREATE TABLE IF NOT EXISTS career_coach_milestones (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    roadmap_id TEXT NOT NULL REFERENCES career_coach_roadmaps(id) ON DELETE CASCADE,
    milestone_json TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'planned'
        CHECK (status IN ('planned', 'in_progress', 'completed')),
    due_date TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    completed_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_career_coach_milestones_roadmap
    ON career_coach_milestones(user_id, roadmap_id, sort_order);

CREATE TABLE IF NOT EXISTS career_coach_messages (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_career_coach_messages_history
    ON career_coach_messages(user_id, created_at);
