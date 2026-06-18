# Sagewell Agent Guide

This file defines agent behavior for this project. It points to the source-of-truth docs instead of repeating architecture, schema, workflow, and policy detail.

## Operating Rules

- Be analytical and direct. Avoid vague hype.
- If a request is wrong or risky, explain what is wrong and the consequence.
- Use sub-agents for implementation work. For small work, use one appropriate sub-agent instead of a swarm. Do not overlap sub-agent responsibilities.
- Keep changes scoped to the requested ownership area.
- Do not revert edits made by other agents or by the user.
- Prefer existing project decisions over new patterns unless there is a clear reason to change them.
- Record durable decisions in `MEMORY.md` and `docs/adr/`.
- Use plain ASCII in markdown files unless a file already requires another character set.
- For all skill routing, read local paths from `SKILLS.md`. Prefer `skills/project/` and `skills/external/` over outside installed skills.
- For commit, push, PR, release, or ship readiness, follow the local gate in `SKILLS.md`.

## Source Of Truth

| Area | File |
|---|---|
| Architecture | `ARCHITECTURE.md` |
| Database schema | `DATABASE_SCHEMA.md` |
| Runtime flows | `WORKFLOWS.md` |
| Security, RBAC, logging | `POLICIES.md` |
| Tools and commands | `TOOLS.md` |
| Local skill routing | `SKILLS.md` |
| Decisions and open questions | `MEMORY.md` |
| Current status | `PROJECT_STATUS.md` |
| Project context | `context/` |
| Architecture decisions | `docs/adr/` |

## CodeGraph Use

CodeGraph is initialized for this workspace. Use it for structural code questions once source files exist:

- Find a symbol: `codegraph_search`
- Understand an area: `codegraph_context`
- Find callers: `codegraph_callers`
- Find callees: `codegraph_callees`
- Estimate change impact: `codegraph_impact`
- Read one symbol: `codegraph_node`
- Read related symbols: `codegraph_explore`
- Inspect indexed files: `codegraph_files`
- Check index health: `codegraph_status`

Use text search only for literal strings, comments, log messages, or markdown.

## Documentation Rule

Keep this file short. Add detail to the correct source document instead of expanding `AGENTS.md`.
