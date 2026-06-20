"""Sagewell V1 application layer.

Use cases, transaction boundaries, and audit event emission.
Imports from `src/domain/ports/` only.

Importing this package does NOT pull any DB driver. The audit
intake use case accepts an `AuditLogRepository` Protocol as a
dependency and the use-case test path does not require asyncpg.

This package MUST NOT import from `src/api/`,
`src/infrastructure/`, or any framework SDK. Concrete adapters
(in-memory, Postgres) are passed in by the test/factory caller.

See ARCHITECTURE.md for the import direction:

    api <- application <- domain
    infrastructure -> application/domain interfaces
"""
