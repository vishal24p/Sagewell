# Workflows

V1 runtime flows. The access decision runs at every boundary.

## Query And Answer

```text
1. Receive query.
2. Validate JWT.
3. Run regex guard on normalized query.
4. Load actor (department, clearance, role).
5. Apply access decision to derive filter.
6. Run dense retrieval with filter.
7. Run BM25 retrieval with filter.
8. RRF fuse dense and BM25 results.
9. Cross-encoder rerank fused list.
10. Re-apply access decision on reranked list (drop unauthorized).
11. Run LLM guard on normalized query and reranked chunks.
12. Generate answer with bounded context.
13. Verify citations (re-run access decision on every cited document).
14. Persist retrieval_logs, audit_logs, evaluation_results hooks.
15. Return safe answer.
```

Failure behavior:

- JWT invalid or missing -> 401.
- Regex guard blocks -> refuse, no generation.
- Access decision error -> 403, reason: POLICY_RESOLVER_ERROR.
- Retrieval empty after retry -> 503, safe error.
- LLM guard blocks -> refuse, no generation.
- Citation verification fails -> drop the citation; regenerate once;
  if still failing, refuse.
- Audit write fails -> do not return a response.

## Incremental Re-Ingestion

```text
1. Connector discovers source documents.
2. Compare content_checksum with stored value.
3. Skip unchanged documents.
4. Re-load changed documents through LlamaIndex.
5. LlamaIndex semantic chunking produces new chunks.
6. Embed chunks using the Embedding Model.
7. Write new chunks; retire replaced chunks.
8. Refresh search indexes as needed.
9. Record job outcome in audit_logs.
```

Failure behavior:

- A failed document does not fail the whole job unless the connector
  requires all-or-nothing behavior.
- A failed embedding write must not leave partially active chunks.
- Deleted source documents retire searchable chunks.

## RBAC Access Outcome Suite

This suite is independent of RAGAS.

```text
1. Load evaluation cases (allow, deny, department, clearance).
2. Build the actor for each case from the case input.
3. Run the access decision function on (actor, document).
4. Assert allow when expected.
5. Assert deny when expected.
6. Assert department boundary.
7. Assert clearance boundary.
8. Store pass or fail with reason_code.
```

Critical checks:

- Same actor across allow and deny cases with different documents.
- Same document across actors with different departments.
- Same document across actors with different clearances.
- ALL department documents are reachable from any department actor
  when clearance is satisfied.
- Restriction case: actor with lower clearance cannot access higher
  clearance documents.

## Regex Guard Evaluation

```text
1. Load regex guard pattern set.
2. Run pattern match on normalized query (before RBAC and retrieval).
3. Record verdict and matched patterns.
4. Block or constrain on high-risk verdict.
```

## LLM Guard Evaluation

```text
1. Send normalized query and retrieved chunks to Guardrail Model.
2. Capture classification and rationale.
3. Apply policy: allow, downgrade, refuse.
4. Record verdict and model identifier (capability only).
```

## RAGAS Evaluation

```text
1. Load RAGAS evaluation cases.
2. Run the answer workflow for each case.
3. Compute metrics: Faithfulness, Context Precision, Context Recall,
   Answer Relevancy.
4. Store per-case scores in evaluation_results.
5. Aggregate and compare against the prior baseline.
```

## Release Gate

Before shipping retrieval, ingestion, or guard changes:

```text
1. Run unit tests.
2. Run integration tests for the access decision.
3. Run the RBAC Access Outcome Suite.
4. Run the regex guard and LLM guard tests.
5. Run the RAGAS suite.
6. Compare results with the previous baseline.
7. Block release on RBAC regression.
```

## Debugging Flow

```text
1. Capture correlation_id.
2. Inspect audit_logs.
3. Inspect retrieval_logs.
4. Check the actor's department and clearance.
5. Check the access decision outcome and reason_code.
6. Check candidate counts (dense, bm25, fused, reranked, after access).
7. Check regex and LLM guard verdicts.
8. Check citation verification results.
9. Reproduce with a minimal evaluation_results case.
10. Add a regression test before fixing.
```