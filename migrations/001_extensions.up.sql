-- 001_extensions.up.sql
-- V1 extensions: pgvector and ParadeDB pg_search.
-- See docs/adr/0002-pg-search-paradedb.md.

CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS pg_search;
