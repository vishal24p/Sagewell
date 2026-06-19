# RBAC Learnings

- V1 authorization is department + clearance. Nothing else.
- The access decision is one pure function, called at three
  boundaries.
- `users.role` is for UI and auditing, not authorization.
- Deny tests assert access-decision outcomes, not answer strings.