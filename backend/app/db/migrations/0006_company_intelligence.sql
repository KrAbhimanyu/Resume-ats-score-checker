CREATE TABLE IF NOT EXISTS company_profile_cache (
    entity_id TEXT PRIMARY KEY,
    company_name TEXT NOT NULL,
    profile_json TEXT NOT NULL,
    retrieved_at TEXT NOT NULL,
    source_modified_at TEXT
);
CREATE INDEX IF NOT EXISTS ix_company_profile_cache_name
    ON company_profile_cache(company_name COLLATE NOCASE);

CREATE TABLE IF NOT EXISTS saved_target_companies (
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    entity_id TEXT NOT NULL,
    company_name TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY(user_id, entity_id)
);
CREATE INDEX IF NOT EXISTS ix_saved_target_companies_user
    ON saved_target_companies(user_id, created_at);
