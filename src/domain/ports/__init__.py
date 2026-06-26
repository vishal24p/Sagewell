"""
V1 ports (Protocols) and value objects that downstream code consumes.

Modules:
    clearances.py     - Clearance enum (the V1 clearance ladder).
    reason_codes.py   - Allowed reason codes emitted by audit_logs.
    users.py          - User aggregate, status/role enums, UserRepository.
    documents.py      - Document aggregate, DocumentStatus, DocumentRepository.
    chunks.py         - Chunk aggregate, ChunkStatus, ChunkRepository.
    ingestion.py      - DocumentChunkerProtocol, EmbeddingModelProtocol,
                        ChunkSegment, DocumentChunk (M7).
    audit_logs.py     - AuditEvent, AuditDecision, AuditLogRepository.
    retrieval_logs.py - RetrievalLog, RetrievalLogRepository.
    evaluation_results.py - EvaluationResult, Suite, EvaluationResultRepository.
    errors.py         - PersistenceError, ResourceNotFound.

Framework-free layer. No asyncpg. No JSON helpers. No psycopg/sqlalchemy/ORM.

The access-decision pure function lives at src/domain/access/access_decision.py.
The RBAC Access Outcome Suite under tests/rbac/ exercises that pure function.
"""
