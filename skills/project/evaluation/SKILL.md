# Evaluation Skill

Use this local skill for RAGAS, RBAC evals, prompt-injection evals, and regression gates.

## Inputs

- `WORKFLOWS.md`
- `POLICIES.md`
- `ARCHITECTURE.md`

## Checklist

- Evaluation datasets are versioned.
- Retrieval configuration and model configuration are stored with each run.
- RBAC deny cases assert absence from candidates, context, answer, and citations.
- RAGAS metrics cover faithfulness, context precision, and context recall.
- Prompt-injection cases include malicious retrieved documents.
- Failures include stable reason codes.
- Release gates block on access-control regression.

## Done Condition

Evaluation can compare current behavior against a prior baseline and explain failures well enough to reproduce them.
