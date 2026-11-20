CREATE TABLE IF NOT EXISTS career_achievements (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    achievement_key TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    evidence TEXT NOT NULL,
    awarded_at TEXT NOT NULL,
    PRIMARY KEY (user_id, achievement_key)
);
CREATE INDEX IF NOT EXISTS ix_career_achievements_user
    ON career_achievements(user_id, awarded_at DESC);

CREATE TABLE IF NOT EXISTS career_notification_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    in_app_applications INTEGER NOT NULL DEFAULT 1,
    in_app_interviews INTEGER NOT NULL DEFAULT 1,
    in_app_deadlines INTEGER NOT NULL DEFAULT 1,
    email_applications INTEGER NOT NULL DEFAULT 1,
    email_interviews INTEGER NOT NULL DEFAULT 1,
    email_deadlines INTEGER NOT NULL DEFAULT 1,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS career_score_preferences (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    weights_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
