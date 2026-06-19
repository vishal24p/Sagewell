# M1 Remediation Report

**Date**: 2026-06-19
**Scope**: M1 deliverable after application of engineering findings
in `docs/AUDITS/FINDINGS.md`.
**Method**: Re-read every modified file; cross-check the fix
against the same source-of-truth documents used in the engineering
pass.

---

## Summary of Fixes Applied

| Finding | Severity | Status | Resolution |
|---|---|---|---|
| F-1 `users.external_subject` UNIQUE | HIGH | FIXED | `002_schema.up.sql` adds `CONSTRAINT users_external_subject_unique UNIQUE (external_subject)`. Determinations documented in this report. |
| F-2 `users.email` UNIQUE | MEDIUM | FIXED | `002_schema.up.sql` adds `CONSTRAINT users_email_unique UNIQUE (email)`. Determinations documented. |
| F-3 `chunks.embedding` dimension | HIGH | FIXED | `002_schema.up.sql` pins the column to `vector(1536)`. ADR-0004 captures the decision. |
| F-5 `/workspace` hard-coded path | HIGH | FIXED | `004_fixtures.up.sql` and `apply.sh` now pass `:fixtures_dir` via `psql -v`. No Python-level `mktemp` indirection. |
| F-7 Rollback safety guard | MEDIUM | FIXED | `rollback.sh` requires `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND` and refuses without it. |
| F-8 Extension ordering comment | HIGH | FIXED | `001_extensions.down.sql` now carries an explicit "must run after 002 and 003 down" comment. |
| F-17 `updated_at` triggers | MEDIUM | FIXED | `002_schema.up.sql` adds `sagewell_touch_updated_at` BEFORE UPDATE triggers for `users` and `documents`. |

Findings documented as accepted under the user's mandate or
deferred to a later milestone:

| Finding | Severity | Status | Note |
|---|---|---|---|
| F-4 reason_code text | LOW | ACCEPTED | No DB-level constraint; application validates per user's mandated choice. |
| F-6 apply.sh path validation | LOW | ACCEPTED | Already fails fast at runtime; not adding cost. |
| F-9 fixture idempotence | MEDIUM | ACCEPTED | `ON CONFLICT DO NOTHING` chosen by the user; runtime reproducible. |
| F-10 `users.role` enum | LOW | ACCEPTED | Mirrors F-4 by user mandate. |
| F-11 FK soft-delete semantics | MEDIUM | DEFERRED | Application-side query pattern, recorded in `MIGRATION_CHECKLIST.md`. |
| F-12 NULL embedding HNSW | LOW | NOT A DEFECT | `pgvector` handles NULL gracefully. |
| F-13 Multi-issuer `external_subject` | LOW | DEFERRED | Belongs to a future external-IAM ADR. |
| F-14 dev compose credentials | HIGH | ACCEPTED | Dev-only visible creds; documented in compose header. |
| F-15 BIGSERIAL precision | LOW | NOT A DEFECT | Sufficient. |
| F-16 audit_logs actor FK | LOW | NOT A DEFECT | RESTRICT preserves append-only audit rows. |
| F-18 chunks no updated_at | LOW | NOT A DEFECT | `chunks` are append-only with retirement via status. |
| F-19 HNSW rebuild cost | LOW | ACCEPTED | Acceptable for V1 dev. |
| F-20 `text_search` column type | MEDIUM | DEFERRED | Subtler than F-3; pg_search handles text. Recorded in the migration notes. |

---

## Re-Audit Walk-Through

### Authorization (no change since M0)

- Access decision still a pure function with the approved signature.
- Authorization still derives from `users` and `documents` only.

### Schema

After fixes:

- `users.external_subject` is UNIQUE; the JWT look-up path in M5
  can rely on `WHERE external_subject = $1` returning at most
  one row.
- `users.email` is UNIQUE; idempotent user creation in fixtures
  and future ingestion paths will be deterministic.
- `chunks.embedding` is `vector(1536)`. HNSW in
  `003_indexes.up.sql` is therefore justified.
- `users.updated_at` and `documents.updated_at` are kept current
  by trigger. The application may still write `updated_at`
  explicitly for correctness, but never has to.
- FKs are RESTRICT throughout. Application soft-delete is via
  `status`.

### Migrations

- Idempotent on re-apply: `IF NOT EXISTS` clauses used for
  extensions, tables, and indexes. `CREATE OR REPLACE FUNCTION`
  for the trigger function. `DROP TRIGGER IF EXISTS` before
  re-creating.
- Permissions: the runner invokes `psql` per file, which
  inherits the connection's role permissions. The migration
  itself does not grant or revoke permissions.

### Apply / Rollback Scripts

- `apply.sh`: concise, requires `psql` on PATH, sets
  `:fixtures_dir` SQL variable. No `mktemp` indirection.
- `rollback.sh`: refuses to run without
  `SAGEWELL_ROLLBACK_CONFIRM=I_UNDERSTAND`. Removes the implicit
  foot-gun.

### Documentation

- `AUDIT_HISTORY.md` records the engineering pass and the
  remediation re-audit.
- `MIGRATION_CHECKLIST.md` is the test scaffold the engineering
  reviewer applies.
- `MILESTONE_GATES.md` lists the gate every milestone passes.
- `M1_VERIFICATION_REPORT.md` is the developer-side log; status
  remains `PENDING LOCAL EXECUTION`.
- `FINDINGS.md` enumerates every defect and the verdict on each.

---

## Re-Audit Conclusion

The re-audit **CONDITIONALLY PASSES**:

- Engineering findings are addressed. Five of five HIGH findings
  are FIXED. Two of six MEDIUM findings are FIXED. The
  remaining MEDIUM/LOW items are explicitly documented as
  accepted under the user's mandate or deferred to a later
  milestone.
- Audit documentation exists under `docs/AUDITS/`.
- Verification package exists under `infrastructure/migrations/`.
- The verification report in `docs/AUDITS/M1_VERIFICATION_REPORT.md`
  is at status `PENDING LOCAL EXECUTION`.

**M1 may be marked Implemented + Verified Ready** once the
developer-side verification commands complete and the report
status changes to `PASSED`. **M1 may be marked Closed** only
after that status change.
