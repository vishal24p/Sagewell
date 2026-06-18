# Requirements

## Functional Requirements

- Authenticate users.
- Map users to roles and groups.
- Track user department and clearance level.
- Ingest documents from approved sources.
- Track document versions and checksums.
- Chunk documents and store embeddings.
- Run vector and lexical retrieval.
- Enforce RBAC before and after retrieval.
- Enforce department and clearance filters during retrieval.
- Generate answers with citations.
- Detect prompt-injection risk in retrieved content.
- Record audit events.
- Run RAGAS and RBAC eval suites.

## Non-Functional Requirements

- Fail closed on authorization uncertainty.
- Keep retrieval behavior observable.
- Keep ingestion idempotent.
- Keep architecture boundaries testable.
- Keep errors safe for end users.
- Avoid storing secrets in logs.
- Support deterministic regression tests.

## Security Requirements

- Deny unauthorized document access.
- Prevent citation leaks.
- Prevent existence leaks where possible.
- Treat documents as untrusted data.
- Log policy decisions with reason codes.
- Redact sensitive data in operational logs.

## Documentation Requirements

- `AGENTS.md` stays concise.
- Architecture detail lives in `ARCHITECTURE.md`.
- Schema detail lives in `DATABASE_SCHEMA.md`.
- Runtime flows live in `WORKFLOWS.md`.
- Policies live in `POLICIES.md`.
- Tooling lives in `TOOLS.md`.
- Skill routing lives in `SKILLS.md`.
- Decisions live in `MEMORY.md` and `docs/adr/`.
