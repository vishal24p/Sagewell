# AGENTS

This file is the project constitution. It defines how an agent must
behave inside this repository. It does not track project state, the
implementation roadmap, current progress, current tasks, or the
handoff status.

For current work, read `NEXT_AGENT.md`.
For current progress, completed work, in-progress work, and known
risks, read `docs/HANDOFF/CURRENT_STATE.md`.
For pending decisions, read `docs/HANDOFF/DECISIONS_PENDING.md`.
For unresolved engineering concerns, read
`docs/HANDOFF/KNOWN_ISSUES.md`.
For the implementation roadmap, read `PROJECT_STATUS.md`.
For skill routing, read `SKILLS.md`.

---

## Mission

Sagewell is a single-company, single-tenant enterprise RAG that
answers questions over private organizational documents, with
department plus clearance as the only authorization inputs.

---

## Required Reading

Before implementation work:

1. Read `AGENTS.md`.
2. Read `NEXT_AGENT.md`.
3. Read source-of-truth documents relevant to the task
   (`ARCHITECTURE.md`, `DATABASE_SCHEMA.md`, `POLICIES.md`,
   `WORKFLOWS.md`).
4. Read the applicable project skill.

Do not begin implementation until these have been reviewed.

---

## Agent Responsibilities

- Do not revert another agent's work or the user's edits.
- Keep changes scoped to the requested ownership area.
- Prefer existing project decisions over new patterns.

---

## Source Of Truth Hierarchy

When two documents disagree, defer to the higher entry.

1. `ARCHITECTURE.md` — system boundaries, components, retrieval
   pipeline, framework responsibilities, primary request path.
2. `DATABASE_SCHEMA.md` — V1 schema narrative.
3. `POLICIES.md` — security, authorization, prompt-protection,
   logging.
4. `WORKFLOWS.md` — runtime flows.
5. `docs/adr/` — accepted architectural decisions. The most
   recent ADR governs in case of conflict with the four primary
   files; otherwise the four primary files govern.
6. `MEMORY.md` — authoritative decisions log for durable project
   decisions that are not architectural.
7. `PROJECT_STATUS.md` — V1 scope summary and the M0-M14
   implementation roadmap.
8. `NEXT_AGENT.md` and `docs/HANDOFF/` — current state, current
   task, pending decisions, known issues. Operational, not
   authoritative.
9. `context/` — supporting context (project overview,
   requirements pointer, glossary).
10. `skills/project/` and `skills/external/` — topical guidance.

---

## Architectural Guardrails

These are locked decisions. An agent must not relax, remove, or
contradict them.

- Authorization is department plus clearance only.
- The access decision is a single pure function invoked at three
  boundaries: pre-retrieval, post-rerank, citation verification.
- `users.role` is for UI behavior and auditing only. It does not
  participate in authorization.
- Retrieval is hybrid and runs all four stages: dense retrieval,
  BM25 retrieval, RRF fusion, cross-encoder reranking. No
  shortcuts.
- LangGraph is responsible for workflow orchestration, state
  management, and node execution. LlamaIndex is responsible for
  document loading, semantic chunking, ingestion, and retrieval
  abstractions. Neither is responsible for the other's domain.
- Prompt protection runs on the primary request path. The order
  is JWT, Regex Guard, RBAC Authorization, Retrieval, LLM Guard,
  Generation. Prompt protection is not deferred.
- JWT validation runs on every request. The workflow is designed
  around an authenticated actor from the first test. The workflow
  state contains `user_id`, `department`, `clearance`, `role`,
  and `correlation_id`.
- V1 tables only: `users`, `documents`, `chunks`, `audit_logs`,
  `retrieval_logs`, `evaluation_results`.
- Models are capability-based. Documentation must never assume a
  specific generation, embedding, reranker, or guardrail model.
- Two evaluation systems run independently: RAGAS (Faithfulness,
  Context Precision, Context Recall, Answer Relevancy) and the
  RBAC Access Outcome Suite (Allow, Deny, Department, Clearance).
  Both are required.

---

## Forbidden Changes

Out of V1 scope. Each requires its own ADR if reintroduced.

- ACL engine, `document_acl`, ACL grants.
- `permissions`, `role_permissions`, role-as-authorization.
- `groups`, `group_memberships`, group-based authorization.
- `user_roles` table.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Multi-tenant isolation.
- Pinning specific model identifiers or versions in docs.

---

## Change Control Rules

- A change that introduces, removes, or renames an architectural
  component requires an ADR in `docs/adr/`.
- A change to the access decision function or its inputs requires
  an ADR.
- A change to the retrieval pipeline (adding, removing, or
  replacing a stage) requires an ADR.
- A change to the prompt-protection policy (placement, ordering,
  or guard responsibilities) requires an ADR.
- A change to the V1 table list (adding, removing, or renaming a
  table) requires an ADR.
- A change to the out-of-V1 list (reintroducing a forbidden
  concept) requires an ADR.
- A change to the implementation sequencing that affects
  dependency order or workflow-state shape requires an update to
  `PROJECT_STATUS.md` and a new row in `MEMORY.md`.
- Small documentation edits that restate existing decisions do
  not require an ADR.

---

## Ambiguity Policy

When requirements, architecture, or roadmap conflict:

1. The higher entry in the Source Of Truth Hierarchy governs.
2. If two same-tier documents disagree, the most recent ADR
   governs.
3. If a request contradicts a guardrail, surface the
   contradiction. Do not silently relax the guardrail.
4. If a request contradicts an out-of-V1 rule, explain that the
   change requires an ADR.

---

## When Unsure

If a requirement is unclear:

- Do not invent architecture.
- Do not invent requirements.
- Do not introduce new systems.
- Do not silently redesign existing systems.

Instead:

1. Identify the ambiguity.
2. Identify the affected source-of-truth document.
3. Request clarification.

For goal-shaped requests (multi-step, ambiguous, or needs a
verifier), restate the user's intent as a concrete, measurable
goal before starting work. The canonical route is
`skills/external/goal/SKILL.md`. Do not invoke the goal skill
for ordinary one-shot implementation tasks — only when the
request is genuinely goal-shaped. For full reviewed plans,
route to `skills/external/autoplan/SKILL.md`. Both are listed
in `SKILLS.md`'s Vendored External Skills table; treat that
table as the canonical routing index.

---

## Handoff Ownership

| Concern | Owning file |
|---|---|
| Current work, next task, exit criteria | `NEXT_AGENT.md` |
| Current state, completed, in progress | `docs/HANDOFF/CURRENT_STATE.md` |
| Pending decisions | `docs/HANDOFF/DECISIONS_PENDING.md` |
| Known issues | `docs/HANDOFF/KNOWN_ISSUES.md` |
| Implementation roadmap | `PROJECT_STATUS.md` |
| Skill routing | `SKILLS.md` |
| Repository execution rules | `SKILLS.md` |

---

## Skill Enforcement

Project skills under `skills/project/` and `skills/external/` are
authoritative for their areas. `SKILLS.md` is the routing index.

Agents must not bypass project skills when a relevant skill
exists:

- RBAC work → `skills/project/rbac/SKILL.md`
- Retrieval work → `skills/project/retrieval_engine/SKILL.md`
- Database work → `skills/project/database_design/SKILL.md`
- Ingestion work → `skills/project/ingestion_pipeline/SKILL.md`
- Evaluation work → `skills/project/evaluation/SKILL.md`
- Debugging work → `skills/project/debugging/SKILL.md`
- Architecture review → `skills/project/architecture_review/SKILL.md`

AGENTS.md does not duplicate the routing table. Read `SKILLS.md`
for full rules, vendored external skills, and the commit and
ship gate.

---

## Testing

Testing requirements are owned by the applicable project skill.
A task is not complete until the required validation defined by
that skill passes.

---

## Milestone Discipline

Agents must not implement future milestones before the current
milestone exit criteria is satisfied.

The current milestone, current status, and exit criteria live in
`NEXT_AGENT.md`.

---

## Commit Discipline

Commit only after milestone completion.

The detailed execution procedure (commit format, ship gate,
pre-landing review, push policy) lives in `SKILLS.md`.

---

## Execution Rules

Repository execution rules — including commit, push, release,
milestone completion, and documentation synchronization — live
in `SKILLS.md`. They are not duplicated here.
