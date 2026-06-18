# RBAC Skill

Use this local skill for authorization, access filters, ACL updates, and security-sensitive retrieval behavior.

## Inputs

- `POLICIES.md`
- `DATABASE_SCHEMA.md`
- `WORKFLOWS.md`

## Checklist

- Default behavior is deny.
- API authorization is not the only authorization layer.
- Retrieval filters include user, group, role, department, clearance, collection, and document constraints as applicable.
- User clearance must satisfy the document clearance level.
- User department must match the document department unless the document department is `ALL`.
- Document-level deny can override broader allow when configured.
- Citation access is checked after generation.
- Denied users cannot infer document existence through errors, counts, citations, or answer text.
- Audit logs record decision and reason code.

## Done Condition

The change has allow-path and deny-path tests, including same-query different-user, different-clearance, and different-department cases.
