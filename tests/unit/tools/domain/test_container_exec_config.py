"""Unit tests for ContainerExecConfig value object."""

import pytest

from core.agents_and_tools.tools.domain.container_exec_config import ContainerExecConfig


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerExecConfigValidation:
    """Test fail-fast validation in ContainerExecConfig."""

    def test_rejects_empty_container(self):
        """Should reject empty container (fail-fast)."""
        with pytest.raises(ValueError, match="container is required and cannot be empty"):
            ContainerExecConfig(container="", command=["ls"])

    def test_rejects_empty_command(self):
        """Should reject empty command (fail-fast)."""
        with pytest.raises(ValueError, match="command is required and must be a non-empty list"):
            ContainerExecConfig(container="test", command=[])

    def test_rejects_non_list_command(self):
        """Should reject non-list command (fail-fast)."""
        with pytest.raises(ValueError, match="command is required and must be a non-empty list"):
            ContainerExecConfig(container="test", command="ls -la")  # type: ignore

    def test_rejects_none_command(self):
        """Should reject None command (fail-fast)."""
        with pytest.raises(ValueError, match="command is required and must be a non-empty list"):
            ContainerExecConfig(container="test", command=None)  # type: ignore

    def test_rejects_non_integer_timeout(self):
        """Should reject non-integer timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be an integer"):
            ContainerExecConfig(container="test", command=["ls"], timeout="60")  # type: ignore

    def test_rejects_zero_timeout(self):
        """Should reject zero timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerExecConfig(container="test", command=["ls"], timeout=0)

    def test_rejects_negative_timeout(self):
        """Should reject negative timeout (fail-fast)."""
        with pytest.raises(ValueError, match="timeout must be positive"):
            ContainerExecConfig(container="test", command=["ls"], timeout=-5)


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerExecConfigHappyPath:
    """Test valid ContainerExecConfig creation."""

    def test_creates_with_minimal_params(self):
        """Should create with container and command only."""
        config = ContainerExecConfig(
            container="webserver",
            command=["ls", "-la"],
        )

        assert config.container == "webserver"
        assert config.command == ["ls", "-la"]
        assert config.timeout == 60  # Default

    def test_creates_with_custom_timeout(self):
        """Should create with custom timeout."""
        config = ContainerExecConfig(
            container="app",
            command=["sleep", "10"],
            timeout=120,
        )

        assert config.timeout == 120

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerExecConfig(container="test", command=["ls"])

        with pytest.raises(Exception):  # FrozenInstanceError
            config.timeout = 30  # type: ignore


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerExecConfigEdgeCases:
    """Test edge cases."""

    def test_accepts_single_word_command(self):
        """Should accept command with single word."""
        config = ContainerExecConfig(
            container="test",
            command=["pwd"],
        )

        assert config.command == ["pwd"]

    def test_accepts_long_command(self):
        """Should accept command with many arguments."""
        config = ContainerExecConfig(
            container="test",
            command=["bash", "-c", "echo 'hello' && sleep 5"],
        )

        assert len(config.command) == 3

    def test_accepts_very_long_timeout(self):
        """Should accept very long timeout."""
        config = ContainerExecConfig(
            container="test",
            command=["long-process"],
            timeout=3600,
        )

        assert config.timeout == 3600

