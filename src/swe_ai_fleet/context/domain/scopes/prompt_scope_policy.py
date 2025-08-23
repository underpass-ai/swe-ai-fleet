import re

from swe_ai_fleet.context.domain.scopes.scope_check_result import (
    ScopeCheckResult,
)


class PromptScopePolicy:
    """
    Enforces role/phase scopes. Use together
    with SessionRehydrationUseCase packs.
    """

    def __init__(self, scopes_cfg: dict[str, dict[str, list[str]]]) -> None:
        self.cfg = scopes_cfg  # phases -> role -> [scopes]

    def expected_scopes(self, phase: str, role: str) -> set[str]:
        return set(self.cfg.get(phase, {}).get(role, []))

    def check(
        self,
        phase: str,
        role: str,
        provided_scopes: set[str],
    ) -> ScopeCheckResult:
        expected = self.expected_scopes(phase, role)
        missing = expected - provided_scopes
        extra = provided_scopes - expected
        return ScopeCheckResult(allowed=(not missing and not extra), missing=missing, extra=extra)

    def redact(self, role: str, block: str) -> str:
        # Keep it simple; extend with allowlist/denylist rules per role.
        # Remove secrets and tokens patterns, endpoints with creds, etc.
        _ = role  # reserved for future role-specific redaction rules
        block = re.sub(
            r"(?i)(password|secret|token)\s*[:=]\s*\S+",
            r"\1: [REDACTED]",
            block,
        )
        block = re.sub(
            r"(?i)(Bearer|Basic)\s+[A-Za-z0-9\._\-]+=*",
            r"\1 [REDACTED]",
            block,
        )
        return block
