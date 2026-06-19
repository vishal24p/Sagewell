# Debugging Skill

Use this skill for broken commands, regressions, failed evals, and
unclear runtime behavior.

## Inputs

- `PROJECT_STATUS.md`
- `WORKFLOWS.md`
- Relevant logs, eval outputs, and correlation IDs.

## Checklist

- Start with the smallest failing reproduction.
- Capture `correlation_id`.
- Inspect `audit_logs` first.
- Inspect `retrieval_logs` next: `policy_filter`, `candidate_counts`,
  and `retrieval_config`.
- Check the actor's `department` and `clearance` against the
  document's `department` and `required_clearance`.
- Check the access decision outcome and `reason_code` at all three
  boundaries: pre-retrieval, post-rerank, citation verification.
- Check regex guard and LLM guard verdicts.
- Check citation verification results.
- Convert confirmed failures into evaluation_results cases.

## Done Condition

The root cause is identified, the fix path is clear, and a regression
case is recorded in `evaluation_results`.