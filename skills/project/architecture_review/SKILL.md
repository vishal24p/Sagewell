# Architecture Review Skill

Use this local skill when reviewing architecture changes for Sagewell.

## Inputs

- `ARCHITECTURE.md`
- `WORKFLOWS.md`
- `POLICIES.md`
- Relevant ADRs in `docs/adr/`

## Checklist

- Clean Architecture dependency direction is preserved.
- Domain policies do not depend on FastAPI, LangGraph, LlamaIndex, or database clients.
- Authorization is enforced in application use cases, not only in API handlers.
- Retrieval cannot bypass RBAC filters.
- LangGraph nodes have typed state and testable boundaries.
- Infrastructure adapters can be replaced without changing domain rules.
- Observability includes correlation IDs and reason codes.

## Done Condition

The review identifies boundary violations, missing policy checks, untested workflow paths, and required ADR updates.
