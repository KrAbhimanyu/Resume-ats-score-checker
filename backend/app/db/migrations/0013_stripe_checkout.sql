ALTER TABLE business_subscriptions
    ADD COLUMN provider_checkout_session_id TEXT;

CREATE UNIQUE INDEX IF NOT EXISTS ix_business_subscriptions_checkout_session
    ON business_subscriptions(provider_checkout_session_id)
    WHERE provider_checkout_session_id IS NOT NULL;

CREATE TABLE IF NOT EXISTS business_stripe_events (
    event_id TEXT PRIMARY KEY,
    event_type TEXT NOT NULL,
    received_at TEXT NOT NULL
);
