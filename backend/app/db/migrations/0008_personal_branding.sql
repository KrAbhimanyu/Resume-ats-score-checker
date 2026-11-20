CREATE TABLE IF NOT EXISTS personal_brand_profiles (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    profile_json TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS personal_brand_versions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    content_type TEXT NOT NULL,
    title TEXT NOT NULL,
    tone TEXT NOT NULL,
    content_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_personal_brand_versions_user
    ON personal_brand_versions(user_id, updated_at);

CREATE TABLE IF NOT EXISTS personal_brand_analytics (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    platform TEXT NOT NULL CHECK (platform IN ('linkedin', 'github', 'portfolio')),
    activity_date TEXT NOT NULL,
    title TEXT NOT NULL,
    impressions INTEGER NOT NULL DEFAULT 0 CHECK (impressions >= 0),
    reactions INTEGER NOT NULL DEFAULT 0 CHECK (reactions >= 0),
    comments INTEGER NOT NULL DEFAULT 0 CHECK (comments >= 0),
    clicks INTEGER NOT NULL DEFAULT 0 CHECK (clicks >= 0),
    followers INTEGER NOT NULL DEFAULT 0 CHECK (followers >= 0),
    source TEXT NOT NULL DEFAULT 'user_reported' CHECK (source = 'user_reported'),
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_personal_brand_analytics_user
    ON personal_brand_analytics(user_id, activity_date DESC);
