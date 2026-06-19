-- 001_extensions.down.sql
-- Drop V1 extensions in the correct order for a clean rollback.
--
-- REQUIREMENT: this file MUST run AFTER 002_schema.down.sql and
-- 003_indexes.down.sql, which drop tables and indexes that
-- reference vector and pg_search types. Dropping the extensions
-- while dependent objects exist requires CASCADE; the prescribed
-- ordering avoids CASCADE and preserves audit chain. The runner
-- infrastructure/migrations/rollback.sh walks down files in
-- reverse numerical order, which satisfies this requirement only
-- when no migration is missing or partially applied.
--
-- See docs/AUDITS/FINDINGS.md F-8 for the rationale.

DROP EXTENSION IF EXISTS pg_search;
DROP EXTENSION IF EXISTS vector;
