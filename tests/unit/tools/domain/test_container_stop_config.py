"""Unit tests for ContainerStopConfig value object."""

import pytest

from core.agents_and_tools.tools.domain.container_stop_config import ContainerStopConfig


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerStopConfigValidation:
    """Test fail-fast validation in ContainerStopConfig."""

    def test_rejects_empty_container(self):
        """Should reject empty container (fail-fast)."""
        with pytest.raises(ValueError, match="container is required and cannot be empty"):
            ContainerStopConfig(container="")

    def test_rejects_non_integer_timeout(self):
        """Should reject non-integer timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ContainerStopConfig(container="test", timeout="10")  # type: ignore

    def test_rejects_zero_timeout(self):
        """Should reject zero timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerStopConfig(container="test", timeout=0)

    def test_rejects_negative_timeout(self):
        """Should reject negative timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerStopConfig(container="test", timeout=-5)


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerStopConfigHappyPath:
    """Test valid ContainerStopConfig creation."""

    def test_creates_with_default_timeout(self):
        """Should create with default timeout."""
        config = ContainerStopConfig(container="webserver")

        assert config.container == "webserver"
        assert config.timeout == 10  # Default grace period

    def test_creates_with_custom_timeout(self):
        """Should create with custom timeout."""
        config = ContainerStopConfig(container="app", timeout=30)

        assert config.timeout == 30

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerStopConfig(container="test")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.timeout = 30  # type: ignore


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerStopConfigEdgeCases:
    """Test edge cases."""

    def test_accepts_very_long_timeout(self):
        """Should accept very long timeout."""
        config = ContainerStopConfig(container="test", timeout=3600)

        assert config.timeout == 3600

    def test_accepts_container_id(self):
        """Should accept container ID."""
        config = ContainerStopConfig(container="abc123def456")

        assert config.container == "abc123def456"

    def test_accepts_container_name_with_hyphens(self):
        """Should accept container name with special chars."""
        config = ContainerStopConfig(container="my-app-server")

        assert config.container == "my-app-server"

