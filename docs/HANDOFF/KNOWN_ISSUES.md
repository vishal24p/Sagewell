# Known Issues

This file tracks unresolved engineering decisions and concerns that
must be addressed before code lands, but are not bugs and not
decisions pending human approval.

For decisions that require human approval, see
`docs/HANDOFF/DECISIONS_PENDING.md`.
For bugs, see the issue tracker. (Not yet created in this repo.)

---

## I-001 — `audit_logs.reason_code` enum not fully enumerated

- **Context**: V1 audit logs record a `reason_code` for every
  security-relevant event. A few codes are named in `POLICIES.md`
  and `WORKFLOWS.md` (`JWT_INVALID`, `POLICY_RESOLVER_ERROR`,
  `CLEARANCE_GATE`, `DEPARTMENT_GATE`, `REGEX_GUARD_BLOCK`,
  `LLM_GUARD_BLOCK`, `CITATION_DENY`, `RETRIEVAL_EMPTY`,
  `AUDIT_WRITE_FAILED`). The full enum is not enumerated.
- **Why it must be resolved**: the migration in M1 needs the full
  enum. The release gate in M13 needs stable codes to assert
  regressions.
- **Proposed resolution**: enumerate the full enum in a follow-up
  ADR before M1. Lock the enum in the migration. Any new code is
  an additive migration.
- **Blocks**: M1 (schema must include the enum), M12 (audit
  writer must use stable codes), M13 (release gate).

## I-002 — RAGAS score thresholds not pinned

- **Context**: V1 runs RAGAS on every release gate. The numeric
  thresholds for Faithfulness, Context Precision, Context Recall,
  and Answer Relevancy are not pinned.
- **Why it must be resolved**: the release gate in M13 needs
  numeric thresholds to block or pass.
- **Proposed resolution**: run RAGAS as informational until the
  baseline is established after M13. Pin thresholds in a follow-up
  ADR. See D-006 in `docs/HANDOFF/DECISIONS_PENDING.md`.
- **Blocks**: M13 (release gate definition).

## I-003 — Reranker Model selection

- **Context**: V1 uses a capability-based reference to a Reranker
  Model. The specific model family, latency profile, and
  cost profile are not pinned.
- **Why it must be resolved**: M8 stage 4 (Cross-Encoder
  Reranking) needs a concrete capability to test against.
- **Proposed resolution**: pin the reranker capability in
  D-003 before M8.
- **Blocks**: M8.

## I-004 — `pg_search` distribution and version

- **Context**: V1 uses `pg_search` for BM25 lexical search. The
  distribution (e.g., ParadeDB's pg_search, the older ZomboDB,
  etc.) and the version are not pinned.
- **Why it must be resolved**: M1 (schema migration) creates
  the extension. The migration needs a specific version.
- **Proposed resolution**: pin `pg_search` distribution and
  version in a follow-up ADR before M1.
- **Blocks**: M1.

## I-005 — JWT signing algorithm and key management

- **Context**: V1 uses JWT for authentication. The algorithm and
  key management approach are not pinned.
- **Why it must be resolved**: M5 needs a concrete validator.
  The validator's behavior (algorithm allowlist, key source,
  rotation handling) is part of M5's exit criteria.
- **Proposed resolution**: see D-001 in
  `docs/HANDOFF/DECISIONS_PENDING.md`.
- **Blocks**: M5.

## I-006 — Audit log retention policy

- **Context**: V1 stores security-relevant events in `audit_logs`.
  The retention period is not pinned.
- **Why it must be resolved**: production deployments need a
  retention policy. M12 completes the audit writer but does not
  enforce retention (which is typically a separate cron job or a
  database partition rotation).
- **Proposed resolution**: see D-008 in
  `docs/HANDOFF/DECISIONS_PENDING.md`.
- **Blocks**: any production deployment after M14. Does not
  block M0-M14 in development.

## I-007 — Retrieval log candidate-counts JSON shape

- **Context**: V1 stores retrieval logs in `retrieval_logs` with a
  `candidate_counts` JSON column. The shape of this JSON is
  described in `DATABASE_SCHEMA.md` as "JSON counts (dense, bm25,
  fused, reranked, after access)" but the exact key set and types
  are not pinned.
- **Why it must be resolved**: M8 must write this JSON correctly.
  M13's RAGAS suite reads it for debugging.
- **Proposed resolution**: pin the exact shape in a follow-up
  ADR or in `DATABASE_SCHEMA.md` before M8. The shape must include
  per-stage counts and per-stage filter drop counts.
- **Blocks**: M8.

## I-008 — Citation tuple shape from the Generation Model

- **Context**: M9 wires the workflow to a stubbed generation
  model that produces a typed `(chunk_id, document_id, span)`
  citation list. The real Generation Model in M13 must produce
  the same shape.
- **Why it must be resolved**: M9's exit criteria include the
  citation data model. If the real Generation Model produces a
  different shape, M13 has to translate.
- **Proposed resolution**: see D-005 in
  `docs/HANDOFF/DECISIONS_PENDING.md`. The capability pinned
  for the Generation Model must include structured output for
  citation tuples.
- **Blocks**: M13.

## I-009 — Regex Guard pattern corpus

- **Context**: V1 runs a Regex Guard on every request with a
  pattern set. The pattern set is "versioned and configurable"
  per `POLICIES.md`, but the corpus itself is not enumerated.
- **Why it must be resolved**: M10 needs a representative test
  corpus (prompt-injection corpus and benign corpus) to validate
  the guard.
- **Proposed resolution**: assemble the corpus as part of M10.
  The corpus is configuration data, not code, so it lives in a
  versioned file checked into the repository.
- **Blocks**: M10.

## I-010 — LLM Guard corpus and rationale format

- **Context**: V1 runs an LLM Guard on the (query, retrieved
  chunks) pair. The Guardrail Model classifies the pair as
  `allow | downgrade | refuse` with a rationale. The rationale
  format is not pinned.
- **Why it must be resolved**: M11 writes the verdict and
  rationale to `audit_logs`. The format must be stable for the
  debugging skill (M14) and for `audit_logs` consumers.
- **Proposed resolution**: pin the rationale format as part of
  D-004 in `docs/HANDOFF/DECISIONS_PENDING.md`. The format must
  include the matched pattern (if any), the model's
  classification, and a free-text rationale.
- **Blocks**: M11.

## I-011 — CI environment and test runners

- **Context**: V1 has a release gate that runs unit tests, the
  RBAC Access Outcome Suite, and the RAGAS suite. The CI
  environment (PostgreSQL version, `pgvector` version, `pg_search`
  version, available memory) is not pinned.
- **Why it must be resolved**: M14 wires the release gate into
  CI. The CI environment must match the production environment.
- **Proposed resolution**: pin the CI environment in a follow-up
  ADR before M14. This is the same ADR family as I-004.
- **Blocks**: M14.

---

## Update Rule

Update this file when a new unresolved engineering concern is
identified, when an existing concern is resolved, or when a
concern's blocking milestone changes.

When a concern is resolved, move it to "Recently Resolved" below
with the resolution date and a brief description.

## Recently Resolved

| Concern | Resolution | Date |
|---|---|---|
| I-001 | Partial resolution. M1 ships `audit_logs.reason_code` as TEXT with no DB-level constraint. Only the seven M0 codes (`allowed`, `department_mismatch`, `clearance_insufficient`, `missing_user_department`, `missing_user_clearance`, `missing_document_department`, `missing_document_clearance`) are emitted in M1. Additional codes are introduced in their own milestones. A full V1 enum ADR remains open. | 2026-06-19 |
| I-004 | Partial resolution. ADR-0002 (`docs/adr/0002-pg-search-paradedb.md`) pins the distribution to ParadeDB `pg_search`. Version pinning is intentionally left to deployment/infrastructure, not the schema. The M1 migration creates the extension with `IF NOT EXISTS`. | 2026-06-19 |
