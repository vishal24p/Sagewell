-- 002_documents.sql
-- Fixture: documents spanning each (department, required_clearance)
-- pair the RBAC Access Outcome Suite expects to exercise, plus the
-- ALL-department wildcard. status is 'active' for fixtures.

INSERT INTO documents (source_system, source_id, title, uri, status, department, required_clearance, content_checksum)
VALUES
    ('fixture', 'doc-fin-public',       'Finance Public Fixture',   'fixture://finance/public',     'active', 'finance',     'PUBLIC',       'sha-fixture-fin-public-001'),
    ('fixture', 'doc-fin-internal',     'Finance Internal Fixture', 'fixture://finance/internal',   'active', 'finance',     'INTERNAL',     'sha-fixture-fin-internal-001'),
    ('fixture', 'doc-fin-confidential', 'Finance Confidential Fixture','fixture://finance/confidential','active','finance','CONFIDENTIAL','sha-fixture-fin-confidential-001'),
    ('fixture', 'doc-fin-restricted',   'Finance Restricted Fixture','fixture://finance/restricted', 'active', 'finance',     'RESTRICTED',   'sha-fixture-fin-restricted-001'),
    ('fixture', 'doc-hr-public',        'HR Public Fixture',        'fixture://hr/public',          'active', 'hr',          'PUBLIC',       'sha-fixture-hr-public-001'),
    ('fixture', 'doc-hr-internal',      'HR Internal Fixture',      'fixture://hr/internal',        'active', 'hr',          'INTERNAL',     'sha-fixture-hr-internal-001'),
    ('fixture', 'doc-hr-confidential',  'HR Confidential Fixture',  'fixture://hr/confidential',    'active', 'hr',          'CONFIDENTIAL', 'sha-fixture-hr-confidential-001'),
    ('fixture', 'doc-hr-restricted',    'HR Restricted Fixture',    'fixture://hr/restricted',      'active', 'hr',          'RESTRICTED',   'sha-fixture-hr-restricted-001'),
    ('fixture', 'doc-all-public',       'ALL Public Fixture',       'fixture://all/public',         'active', 'ALL',         'PUBLIC',       'sha-fixture-all-public-001'),
    ('fixture', 'doc-all-internal',     'ALL Internal Fixture',     'fixture://all/internal',       'active', 'ALL',         'INTERNAL',     'sha-fixture-all-internal-001')
ON CONFLICT (source_system, source_id) DO NOTHING;
