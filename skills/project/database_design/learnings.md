# Database Design Learnings

- `document_acl` is the authority unless an ADR changes that.
- `chunk_acl_snapshot` is an optimization, not the source of truth.
- ACL and retrieval indexes are release blockers, not later polish.
