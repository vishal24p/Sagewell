-- 004_fixtures.down.sql
-- Remove the fixture rows loaded by 004_fixtures.up.sql. Uses
-- `external_subject` starting with `fixture-` (users) and
-- `source_system='fixture'` (documents/chunks). These markers
-- are part of the fixture layout, not the canonical schema in
-- DATABASE_SCHEMA.md, so the canonical schema is unchanged.

DELETE FROM chunks WHERE document_id IN (SELECT id FROM documents WHERE source_system = 'fixture');
DELETE FROM documents WHERE source_system = 'fixture';
DELETE FROM users WHERE external_subject LIKE 'fixture-%';

