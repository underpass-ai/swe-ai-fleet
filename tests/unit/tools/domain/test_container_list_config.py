"""Unit tests for ContainerListConfig value object."""

import pytest
from core.agents_and_tools.tools.domain.container_list_config import ContainerListConfig

# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerListConfigValidation:
    """Test fail-fast validation in ContainerListConfig."""

    def test_rejects_non_boolean_all_containers(self):
        """Should reject non-boolean all_containers (fail-fast)."""
        with pytest.raises(ValueError, match="all_containers must be a boolean"):
            ContainerListConfig(all_containers="yes")  # type: ignore


# =============================================================================
# Happy Path Tests
# =============================================================================

class TestContainerListConfigHappyPath:
    """Test valid ContainerListConfig creation."""

    def test_creates_with_defaults(self):
        """Should create with default values."""
        config = ContainerListConfig()

        assert config.all_containers is False

    def test_creates_with_all_containers_true(self):
        """Should create with all_containers=True."""
        config = ContainerListConfig(all_containers=True)

        assert config.all_containers is True
        assert config.should_list_all() is True

    def test_creates_running_only(self):
        """Should create config for running containers only."""
        config = ContainerListConfig(all_containers=False)

        assert config.all_containers is False

    def test_is_immutable(self):
        """Should be immutable (frozen dataclass)."""
        config = ContainerListConfig()

        with pytest.raises(Exception):  # FrozenInstanceError
            config.all_containers = True  # type: ignore


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestContainerListConfigBusinessLogic:
    """Test business methods."""

    def test_should_list_all_returns_true_when_all_containers_true(self):
        """Should return True when all_containers is True."""
        config = ContainerListConfig(all_containers=True)

        assert config.should_list_all() is True

    def test_should_list_all_returns_false_when_all_containers_false(self):
        """Should return False when all_containers is False."""
        config = ContainerListConfig(all_containers=False)

        assert config.should_list_all() is False


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestContainerListConfigEdgeCases:
    """Test edge cases."""

    def test_defaults_for_running_containers_only(self):
        """Should default to running containers only."""
        config = ContainerListConfig()

        assert config.all_containers is False
        assert config.should_list_all() is False
    
    def test_factory_running_only(self):
        """Should create config for running containers only."""
        config = ContainerListConfig.running_only()

        assert config.all_containers is False
    
    def test_factory_all(self):
        """Should create config for all containers."""
        config = ContainerListConfig.all()

        assert config.all_containers is True

