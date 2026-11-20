CREATE TABLE IF NOT EXISTS salary_offer_comparisons (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    title TEXT NOT NULL,
    offer_ids_json TEXT NOT NULL,
    offers_snapshot_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_salary_offer_comparisons_user
    ON salary_offer_comparisons(user_id, updated_at DESC);
