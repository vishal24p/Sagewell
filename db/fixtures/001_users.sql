-- 001_users.sql
-- Fixture: users covering every V1 department (finance, hr,
-- engineering, marketing) and every clearance tier
-- (PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED). Roles span
-- employee, manager, and admin. Fixtures are intentionally
-- small; downstream milestones can add more.

-- All fixture users carry an `external_subject` prefixed
-- with `fixture-` so 004_fixtures.down.sql can identify them
-- without altering the canonical `users` schema in any way.
-- The data-layer boundary (prefix) and the schema (no
-- is_fixture column) keep DATABASE_SCHEMA.md unchanged.

INSERT INTO users (external_subject, email, display_name, status, department, clearance, role)
VALUES
    ('fixture-finance-employee-1',    'finance-employee-1@example.com',      'Finance Employee 1',         'active', 'finance',     'INTERNAL',    'employee'),
    ('fixture-finance-manager-1',     'finance-manager-1@example.com',       'Finance Manager 1',          'active', 'finance',     'CONFIDENTIAL','manager'),
    ('fixture-hr-employee-1',         'hr-employee-1@example.com',           'HR Employee 1',              'active', 'hr',          'INTERNAL',    'employee'),
    ('fixture-hr-restricted-1',       'hr-restricted-1@example.com',         'HR Restricted 1',            'active', 'hr',          'RESTRICTED',  'manager'),
    ('fixture-eng-public-1',          'eng-public-1@example.com',            'Engineering Public 1',       'active', 'engineering', 'PUBLIC',      'employee'),
    ('fixture-eng-confidential-1',    'eng-confidential-1@example.com',      'Engineering Confidential 1', 'active', 'engineering', 'CONFIDENTIAL','employee'),
    ('fixture-mkt-employee-1',        'mkt-employee-1@example.com',          'Marketing Employee 1',       'active', 'marketing',   'INTERNAL',    'employee'),
    ('fixture-cross-internal-admin',  'cross-internal-admin@example.com',    'Cross Department Internal 1','active', 'finance',     'INTERNAL',    'admin'),
    ('fixture-finance-conf-1',        'finance-confidential-1@example.com',  'Finance Confidential 1',     'active', 'finance',     'CONFIDENTIAL','employee'),
    ('fixture-finance-public-1',      'finance-public-1@example.com',        'Finance Public 1',           'active', 'finance',     'PUBLIC',      'employee')
ON CONFLICT DO NOTHING;
