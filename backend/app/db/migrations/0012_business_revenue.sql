CREATE TABLE IF NOT EXISTS business_plans (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    tier TEXT NOT NULL CHECK (tier IN ('free', 'starter', 'pro', 'premium', 'student', 'enterprise')),
    billing_interval TEXT NOT NULL CHECK (billing_interval IN ('free', 'monthly', 'yearly', 'one_time')),
    price_minor INTEGER,
    currency TEXT NOT NULL DEFAULT 'INR',
    credits_grant INTEGER NOT NULL DEFAULT 0 CHECK (credits_grant >= 0),
    entitlement_json TEXT NOT NULL DEFAULT '{}',
    gateway_plan_id TEXT,
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_subscriptions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id TEXT NOT NULL REFERENCES business_plans(id),
    status TEXT NOT NULL CHECK (status IN ('pending', 'active', 'past_due', 'cancelled', 'expired')),
    provider TEXT NOT NULL,
    provider_subscription_id TEXT UNIQUE,
    pending_plan_id TEXT REFERENCES business_plans(id),
    current_period_start TEXT,
    current_period_end TEXT,
    cancel_at_period_end INTEGER NOT NULL DEFAULT 0 CHECK (cancel_at_period_end IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_subscriptions_user
    ON business_subscriptions(user_id, status, updated_at DESC);

CREATE TABLE IF NOT EXISTS business_transactions (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    plan_id TEXT REFERENCES business_plans(id),
    marketplace_order_id TEXT,
    provider TEXT NOT NULL,
    provider_order_id TEXT UNIQUE,
    provider_payment_id TEXT UNIQUE,
    amount_minor INTEGER NOT NULL CHECK (amount_minor >= 0),
    discount_minor INTEGER NOT NULL DEFAULT 0 CHECK (discount_minor >= 0),
    currency TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('created', 'captured', 'failed', 'refund_pending', 'refunded')),
    provider_refund_id TEXT UNIQUE,
    coupon_id TEXT,
    purpose TEXT NOT NULL CHECK (purpose IN ('subscription', 'one_time', 'credits', 'marketplace')),
    captured_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_transactions_user
    ON business_transactions(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_payment_attempts (
    id TEXT PRIMARY KEY,
    transaction_id TEXT NOT NULL REFERENCES business_transactions(id) ON DELETE CASCADE,
    provider_payment_id TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('failed', 'captured')),
    error_code TEXT,
    created_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_payment_attempts_transaction
    ON business_payment_attempts(transaction_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_credit_ledger (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    delta INTEGER NOT NULL CHECK (delta != 0),
    balance_after INTEGER NOT NULL,
    entry_type TEXT NOT NULL CHECK (
        entry_type IN ('monthly_grant', 'purchase', 'subscription_grant', 'ai_usage', 'referral_reward', 'admin_adjustment', 'refund_reversal')
    ),
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    reference_id TEXT,
    created_at TEXT NOT NULL,
    UNIQUE(user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_business_credit_ledger_user
    ON business_credit_ledger(user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_credit_reservations (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    operation TEXT NOT NULL,
    idempotency_key TEXT NOT NULL,
    credits INTEGER NOT NULL CHECK (credits > 0),
    status TEXT NOT NULL CHECK (status IN ('reserved', 'completed', 'released')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    UNIQUE(user_id, idempotency_key)
);
CREATE INDEX IF NOT EXISTS ix_business_credit_reservations_user
    ON business_credit_reservations(user_id, status);

CREATE TABLE IF NOT EXISTS business_operation_pricing (
    operation TEXT PRIMARY KEY,
    credit_cost INTEGER NOT NULL CHECK (credit_cost >= 0),
    required_entitlement TEXT,
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0, 1)),
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_settings (
    setting_key TEXT PRIMARY KEY,
    setting_value TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
INSERT OR IGNORE INTO business_settings(setting_key, setting_value, updated_at)
VALUES
    ('free_monthly_credits', '20', strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('referral_reward_credits', '50', strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'));

INSERT OR IGNORE INTO business_operation_pricing(operation, credit_cost, enabled, updated_at)
VALUES
    ('career_coach', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('career_roadmap', 5, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('job_recommendation_rerank', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('application_draft', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('salary_guidance', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('company_research', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('learning_assistant', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('project_evaluation', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')),
    ('personal_branding', 2, 1, strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now'));

CREATE TABLE IF NOT EXISTS business_coupons (
    id TEXT PRIMARY KEY,
    code TEXT NOT NULL UNIQUE COLLATE NOCASE,
    discount_type TEXT NOT NULL CHECK (discount_type IN ('percent', 'fixed')),
    discount_value INTEGER NOT NULL CHECK (discount_value > 0),
    currency TEXT,
    max_redemptions INTEGER,
    redemption_count INTEGER NOT NULL DEFAULT 0,
    expires_at TEXT,
    active INTEGER NOT NULL DEFAULT 1 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_coupon_redemptions (
    id TEXT PRIMARY KEY,
    coupon_id TEXT NOT NULL REFERENCES business_coupons(id),
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_id TEXT NOT NULL UNIQUE REFERENCES business_transactions(id),
    discount_minor INTEGER NOT NULL,
    status TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'redeemed', 'released')),
    created_at TEXT NOT NULL,
    UNIQUE(coupon_id, user_id)
);

CREATE TABLE IF NOT EXISTS business_referral_codes (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_referrals (
    id TEXT PRIMARY KEY,
    referrer_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id TEXT NOT NULL UNIQUE REFERENCES users(id) ON DELETE CASCADE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'qualified', 'rewarded', 'rejected')),
    qualified_transaction_id TEXT UNIQUE REFERENCES business_transactions(id),
    reward_credits INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    CHECK (referrer_user_id != referred_user_id)
);
CREATE INDEX IF NOT EXISTS ix_business_referrals_referrer
    ON business_referrals(referrer_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_affiliates (
    user_id TEXT PRIMARY KEY REFERENCES users(id) ON DELETE CASCADE,
    code TEXT NOT NULL UNIQUE,
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'rejected', 'suspended')),
    commission_basis_points INTEGER NOT NULL DEFAULT 0 CHECK (commission_basis_points BETWEEN 0 AND 10000),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_affiliate_conversions (
    id TEXT PRIMARY KEY,
    affiliate_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    referred_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    transaction_id TEXT NOT NULL UNIQUE REFERENCES business_transactions(id),
    commission_minor INTEGER NOT NULL CHECK (commission_minor >= 0),
    status TEXT NOT NULL CHECK (status IN ('pending', 'approved', 'paid', 'reversed')),
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS business_leads (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    lead_type TEXT NOT NULL CHECK (lead_type IN ('student', 'enterprise', 'recruitment', 'university')),
    organization TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'submitted' CHECK (status IN ('submitted', 'reviewing', 'approved', 'declined', 'closed')),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_leads_status
    ON business_leads(lead_type, status, created_at DESC);

CREATE TABLE IF NOT EXISTS business_marketplace_listings (
    id TEXT PRIMARY KEY,
    provider_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_type TEXT NOT NULL CHECK (listing_type IN ('resume_review', 'career_coaching', 'resume_template')),
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    price_minor INTEGER NOT NULL CHECK (price_minor > 0),
    currency TEXT NOT NULL,
    active INTEGER NOT NULL DEFAULT 0 CHECK (active IN (0, 1)),
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_marketplace_active
    ON business_marketplace_listings(listing_type, active, created_at DESC);

CREATE TABLE IF NOT EXISTS business_marketplace_orders (
    id TEXT PRIMARY KEY,
    customer_user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    listing_id TEXT NOT NULL REFERENCES business_marketplace_listings(id),
    status TEXT NOT NULL CHECK (status IN ('pending_payment', 'paid', 'in_progress', 'completed', 'cancelled', 'disputed', 'refunded')),
    amount_minor INTEGER NOT NULL,
    currency TEXT NOT NULL,
    requirements TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_business_marketplace_orders_customer
    ON business_marketplace_orders(customer_user_id, created_at DESC);

CREATE TABLE IF NOT EXISTS business_marketplace_events (
    id TEXT PRIMARY KEY,
    order_id TEXT NOT NULL REFERENCES business_marketplace_orders(id) ON DELETE CASCADE,
    actor_user_id TEXT NOT NULL REFERENCES users(id),
    event_type TEXT NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);
