import pytest
from importlib import import_module

PromptScopePolicy = import_module("swe_ai_fleet.context.domain.scopes.prompt_scope_policy").PromptScopePolicy
ScopeCheckResult = import_module("swe_ai_fleet.context.domain.scopes.scope_check_result").ScopeCheckResult


class TestPromptScopePolicy:
    """Comprehensive unit tests for PromptScopePolicy class."""

    def test_init_with_valid_config(self):
        """Test initialization with valid configuration."""
        cfg = {"plan": {"dev": ["A", "B"], "qa": ["C"]}}
        policy = PromptScopePolicy(cfg)
        assert policy.cfg == cfg

    def test_init_with_empty_config(self):
        """Test initialization with empty configuration."""
        policy = PromptScopePolicy({})
        assert policy.cfg == {}

    def test_expected_scopes_with_valid_phase_and_role(self):
        """Test expected_scopes returns correct scopes for valid phase and role."""
        cfg = {"plan": {"dev": ["A", "B"], "qa": ["C"]}}
        policy = PromptScopePolicy(cfg)

        assert policy.expected_scopes("plan", "dev") == {"A", "B"}
        assert policy.expected_scopes("plan", "qa") == {"C"}

    def test_expected_scopes_with_nonexistent_phase(self):
        """Test expected_scopes returns empty set for nonexistent phase."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.expected_scopes("nonexistent", "dev")
        assert result == set()

    def test_expected_scopes_with_nonexistent_role(self):
        """Test expected_scopes returns empty set for nonexistent role."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.expected_scopes("plan", "nonexistent")
        assert result == set()

    def test_expected_scopes_with_empty_role_list(self):
        """Test expected_scopes returns empty set for role with empty scope list."""
        cfg = {"plan": {"dev": []}}
        policy = PromptScopePolicy(cfg)

        result = policy.expected_scopes("plan", "dev")
        assert result == set()

    def test_check_with_matching_scopes(self):
        """Test check returns allowed=True when scopes match exactly."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", {"A", "B"})
        assert isinstance(result, ScopeCheckResult)
        assert result.allowed is True
        assert result.missing == set()
        assert result.extra == set()

    def test_check_with_missing_scopes(self):
        """Test check returns allowed=False when scopes are missing."""
        cfg = {"plan": {"dev": ["A", "B", "C"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", {"A", "B"})
        assert result.allowed is False
        assert result.missing == {"C"}
        assert result.extra == set()

    def test_check_with_extra_scopes(self):
        """Test check returns allowed=False when extra scopes are provided."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", {"A", "B", "C", "D"})
        assert result.allowed is False
        assert result.missing == set()
        assert result.extra == {"C", "D"}

    def test_check_with_missing_and_extra_scopes(self):
        """Test check returns allowed=False when both missing and extra scopes exist."""
        cfg = {"plan": {"dev": ["A", "B", "C"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", {"A", "D", "E"})
        assert result.allowed is False
        assert result.missing == {"B", "C"}
        assert result.extra == {"D", "E"}

    def test_check_with_empty_provided_scopes(self):
        """Test check when no scopes are provided but some are expected."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", set())
        assert result.allowed is False
        assert result.missing == {"A", "B"}
        assert result.extra == set()

    def test_check_with_nonexistent_phase_and_role(self):
        """Test check with nonexistent phase and role."""
        cfg = {"plan": {"dev": ["A", "B"]}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("nonexistent", "nonexistent", {"A", "B"})
        assert result.allowed is False
        assert result.missing == set()
        assert result.extra == {"A", "B"}

    def test_check_with_empty_expected_scopes(self):
        """Test check when no scopes are expected but some are provided."""
        cfg = {"plan": {"dev": []}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", {"A", "B"})
        assert result.allowed is False
        assert result.missing == set()
        assert result.extra == {"A", "B"}

    def test_check_with_empty_expected_and_provided_scopes(self):
        """Test check when both expected and provided scopes are empty."""
        cfg = {"plan": {"dev": []}}
        policy = PromptScopePolicy(cfg)

        result = policy.check("plan", "dev", set())
        assert result.allowed is True
        assert result.missing == set()
        assert result.extra == set()

    def test_redact_password_patterns(self):
        """Test redact removes password patterns."""
        policy = PromptScopePolicy({})
        block = "password: mypassword\npassword=secret123\nPASSWORD: admin123"

        redacted = policy.redact("dev", block)

        assert "password: [REDACTED]" in redacted
        assert "password: [REDACTED]" in redacted  # The regex always uses : in replacement
        assert "PASSWORD: [REDACTED]" in redacted
        assert "mypassword" not in redacted
        assert "secret123" not in redacted
        assert "admin123" not in redacted

    def test_redact_secret_patterns(self):
        """Test redact removes secret patterns."""
        policy = PromptScopePolicy({})
        block = "secret: mysecret\nsecret=topsecret\nSECRET: confidential"

        redacted = policy.redact("dev", block)

        assert "secret: [REDACTED]" in redacted
        assert "secret: [REDACTED]" in redacted  # The regex always uses : in replacement
        assert "SECRET: [REDACTED]" in redacted
        assert "mysecret" not in redacted
        assert "topsecret" not in redacted
        assert "confidential" not in redacted

    def test_redact_token_patterns(self):
        """Test redact removes token patterns."""
        policy = PromptScopePolicy({})
        block = "token: mytoken\ntoken=apitoken\nTOKEN: accesstoken"

        redacted = policy.redact("dev", block)

        assert "token: [REDACTED]" in redacted
        assert "token: [REDACTED]" in redacted  # The regex always uses : in replacement
        assert "TOKEN: [REDACTED]" in redacted
        assert "mytoken" not in redacted
        assert "apitoken" not in redacted
        assert "accesstoken" not in redacted

    def test_redact_bearer_tokens(self):
        """Test redact removes Bearer authorization tokens."""
        policy = PromptScopePolicy({})
        block = "Authorization: Bearer abc.def123==\nBearer token123\nBEARER: jwt.token.here"

        redacted = policy.redact("dev", block)

        assert "Bearer [REDACTED]" in redacted
        # Note: The regex only matches "Bearer" and "Basic", not "BEARER"
        assert "BEARER: jwt.token.here" in redacted  # This should remain unchanged
        assert "abc.def123==" not in redacted
        assert "token123" not in redacted

    def test_redact_basic_auth(self):
        """Test redact removes Basic authorization tokens."""
        policy = PromptScopePolicy({})
        block = "Authorization: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==\nBasic dXNlcjpwYXNz"

        redacted = policy.redact("dev", block)

        assert "Basic [REDACTED]" in redacted
        assert "QWxhZGRpbjpvcGVuIHNlc2FtZQ==" not in redacted
        assert "dXNlcjpwYXNz" not in redacted

    def test_redact_preserves_non_sensitive_content(self):
        """Test redact preserves non-sensitive content."""
        policy = PromptScopePolicy({})
        block = (
            "Some normal text here.\n"
            "password: secret123\n"
            "More normal content.\n"
            "Authorization: Bearer token123\n"
            "Final normal text."
        )

        redacted = policy.redact("dev", block)

        assert "Some normal text here." in redacted
        assert "More normal content." in redacted
        assert "Final normal text." in redacted
        assert "password: [REDACTED]" in redacted
        assert "Bearer [REDACTED]" in redacted

    def test_redact_with_empty_block(self):
        """Test redact with empty string."""
        policy = PromptScopePolicy({})
        result = policy.redact("dev", "")
        assert result == ""

    def test_redact_with_no_sensitive_content(self):
        """Test redact when no sensitive content is present."""
        policy = PromptScopePolicy({})
        block = "This is just normal text with no secrets or tokens."
        result = policy.redact("dev", block)
        assert result == block

    def test_redact_role_parameter_reserved(self):
        """Test that role parameter is reserved for future use (currently unused)."""
        policy = PromptScopePolicy({})
        block = "password: secret123"
        
        # Both calls should produce the same result since role is not used yet
        result1 = policy.redact("dev", block)
        result2 = policy.redact("admin", block)
        
        assert result1 == result2
        assert "password: [REDACTED]" in result1

    def test_comprehensive_redaction_scenario(self):
        """Test comprehensive redaction with multiple sensitive patterns."""
        policy = PromptScopePolicy({})
        block = (
            "Configuration:\n"
            "  database:\n"
            "    password: db_password_123\n"
            "    secret: db_secret_key\n"
            "  api:\n"
            "    token: api_token_456\n"
            "    auth: Bearer jwt.token.here\n"
            "    basic_auth: Basic QWxhZGRpbjpvcGVuIHNlc2FtZQ==\n"
            "  normal_setting: value\n"
        )

        redacted = policy.redact("dev", block)

        # Check that sensitive data is redacted
        assert "password: [REDACTED]" in redacted
        assert "secret: [REDACTED]" in redacted
        assert "token: [REDACTED]" in redacted
        assert "Bearer [REDACTED]" in redacted
        assert "Basic [REDACTED]" in redacted

        # Check that normal content is preserved
        assert "Configuration:" in redacted
        assert "database:" in redacted
        assert "api:" in redacted
        assert "normal_setting: value" in redacted

        # Check that original sensitive values are not present
        assert "db_password_123" not in redacted
        assert "db_secret_key" not in redacted
        assert "api_token_456" not in redacted
        assert "jwt.token.here" not in redacted
        assert "QWxhZGRpbjpvcGVuIHNlc2FtZQ==" not in redacted
