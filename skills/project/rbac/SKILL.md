# RBAC Skill

Use this skill for the V1 access decision and any change that touches
authorization behavior.

## Inputs

- `POLICIES.md`
- `DATABASE_SCHEMA.md`
- `WORKFLOWS.md`
- `ARCHITECTURE.md`

## V1 Authorization Rule

Authorization is department plus clearance only.

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

Clearance hierarchy: `PUBLIC < INTERNAL < CONFIDENTIAL < RESTRICTED`.

## Out of V1

These do not exist in V1 and must not be reintroduced without an ADR:

- ACL engine, `document_acl` table, ACL grants.
- `permissions`, `role_permissions`, role-as-authorization.
- `groups`, `group_memberships`, group-based authorization.
- OIDC, Okta, Entra ID, LDAP, identity federation, external IAM.
- Permission resolution engines.

`users.role` exists for UI behavior and auditing only. It does not
participate in authorization.

## Checklist

- Default behavior is deny.
- The access decision runs at three boundaries: pre-retrieval,
  post-rerank, citation verification.
- The function is pure: `(user, document) -> (allowed, reason)`.
- Department match is exact, with `ALL` as the company-wide escape.
- Clearance is greater-than-or-equal.
- The actor cannot infer existence through counts, citations, errors,
  or answer text when access is denied.
- `audit_logs` records the decision, the `reason_code`, and the
  `correlation_id`.
- Failures fail closed.

## Test Categories (RBAC Access Outcome Suite)

- Allow Tests
- Deny Tests
- Department Tests
- Clearance Tests

## Done Condition

The change has Allow and Deny cases with Department and Clearance
coverage. Cases assert access-decision outcomes, not answer strings.