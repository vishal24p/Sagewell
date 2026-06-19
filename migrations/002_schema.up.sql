-- 002_schema.up.sql
-- V1 schema. Six tables only: users, documents, chunks,
-- audit_logs, retrieval_logs, evaluation_results.
--
-- Conventions in this schema narrative:
--   * Application-soft-delete via the `status` column where one
--     is defined. No ON DELETE CASCADE; RESTRICT is the default
--     (see ADR for cascade choice).
--   * reason_code is TEXT, no DB-level constraint, application
--     validates per the M0 IMM start codes plus M2+ codes added
--     in their own milestones (see NEXT_AGENT.md M1 resolution).
--   * `role` on `users` is for UI behavior and auditing only;
--     it does not participate in authorization.
--   * `documents.department` may be 'ALL' for company-wide docs.
--     The check is application-enforced.
--   * `chunks.embedding` is `vector(1536)` per the Embedding
--     Model capability decision recorded in docs/adr/0004-
--     embedding-dimension.md. The dimension is a column-level
--     constraint; ALTER will be required if the capability
--     changes (and that change must be ADR-driven).
--   * `users.external_subject` and `users.email` are UNIQUE.
--     external_subject is the JWT look-up key in M5; uniqueness
--     is non-negotiable for identity correctness.
--   * `users.updated_at` and `documents.updated_at` are kept
--     current by BEFORE UPDATE triggers (see the end of this
--     file). Application code may still write updated_at for
--     explicit corrections.
--
-- See DATABASE_SCHEMA.md for the canonical narrative and
-- docs/adr/0001-... for the architectural baseline.

-- users
CREATE TABLE IF NOT EXISTS users (
    id               BIGSERIAL PRIMARY KEY,
    external_subject TEXT NOT NULL,
    email            TEXT NOT NULL,
    display_name     TEXT NOT NULL,
    status           TEXT NOT NULL,
    department       TEXT NOT NULL,
    clearance        TEXT NOT NULL,
    role             TEXT,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT users_external_subject_unique UNIQUE (external_subject),
    CONSTRAINT users_email_unique UNIQUE (email)
);

-- documents
CREATE TABLE IF NOT EXISTS documents (
    id                 BIGSERIAL PRIMARY KEY,
    source_system      TEXT NOT NULL,
    source_id          TEXT NOT NULL,
    title              TEXT NOT NULL,
    uri                TEXT,
    status             TEXT NOT NULL,
    department         TEXT NOT NULL,
    required_clearance TEXT NOT NULL,
    content_checksum   TEXT NOT NULL,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT documents_source_unique UNIQUE (source_system, source_id)
);

-- chunks
CREATE TABLE IF NOT EXISTS chunks (
    id           BIGSERIAL PRIMARY KEY,
    document_id  BIGINT NOT NULL REFERENCES documents(id) ON DELETE RESTRICT,
    ordinal      INTEGER NOT NULL,
    text         TEXT NOT NULL,
    text_search  TEXT,
    embedding    vector(1536),
    metadata     JSONB NOT NULL DEFAULT '{}'::jsonb,
    token_count  INTEGER,
    status       TEXT NOT NULL,
    created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- audit_logs
CREATE TABLE IF NOT EXISTS audit_logs (
    id             BIGSERIAL PRIMARY KEY,
    actor_user_id  BIGINT REFERENCES users(id) ON DELETE RESTRICT,
    action         TEXT NOT NULL,
    resource_type  TEXT,
    resource_id    TEXT,
    decision       TEXT NOT NULL,
    reason_code    TEXT NOT NULL,
    correlation_id TEXT NOT NULL,
    metadata       JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- retrieval_logs
CREATE TABLE IF NOT EXISTS retrieval_logs (
    id               BIGSERIAL PRIMARY KEY,
    actor_user_id    BIGINT NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
    query_text       TEXT NOT NULL,
    policy_filter    JSONB NOT NULL DEFAULT '{}'::jsonb,
    retrieval_config JSONB NOT NULL DEFAULT '{}'::jsonb,
    candidate_counts JSONB NOT NULL DEFAULT '{}'::jsonb,
    correlation_id   TEXT NOT NULL,
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- evaluation_results
CREATE TABLE IF NOT EXISTS evaluation_results (
    id              BIGSERIAL PRIMARY KEY,
    suite           TEXT NOT NULL,
    case_key        TEXT NOT NULL,
    input           JSONB NOT NULL DEFAULT '{}'::jsonb,
    expected        JSONB NOT NULL DEFAULT '{}'::jsonb,
    status          TEXT NOT NULL,
    scores          JSONB NOT NULL DEFAULT '{}'::jsonb,
    failure_reason  TEXT,
    model_config    JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- updated_at maintenance. PostgreSQL supports per-row trigger
-- functions. We keep the function narrowly scoped so it does
-- nothing except touch updated_at. The trigger is created once
-- per table; the function is shared.
CREATE OR REPLACE FUNCTION sagewell_touch_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS users_touch_updated_at ON users;
CREATE TRIGGER users_touch_updated_at
    BEFORE UPDATE ON users
    FOR EACH ROW
    EXECUTE FUNCTION sagewell_touch_updated_at();

DROP TRIGGER IF EXISTS documents_touch_updated_at ON documents;
CREATE TRIGGER documents_touch_updated_at
    BEFORE UPDATE ON documents
    FOR EACH ROW
    EXECUTE FUNCTION sagewell_touch_updated_at();

