from importlib import import_module

PromptScopePolicy = import_module("swe_ai_fleet.context.domain.scopes.prompt_scope_policy").PromptScopePolicy
ScopeCheckResult = import_module("swe_ai_fleet.context.domain.scopes.scope_check_result").ScopeCheckResult


def test_expected_scopes_and_check_allows_when_scopes_match():
    cfg = {"plan": {"dev": ["A", "B"], "qa": ["C"]}}
    policy = PromptScopePolicy(cfg)

    assert policy.expected_scopes("plan", "dev") == {"A", "B"}

    result = policy.check("plan", "dev", {"A", "B"})
    assert isinstance(result, ScopeCheckResult)
    assert result.allowed is True
    assert result.missing == set()
    assert result.extra == set()


def test_check_flags_missing_and_extra_scopes():
    cfg = {"plan": {"dev": ["A", "B"]}}
    policy = PromptScopePolicy(cfg)

    result = policy.check("plan", "dev", {"A", "C", "D"})
    assert result.allowed is False
    assert result.missing == {"B"}
    assert result.extra == {"C", "D"}


def test_redact_removes_common_secrets_and_auth_tokens():
    policy = PromptScopePolicy({})
    block = (
        "Some context before.\n"
        "password: p@ssw0rd\n"
        "secret = topsecret\n"
        "api_token=abc.def==\n"
        "Authorization: Bearer abc.def123==\n"
        "Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==\n"
        "hello world\n"
    )

    redacted = policy.redact("dev", block)

    assert "password: [REDACTED]" in redacted
    assert "secret: [REDACTED]" in redacted
    # "api_token" should still be normalized by the pattern that targets "token"
    assert "token: [REDACTED]" in redacted
    assert "Bearer [REDACTED]" in redacted
    assert "Basic [REDACTED]" in redacted
    # Non-sensitive content remains
    assert "hello world" in redacted
