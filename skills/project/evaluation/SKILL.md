# Evaluation Skill

V1 has two independent evaluation systems. Both are required. Neither
replaces the other.

## Inputs

- `WORKFLOWS.md`
- `POLICIES.md`
- `ARCHITECTURE.md`
- `DATABASE_SCHEMA.md` (for `evaluation_results`)

## System 1: RAGAS

Metrics:

- Faithfulness
- Context Precision
- Context Recall
- Answer Relevancy

Purpose: answer quality.

## System 2: RBAC Access Outcome Suite

Tests:

- Allow Tests
- Deny Tests
- Department Tests
- Clearance Tests

Purpose: access-decision correctness.

## Checklist

- Both systems run on the release gate.
- Each evaluation case records `suite` (`ragas` or
  `rbac_access_outcome`), `case_key`, `input`, `expected`, `status`,
  `scores`, `failure_reason`, and `model_config` (capability-based).
- RBAC cases assert access-decision outcomes, not answer strings.
  Deny cases assert the access decision returns deny at all three
  boundaries for the test actor and document.
- RAGAS cases assert quality metrics only; they do not assert
  access-decision outcomes.
- Failures include stable `reason_code`.
- The release gate blocks on RBAC regression.

## Done Condition

Both systems have run, both report pass or fail with reason codes,
and the results are stored in `evaluation_results` with their
`model_config`. The release gate has a clear yes or no.