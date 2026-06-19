-- 003_indexes.down.sql
-- Drop the V1 indexes in dependency order.

DROP INDEX IF EXISTS chunks_embedding_idx;
DROP INDEX IF EXISTS documents_access_filter_idx;
DROP INDEX IF EXISTS chunks_status_idx;
DROP INDEX IF EXISTS chunks_document_id_idx;
