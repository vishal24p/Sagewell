# Skills

This project routes agents to local skill files. Prefer local paths
over any outside installed skills with similar names.

## Namespaces

| Namespace | Purpose |
|---|---|
| `skills/project/` | Project-specific operating notes for Sagewell V1 areas. |
| `skills/external/` | Vendored external skills copied into this repo for stable local routing. |

## Protective Rules

- Read the routed local `SKILL.md` before acting on that area.
- Prefer `skills/project/` and `skills/external/` over installed
  outside skills.
- Do not edit vendored files under `skills/external/` unless the task
  explicitly asks to sync, upgrade, or repair the vendored copy.
- If a routed local `SKILL.md` is missing, report the missing path
  and ask before falling back to an outside installed skill.
- Keep project-specific learnings in
  `skills/project/<area>/learnings.md`, not in vendored external
  skill bodies.
- Use ASCII for skill routing docs unless an existing file already
  requires another character set.

## Project Skills

| Route | Use |
|---|---|
| `skills/project/architecture_review/SKILL.md` | Architecture review, boundary checks, cross-area consistency. |
| `skills/project/database_design/SKILL.md` | V1 schema, migrations, indexes. |
| `skills/project/retrieval_engine/SKILL.md` | Dense + BM25 + RRF + cross-encoder pipeline. |
| `skills/project/ingestion_pipeline/SKILL.md` | Incremental re-ingestion through LlamaIndex. |
| `skills/project/rbac/SKILL.md` | Department + clearance access decision. |
| `skills/project/evaluation/SKILL.md` | RAGAS suite and RBAC Access Outcome Suite. |
| `skills/project/debugging/SKILL.md` | Failure investigation, regressions, triage. |

## Vendored External Skills

Use vendored external skills for reusable workflow guidance.

| Route | Replaces | Use |
|---|---|---|
| `skills/external/plan-eng-review/SKILL.md` | `gstack-plan-eng-review` | Architecture, data flow, edge cases, and test-plan review. |
| `skills/external/autoplan/SKILL.md` | `gstack-autoplan` | Full reviewed implementation plan. |
| `skills/external/goal/SKILL.md` | `gstack-define-goal` | Restate the user's intent as a concrete, measurable goal before starting work; only invoke when the request is genuinely goal-shaped (multi-step, ambiguous, or needs a verifier), not for ordinary one-shot implementation tasks. |
| `skills/external/review/SKILL.md` | `gstack-review` | Diff risk review. |
| `skills/external/ship/SKILL.md` | `gstack-ship` | Commit, push, PR, release readiness. |
| `skills/external/cso/SKILL.md` | `gstack-cso` | Security review and policy risk review. |
| `skills/external/devex-review/SKILL.md` | `gstack-devex-review` | Onboarding, command, docs, API friction review. |
| `skills/external/context-save/SKILL.md` | `gstack-context-save` | Save session context. |
| `skills/external/context-restore/SKILL.md` | `gstack-context-restore` | Restore saved context. |
| `skills/external/agentic-engineering/SKILL.md` | `ecc:agentic-engineering` | Decompose agent-sized work and apply eval-first execution. |
| `skills/external/architecture-decision-records/SKILL.md` | `ecc:architecture-decision-records` | Capture architectural decisions. |
| `skills/external/api-design/SKILL.md` | `ecc:api-design` | API shape, naming, versioning, error contracts. |
| `skills/external/backend-patterns/SKILL.md` | `ecc:backend-patterns` | Backend layering and service patterns. |
| `skills/external/agent-architecture-audit/SKILL.md` | `ecc:agent-architecture-audit` | Audit multi-agent architecture. |
| `skills/external/ai-regression-testing/SKILL.md` | `ecc:ai-regression-testing` | Regression checks for AI, RAG, and workflow behavior. |

## Missing Expected Skills

- `skills/external/accessibility/SKILL.md` is not present. If UI work
  needs accessibility guidance, report this missing local route
  before using any outside installed accessibility skill.

## Routing Rules

- For architecture changes, read
  `skills/external/plan-eng-review/SKILL.md` and
  `skills/project/architecture_review/SKILL.md`.
- For large implementation planning, read
  `skills/external/autoplan/SKILL.md`.
- For security-sensitive changes, read `skills/external/cso/SKILL.md`
  and `skills/project/rbac/SKILL.md`.
- For retrieval changes, read
  `skills/project/retrieval_engine/SKILL.md` and
  `skills/project/evaluation/SKILL.md`.
- For ingestion changes, read
  `skills/project/ingestion_pipeline/SKILL.md` and
  `skills/project/database_design/SKILL.md`.
- For API work, read `skills/external/api-design/SKILL.md` and
  `skills/external/backend-patterns/SKILL.md`.
- For commit, push, PR, release, or ship readiness, read
  `skills/external/ship/SKILL.md` and apply the commit and ship gate.
- For new durable decisions, read
  `skills/external/architecture-decision-records/SKILL.md` and
  create or update an ADR.
- For small documentation edits, do not invoke a large review
  pipeline unless risk justifies it.

## Commit And Ship Gate

Use `skills/external/ship/SKILL.md` before committing meaningful work,
before pushing, before opening a PR or MR, when the user says
ship, deploy, push, or create PR, or when implementation is ready to
land.

The gate requires:

- Check repo status and understand all changed files.
- Confirm changes match the requested scope and docs and status are
  updated when needed.
- Run relevant tests, evals, lint, or build checks for changed areas.
- Run a pre-landing review, using `skills/external/review/SKILL.md`
  for meaningful changes.
- Block commit on failing tests, unresolved P1 or security issues,
  access-decision regressions, or stale verification after code
  changes.
- Split large changes into logical, bisectable commits. A single
  commit is fine for tiny docs-only changes.
- Never force push.
- Push or create a PR only after fresh verification evidence.