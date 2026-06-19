# NEXT_AGENT

This file is the operational entry point for a new agent. It answers
one question: "what is the next task, and what do I need to know to
do it?"

Read `AGENTS.md` first. Read `docs/HANDOFF/CURRENT_STATE.md` for a
snapshot of progress. Read the files listed under "Relevant
Documents" before doing anything.

---

## Current Milestone

**M0 — Access Decision (pure).**

No source code exists yet. The first implementation task is to build
the access decision as a pure function and prove it correct.

---

## Current Status

**Not Started.**

The repository contains only documentation. No source files. No
tests. No migrations. No API. No workflow.

---

## Next Task

Build the access decision function and the RBAC Access Outcome
Suite.

The access decision is the only piece of business logic that must
be correct for the system to be safe. It is a pure function with no
IO, no framework imports, no database. It must be validated
independently of every other component.

### Task definition

1. Implement the access decision as a pure function with the
   signature `access(user, document) -> (allowed, reason)`.
2. Implement the RBAC Access Outcome Suite (Allow, Deny,
   Department, Clearance) and run it against the pure function.
3. Confirm 100% of RBAC suite cases pass before moving on.
4. Record the result in `docs/HANDOFF/CURRENT_STATE.md` under
   "Recently Completed."

### How to test

- Table-driven unit tests covering every cell of the truth table
  for `(user.department, user.clearance)` × `(document.department,
  document.required_clearance)`.
- Edge cases: `ALL` department as wildcard, equal clearance,
  missing fields (must deny), `users.role` excluded from the
  decision.
- RBAC suite asserts allow, deny, department boundary, clearance
  boundary.

### How to verify before moving on

- All RBAC suite cases pass.
- The pure function has zero framework imports.
- The pure function has zero database calls.

---

## Relevant Documents

Read these before starting:

- `POLICIES.md` — the access rule formula and clearance hierarchy.
- `ARCHITECTURE.md` — Authorization Architecture, the access
  decision function shape, the three boundaries.
- `skills/project/rbac/SKILL.md` — the V1 authorization rule and
  checklist.
- `docs/adr/0001-single-tenant-enterprise-rag-baseline.md` — the
  architecture decision.

Do not read the four retrieval skill files, the database design
skill, the debugging skill, or the evaluation skill yet. They are
for later milestones.

---

## Do Not Touch

The following are out of scope for this milestone. Do not start
them, do not scaffold them, do not write code for them:

- M1 Schema and migrations. Wait for M0 to exit.
- M2 Repositories. Wait for M1.
- M3 API Skeleton. Wait for M2.
- M4 Audit Infrastructure. Wait for M3.
- M5 JWT Validation. Wait for M4.
- M6 LangGraph Skeleton. Wait for M5.
- M7 Ingestion. Wait for M6.
- M8 Retrieval. Wait for M7.
- M9 Workflow Wiring. Wait for M8.
- M10 Regex Guard. Wait for M9.
- M11 LLM Guard. Wait for M9.
- M12 Audit and Retrieval Logs (complete). Wait for M11.
- M13 RAGAS Evaluation. Wait for M12.
- M14 End-to-end Hardening. Wait for M13.
- Out-of-V1 concepts: ACL engine, groups, OIDC, Okta, Entra,
  LDAP, identity federation, external IAM, permission resolution
  engines, multi-tenant isolation.

---

## Exit Criteria

M0 is complete when all of the following are true:

- The access decision is implemented as a pure function with the
  approved signature.
- The RBAC Access Outcome Suite passes 100% against the pure
  function.
- The pure function has zero framework imports.
- The pure function has zero database calls.
- The result is recorded in `docs/HANDOFF/CURRENT_STATE.md`.

When these are true, advance to M1. Update
`docs/HANDOFF/CURRENT_STATE.md` to mark M0 as complete and M1 as
in progress. Update the "Next Task" section of this file.

---

## Known Open Questions

These are tracked in `MEMORY.md` and `docs/HANDOFF/KNOWN_ISSUES.md`:

- Which JWT signing algorithm and key management approach?
- Which Embedding Model, Reranker Model, Guardrail Model, and
  Generation Model capabilities will be adopted?
- Which `pg_search` distribution and version?
- What are the RAGAS score thresholds and the RBAC Access Outcome
  thresholds for the release gate?
- What retention policy applies to `audit_logs`, `retrieval_logs`,
  and `evaluation_results`?

These do not block M0. They block later milestones.