"""M10 -- Regex Guard application orchestrator.

The `RegexGuard` use case runs BEFORE the M9 retrieval +
citation-verification pipeline. The guard inspects the
normalized query against the versioned rule catalog and
returns a typed `RegexGuardVerdict`.

Per `POLICIES.md` and `WORKFLOWS.md` ordering:

  JWT -> Regex Guard -> RBAC Authorization -> Retrieval
      -> LLM Guard -> Generation

The M9 orchestrator (`/v1/query`) gains a regex-guard
node upstream of the `ingest_query` step; the guard's
verdict is recorded on the workflow channel and forwarded
to the API layer.

API contract:
  - `pass_` verdict -> continue with the M9 pipeline.
  - `refusal` verdict -> 400-class response. The audit
    row carries the typed reason code (one of
    `regex_refused_high`, `regex_refused_critical`)
    added at the M10 milestone.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

from src.domain.ports.regex_guard import (
    RegexGuardVerdict,
    RegexRule,
    RegexRuleCatalog,
    RegexTier,
    default_v1_catalog,
)


__all__ = [
    "RegexGuard",
    "RegexGuardCommand",
    "RegexGuardResult",
]


@dataclass(frozen=True)
class RegexGuardCommand:
    """Typed command for the RegexGuard step."""

    query: str
    catalog: Optional[RegexRuleCatalog] = None


@dataclass(frozen=True)
class RegexGuardResult:
    """Typed result carrying the verdict + canonical reason codes."""

    verdict: RegexGuardVerdict
    reason_code: str
    catalog_version: str


# Reason codes the M10 guard introduces. The repository-side
# allowed-codes predicate widens to include these at the M10
# entrypoint.
REASON_REGEX_REFUSED_HIGH = "regex_refused_high"
REASON_REGEX_REFUSED_CRITICAL = "regex_refused_critical"
REASON_REGEX_PASSED = "regex_passed"


class RegexGuard:
    """M10 Regex Guard use case.

    Constructor dependencies:
      `default_catalog`: optional pre-built catalog. Default
        is the V1 pattern set (`default_v1_catalog()`).

    `execute(command)` runs against the supplied catalog
    (or the default V1 catalog). The guard is pure: it
    does not write audit rows; the workflow boundary
    records the reason_code through M4's `RecordAuditEvent`.
    """

    def __init__(
        self,
        *,
        default_catalog: Optional[RegexRuleCatalog] = None,
    ) -> None:
        self._default_catalog = default_catalog or default_v1_catalog()

    def execute(self, command: RegexGuardCommand) -> RegexGuardResult:
        catalog = command.catalog or self._default_catalog
        if not command.query or not command.query.strip():
            # An empty query is a 400-class error at the route boundary;
            # the guard returns a `refusal` with a sentinel rule id so
            # the workflow can translate it deterministically.
            sentinel = RegexRule(
                rule_id="blank_query",
                tier=RegexTier.HIGH,
                pattern=__import__("re").compile(r".*"),
                description="Empty or blank query.",
            )
            verdict = RegexGuardVerdict.refuse(sentinel)
            return RegexGuardResult(
                verdict=verdict,
                reason_code=REASON_REGEX_REFUSED_HIGH,
                catalog_version=catalog.version,
            )
        return self._evaluate(command.query.strip(), catalog)

    def _evaluate(
        self,
        query: str,
        catalog: RegexRuleCatalog,
    ) -> RegexGuardResult:
        # CRITICAL tier rules are evaluated first so a critical
        # match wins over a high-tier rule.
        ordered = sorted(
            catalog.rules,
            key=lambda rule: 0 if rule.tier is RegexTier.CRITICAL else 1,
        )
        for rule in ordered:
            if rule.pattern.search(query):
                verdict = RegexGuardVerdict.refuse(rule)
                reason_code = (
                    REASON_REGEX_REFUSED_CRITICAL
                    if rule.tier is RegexTier.CRITICAL
                    else REASON_REGEX_REFUSED_HIGH
                )
                return RegexGuardResult(
                    verdict=verdict,
                    reason_code=reason_code,
                    catalog_version=catalog.version,
                )
        return RegexGuardResult(
            verdict=RegexGuardVerdict.pass_(),
            reason_code=REASON_REGEX_PASSED,
            catalog_version=catalog.version,
        )
