from dataclasses import dataclass


@dataclass(frozen=True)
class ScopeCheckResult:
    allowed: bool
    missing: set[str]
    extra: set[str]
