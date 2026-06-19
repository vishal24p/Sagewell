-- 003_indexes.up.sql
-- V1 indexes per DATABASE_SCHEMA.md.
--
-- Listing:
--   chunks_document_id_idx            (chunks.document_id)
--   chunks_status_idx                 (chunks.status)
--   documents_access_filter_idx       (documents.department,
--                                      required_clearance, status)
--   chunks_embedding_idx              (chunks.embedding via HNSW)
--
-- Note: the lexical index on chunks.text_search is created by
-- ParadeDB pg_search (BM25) and is fixture-driven; the schema
-- narrative says "Lexical index details follow the chosen
-- pg_search integration". When implementing retrieval (M8) a
-- follow-up migration adds the BM25 index explicitly.

CREATE INDEX IF NOT EXISTS chunks_document_id_idx
    ON chunks (document_id);

CREATE INDEX IF NOT EXISTS chunks_status_idx
    ON chunks (status);

CREATE INDEX IF NOT EXISTS documents_access_filter_idx
    ON documents (department, required_clearance, status);

CREATE INDEX IF NOT EXISTS chunks_embedding_idx
    ON chunks USING hnsw (embedding vector_cosine_ops);
