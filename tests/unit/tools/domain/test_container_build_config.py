"""Unit tests for ContainerBuildConfig value object."""

from pathlib import Path

import pytest
from core.agents_and_tools.tools.domain.container_build_config import ContainerBuildConfig

# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerBuildConfigValidation:
    """Test fail-fast validation in ContainerBuildConfig."""

    def test_rejects_empty_context_path(self):
        """Should reject empty context_path (fail-fast)."""
        with pytest.raises(ValueError, match="context_path is required"):
            ContainerBuildConfig(context_path="")

    def test_rejects_empty_dockerfile(self):
        """Should reject empty dockerfile (fail-fast)."""
        with pytest.raises(ValueError, match="dockerfile is required and cannot be empty"):
            ContainerBuildConfig(context_path=".", dockerfile="")

    def test_rejects_non_integer_timeout(self):
        """Should reject non-integer timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ContainerBuildConfig(context_path=".", timeout="600")  # type: ignore

    def test_rejects_zero_timeout(self):
        """Should reject zero timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerBuildConfig(context_path=".", timeout=0)

    def test_rejects_negative_timeout(self):
        """Should reject negative timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerBuildConfig(context_path=".", timeout=-100)

    def test_rejects_non_dict_build_args(self):
        """Should reject non-dict build_args (fail-fast)."""
        with pytest.raises(ValueError, match="build_args must be a dictionary or None"):
            ContainerBuildConfig(context_path=".", build_args="invalid")  # type: ignore

    def test_rejects_non_boolean_no_cache(self):
        """Should reject non-boolean no_cache (fail-fast)."""
        with pytest.raises(ValueError, match="no_cache must be a boolean"):
            ContainerBuildConfig(context_path=".", no_cache="true")  # type: ignore


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerBuildConfigHappyPath:
    """Test valid ContainerBuildConfig creation."""

    def test_creates_with_defaults(self):
        """Should create with default values."""
        config = ContainerBuildConfig(context_path=".")

        assert config.context_path == "."
        assert config.dockerfile == "Dockerfile"
        assert config.tag is None
        assert config.build_args is None
        assert config.no_cache is False
        assert config.timeout == 600

    def test_creates_with_path_object(self):
        """Should accept Path object for context_path."""
        config = ContainerBuildConfig(context_path=Path("/app"))

        assert config.context_path == Path("/app")

    def test_creates_with_tag(self):
        """Should create with tag."""
        config = ContainerBuildConfig(context_path=".", tag="myapp:v1.0")

        assert config.tag == "myapp:v1.0"
        assert config.has_tag() is True

    def test_creates_with_build_args(self):
        """Should create with build arguments."""
        config = ContainerBuildConfig(
            context_path=".",
            build_args={"VERSION": "1.0", "ENV": "production"},
        )

        assert config.build_args == {"VERSION": "1.0", "ENV": "production"}
        assert config.has_build_args() is True

    def test_creates_with_no_cache(self):
        """Should create with no_cache=True."""
        config = ContainerBuildConfig(context_path=".", no_cache=True)

        assert config.no_cache is True
        assert config.is_cache_disabled() is True

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerBuildConfig(context_path=".")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.tag = "test:latest"  # type: ignore


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestContainerBuildConfigBusinessLogic:
    """Test business methods."""

    def test_has_tag_returns_true_when_tag_set(self):
        """Should return True when tag is set."""
        config = ContainerBuildConfig(context_path=".", tag="app:v1")

        assert config.has_tag() is True

    def test_has_tag_returns_false_when_tag_none(self):
        """Should return False when tag is None."""
        config = ContainerBuildConfig(context_path=".")

        assert config.has_tag() is False

    def test_has_tag_returns_false_when_tag_empty_string(self):
        """Should return False when tag is empty string."""
        config = ContainerBuildConfig(context_path=".", tag="")

        assert config.has_tag() is False

    def test_has_build_args_returns_true_when_set(self):
        """Should return True when build_args is set."""
        config = ContainerBuildConfig(context_path=".", build_args={"VAR": "value"})

        assert config.has_build_args() is True

    def test_has_build_args_returns_false_when_none(self):
        """Should return False when build_args is None."""
        config = ContainerBuildConfig(context_path=".")

        assert config.has_build_args() is False

    def test_has_build_args_returns_false_when_empty_dict(self):
        """Should return False when build_args is empty dict."""
        config = ContainerBuildConfig(context_path=".", build_args={})

        assert config.has_build_args() is False

    def test_get_context_str_returns_string(self):
        """Should return context path as string."""
        config = ContainerBuildConfig(context_path=Path("/app"))

        assert config.get_context_str() == "/app"

    def test_get_context_str_with_string_input(self):
        """Should return context path as string when input is string."""
        config = ContainerBuildConfig(context_path=".")

        assert config.get_context_str() == "."

    def test_is_cache_disabled_returns_true_when_no_cache(self):
        """Should return True when no_cache is True."""
        config = ContainerBuildConfig(context_path=".", no_cache=True)

        assert config.is_cache_disabled() is True

    def test_is_cache_disabled_returns_false_when_cache_enabled(self):
        """Should return False when no_cache is False."""
        config = ContainerBuildConfig(context_path=".", no_cache=False)

        assert config.is_cache_disabled() is False


# =============================================================================
# Factory Method Tests
# =============================================================================

class TestContainerBuildConfigFactoryMethods:
    """Test factory methods."""

    def test_simple_factory_creates_minimal_config(self):
        """Should create simple config with defaults."""
        config = ContainerBuildConfig.simple(context_path="/app")

        assert config.context_path == "/app"
        assert config.dockerfile == "Dockerfile"
        assert config.tag is None
        assert config.no_cache is False

    def test_simple_factory_uses_dot_by_default(self):
        """Should use '.' as default context."""
        config = ContainerBuildConfig.simple()

        assert config.context_path == "."


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerBuildConfigEdgeCases:
    """Test edge cases."""

    def test_accepts_absolute_context_path(self):
        """Should accept absolute paths."""
        config = ContainerBuildConfig(context_path="/absolute/path")

        assert config.context_path == "/absolute/path"

    def test_accepts_relative_context_path(self):
        """Should accept relative paths."""
        config = ContainerBuildConfig(context_path="./app")

        assert config.context_path == "./app"

    def test_accepts_custom_dockerfile_name(self):
        """Should accept custom Dockerfile name."""
        config = ContainerBuildConfig(
            context_path=".",
            dockerfile="Dockerfile.prod",
        )

        assert config.dockerfile == "Dockerfile.prod"

    def test_accepts_very_long_timeout(self):
        """Should accept very long timeout."""
        config = ContainerBuildConfig(context_path=".", timeout=3600)

        assert config.timeout == 3600

    def test_accepts_multiple_build_args(self):
        """Should accept multiple build arguments."""
        config = ContainerBuildConfig(
            context_path=".",
            build_args={
                "VERSION": "1.0",
                "BUILD_DATE": "2025-11-01",
                "COMMIT_SHA": "abc123",
            },
        )

        assert len(config.build_args) == 3
        assert config.build_args["VERSION"] == "1.0"

