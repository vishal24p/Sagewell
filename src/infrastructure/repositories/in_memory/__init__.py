"""
In-memory reference implementations of the repository ports.

These are reference implementations for parity tests only. They
must NOT be used in production code paths. The Postgres adapter
under src/infrastructure/repositories/postgres/ is the production
implementation.

Single-process, single-event-loop semantics. No asyncio.Lock is
added because pytest is single-process; if this implementation
ever needs to be made concurrent-safe, locks live here.
"""
