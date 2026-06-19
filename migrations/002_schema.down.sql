-- 002_schema.down.sql
-- Drop the V1 tables in dependency order.
-- RESTRICT FKs make application soft-delete via `status` the
-- first-class delete path.

DROP TABLE IF EXISTS evaluation_results;
DROP TABLE IF EXISTS retrieval_logs;
DROP TABLE IF EXISTS audit_logs;
DROP TABLE IF EXISTS chunks;
DROP TABLE IF EXISTS documents;
DROP TABLE IF EXISTS users;
