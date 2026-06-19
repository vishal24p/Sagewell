# Retrieval Engine Skill

Use this skill for the V1 retrieval pipeline.

## Inputs

- `ARCHITECTURE.md`
- `WORKFLOWS.md`
- `POLICIES.md`
- `DATABASE_SCHEMA.md`

## V1 Retrieval Pipeline (Mandatory, All Four Stages)

```text
Dense Retrieval
  +
BM25 Retrieval
  +
RRF Fusion
  +
Cross-Encoder Reranking
```

No stage may be omitted. Vector-only or BM25-only retrieval is not
permitted in V1.

## Stage Responsibilities

### Dense Retrieval

- Embedding Model (capability-based).
- `pgvector` similarity search.
- Returns top-K with vector score.

### BM25 Retrieval

- `pg_search` lexical search.
- Returns top-K with BM25 score.

### RRF Fusion

- Reciprocal Rank Fusion merges dense and BM25 ranked lists.
- Configurable K constant.

### Cross-Encoder Reranking

- Reranker Model (capability-based).
- Reranks the fused list.
- Returns the final top-N chunks.

## Access Decision Integration

- The access decision runs before retrieval (filter) and after
  reranking (drop). See `skills/project/rbac/SKILL.md`.
- The same access decision runs at citation verification.

## LlamaIndex Scope

LlamaIndex provides retrieval abstractions. It does not handle
authorization. The workflow applies the access decision to
LlamaIndex output.

## Checklist

- All four stages run on every retrieval.
- The access decision is applied at both boundaries.
- Retrieval configuration is versioned in `retrieval_logs.retrieval_config`.
- Candidate counts are observable at each stage.
- Citation verification re-runs the access decision on every cited
  document.

## Done Condition

Retrieval returns useful authorized evidence and cannot leak denied
documents through candidates, context, citations, or answer text.