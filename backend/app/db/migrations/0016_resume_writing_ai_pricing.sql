INSERT OR IGNORE INTO business_operation_pricing(operation, credit_cost, enabled, updated_at)
VALUES (
    'resume_writing',
    2,
    1,
    strftime('%Y-%m-%dT%H:%M:%f+00:00', 'now')
);
