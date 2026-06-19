-- 004_fixtures.up.sql
-- Load M1 fixture rows from db/fixtures/*.sql relative to the
-- repository root. \i is a psql include directive; the rows below
-- read the three fixture files in dependency order. The fixture
-- boundary is the 'fixture-' external_subject prefix and
-- source_system='fixture'; neither requires a schema change.

\i /workspace/db/fixtures/001_users.sql
\i /workspace/db/fixtures/002_documents.sql
\i /workspace/db/fixtures/003_chunks.sql


