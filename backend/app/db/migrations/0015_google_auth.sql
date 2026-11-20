ALTER TABLE users ADD COLUMN auth_provider TEXT NOT NULL DEFAULT 'email';
ALTER TABLE users ADD COLUMN google_sub TEXT;
ALTER TABLE users ADD COLUMN display_name TEXT;
ALTER TABLE users ADD COLUMN avatar_url TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ux_users_google_sub
    ON users(google_sub)
    WHERE google_sub IS NOT NULL;
