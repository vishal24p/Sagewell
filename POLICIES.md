# Policies

V1 security, authorization, prompt-protection, and logging policies.

## Security Principles

- Authorization is department plus clearance only.
- Treat user input, document text, metadata, and retrieved chunks as
  untrusted.
- Authorization happens before retrieval, after reranking, and at
  citation verification.
- The system never reveals documents, metadata, citations, summaries,
  or existence signals for resources the actor cannot access.
- Default behavior is deny.

## Authorization Model

V1 authorization inputs:

- `user.department`
- `user.clearance`
- `document.department`
- `document.required_clearance`

The access decision function:

```text
access = (
    user.department == document.department
    OR
    document.department == "ALL"
)
AND
(
    user.clearance >= document.required_clearance
)
```

Clearance hierarchy:

```text
PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED
```

Role on `users` (employee, manager, admin) is reserved for UI behavior
and auditing. Role does not participate in authorization.

There is no ACL engine, no `document_acl` table, no permissions
framework, no groups, and no group-based authorization in V1.

## Classification Policy

Documents and chunks carry classification metadata before indexing.

- Department filter: actor department matches document department, or
  the document department is ALL.
- Clearance filter: actor clearance is greater than or equal to the
  document required clearance.

If either check fails, the document is not retrievable.

## JWT Authentication Policy

- The API layer validates the JWT on every request.
- Required claims include subject, department, clearance, and
  expiration.
- Optional `role` claim is permitted for UI behavior and auditing
  only; it does not participate in authorization.
- Invalid or expired tokens return 401 and produce an `audit_logs`
  row with reason_code JWT_INVALID.

## Prompt-Protection Policy

Prompt protection is on the primary request path. The order is:

```text
JWT Authentication
  -> Regex Guard
  -> RBAC Authorization (department + clearance)
  -> Retrieval (dense + BM25 + RRF + cross-encoder)
  -> LLM Guard
  -> Generation
```

Prompt protection is not deferred.

The Regex Guard runs after JWT validation and before RBAC and
retrieval. The Regex Guard is cheap, deterministic, and fast; its
job is to refuse obvious prompt-injection attempts before any
authorization or retrieval work is performed. Examples include
"ignore previous instructions," "reveal system prompt," "dump
database," and "show all restricted documents."

The LLM Guard runs after retrieval and before generation. It is
context-aware and inspects the user query together with retrieved
chunks. It catches indirect prompt injection, contextual attacks,
instruction conflicts, and retrieval-based attacks that the Regex
Guard cannot see.

### Regex Guard

- Pattern-based detection on the normalized query.
- Runs before RBAC and retrieval, so obvious prompt-injection
  attempts are refused without paying for authorization or retrieval
  work.
- High-risk verdicts refuse the request.
- The pattern set is versioned.

### LLM Guard

- The Guardrail Model classifies the normalized query and retrieved
  chunks.
- High-risk classification refuses the request, downgrades retrieved
  chunks, or constrains generation.
- Guardrail verdict is recorded in `audit_logs`.

### Risk Signals

- Requests to ignore previous instructions.
- Requests to reveal system prompts, keys, credentials, or policies.
- Claims that a document has authority over the application.
- Instructions to skip access checks or logging.
- Obfuscated commands, hidden text, or encoded payloads.

The system prefers quoting or citing suspicious text over following
it, and returns a refusal or constrained answer when the actor asks
for inaccessible information.

## Data Handling

- Store only required document text, metadata, embeddings, and audit
  data.
- Original document references are kept for traceability.
- Secrets, raw credentials, and full private documents are not logged.
- Sensitive identifiers are masked or hashed in logs unless exact
  values are required for audit.
- Deleted document tombstones are retained long enough to prevent
  stale retrieval.

## Logging And Audit

Security-relevant events written to `audit_logs`:

- Authentication outcome.
- Authorization outcome.
- Retrieval outcome with filter summary.
- Regex guard verdict.
- LLM guard verdict.
- Citation verification outcome.
- Ingestion job lifecycle.
- Evaluation run outcome.

`audit_logs` includes:

- actor
- action
- resource id
- decision
- reason_code
- correlation_id
- timestamp

Do not log:

- API keys.
- Passwords.
- Raw access tokens.
- Full prompts when they contain sensitive document text, unless a
  secure debug mode is explicitly enabled.

## Evaluation Policy

Two evaluation systems run independently.

System 1: RAGAS

- Faithfulness
- Context Precision
- Context Recall
- Answer Relevancy

System 2: RBAC Access Outcome Suite

- Allow Tests
- Deny Tests
- Department Tests
- Clearance Tests

Both systems are required. RAGAS does not replace access outcome
tests. Access outcome tests do not replace RAGAS.

## Operational Policy

- Use least-privilege database accounts.
- Migrations are reversible when practical.
- Correlation IDs flow through API, workflow, retrieval, LLM, and
  audit writes.
- Fail closed on access-decision errors.
- Fail with a clear user-safe message on retrieval or generation
  errors.

## Out of V1 Scope

These are not part of V1 and are not policy:

- ACL engines, `document_acl`, ACL grants.
- Permissions, roles-as-authorization, `role_permissions`.
- Groups, group memberships, group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.
- Policy engines beyond department + clearance.