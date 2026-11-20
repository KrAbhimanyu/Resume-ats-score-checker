ALTER TABLE reminders
ADD COLUMN job_id TEXT REFERENCES jobs(id) ON DELETE CASCADE;

CREATE INDEX IF NOT EXISTS ix_reminders_job ON reminders(job_id, due_at);
