"""M6 application-layer workflow package.

The `WorkflowState` dataclass is the typed contract that the
LangGraph state machine reads and writes. Every field is required
and frozen. Construction is gated by a `from_actor` factory that
rejects any partial / anonymous input. The forbidden-construction
path surfaces the `AnonymousExecutionError` typed-exception so
workflow callers (M9+) cannot start the workflow without an
authenticated actor.

Bounding decisions (locked at M6; raise an ADR to revisit):

  - State is a frozen dataclass with five required string fields:
    `user_id`, `department`, `clearance`, `role`,
    `correlation_id`. The role claim is preserved for UI behavior
    and auditing; it does not participate in authorization
    (POLICIES.md).

  - Construction via `WorkflowState(...)` is not exposed at the
    application boundary. Callers go through
    `WorkflowState.from_actor(...)` so missing fields raise
    `AnonymousExecutionError` early and consistently.

  - State objects do NOT import any framework SDK; they live in
    the application layer. The framework-specific runtime
    (`langgraph`) imports `WorkflowState` from here and adapts it
    to its own `StateGraph` channel shape via the boundary in
    `src/infrastructure/langgraph/`.

  - The package imports only standard-library types and
    intra-application / domain-side ports. No framework, no DB
    driver. This balances the AGENTS.md "domain code does not
    import from ... LangGraph" rule by keeping the
    framework-specific adapter in `src/infrastructure/langgraph/`
    (which may import langgraph).
"""
