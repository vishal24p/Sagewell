"""M10 -- Regex Guard ports.

The Regex Guard inspects the normalized query for
high-risk patterns BEFORE the M9 retrieval + citation
verification pipeline. The pattern catalog is versioned
and lives in the application layer's module; M10 ships
the canonical V1 patterns.

Ports:

  - `RegexRule`: a single compiled rule carrying a
    pattern, a stable rule id, a tier (HIGH / CRITICAL),
    and an optional example match for logs.
  - `RegexRuleCatalog`: the versioned bag of compiled
    rules. The catalog supports safe iteration +
    upgrade between versions without mutating an in-progress
    match.
  - `RegexGuardVerdict`: the typed outcome of the guard
    step. A `pass` verdict carries the rule id `none`;
    a `refusal` verdict carries the rule id that fired.

The V1 catalog is a list of rule stubs the operator
configures. New patterns land at the M10-extension
milestones. Per `POLICIES.md`:

  - Pattern-based detection on the normalized query.
  - Runs before RBAC and retrieval.
  - High-risk verdicts refuse the request.
  - The pattern set is versioned.

The rule tiers:

  - `TIER_HIGH`: refused at the workflow boundary.
  - `TIER_CRITICAL`: refused at the API boundary, BEFORE
    audit-row writes are attempted (a defense in depth
    against an attacker spamming the audit table).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Iterable, Pattern


class RegexTier(str, Enum):
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class RegexRule:
    """A single compiled rule.

    - `rule_id`: stable slug, e.g. `prompt_injection_ignore`.
    - `tier`: `RegexTier.HIGH` or `RegexTier.CRITICAL`.
    - `pattern`: the compiled regex. Compile-time only;
      rules are immutable in the catalog.
    - `negate`: when True, the rule is treated as a
      allow-list and matches trigger a `pass`-with-warning.
      Future M10-extension milestones expose this.
    - `description`: human-readable summary; may be
      persisted on the audit row.
    """

    rule_id: str
    tier: RegexTier
    pattern: Pattern[str]
    negate: bool = False
    description: str = ""


@dataclass(frozen=True)
class RegexRuleCatalog:
    """A versioned bag of compiled rules.

    - `version`: catalog version slug.
    - `rules`: tuple of compiled rules. Tuple to keep the
      catalog immutable.
    - `tier_for(rule_id)`: lookup the tier of a rule.
    """

    version: str
    rules: tuple[RegexRule, ...]

    def __post_init__(self) -> None:
        seen: set[str] = set()
        for rule in self.rules:
            if rule.rule_id in seen:
                raise ValueError(
                    f"RegexRuleCatalog version {self.version!r} carries "
                    f"duplicate rule id {rule.rule_id!r}."
                )
            seen.add(rule.rule_id)

    def tier_for(self, rule_id: str) -> RegexTier:
        for rule in self.rules:
            if rule.rule_id == rule_id:
                return rule.tier
        raise KeyError(f"No rule with id {rule_id!r} in catalog version {self.version!r}.")


@dataclass(frozen=True)
class RegexGuardVerdict:
    """The typed outcome of the RegexGuard step.

    - `allowed`: True iff the query did not match any
      refuse-tier rule.
    - `rule_id`: when `allowed=False`, the stable rule id
      that fired. When `allowed=True`, the literal `none`.
    - `tier`: the tier of the rule that fired
      (HIGH / CRITICAL); `None` when `allowed=True`.
    - `description`: human-readable summary; `None`
      when `allowed=True`.
    """

    allowed: bool
    rule_id: str
    tier: Optional[RegexTier] = None
    description: Optional[str] = None

    @classmethod
    def pass_(cls) -> "RegexGuardVerdict":
        return cls(allowed=True, rule_id="none")

    @classmethod
    def refuse(
        cls,
        rule: RegexRule,
    ) -> "RegexGuardVerdict":
        return cls(
            allowed=False,
            rule_id=rule.rule_id,
            tier=rule.tier,
            description=rule.description,
        )


def default_v1_catalog() -> RegexRuleCatalog:
    """The V1 default Regex Guard catalog.

    Patterns are compiled at module-import time. The set
    covers the four POLICIES.md risk signals plus the
    canonical prompt-injection idioms.
    """
    rules = (
        RegexRule(
            rule_id="prompt_injection_ignore",
            tier=RegexTier.HIGH,
            pattern=re.compile(
                r"\b(?:ignore|disregard|skip|forget)\b"
                r"(?:[^.\n]{0,40})\b(?:previous|prior|earlier|all|system)\b"
                r"(?:[^.\n]{0,40})\b(?:instructions?|prompts?|rules?)\b",
                re.IGNORECASE | re.MULTILINE,
            ),
            description="Request to ignore or skip prior instructions.",
        ),
        RegexRule(
            rule_id="system_prompt_reveal",
            tier=RegexTier.HIGH,
            pattern=re.compile(
                r"\b(?:reveal|show|dump|leak|disclose|expose)\b"
                r"(?:[^.\n]{0,30})\b"
                r"(?:system\s*prompt|hidden\s*instructions?|developer\s*message|"
                r"internal\s*policy|secrets?|credentials?)\b",
                re.IGNORECASE,
            ),
            description="Request to reveal system prompt or secrets.",
        ),
        RegexRule(
            rule_id="instruction_override_authority",
            tier=RegexTier.CRITICAL,
            pattern=re.compile(
                r"\b(?:override|bypass|circumvent|disable|rewrite)\b"
                r"(?:[^.\n]{0,30})\b"
                r"(?:authorization|access|rbac|policy|audit|logging|guard)\b",
                re.IGNORECASE,
            ),
            description="Request to bypass authorization or audit policy.",
        ),
        RegexRule(
            rule_id="document_authority_claim",
            tier=RegexTier.HIGH,
            pattern=re.compile(
                r"\b(?:the|a)\s+(?:document|file|attachment|chunk)\s+"
                r"(?:says|authorizes|orders|commands|requires)\b"
                r"(?:[^.\n]{0,40})\b(?:to|you\s+to|the\s+system\s+to)\b",
                re.IGNORECASE,
            ),
            description="Claim that a document authorizes a system action.",
        ),
        RegexRule(
            rule_id="obfuscated_payload",
            tier=RegexTier.HIGH,
            pattern=re.compile(
                r"(?:[A-Za-z0-9+/]{40,}\s*=\s*=|"
                r"\b(?:base64|hex|rot13)\b\s*:\s*[A-Za-z0-9]{40,}|"
                r"\\x[0-9a-fA-F]{2}(?:\\x[0-9a-fA-F]{2}){8,})",
                re.IGNORECASE,
            ),
            description="Encoded / obfuscated payload detected.",
        ),
    )
    return RegexRuleCatalog(version="v1", rules=rules)


__all__ = [
    "RegexRule",
    "RegexRuleCatalog",
    "RegexGuardVerdict",
    "RegexTier",
    "default_v1_catalog",
]
