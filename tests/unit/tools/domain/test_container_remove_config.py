"""Unit tests for ContainerRemoveConfig value object."""

import pytest
from core.agents_and_tools.tools.domain.container_remove_config import ContainerRemoveConfig

# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerRemoveConfigValidation:
    """Test fail-fast validation in ContainerRemoveConfig."""

    def test_rejects_empty_container(self):
        """Should reject empty container (fail-fast)."""
        with pytest.raises(ValueError, match="container is required and cannot be empty"):
            ContainerRemoveConfig(container="")

    def test_rejects_non_boolean_force(self):
        """Should reject non-boolean force (fail-fast)."""
        with pytest.raises(ValueError, match="force must be a boolean"):
            ContainerRemoveConfig(container="test", force="yes")  # type: ignore

    def test_rejects_non_boolean_remove_volumes(self):
        """Should reject non-boolean remove_volumes (fail-fast)."""
        with pytest.raises(ValueError, match="remove_volumes must be a boolean"):
            ContainerRemoveConfig(container="test", remove_volumes=1)  # type: ignore


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerRemoveConfigHappyPath:
    """Test valid ContainerRemoveConfig creation."""

    def test_creates_with_defaults(self):
        """Should create with default values."""
        config = ContainerRemoveConfig(container="test")

        assert config.container == "test"
        assert config.force is False
        assert config.remove_volumes is False

    def test_creates_with_force(self):
        """Should create with force=True."""
        config = ContainerRemoveConfig(container="test", force=True)

        assert config.force is True

    def test_creates_with_remove_volumes(self):
        """Should create with remove_volumes=True."""
        config = ContainerRemoveConfig(container="test", remove_volumes=True)

        assert config.remove_volumes is True

    def test_creates_with_all_options(self):
        """Should create with all options."""
        config = ContainerRemoveConfig(
            container="test",
            force=True,
            remove_volumes=True,
        )

        assert config.force is True
        assert config.remove_volumes is True

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerRemoveConfig(container="test")

        with pytest.raises(Exception):  # FrozenInstanceError
            config.force = True  # type: ignore


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerRemoveConfigEdgeCases:
    """Test edge cases."""

    def test_accepts_container_id(self):
        """Should accept container ID."""
        config = ContainerRemoveConfig(container="abc123def456")

        assert config.container == "abc123def456"

    def test_accepts_container_name(self):
        """Should accept container name."""
        config = ContainerRemoveConfig(container="my-webserver")

        assert config.container == "my-webserver"

