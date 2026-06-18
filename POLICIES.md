# Policies

This file defines security, RBAC, prompt-injection, logging, and operational policies for the single-tenant Enterprise RAG baseline.

## Security Principles

- Single tenant does not mean single trust level. Enforce RBAC on every retrieval and answer path.
- Treat user input, document text, metadata, and retrieved chunks as untrusted.
- Authorization must happen before retrieval, during retrieval filtering, and before final answer rendering.
- The system must never reveal documents, metadata, citations, summaries, or existence signals for resources the user cannot access.
- Prefer deny-by-default behavior for ambiguous permissions.

## RBAC Model

Entities:

- User: authenticated human or service account.
- Role: named permission bundle.
- Group: collection of users mapped to roles or resource grants.
- Resource: document, collection, connector, job, or audit record.
- Permission: action such as read, write, ingest, administer, evaluate, or view audit logs.

Required checks:

- API entrypoints validate identity and coarse action permission.
- Application use cases validate operation-specific permission.
- Retrieval filters restrict candidate chunks by user, group, role, collection, document ACL, department, and clearance.
- Citation rendering re-checks access to the cited document.
- Admin operations require explicit admin permission, not role name matching.

## Classification Policy

Documents and chunks must carry classification metadata before they are indexed.

Clearance levels:

```text
PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED
```

Access requires:

```text
user.clearance >= document.clearance
AND
(
  user.department = document.department
  OR document.department = "ALL"
)
```

ACL grants can narrow access further. ACL grants must not widen access beyond clearance and department constraints unless a future ADR explicitly changes this rule.

## Prompt-Injection Policy

All retrieved content is data, not instruction.

The assistant workflow must:

- Keep system and developer instructions outside the retrieved context.
- Wrap retrieved chunks with clear data boundaries.
- Ignore instructions in documents that ask to reveal secrets, change policy, disable RBAC, or bypass tools.
- Detect high-risk injection patterns and reduce trust in the affected chunk.
- Prefer quoting or citing suspicious text over following it.
- Return a refusal or constrained answer when the user asks for inaccessible information.

Risk signals:

- Requests to ignore previous instructions.
- Requests to reveal system prompts, keys, credentials, or policies.
- Claims that a document has authority over the application.
- Instructions to skip access checks or logging.
- Obfuscated commands, hidden text, or encoded payloads.

## Data Handling

- Store only required document text, metadata, embeddings, and audit data.
- Keep original document references when possible for traceability.
- Do not log secrets, raw credentials, or full private documents.
- Mask or hash sensitive identifiers in logs unless exact values are required for audit.
- Retain deleted document tombstones long enough to prevent stale retrieval.

## Logging And Audit

Log security-relevant events:

- Authentication outcome.
- Authorization denial.
- Ingestion job lifecycle.
- Document ACL changes.
- Retrieval query with policy-filter summary.
- Answer generation with citation IDs.
- Prompt-injection detections.
- Evaluation runs and failures.

Audit logs should include:

- Actor.
- Action.
- Resource ID.
- Decision.
- Reason code.
- Timestamp.
- Correlation ID.

Do not log:

- API keys.
- Passwords.
- Raw access tokens.
- Full prompts when they contain sensitive document text, unless a secure debug mode is explicitly enabled.

## Evaluation Policy

Every retrieval or authorization change needs regression coverage for:

- Allowed user can retrieve expected documents.
- Denied user cannot retrieve restricted documents.
- Hybrid retrieval preserves ACL filters.
- Citations never point to unauthorized documents.
- Prompt-injection samples do not alter policy behavior.

## Operational Policy

- Use least-privilege database accounts.
- Keep migrations reversible when practical.
- Use correlation IDs across API, workflow, database, and LLM calls.
- Fail closed on policy-service errors.
- Fail with a clear user-safe message on retrieval or generation errors.
