"""ASGI middleware subpackage.

`CorrelationIdMiddleware` (M3) attaches a request-scoped
correlation id to `scope["state"]["correlation_id"]`. The
id is generated when the request did not carry an
`X-Correlation-ID` header (UUID4) or read from the header
when the caller supplies one.

`JwtAuthMiddleware` (M5) attaches the typed `AuthActor` to
`scope["state"]["actor"]` on every request whose path is
not in `PUBLIC_PATHS` and whose `Authorization` header
verified successfully. The middleware reads
`scope["app"].state.verify_jwt` at request time. With no
verify_jwt on state, the middleware is a no-op and the
launch contract remains M3-style.

Middleware ordering (Starlette convention: the LAST
`add_middleware` call wraps the INNER-most layer): auth
middleware mounts LAST and correlation middleware mounts
FIRST, so the `CorrelationIdMiddleware` is on the outer
edge and writes the correlation id BEFORE auth reads it.
"""
