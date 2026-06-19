-- 003_chunks.sql
-- Fixture: one chunk per document so retrieval and access-decision
-- test paths have a row to look up. embeddings are null in the
-- fixture because the M0 embedding model is capability-based and
-- not pinned (D-002). M7 ingestion will populate embeddings.

INSERT INTO chunks (document_id, ordinal, text, text_search, embedding, metadata, token_count, status)
SELECT
    d.id,
    0,
    'Fixture chunk for ' || d.title || '. Placeholder text used by Sagewell M1 fixtures.',
    'fixture ' || d.title || ' placeholder',
    NULL,
    jsonb_build_object('fixture', true, 'source', d.source_system || ':' || d.source_id),
    12,
    'active'
FROM documents d
WHERE d.source_system = 'fixture'
ON CONFLICT DO NOTHING;
