"""Sagewell V1 API skeleton (M3).

The package exposes a single `create_app()` factory. The SKU
surface in M3 is intentionally tiny:

    GET /health
    GET /openapi.json
    GET /docs
    GET /redoc

Every layer below is allowed to grow into a future milestone
(M4 audit, M5 JWT, M6 LangGraph, M8 retrieval) without the
package's public surface changing.

`src/api/` MUST NOT import from `src/domain/`, `src/infrastructure/`,
or any DB driver. This guardrail enforces the layered-boundary
architecture review recommendation R-M3r-1.
"""
