CREATE TABLE IF NOT EXISTS resume_builder_documents (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    document_type TEXT NOT NULL CHECK (document_type IN ('profile', 'version')),
    name TEXT NOT NULL,
    document_json TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_resume_builder_documents_user
    ON resume_builder_documents(user_id, document_type, updated_at);
