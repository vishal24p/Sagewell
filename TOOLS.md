# Tools

Local toolchain for development, documentation, and code navigation.

## Runtime Stack (Capability-Based)

- API: HTTP layer with JWT validation.
- Workflow orchestration: LangGraph.
- Document loading, semantic chunking, ingestion, retrieval
  abstractions: LlamaIndex.
- Authorization: department + clearance, applied at every boundary.
- Retrieval pipeline: dense + BM25 + RRF fusion + cross-encoder
  reranking.
- Database: PostgreSQL with `pgvector` and `pg_search`.
- Models: capability-based. Generation Model, Embedding Model,
  Reranker Model, Guardrail Model. No specific model is pinned in V1.

## Expected Commands

These commands are placeholders until implementation files exist.

```powershell
git status --short

python -m ruff format .
python -m ruff check .
python -m pytest
```

Do not run network commands unless the user explicitly asks for
dependency installation or external lookup.

## CodeGraph

CodeGraph is initialized for this workspace. At scaffold time it may
report zero indexed files because source files have not been added.

### Status

```text
codegraph_status
```

Expected healthy signs:

- A database exists.
- Indexed file count is greater than zero after source files are
  added.
- Node and edge counts increase after implementation begins.

### Init And Sync

```powershell
codegraph init -i
codegraph sync
codegraph index
```

CodeGraph is not a compiler or test runner. It is a fast structural
index.

### Tool Selection

| Need | Tool |
|---|---|
| Find a named symbol | `codegraph_search` |
| Understand an area | `codegraph_context` |
| Find who calls a symbol | `codegraph_callers` |
| Find what a symbol calls | `codegraph_callees` |
| Estimate change impact | `codegraph_impact` |
| Read one symbol source | `codegraph_node` |
| Read several related symbols | `codegraph_explore` |
| Inspect indexed file layout | `codegraph_files` |
| Check index health | `codegraph_status` |

Use CodeGraph before grep for structural questions. Use
`codegraph_context` before separate search and read calls. Use
`codegraph_explore` for several related symbols. Use `rg` for literal
strings in docs, logs, config, or comments.

## Documentation Commands

```powershell
rg --files
git diff --check
```

If the workspace is not a Git repository, `git diff --check` will
fail. Report that instead of hiding it.