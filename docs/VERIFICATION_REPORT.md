# Architecture Verification Report

**Date**: 2026-06-19
**Scope**: Sagewell V1 documentation verification
**Method**: Read every project doc, then cross-check against the
approved V1 architecture and the four primary source-of-truth files
(`ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `WORKFLOWS.md`,
`POLICIES.md`).
**Status of files**: no modifications made in this pass. After this
pass was issued, a follow-up fix instruction dated 2026-06-19 moved
the Regex Guard to run before RBAC and retrieval. Affected docs
(`ARCHITECTURE.md`, `WORKFLOWS.md`, `POLICIES.md`, `README.md`,
`skills/project/architecture_review/SKILL.md`) have been updated.
This report has been updated to reflect the new state.

---

## 1. Architecture Verification Report

### 1.1 Architectural Correctness

| Item | Result | Evidence |
|---|---|---|
| V1 scope correctly stated | PASS | `README.md` 13-39, `PROJECT_STATUS.md` 10-39, `MEMORY.md` 6-22, ADR-0001 18-38, `context/project_overview.md` 1-22, `AGENTS.md` 7-16 all list single-company, single-tenant, dept+clearance, hybrid retrieval, LangGraph, LlamaIndex, PostgreSQL+pgvector+pg_search, JWT, regex+LLM guard, RAGAS+RBAC suite. |
| Out-of-V1 concepts absent from active architecture | PASS | `document_acl`, `permissions`, `role_permissions`, `groups`, `group_memberships`, OIDC, Okta, Entra, LDAP, identity federation appear only in "Out of V1 Scope" or "Alternatives Considered" sections, or in the audit report. Never in an active architecture claim. |
| Framework responsibilities stated | PASS | `ARCHITECTURE.md` 81-117 names LangGraph (orchestration/state/node-execution; NOT auth/retrieval/DB/business-logic) and LlamaIndex (loading/chunking/ingestion/retrieval-abstractions; NOT RBAC/auth/orchestration/business-rules). `context/glossary.md` 64-74 matches. `skills/project/architecture_review/SKILL.md` 19-25 matches. `skills/project/ingestion_pipeline/SKILL.md` 31-35 matches. `skills/project/retrieval_engine/SKILL.md` 57-61 matches. |
| Capability-based model references | PASS | No specific model identifier, vendor, or version appears in any project doc. `ARCHITECTURE.md` 320-331, `MEMORY.md` 19-20, `AGENTS.md` 11, `PROJECT_STATUS.md` 58-60, `skills/project/architecture_review/SKILL.md` 34-35 all use Generation Model / Embedding Model / Reranker Model / Guardrail Model. (Mentions in `skills/external/` are routing references to the `claude` model family used to run the agent itself, not the application. They are out of the application scope.) |
| Single source of truth honored | PASS WITH NOTE | `AGENTS.md` and `MEMORY.md` correctly defer detail to the four primary files. `MEMORY.md` and `context/decisions.md` no longer duplicate; `context/decisions.md` is a pointer. Some architectural statements are repeated in `README.md`, `PROJECT_STATUS.md`, `MEMORY.md`, and ADR-0001. This is a "summary restatement" pattern, not a competing source of truth — every restated statement traces back to the four primary files. The four primary files do not contradict each other. |

### 1.2 Authorization Correctness

| Item | Result | Evidence |
|---|---|---|
| Access rule formula identical in all locations | PASS | Same formula appears in `ARCHITECTURE.md` 163-172, `DATABASE_SCHEMA.md` 34-43, `POLICIES.md` 28-37, `skills/project/rbac/SKILL.md` 18-27, ADR-0001 43-52. Field names consistent: `user.department`, `document.department`, `user.clearance`, `document.required_clearance`. |
| Field naming consistency | PASS WITH MINOR NOTE | `POLICIES.md` lines 20-23 use bare `user.department` / `user.clearance` / `document.department` / `document.required_clearance`. `DATABASE_SCHEMA.md` uses `users.department` (with trailing `s`) and `documents.department` (with trailing `s`) at line 28-29. The two presentations are equivalent (the former is the field reference, the latter is the table.column). No logical contradiction. |
| Three boundaries stated | PASS | Pre-retrieval, post-rerank, citation verification named in `ARCHITECTURE.md` 181-185, `WORKFLOWS.md` 11/16/20, `POLICIES.md` 10-11, `skills/project/rbac/SKILL.md` 47-49, `skills/project/architecture_review/SKILL.md` 16-17, `skills/project/retrieval_engine/SKILL.md` 53-55, `MEMORY.md` 41-42. |
| Clearance hierarchy stated | PASS | `PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED` in `ARCHITECTURE.md` 176-178, `DATABASE_SCHEMA.md` 46-49, `POLICIES.md` 40-43, `skills/project/rbac/SKILL.md` 29. |
| `users.role` retained and disclaimed | PASS | `DATABASE_SCHEMA.md` 66 says `role` is for "UI behavior and auditing only. Does not participate in authorization." Same disclaimer in `POLICIES.md` 45-46, `MEMORY.md` not contradicting, `skills/project/rbac/SKILL.md` 41-42, `skills/project/rbac/learnings.md` 6, `skills/project/database_design/SKILL.md` 25-26. No document claims role grants access or role participates in access decisions. |
| No competing authorization mechanisms | PASS | No ACL engine, no document_acl, no groups, no permissions, no OIDC/Okta/Entra/LDAP anywhere in active architecture. |

### 1.3 Retrieval Correctness

| Item | Result | Evidence |
|---|---|---|
| Four stages named everywhere retrieval is described | PASS | Dense + BM25 + RRF + Cross-Encoder named in `ARCHITECTURE.md` 121-131, `WORKFLOWS.md` 12-15, `skills/project/retrieval_engine/SKILL.md` 12-22, ADR-0001 22. |
| No vector-only description | PASS | No active description says "vector search only." `skills/project/architecture_review/SKILL.md` 19 says "No vector-only or BM25-only retrieval. Reranking is mandatory" — that is a guardrail, not a claim. |
| No BM25-only description | PASS | Same as above. |
| Reranking is mandatory | PASS | `ARCHITECTURE.md` 121, `WORKFLOWS.md` 15, `skills/project/retrieval_engine/SKILL.md` 23-25, `skills/project/architecture_review/SKILL.md` 19, ADR-0001 80-86, `MEMORY.md` 10. |
| `pgvector` named for vector store | PASS | `ARCHITECTURE.md` 137, `DATABASE_SCHEMA.md` 17/114, `skills/project/retrieval_engine/SKILL.md` 32, `PROJECT_STATUS.md` 24. |
| `pg_search` named for lexical store | PASS | `ARCHITECTURE.md` 142, `DATABASE_SCHEMA.md` 18/118, `skills/project/retrieval_engine/SKILL.md` 37. |
| LlamaIndex scope correct | PASS | `ARCHITECTURE.md` 100-117, `skills/project/architecture_review/SKILL.md` 23-25, `skills/project/ingestion_pipeline/SKILL.md` 31-35, `skills/project/retrieval_engine/SKILL.md` 57-61. LlamaIndex is consistently named for loading/semantic chunking/ingestion/retrieval abstractions, and consistently excluded from RBAC/auth/orchestration/business rules. |

### 1.4 Database Correctness

| Item | Result | Evidence |
|---|---|---|
| V1 tables present | PASS | `users`, `documents`, `chunks`, `audit_logs`, `retrieval_logs`, `evaluation_results` in `DATABASE_SCHEMA.md` 3-10, `PROJECT_STATUS.md` 72, `MEMORY.md` 21-22, `AGENTS.md` 12-13, `skills/project/database_design/SKILL.md` 11-18, `ARCHITECTURE.md` 335-342. |
| No undocumented table appears in a workflow | PASS | Every flow references only V1 tables. `WORKFLOWS.md` line 21, 46, 107, 132, 136 use `audit_logs`, `retrieval_logs`, `evaluation_results`. |
| Authorization fields present where needed | PASS | `users.department`, `users.clearance`, `users.role` in `DATABASE_SCHEMA.md` 64-66. `documents.department`, `documents.required_clearance`, `documents.content_checksum` in `DATABASE_SCHEMA.md` 80-82. `chunks.document_id` reference, `ordinal`, `text`, `text_search`, `embedding`, `metadata`, `token_count`, `status` in `DATABASE_SCHEMA.md` 95-105. |
| `created_at` / `updated_at` / `content_checksum` | PASS | `users` and `documents` carry `created_at` and `updated_at` (`DATABASE_SCHEMA.md` 67-68, 83-84). `chunks` carries `created_at` but not `updated_at` (line 105). `content_checksum` is on `documents` (line 82) and used by `WORKFLOWS.md` 39, `ingestion_pipeline/SKILL.md` 19, and `database_design/SKILL.md` 28. |
| Indexes relevant to access decision present | PASS | `documents_access_filter_idx` on `(department, required_clearance, status)` at `DATABASE_SCHEMA.md` 112-113. `chunks_embedding_idx` HNSW at line 114-115. |
| Out-of-V1 tables correctly listed as such | PASS | `DATABASE_SCHEMA.md` 165-179 lists `document_acl`, `permissions`, `role_permissions`, `user_roles`, `groups`, `group_memberships`, `ingestion_jobs`, `eval_runs`, `eval_cases`, `eval_results` in an explicit "Out of V1 Scope" section. ADR-0001 134-141 repeats this. `skills/project/database_design/SKILL.md` 46-51 repeats this. |

### 1.5 Workflow Correctness

The approved V1 query workflow is:

```text
User Query
  -> JWT Authentication
  -> Regex Guard
  -> RBAC Authorization
  -> Dense Retrieval
  -> BM25 Retrieval
  -> RRF Fusion
  -> Cross-Encoder Reranker
  -> LLM Guard
  -> Generation
  -> Citation Verification
  -> Audit Logging
```

**Post-fix state (2026-06-19)**: Earlier in this verification pass,
the docs had placed the Regex Guard after retrieval, between
retrieval and the LLM Guard. The spec author issued a follow-up fix
instruction moving the Regex Guard to its correct position
(immediately after JWT validation, before RBAC and retrieval). All
docs (`ARCHITECTURE.md` LangGraph workflow, `ARCHITECTURE.md`
Security Architecture primary-path diagram, `WORKFLOWS.md` query
flow, `POLICIES.md` Prompt-Protection Policy, `README.md` V1 scope,
`skills/project/architecture_review/SKILL.md` checklist) now reflect
the approved ordering. The earlier mismatch warning (W1) is
resolved.

Other workflow checks:

| Item | Result | Evidence |
|---|---|---|
| JWT validated on every request | PASS | `ARCHITECTURE.md` validate_jwt node, Security Architecture JWT section; `WORKFLOWS.md` step 2 and failure behavior; `POLICIES.md` JWT Authentication Policy; `MEMORY.md` baseline. |
| Regex Guard runs before RBAC and retrieval | PASS | `ARCHITECTURE.md` LangGraph workflow regex_guard node; Security Architecture primary-path diagram; `WORKFLOWS.md` step 3; `POLICIES.md` Prompt-Protection Policy. |
| Access decision applied before retrieval | PASS | `ARCHITECTURE.md` apply_access_decision (constraint for retrieval) node; `WORKFLOWS.md` step 5; `POLICIES.md` Security Principles. |
| Access decision re-applied after rerank | PASS | `ARCHITECTURE.md` apply_access_decision (drop unauthorized) node; `WORKFLOWS.md` step 10. |
| LLM Guard runs after retrieval | PASS | `ARCHITECTURE.md` llm_guard node; Security Architecture primary-path diagram; `WORKFLOWS.md` step 11; `POLICIES.md` Prompt-Protection Policy. |
| Citation verification re-runs access decision | PASS | `ARCHITECTURE.md` verify_citations node; `WORKFLOWS.md` step 13; `POLICIES.md` Security Principles. |
| Audit write precedes response on failure | PASS | `ARCHITECTURE.md` failure paths. |
| Ingestion idempotent by `content_checksum` | PASS | `WORKFLOWS.md` Incremental Re-Ingestion; `skills/project/ingestion_pipeline/SKILL.md` checklist. |
| No workflow bypasses JWT | PASS | `WORKFLOWS.md` step 2 is "Validate JWT" — every workflow goes through JWT. |
| No workflow bypasses guards | PASS | `WORKFLOWS.md` step 3 is regex guard and step 11 is LLM guard. `ARCHITECTURE.md` workflow nodes include both. No alternative path is described. |

### 1.6 Evaluation Correctness

| Item | Result | Evidence |
|---|---|---|
| Both systems named | PASS | RAGAS and RBAC Access Outcome Suite in `ARCHITECTURE.md` 275-298, `WORKFLOWS.md` 56-69, 100-109, `POLICIES.md` 156-175, `skills/project/evaluation/SKILL.md` 6-33, ADR-0001 33-34, `MEMORY.md` 18, `context/glossary.md` 76-84, `context/requirements.md` 40-46, `README.md` 29-30, `AGENTS.md` 14, `PROJECT_STATUS.md` 25-26. |
| RAGAS metrics | PASS | Faithfulness, Context Precision, Context Recall, Answer Relevancy all named in `ARCHITECTURE.md` 282-286, `WORKFLOWS.md` 105-106, `POLICIES.md` 162-165, `skills/project/evaluation/SKILL.md` 16-20, `context/glossary.md` 78-79, `context/requirements.md` 42-43. |
| RBAC test categories | PASS | Allow, Deny, Department, Clearance all named in `ARCHITECTURE.md` 291-295, `POLICIES.md` 169-172, `WORKFLOWS.md` 61, `skills/project/evaluation/SKILL.md` 28-31, `skills/project/rbac/SKILL.md` 60-63. |
| Systems are independent | PASS | `ARCHITECTURE.md` 297-298, `POLICIES.md` 174-175, `skills/project/evaluation/SKILL.md` 1-3, `WORKFLOWS.md` 58. |
| Release gate covers both | PASS | `WORKFLOWS.md` 111-123. |

### 1.7 Security Correctness

| Item | Result | Evidence |
|---|---|---|
| JWT validation policy | PASS | `POLICIES.md` JWT Authentication Policy. Required claims listed. Failure returns 401. Audit row written. |
| RBAC policy | PASS | `POLICIES.md` Authorization Model. Inputs and rule stated. `users.role` excluded. |
| Regex Guard policy | PASS | `POLICIES.md` Regex Guard subsection. Pattern-based. Runs before RBAC. Versioned. |
| LLM Guard policy | PASS | `POLICIES.md` LLM Guard subsection. Guardrail Model. Runs after retrieval. Verdict recorded. |
| Prompt protection on primary request path | PASS | `ARCHITECTURE.md` Security Architecture primary-path diagram and Prompt-Protection narrative; `POLICIES.md` Prompt-Protection Policy. Both explicit. |
| Risk signals defined | PASS | `POLICIES.md` 102-112. |
| Audit table for security events | PASS | `POLICIES.md` 125-138; `audit_logs` schema in `DATABASE_SCHEMA.md` 120-133. |
| Do-not-log list | PASS | `POLICIES.md` 148-154. |
| Fail closed | PASS | `ARCHITECTURE.md` 187-188, `POLICIES.md` 14, `POLICIES.md` 183, `skills/project/rbac/SKILL.md` 56. |

### 1.8 Source-of-Truth Correctness

| Item | Result | Evidence |
|---|---|---|
| `AGENTS.md` does not redefine architecture | PASS | `AGENTS.md` 7-16 is a V1 scope reminder; full architecture detail is in the four primary files. |
| `README.md` is summary, not competing source | PASS | `README.md` 13-39 restates V1 scope and out-of-scope list. It does not contradict the four primary files. |
| `PROJECT_STATUS.md` is summary, not competing source | PASS | `PROJECT_STATUS.md` 11-39 restates the same scope. The "Next Implementation Milestones" list (67-77) is implementation order, not architecture. |
| `MEMORY.md` is authoritative decisions log | PASS | `MEMORY.md` 1-4. `context/decisions.md` is a pointer. |
| `context/*` do not redefine architecture | PASS | `context/requirements.md` lists requirements and references the four primary files. `context/glossary.md` defines terms. `context/project_overview.md` is a one-page summary. |

---

## 2. Consistency Report

### 2.1 Internal Consistency Among the Four Primary Files

| Boundary | ARCHITECTURE.md | DATABASE_SCHEMA.md | WORKFLOWS.md | POLICIES.md | Status |
|---|---|---|---|---|---|
| Access rule formula | 163-172 | 34-43 | (referenced) | 28-37 | Consistent |
| Access rule inputs | `user.department`, `document.department`, `user.clearance`, `document.required_clearance` | `users.department`, `documents.department`, `users.clearance`, `documents.required_clearance` | "department and clearance" | `user.department`, `user.clearance`, `document.department`, `document.required_clearance` | Consistent (table.column vs field reference) |
| Retrieval pipeline | dense + BM25 + RRF + cross-encoder (4 stages) | (referenced via `pgvector`, `pg_search`) | dense + BM25 + RRF + cross-encoder (4 stages) | dense + BM25 + RRF + cross-encoder (4 stages, abbrev) | Consistent |
| Three boundaries | 181-185 | (n/a) | 11, 16, 20 | 10-11 | Consistent |
| V1 tables | 335-342 | 3-10 | `audit_logs`, `retrieval_logs`, `evaluation_results` | `audit_logs` | Consistent |
| Out-of-V1 list | 39-47 | 51-53, 165-179 | (none — flow-level) | 187-196 | Consistent (each file carries the slice relevant to its scope) |
| `users.role` retention | (referenced via field) | 66 (disclaimer) | (referenced via "role" in step 3) | 45-46 (disclaimer) | Consistent |
| Two evaluation systems | 275-298 | (table `evaluation_results` with `suite`) | 56-69, 100-109 | 156-175 | Consistent |
| Guard ordering on primary path | "regex guard" before "LLM guard" before "generate_answer" | n/a | regex guard (10) then LLM guard (11) | regex guard then LLM guard (lines 79-82) | Consistent |

### 2.2 Cross-File Consistency (Project Skills vs Primary Files)

| Skill | Anchors to | Status |
|---|---|---|
| `skills/project/architecture_review/SKILL.md` | All four primary files and ADR-0001 | Consistent |
| `skills/project/database_design/SKILL.md` | `DATABASE_SCHEMA.md`, `POLICIES.md` | Consistent |
| `skills/project/debugging/SKILL.md` | `WORKFLOWS.md`, `audit_logs`, `retrieval_logs` | Consistent |
| `skills/project/evaluation/SKILL.md` | `WORKFLOWS.md`, `POLICIES.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md` | Consistent |
| `skills/project/ingestion_pipeline/SKILL.md` | `WORKFLOWS.md`, `DATABASE_SCHEMA.md`, `POLICIES.md` | Consistent |
| `skills/project/rbac/SKILL.md` | All four primary files | Consistent |
| `skills/project/retrieval_engine/SKILL.md` | All four primary files | Consistent |

### 2.3 Summary Restatement Sites (Not Competing Sources)

The following files restate the V1 scope statement. Each restatement is
identical to the four primary files:

- `README.md` lines 13-39
- `AGENTS.md` lines 7-16
- `PROJECT_STATUS.md` lines 10-39
- `MEMORY.md` lines 6-22
- `context/project_overview.md` lines 1-22
- `context/requirements.md` lines 59-65
- ADR-0001 lines 18-38

This is restatement, not duplication. None of these files add a
contradicting statement. The four primary files remain the single
point of architectural truth.

---

## 3. Missing Information Report

| # | Missing item | Severity | Where it should appear | Notes |
|---|---|---|---|---|
| M1 | Exact JWT signing algorithm | LOW | `POLICIES.md` JWT section, `MEMORY.md` open questions | Already listed as an open question in `MEMORY.md` 46. The capability-based V1 is consistent with leaving this open. |
| M2 | Exact model identifiers and versions | LOW | Every doc that references models | Already enforced capability-based by V1 policy. The absence is correct, not missing. |
| M3 | Threshold values for RAGAS and RBAC release gate | MEDIUM | `POLICIES.md` Evaluation Policy, `WORKFLOWS.md` Release Gate, `skills/project/evaluation/SKILL.md` | Listed as open question in `MEMORY.md` 50-51. The release gate runs and "blocks on RBAC regression" (`WORKFLOWS.md` 122) but the numeric threshold is not pinned. This is acceptable for a doc-only pass but should be pinned before code lands. |
| M4 | `retrieval_logs.candidate_counts` JSON shape | LOW | `DATABASE_SCHEMA.md` | Documented as "JSON counts (dense, bm25, fused, reranked, after access)" at line 144. The exact key set is left for the migration. Acceptable. |
| M5 | `audit_logs.reason_code` enum values | LOW | `POLICIES.md` Logging section | A few are named (`JWT_INVALID`, `POLICY_RESOLVER_ERROR`, `CLEARANCE_GATE`, `DEPARTMENT_GATE`, `ACL_DENY`, `ACL_BYPASS_BLOCKED_BY_CLASSIFICATION`). The full enum is not enumerated. Acceptable for V1 docs; the migration will own it. |
| M6 | `pg_search` distribution and version | LOW | `MEMORY.md` open questions | Listed as open. Acceptable. |
| M7 | Conflict between spec and docs on regex-guard placement | RESOLVED | `ARCHITECTURE.md` 197-213 and following, `POLICIES.md` 74-101, `WORKFLOWS.md` 7-23, `README.md` 25-30, `skills/project/architecture_review/SKILL.md` 28-35 | Resolved by a follow-up fix instruction dated 2026-06-19. The Regex Guard is now placed between JWT validation and RBAC. The LLM Guard remains between retrieval and generation. All primary docs, the README, and the architecture review skill have been updated. Warning W1 is removed (see section 5.3). |

---

## 4. Hidden Scope Creep Report

| # | File | Creep | Reason | Status |
|---|---|---|---|---|
| HS1 | None | — | — | All out-of-V1 concepts (ACL engine, document_acl, permissions, role_permissions, groups, group_memberships, OIDC, Okta, Entra, LDAP, identity federation, permission resolution engines) appear only in explicit out-of-scope sections, in ADR-0001 alternatives, or in the audit report. No active architecture claim uses them. |
| HS2 | `POLICIES.md` 102-112 ("Risk Signals") | None | — | This is a non-controversial enumeration of the kinds of risky content the guards look for. It is consistent with the V1 prompt-protection policy. |
| HS3 | `ARCHITECTURE.md` 81-98 (LangGraph responsibilities) | None | — | The "IS / IS NOT" structure restates the approved architecture. It is not scope creep; it is the architecture. |
| HS4 | `ARCHITECTURE.md` 100-117 (LlamaIndex responsibilities) | None | — | Same as above. |
| HS5 | `ARCHITECTURE.md` 275-298 (Two evaluation systems) | None | — | The evaluation system split was explicitly required by the approved architecture. |

**Result**: No hidden scope creep detected. Every out-of-V1 concept
that appears anywhere does so only inside an explicit "out of scope"
or "rejected alternative" container.

---

## 5. Final Readiness Assessment

### 5.1 Verdict

**PASS**

### 5.2 What passed

- Authorization rule, clearance hierarchy, `users.role` retention,
  three boundaries — all consistent across the four primary files and
  the seven project skills.
- Retrieval pipeline — dense + BM25 + RRF + cross-encoder named in
  every doc that describes retrieval. No vector-only or BM25-only
  description in any active architecture claim. Reranking is
  mandatory and stated as such.
- Database — V1 table list consistent across all docs. Out-of-V1
  tables listed as out-of-V1 in every doc that mentions them. No
  unauthorized table appears in a workflow.
- Evaluation — RAGAS and RBAC Access Outcome Suite are both named
  everywhere evaluation is described. All four RAGAS metrics and all
  four RBAC test categories are present. The two systems are
  correctly marked as independent and both required.
- Security — JWT, RBAC, regex guard, LLM guard all named in the
  primary path. Prompt protection explicitly stated as part of the
  primary request path, not deferred. Fail-closed behavior stated.
- Framework responsibilities — LangGraph and LlamaIndex "IS / IS NOT"
  statements consistent across `ARCHITECTURE.md`, the project skills,
  and `context/glossary.md`.
- Model policy — capability-based throughout. No specific model
  identifier, vendor, or version pinned in any project doc.
- Source of truth — `MEMORY.md` is authoritative; `context/decisions.md`
  is a pointer. `AGENTS.md`, `README.md`, `PROJECT_STATUS.md` are
  summaries that defer detail. The four primary files are consistent
  with each other.
- Hidden scope creep — none detected.

### 5.3 Warnings (non-blocking)

1. **Field-name presentation difference** (Warning W2, LOW).
   `POLICIES.md` Authorization Model uses bare field references
   (`user.department`, `user.clearance`); `DATABASE_SCHEMA.md` uses
   `users.department` (with trailing `s`). This is table.column
   notation versus field reference. No logical difference. The
   inconsistency is cosmetic. **No action required**, but a single
   one-line edit to `POLICIES.md` could align them.

2. **RAGAS / RBAC release-gate thresholds not pinned** (Warning W3,
   LOW). Documented as open question. Acceptable for the doc-only
   pass; should be pinned in an ADR before code lands.

3. **Audit reason-code enum not fully enumerated** (Warning W4, LOW).
   A few codes are named. The full list is the migration's job. This
   is acceptable for V1 docs.

### 5.4 What was not modified

- No file was edited in this verification pass.
- No application code, no tests, no infrastructure code was
  inspected or modified.
- `skills/external/` was not inspected for content drift (it is
  intentionally untouched per the routing rule in `SKILLS.md`).

### 5.5 Required spec author decision

**Decision 1 — regex-guard placement** (W1): RESOLVED on 2026-06-19.
The spec author chose Option B. The new ordering
(`JWT -> Regex Guard -> RBAC -> Retrieval -> LLM Guard -> Generation`)
is now reflected in `ARCHITECTURE.md`, `WORKFLOWS.md`, `POLICIES.md`,
`README.md`, and `skills/project/architecture_review/SKILL.md`. No
further spec-author decisions are open.
