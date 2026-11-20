CREATE TABLE IF NOT EXISTS application_drafts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    application_id TEXT NOT NULL REFERENCES applications(id) ON DELETE CASCADE,
    resume_profile_id TEXT REFERENCES resume_profiles(id) ON DELETE SET NULL,
    draft_type TEXT NOT NULL CHECK (
        draft_type IN (
            'cover_letter', 'application_email', 'recruiter_follow_up',
            'interview_follow_up', 'application_assistant'
        )
    ),
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_application_drafts_user_application
    ON application_drafts(user_id, application_id, updated_at DESC);
