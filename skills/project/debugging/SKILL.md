# Debugging Skill

Use this local skill for broken commands, regressions, failed evals, and unclear runtime behavior.

## Inputs

- `PROJECT_STATUS.md`
- `WORKFLOWS.md`
- Relevant logs, eval outputs, and correlation IDs.

## Checklist

- Start with the smallest failing reproduction.
- Capture correlation ID when available.
- Check audit events before assuming retrieval is wrong.
- Compare actor roles, groups, and document ACLs.
- Inspect policy filter summary.
- Inspect candidate counts before and after filters.
- Convert confirmed failures into regression tests.

## Done Condition

The root cause is identified, the fix path is clear, and a regression check is defined.
