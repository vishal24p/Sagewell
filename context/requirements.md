# Requirements

## Functional Requirements

- Authenticate the actor via JWT on every request.
- Apply the access decision (department + clearance) before retrieval.
- Ingest documents from approved sources.
- Track document content checksums for incremental re-ingestion.
- Chunk documents and store embeddings using LlamaIndex.
- Run dense retrieval (pgvector) and BM25 retrieval (pg_search) with
  the access decision applied.
- Apply RRF fusion and cross-encoder reranking.
- Re-apply the access decision after reranking.
- Run regex guard and LLM guard on the primary request path.
- Generate answers with citation verification.
- Verify every citation by re-running the access decision.
- Write `audit_logs`, `retrieval_logs`, and `evaluation_results` for
  every workflow run.

## Non-Functional Requirements

- Fail closed on authorization uncertainty.
- Keep retrieval behavior observable.
- Keep ingestion idempotent through content checksums.
- Keep workflow steps explicit and individually testable.
- Keep errors safe for end users.
- Avoid storing secrets in logs.
- Support deterministic regression tests.

## Security Requirements

- Deny access when the access decision fails.
- Prevent citation leaks by re-running the access decision at
  citation verification.
- Prevent existence leaks through counts, citations, or answer text.
- Treat retrieved documents as untrusted data.
- Log policy decisions with stable reason codes.
- Redact sensitive data in operational logs.

## Evaluation Requirements

- Run the RAGAS suite with Faithfulness, Context Precision, Context
  Recall, and Answer Relevancy.
- Run the RBAC Access Outcome Suite with Allow, Deny, Department, and
  Clearance tests.
- Both suites are required. Neither replaces the other.

## Documentation Requirements

- `AGENTS.md` stays concise.
- Architecture detail lives in `ARCHITECTURE.md`.
- Schema detail lives in `DATABASE_SCHEMA.md`.
- Runtime flows live in `WORKFLOWS.md`.
- Policies live in `POLICIES.md`.
- Tooling lives in `TOOLS.md`.
- Skill routing lives in `SKILLS.md`.
- Authoritative decisions live in `MEMORY.md` and `docs/adr/`.

## V1 Out of Scope

- Multi-tenant isolation.
- ACL engine, `document_acl`, permissions, role_permissions.
- Groups and group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.