-- 001_extensions.down.sql
-- Drop V1 extensions. CASCADE is required because tables
-- reference types from both extensions.

DROP EXTENSION IF EXISTS pg_search;
DROP EXTENSION IF EXISTS vector;
