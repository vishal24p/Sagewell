# Tools

This project uses a small, explicit toolchain for development, documentation, code navigation, and quality checks.

## Runtime Stack

- Python backend with FastAPI.
- Clean Architecture boundaries for API, application use cases, domain policy, and infrastructure adapters.
- LangGraph for RAG workflow orchestration.
- LlamaIndex for ingestion and retrieval utilities.
- PostgreSQL for relational state.
- `pgvector` for dense vector search.
- `pg_search` for lexical and hybrid retrieval support.
- RAGAS and custom RBAC evals for answer quality and access-control regression tests.

## Expected Commands

These commands are placeholders until implementation files exist. Keep project commands simple and copy-pasteable.

```powershell
# Check repository status when this directory becomes a Git repository.
git status --short

# Format Python code when formatter configuration exists.
python -m ruff format .

# Lint Python code when ruff configuration exists.
python -m ruff check .

# Run tests when test files exist.
python -m pytest
```

Do not run network commands unless the user explicitly asks for dependency installation or external lookup.

## CodeGraph

CodeGraph is initialized for this workspace. At scaffold time it may report zero indexed files because source files have not been added yet.

### Status

Use the MCP tool when available:

```text
codegraph_status
```

Expected healthy signs:

- A database exists.
- Indexed file count is greater than zero after source files are added.
- Node and edge counts increase after implementation begins.

### Init And Sync

When a workspace has no `.codegraph/` directory, ask before initializing:

```powershell
codegraph init -i
```

When the index is stale after source changes, sync it from the project root:

```powershell
codegraph sync
```

When a full rebuild is needed, use:

```powershell
codegraph index
```

Do not treat CodeGraph as a compiler or test runner. It is a fast structural index.

### Tool Selection

| Need | Tool |
|---|---|
| Find a named class, function, or method | `codegraph_search` |
| Understand a feature or area | `codegraph_context` |
| Find who calls a symbol | `codegraph_callers` |
| Find what a symbol calls | `codegraph_callees` |
| Estimate change impact | `codegraph_impact` |
| Read one symbol source | `codegraph_node` |
| Read several related symbols | `codegraph_explore` |
| Inspect indexed file layout | `codegraph_files` |
| Check index health | `codegraph_status` |

Rules:

- Use CodeGraph before grep for structural questions.
- Use `codegraph_context` before separate search and read calls.
- Use `codegraph_explore` for several related symbols instead of repeated node reads.
- Use `rg` for literal strings in docs, logs, config, or comments.
- Wait briefly after file edits before relying on a refreshed index.

## Documentation Commands

Useful local checks for markdown-only work:

```powershell
rg --files
git diff --check
```

If the workspace is not a Git repository, `git diff --check` will fail. Report that instead of hiding it.
