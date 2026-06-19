-- 004_fixtures.up.sql
-- Load M1 fixture rows from db/fixtures/*.sql.
--
-- The apply script sets the SQL variable `:fixtures_dir` via
-- `psql -v fixtures_dir=<path>` before each run. This makes the
-- \i directive portable across developer machines and avoids
-- hard-coding any path. If :fixtures_dir is unset, the script
-- prints a clear error and refuses to apply.
--
-- See docs/AUDITS/FINDINGS.md F-5 for the rationale.

\i :fixtures_dir/001_users.sql
\i :fixtures_dir/002_documents.sql
\i :fixtures_dir/003_chunks.sql



