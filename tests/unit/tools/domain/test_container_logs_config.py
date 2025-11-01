"""Unit tests for ContainerLogsConfig value object."""

import pytest

from core.agents_and_tools.tools.domain.container_logs_config import ContainerLogsConfig


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerLogsConfigValidation:
    """Test fail-fast validation in ContainerLogsConfig."""

    def test_rejects_empty_container(self):
        """Should reject empty container (fail-fast)."""
        with pytest.raises(ValueError, match="container is required and cannot be empty"):
            ContainerLogsConfig(container="")

    def test_rejects_non_integer_tail(self):
        """Should reject non-integer tail (fail-fast)."""
        with pytest.raises(ValueError, match="tail must be an integer or None"):
            ContainerLogsConfig(container="test", tail="10")  # type: ignore

    def test_rejects_zero_tail(self):
        """Should reject zero tail (fail-fast)."""
        with pytest.raises(ValueError, match="tail must be positive"):
            ContainerLogsConfig(container="test", tail=0)

    def test_rejects_negative_tail(self):
        """Should reject negative tail (fail-fast)."""
        with pytest.raises(ValueError, match="tail must be positive"):
            ContainerLogsConfig(container="test", tail=-10)

    def test_rejects_non_boolean_follow(self):
        """Should reject non-boolean follow (fail-fast)."""
        with pytest.raises(ValueError, match="follow must be a boolean"):
            ContainerLogsConfig(container="test", follow="yes")  # type: ignore

    def test_rejects_non_integer_timeout(self):
        """Should reject non-integer timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ContainerLogsConfig(container="test", timeout=60.5)  # type: ignore

    def test_rejects_zero_timeout(self):
        """Should reject zero timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerLogsConfig(container="test", timeout=0)

    def test_rejects_negative_timeout(self):
        """Should reject negative timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerLogsConfig(container="test", timeout=-30)


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerLogsConfigHappyPath:
    """Test valid ContainerLogsConfig creation."""

    def test_creates_with_defaults(self):
        """Should create with default values."""
        config = ContainerLogsConfig(container="webserver")

        assert config.container == "webserver"
        assert config.tail is None
        assert config.follow is False
        assert config.timeout == 60

    def test_creates_with_tail_limit(self):
        """Should create with tail limit."""
        config = ContainerLogsConfig(container="app", tail=100)

        assert config.tail == 100
        assert config.has_tail_limit() is True

    def test_creates_with_follow_mode(self):
        """Should create with follow mode."""
        config = ContainerLogsConfig(container="app", follow=True)

        assert config.follow is True
        assert config.is_following() is True

    def test_creates_with_custom_timeout(self):
        """Should create with custom timeout."""
        config = ContainerLogsConfig(container="app", timeout=300)

        assert config.timeout == 300

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerLogsConfig(container="test")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.timeout = 120  # type: ignore


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestContainerLogsConfigBusinessLogic:
    """Test business methods."""

    def test_has_tail_limit_returns_true_when_set(self):
        """Should return True when tail is set."""
        config = ContainerLogsConfig(container="test", tail=50)

        assert config.has_tail_limit() is True

    def test_has_tail_limit_returns_false_when_none(self):
        """Should return False when tail is None."""
        config = ContainerLogsConfig(container="test")

        assert config.has_tail_limit() is False

    def test_is_following_returns_true_when_follow(self):
        """Should return True when follow is True."""
        config = ContainerLogsConfig(container="test", follow=True)

        assert config.is_following() is True

    def test_is_following_returns_false_when_not_follow(self):
        """Should return False when follow is False."""
        config = ContainerLogsConfig(container="test", follow=False)

        assert config.is_following() is False


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerLogsConfigEdgeCases:
    """Test edge cases."""

    def test_accepts_tail_one(self):
        """Should accept tail=1."""
        config = ContainerLogsConfig(container="test", tail=1)

        assert config.tail == 1

    def test_accepts_very_large_tail(self):
        """Should accept very large tail value."""
        config = ContainerLogsConfig(container="test", tail=1000000)

        assert config.tail == 1000000

    def test_follow_with_extended_timeout(self):
        """Should work with follow and long timeout."""
        config = ContainerLogsConfig(
            container="test",
            follow=True,
            timeout=3600,
        )

        assert config.is_following() is True
        assert config.timeout == 3600

