# Documentation Audit Report

**Date**: 2026-06-19
**Scope**: Sagewell V1 documentation alignment
**Source of Truth**: Approved V1 Architecture (single-company,
single-tenant; department + clearance; hybrid retrieval;
LangGraph; LlamaIndex; JWT; regex guard + LLM guard;
RAGAS + RBAC Access Outcome Suite; capability-based models;
V1 tables only).

This report records the audit findings and the corrections applied
to every documentation file. Source code, tests, and infrastructure
code were not modified.

---

## 1. Architectural Drift Report

| # | File | Drift | Reason | Correction |
|---|---|---|---|---|
| D1 | `DATABASE_SCHEMA.md` | Listed `document_acl`, `permissions`, `role_permissions`, `groups`, `group_memberships`, `user_roles`, `ingestion_jobs`, `eval_runs`, `eval_cases`, `eval_results` as baseline tables. | Out of V1 scope. ACL engine, groups, and separate eval tables are not approved for V1. | Rewrote to V1 tables only: `users`, `documents`, `chunks`, `audit_logs`, `retrieval_logs`, `evaluation_results`. Added explicit "Out of V1 Scope" section listing removed tables. |
| D2 | `DATABASE_SCHEMA.md` | `users.clearance_level` and `documents.clearance_level` used an unclear name. | Naming must be consistent with `users.clearance` and `documents.required_clearance` used in the approved access formula. | Renamed to `users.clearance` and `documents.required_clearance`. |
| D3 | `ARCHITECTURE.md` | Retrieval section described hybrid as "vector search + lexical search" generically. | V1 mandates the four-stage pipeline: dense + BM25 + RRF + cross-encoder. | Replaced with the four named stages. |
| D4 | `ARCHITECTURE.md` | No explicit LangGraph responsibilities section. | The approved architecture requires an explicit "LangGraph IS / IS NOT" statement. | Added the responsibility section. |
| D5 | `ARCHITECTURE.md` | No explicit LlamaIndex responsibilities section. | The approved architecture requires an explicit "LlamaIndex IS / IS NOT" statement. | Added the responsibility section. |
| D6 | `ARCHITECTURE.md` | No JWT section, no regex guard section, no LLM guard section. | All three are required in V1 and must appear in architecture. | Added each section. |
| D7 | `ARCHITECTURE.md` | Listed `clean architecture` with `evals -> public use cases and test adapters` as a load-bearing concept. | Clean Architecture layering is not part of the approved architecture and was not pinned by any ADR. | Removed Clean Architecture claim. Replaced with a layered boundary description that is consistent with the approved scope. |
| D8 | `WORKFLOWS.md` | Retrieval flow said "Run vector search with policy filters. Run lexical search with policy filters. Merge and rerank candidates." | V1 mandates the four stages by name. | Rewrote to dense + BM25 + RRF + cross-encoder, with the access decision applied at pre-retrieval and post-rerank. |
| D9 | `WORKFLOWS.md` | "ACL Update" flow described adding ACL grants. | Out of V1 scope. | Removed the ACL Update flow. |
| D10 | `POLICIES.md` | "RBAC Model" described user/role/group/resource/permission/ACL grants. | Out of V1 scope. | Rewrote to department + clearance only, with `users.role` retained for UI and auditing. |
| D11 | `POLICIES.md` | Authorization lists included `users`, `roles`, `permissions`, `role_permissions`, `groups`, `group_memberships`. | Out of V1 scope. | Removed. Authorization inputs reduced to department and clearance. |
| D12 | `SKILLS.md` and project skills | References to ACL, groups, OIDC, Okta, Entra, LDAP. | Out of V1 scope. | Removed from project skills. Vendored external skills left untouched per routing rule. |
| D13 | `PROJECT_STATUS.md` | Listed "Next Implementation Milestones" out of order: ingest before query. | The approved build order puts the access decision and the retrieval pipeline before ingestion, eval, and admin. | Reordered milestones to: JWT, skeleton + access decision, migrations + fixtures, retrieval with access decision, LangGraph workflow with guards and citation verification, evaluation wiring. |
| D14 | `README.md` | Listed "RAGAS and custom RBAC evals" without splitting them. | V1 has two named evaluation systems. | Renamed and split into "RAGAS" and "RBAC Access Outcome Suite." |

## 2. Scope Creep Report

| # | File | Creep | Reason | Correction |
|---|---|---|---|---|
| S1 | `ARCHITECTURE.md` (prior) | Implied OIDC, Okta, Entra ID, LDAP as future auth options. | Out of V1 scope. | Removed. V1 is JWT only. A future version may introduce external IAM via its own ADR. |
| S2 | `DATABASE_SCHEMA.md` (prior) | Described `document_acl`, `chunk_acl_snapshot`, `permissions`, `role_permissions`, `groups`, `group_memberships`, `user_roles` as part of the access-control model. | Out of V1 scope. | Removed all ACL/group/permission tables. Added an explicit out-of-scope section. |
| S3 | `POLICIES.md` (prior) | "Logging and Audit" listed "API keys, passwords, raw access tokens" as things not to log, but the audit store was `audit_events`. | V1 table is `audit_logs`. The table name was inconsistent with the approved schema. | Renamed throughout to `audit_logs`. |
| S4 | `context/requirements.md` (prior) | "Map users to roles and groups" listed as a functional requirement. | Out of V1 scope. | Removed group mapping. Replaced with "Apply the access decision (department + clearance) before retrieval." |
| S5 | `skills/project/rbac/SKILL.md` (prior) | Described a full RBAC framework with document-level deny, group membership, role scoping. | Out of V1 scope. | Rewrote to department + clearance only. |
| S6 | `skills/project/database_design/SKILL.md` (prior) | Listed ACL lookup indexes as a release blocker. | Out of V1 scope. | Replaced with V1 indexes. |
| S7 | `skills/project/ingestion_pipeline/SKILL.md` (prior) | Referenced ACL snapshots and document versions. | Out of V1 scope. | Replaced with `documents.content_checksum` and `chunks.status` for incremental re-ingestion. |
| S8 | `skills/project/evaluation/SKILL.md` (prior) | Bundled RAGAS and RBAC evals as one suite. | V1 has two independent systems. | Split into System 1 (RAGAS) and System 2 (RBAC Access Outcome Suite). |

## 3. Contradiction Report

| # | Files | Contradiction | Resolution |
|---|---|---|---|
| C1 | `ARCHITECTURE.md` and `skills/project/rbac/SKILL.md` (prior) | Architecture said classification was a hard pre-ACL filter. RBAC skill said document-level deny could override allow "when configured." | Removed the override clause. Document-level deny is not a V1 concept. Authorization is one function with two inputs. |
| C2 | `POLICIES.md` (prior) "ACL grants must not widen access beyond clearance and department constraints" and `ARCHITECTURE.md` "ACLs can restrict access further." | Both refer to an ACL model that is out of V1 scope. | Removed all references. The V1 access decision is department + clearance only. |
| C3 | `DATABASE_SCHEMA.md` (prior) `documents.clearance_level` and `ARCHITECTURE.md` (prior) `document.clearance` | Inconsistent column name for the same field. | Standardized on `documents.required_clearance` and `users.clearance`. |
| C4 | `context/decisions.md` and `MEMORY.md` (prior) | Both listed the same accepted decisions. | Demoted `context/decisions.md` to a pointer. `MEMORY.md` is authoritative. |
| C5 | `skills/project/database_design/learnings.md` (prior) "`document_acl` is the authority unless an ADR changes that." | Out of V1 scope. | Removed. V1 has no `document_acl` table. |

## 4. Missing Documentation Report

| # | Topic | Where it must appear | Correction |
|---|---|---|---|
| M1 | Access decision function (pure, formula) | `ARCHITECTURE.md`, `POLICIES.md`, `skills/project/rbac/SKILL.md` | Added to all three with identical formula. |
| M2 | Three boundaries for the access decision | `ARCHITECTURE.md`, `skills/project/rbac/SKILL.md`, `WORKFLOWS.md` | Added to all three. |
| M3 | Four-stage retrieval pipeline by name | `ARCHITECTURE.md`, `WORKFLOWS.md`, `skills/project/retrieval_engine/SKILL.md` | Added to all three. |
| M4 | LangGraph IS / IS NOT | `ARCHITECTURE.md`, `skills/project/architecture_review/SKILL.md` | Added to both. |
| M5 | LlamaIndex IS / IS NOT | `ARCHITECTURE.md`, `skills/project/architecture_review/SKILL.md`, `skills/project/ingestion_pipeline/SKILL.md`, `skills/project/retrieval_engine/SKILL.md` | Added. |
| M6 | JWT validation requirements | `ARCHITECTURE.md`, `POLICIES.md`, `skills/project/architecture_review/SKILL.md` | Added. |
| M7 | Regex guard on primary request path | `ARCHITECTURE.md`, `POLICIES.md`, `WORKFLOWS.md` | Added. |
| M8 | LLM guard on primary request path | `ARCHITECTURE.md`, `POLICIES.md`, `WORKFLOWS.md` | Added. |
| M9 | Capability-based model references | Every doc that names a model | Replaced concrete identifiers with capability names (Generation Model, Embedding Model, Reranker Model, Guardrail Model). |
| M10 | Two named evaluation systems | `ARCHITECTURE.md`, `POLICIES.md`, `WORKFLOWS.md`, `skills/project/evaluation/SKILL.md` | Split into RAGAS (Faithfulness, Context Precision, Context Recall, Answer Relevancy) and RBAC Access Outcome Suite (Allow, Deny, Department, Clearance). |
| M11 | `audit_logs`, `retrieval_logs`, `evaluation_results` as the V1 audit and eval stores | `DATABASE_SCHEMA.md`, `POLICIES.md`, `WORKFLOWS.md`, skills | Standardized table names. |

## 5. Duplicate Documentation Report

| # | Duplicate | Resolution |
|---|---|---|
| U1 | Accepted decisions listed in `MEMORY.md` and `context/decisions.md`. | Demoted `context/decisions.md` to a pointer. `MEMORY.md` is authoritative. |
| U2 | Schema narrative duplicated across `DATABASE_SCHEMA.md`, `ARCHITECTURE.md`, and `skills/project/database_design/SKILL.md`. | Kept `DATABASE_SCHEMA.md` as the V1 schema narrative. Reduced schema references in `ARCHITECTURE.md` to a single "V1 Tables" section. Reduced `skills/project/database_design/SKILL.md` to a checklist that points back to `DATABASE_SCHEMA.md`. |
| U3 | Workflow definitions duplicated across `WORKFLOWS.md`, `ARCHITECTURE.md`, and project skills. | `WORKFLOWS.md` is the runtime flow source. `ARCHITECTURE.md` keeps only the LangGraph node list. Project skills reference `WORKFLOWS.md` and check the boundary rules. |
| U4 | Out-of-V1 scope concepts repeated across files (ACL, OIDC, groups). | Centralized "Out of V1 Scope" in `README.md`, `ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `POLICIES.md`, `context/project_overview.md`, `context/requirements.md`, and ADR-0001. Other files reference ADR-0001 instead of repeating the list. |

## 6. Per-File Change Summary

### Root docs

- `README.md`: rewritten. V1 scope stated up front; out-of-scope list
  stated up front; doc map updated.
- `AGENTS.md`: rewritten. V1 scope reminder added; source-of-truth
  table updated to include `docs/AUDIT_REPORT.md`.
- `ARCHITECTURE.md`: rewritten. LangGraph and LlamaIndex
  responsibilities added. Four-stage retrieval pipeline named.
  Access decision function and three boundaries named. JWT, regex
  guard, and LLM guard sections added. Two named evaluation systems.
  Capability-based model references. V1 table list.
- `DATABASE_SCHEMA.md`: rewritten. V1 tables only. `audit_logs`,
  `retrieval_logs`, `evaluation_results` introduced. `user_roles`,
  `document_acl`, `permissions`, `role_permissions`, `groups`,
  `group_memberships`, `ingestion_jobs`, `eval_runs`, `eval_cases`,
  `eval_results` moved to an explicit out-of-scope section.
- `WORKFLOWS.md`: rewritten. Retrieval flow uses dense + BM25 + RRF
  + cross-encoder. Regex guard and LLM guard are on the primary
  request path. ACL Update flow removed. RBAC Access Outcome Suite
  described as a distinct evaluation system.
- `POLICIES.md`: rewritten. Authorization is department + clearance.
  `users.role` retained for UI and auditing only. JWT policy added.
  Regex guard and LLM guard policy added. Two evaluation systems.
  Out-of-V1 scope list at the end.
- `TOOLS.md`: rewritten. Runtime stack described capability-based.
  No model pin.
- `SKILLS.md`: rewritten. Project skills table reflects V1 areas
  only. Routing rules updated.
- `PROJECT_STATUS.md`: rewritten. Milestones reordered: JWT,
  skeleton + access decision, migrations + fixtures, retrieval with
  access decision, LangGraph workflow with guards and citation
  verification, evaluation wiring.
- `MEMORY.md`: rewritten. Authoritative decisions. `context/decisions.md`
  becomes a pointer.

### context/

- `context/project_overview.md`: rewritten. Authorization is
  department + clearance. Two evaluation systems. Capability-based
  models.
- `context/requirements.md`: rewritten. Functional requirements
  describe the V1 access decision. Group mapping removed. Eval
  requirements split into RAGAS and RBAC Access Outcome Suite.
- `context/decisions.md`: rewritten to a pointer.
- `context/glossary.md`: rewritten. Removed ACL, groups, IAM
  entries. Added RRF Fusion, Cross-Encoder Reranker, Hybrid
  Retrieval, JWT, Regex Guard, LLM Guard, BM25 Retrieval, Dense
  Retrieval, Clearance, Department.

### docs/adr/

- `docs/adr/0001-single-tenant-enterprise-rag-baseline.md`:
  rewritten. Out-of-V1 alternatives expanded with explicit
  rejection rationale. Access decision formula stated. Three
  boundaries stated.
- `docs/adr/README.md`: minor update. Date updated. Out-of-V1 ADR
  rule added.
- `docs/adr/template.md`: unchanged. Generic template.

### skills/project/

All seven `SKILL.md` files rewritten to V1 scope. All seven
`learnings.md` files updated to V1-scope notes. No edits to
`skills/external/` per the routing rule.

- `architecture_review/SKILL.md`: checklist rewritten around the
  V1 access decision, four-stage retrieval, JWT, regex guard, LLM
  guard, capability-based models, V1 table scope.
- `database_design/SKILL.md`: V1 table list. Out-of-V1 list with
  ADR requirement.
- `debugging/SKILL.md`: rewritten to inspect `audit_logs`,
  `retrieval_logs`, and `correlation_id` first. Check access
  decision at all three boundaries.
- `evaluation/SKILL.md`: split into System 1 (RAGAS) and System 2
  (RBAC Access Outcome Suite).
- `ingestion_pipeline/SKILL.md`: incremental re-ingestion through
  LlamaIndex, keyed on `documents.content_checksum`. Job outcome in
  `audit_logs`. No ACL snapshots.
- `rbac/SKILL.md`: rewritten to department + clearance only.
  Access decision formula. Three boundaries. Out-of-V1 list.
- `retrieval_engine/SKILL.md`: four-stage pipeline. LlamaIndex
  scope. Access decision at both boundaries.

## 7. Items Recorded For Future Implementation

These documentation changes describe behavior that requires code
changes. They are recorded here per the constraint that no code is
to be modified in this pass.

| # | Item | Where it is documented | Why it is recorded here |
|---|---|---|---|
| F1 | The access decision is a single pure function `(user, document) -> (allowed, reason)`. | `ARCHITECTURE.md`, `POLICIES.md`, `skills/project/rbac/SKILL.md` | Implementation must expose this as a pure function and invoke it at three boundaries. |
| F2 | The retrieval pipeline runs all four stages. | `ARCHITECTURE.md`, `WORKFLOWS.md`, `skills/project/retrieval_engine/SKILL.md` | Implementation must wire dense + BM25 + RRF + cross-encoder with no shortcut paths. |
| F3 | JWT validation runs on every request. | `ARCHITECTURE.md`, `POLICIES.md` | Implementation must reject invalid or missing tokens before any retrieval call. |
| F4 | Regex guard and LLM guard run on the primary request path. | `ARCHITECTURE.md`, `WORKFLOWS.md`, `POLICIES.md` | Implementation must place both guards between retrieval and generation. |
| F5 | Citation verification re-runs the access decision on every cited document. | `ARCHITECTURE.md`, `WORKFLOWS.md`, `skills/project/retrieval_engine/SKILL.md` | Implementation must drop any citation whose document fails the access decision at verification time. |
| F6 | V1 tables only. | `DATABASE_SCHEMA.md`, `skills/project/database_design/SKILL.md` | The first migration must include only `users`, `documents`, `chunks`, `audit_logs`, `retrieval_logs`, `evaluation_results`. |
| F7 | Models are capability-based. | `ARCHITECTURE.md`, `TOOLS.md`, `skills/project/architecture_review/SKILL.md`, `skills/project/retrieval_engine/SKILL.md`, `skills/project/ingestion_pipeline/SKILL.md` | Implementation must accept capability-based model references with no hardcoded vendor or version. |
| F8 | Two evaluation systems. | `ARCHITECTURE.md`, `WORKFLOWS.md`, `POLICIES.md`, `skills/project/evaluation/SKILL.md` | Implementation must run both suites and record results in `evaluation_results` with `suite` set to `ragas` or `rbac_access_outcome`. |

## 8. Out of V1 (Recorded for Future Versions)

These are intentionally absent from V1 documentation. If reintroduced,
each requires its own ADR.

- ACL engine, `document_acl` table, ACL grants.
- `permissions`, `role_permissions`, role-as-authorization.
- `groups`, `group_memberships`, group-based authorization.
- `user_roles` table.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Multi-tenant isolation.
- Pinning specific model identifiers or versions in docs.

## 9. Verification

- All 9 root docs updated.
- All 4 context docs updated.
- All 3 ADR files updated (template.md unchanged).
- All 7 project skill files updated (`SKILL.md` and `learnings.md`).
- `skills/external/` not modified, per `SKILLS.md` rule.
- No application code modified.
- No tests modified.
- No infrastructure code modified.
