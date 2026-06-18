# Workflows

This file defines baseline runtime flows. Implementation should keep each step explicit enough to test.

## Query And Answer

```text
1. Receive query.
2. Authenticate actor.
3. Authorize query action.
4. Build policy filter from actor roles, groups, department, clearance, and resource grants.
5. Normalize query.
6. Run vector search with policy filters.
7. Run lexical search with policy filters.
8. Merge and rerank candidates.
9. Detect prompt-injection risk in query and retrieved chunks.
10. Pack bounded context as untrusted data.
11. Generate answer.
12. Verify citations and document access.
13. Persist retrieval run, answer, citations, and audit events.
14. Return safe answer.
```

Failure behavior:

- Authentication failure returns unauthorized.
- Authorization failure returns forbidden without revealing resource existence.
- Retrieval failure returns a safe error and logs a reason code.
- Citation verification failure removes the citation or fails closed.
- Prompt-injection risk can reduce context, add caution, or refuse.

## Incremental Ingestion

```text
1. Start ingestion job.
2. Authenticate and authorize actor.
3. Discover source documents.
4. Compare source version and checksum with stored document versions.
5. Skip unchanged documents.
6. Parse changed documents.
7. Normalize text and metadata.
8. Chunk content.
9. Generate embeddings.
10. Write document version, chunks, embeddings, and ACL snapshot.
11. Retire replaced chunks.
12. Refresh search indexes as needed.
13. Record job stats and audit events.
```

Failure behavior:

- A failed document should not fail the whole job unless the connector requires all-or-nothing behavior.
- A failed embedding write must not leave partially active chunks.
- Deleted source documents must retire searchable chunks.

## RBAC Evaluation

```text
1. Load eval dataset.
2. Create actors with allowed and denied access profiles.
3. Run retrieval for each actor and query.
4. Assert allowed documents appear when expected.
5. Assert denied documents never appear in candidates, context, answer, or citations.
6. Store pass or fail result with policy filter summary.
```

Critical checks:

- Same query across two users with different permissions.
- Same query across users with different clearance levels.
- Same query across users from different departments.
- Group membership grant.
- Role scoped to collection.
- Document-level deny overriding broader allow.
- Deleted or retired document is not retrievable.

## Prompt-Injection Evaluation

```text
1. Seed documents with malicious instructions.
2. Retrieve them through normal search.
3. Run answer workflow.
4. Verify system policy is not changed.
5. Verify secrets and inaccessible data are not revealed.
6. Verify suspicious content is handled as data.
```

## ACL Update

```text
1. Receive ACL update request.
2. Authenticate actor.
3. Authorize ACL administration on target resource.
4. Validate principal and permission.
5. Write ACL change in a transaction.
6. Update ACL hash or retrieval filter cache.
7. Audit the change.
8. Trigger reindex or cache invalidation when needed.
```

## Evaluation Release Gate

Before shipping retrieval, ingestion, RBAC, or prompt changes:

```text
1. Run unit tests.
2. Run integration tests for database and retrieval filters.
3. Run RBAC eval suite.
4. Run prompt-injection eval suite.
5. Run RAGAS quality suite.
6. Compare results with previous baseline.
7. Block release on access-control regression.
```

## Debugging Flow

```text
1. Capture correlation ID.
2. Inspect audit event.
3. Inspect retrieval run.
4. Check actor roles and groups.
5. Check policy filter summary.
6. Check candidate counts before and after filters.
7. Check selected citations.
8. Reproduce with a minimal eval case.
9. Add regression test before fixing.
```
