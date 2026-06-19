# Glossary

## Access Decision

The pure function in Sagewell V1 that takes an actor and a document
and returns `(allowed, reason)` based on department and clearance
only.

## Actor

The authenticated principal (user or service) whose department and
clearance are loaded from the JWT.

## Chunk

A searchable segment of a document, produced by LlamaIndex semantic
chunking, with text, metadata, and embedding.

## Citation

A reference from an answer to a chunk. Every citation is verified by
re-running the access decision on the cited document.

## Clearance

One of PUBLIC, INTERNAL, CONFIDENTIAL, RESTRICTED. A user must have
clearance greater than or equal to a document's required clearance.

## Cross-Encoder Reranker

The fourth stage of the V1 retrieval pipeline. The Reranker Model
reranks the RRF-fused list using query-document cross-attention.

## Department

A string field on users and documents. The user department must
match the document department, unless the document department is ALL.

## Dense Retrieval

The first stage of the V1 retrieval pipeline. Vector similarity
search using the Embedding Model and `pgvector`.

## BM25 Retrieval

The second stage of the V1 retrieval pipeline. Lexical search using
`pg_search`.

## Hybrid Retrieval

The mandatory V1 retrieval pipeline: dense retrieval, BM25 retrieval,
RRF fusion, cross-encoder reranking.

## RRF Fusion

Reciprocal Rank Fusion. The third stage of the V1 retrieval pipeline.
Merges the dense and BM25 ranked lists.

## JWT

JSON Web Token. The V1 authentication mechanism. Required claims
include subject, department, clearance, and expiration.

## LangGraph

The V1 workflow orchestration library. Responsible for workflow
orchestration, state management, and node execution. Not responsible
for authorization, retrieval, database access, or business logic.

## LlamaIndex

The V1 library for document loading, semantic chunking, ingestion,
and retrieval abstractions. Not responsible for authorization,
workflow orchestration, or business rules.

## RAGAS

The V1 quality evaluation system. Required metrics are Faithfulness,
Context Precision, Context Recall, and Answer Relevancy.

## RBAC Access Outcome Suite

The V1 access evaluation system. Required tests are Allow, Deny,
Department, and Clearance. Independent of RAGAS.

## Regex Guard

Pattern-based prompt protection that runs on the primary request
path. Refuses or constrains the request on high-risk verdict.

## LLM Guard

The Guardrail Model classifies the normalized query and retrieved
chunks. Refuses, downgrades, or constrains on high-risk verdict.

## Single Tenant

A single company in a single deployment. Does not remove the need
for per-user authorization.