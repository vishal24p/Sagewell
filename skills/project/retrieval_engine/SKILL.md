# Retrieval Engine Skill

Use this local skill for hybrid retrieval, ranking, citations, and context packing.

## Inputs

- `ARCHITECTURE.md`
- `WORKFLOWS.md`
- `POLICIES.md`
- `DATABASE_SCHEMA.md`

## Checklist

- Policy filters are applied before vector and lexical candidate selection.
- Vector retrieval and lexical retrieval use the same authorization constraints.
- Merge and rerank steps do not reintroduce unauthorized chunks.
- Citation rendering re-checks document access.
- Context packing treats chunks as untrusted data.
- Retrieval configuration is versioned for eval comparison.
- Candidate counts before and after filtering are observable.

## Done Condition

Retrieval returns useful authorized evidence and cannot leak denied documents through candidates, context, citations, or answer text.
