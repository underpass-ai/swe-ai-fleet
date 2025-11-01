"""Unit tests for ContainerRuntime value object."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.tools.domain.container_runtime import ContainerRuntime


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestContainerRuntimeConstructorValidation:
    """Test constructor fail-fast validation."""

    def test_rejects_invalid_runtime_type(self):
        """Should raise ValueError for invalid runtime type."""
        with pytest.raises(ValueError, match="runtime_type must be one of"):
            ContainerRuntime(runtime_type="kubernetes")  # Invalid type

    def test_accepts_docker(self):
        """Should accept 'docker' as valid runtime type."""
        runtime = ContainerRuntime(runtime_type="docker")
        assert runtime.runtime_type == "docker"

    def test_accepts_podman(self):
        """Should accept 'podman' as valid runtime type."""
        runtime = ContainerRuntime(runtime_type="podman")
        assert runtime.runtime_type == "podman"

    def test_accepts_auto(self):
        """Should accept 'auto' as valid runtime type."""
        runtime = ContainerRuntime(runtime_type="auto")
        assert runtime.runtime_type == "auto"


# =============================================================================
# Immutability Tests
# =============================================================================

class TestContainerRuntimeImmutability:
    """Test that ContainerRuntime is immutable (frozen=True)."""

    def test_cannot_modify_runtime_type(self):
        """Should prevent modification of runtime_type field."""
        runtime = ContainerRuntime(runtime_type="docker")

        with pytest.raises(Exception):  # FrozenInstanceError
            runtime.runtime_type = "podman"


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestContainerRuntimeBusinessLogic:
    """Test domain logic methods."""

    def test_is_auto_returns_true_for_auto(self):
        """Should return True when runtime is 'auto'."""
        runtime = ContainerRuntime(runtime_type="auto")
        assert runtime.is_auto() is True
        assert runtime.is_docker() is False
        assert runtime.is_podman() is False

    def test_is_docker_returns_true_for_docker(self):
        """Should return True when runtime is 'docker'."""
        runtime = ContainerRuntime(runtime_type="docker")
        assert runtime.is_docker() is True
        assert runtime.is_auto() is False
        assert runtime.is_podman() is False

    def test_is_podman_returns_true_for_podman(self):
        """Should return True when runtime is 'podman'."""
        runtime = ContainerRuntime(runtime_type="podman")
        assert runtime.is_podman() is True
        assert runtime.is_auto() is False
        assert runtime.is_docker() is False


# =============================================================================
# Factory Methods Tests
# =============================================================================

class TestContainerRuntimeFactoryMethods:
    """Test factory methods for creating ContainerRuntime instances."""

    def test_auto_factory_creates_auto_runtime(self):
        """Should create runtime with 'auto' type."""
        runtime = ContainerRuntime.auto()
        
        assert runtime.runtime_type == "auto"
        assert runtime.is_auto() is True

    def test_docker_factory_creates_docker_runtime(self):
        """Should create runtime with 'docker' type."""
        runtime = ContainerRuntime.docker()
        
        assert runtime.runtime_type == "docker"
        assert runtime.is_docker() is True

    def test_podman_factory_creates_podman_runtime(self):
        """Should create runtime with 'podman' type."""
        runtime = ContainerRuntime.podman()
        
        assert runtime.runtime_type == "podman"
        assert runtime.is_podman() is True

    def test_factory_methods_create_immutable_instances(self):
        """Should create immutable instances via factory methods."""
        runtime = ContainerRuntime.docker()
        
        with pytest.raises(Exception):  # FrozenInstanceError
            runtime.runtime_type = "podman"


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestContainerRuntimeEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_equality_of_same_runtime_type(self):
        """Should be equal when runtime_type is the same."""
        runtime1 = ContainerRuntime(runtime_type="docker")
        runtime2 = ContainerRuntime(runtime_type="docker")
        
        assert runtime1 == runtime2

    def test_inequality_of_different_runtime_types(self):
        """Should not be equal when runtime_type differs."""
        runtime1 = ContainerRuntime(runtime_type="docker")
        runtime2 = ContainerRuntime(runtime_type="podman")
        
        assert runtime1 != runtime2

    def test_factory_and_constructor_produce_equal_instances(self):
        """Should be equal whether created via factory or constructor."""
        runtime1 = ContainerRuntime.docker()
        runtime2 = ContainerRuntime(runtime_type="docker")
        
        assert runtime1 == runtime2

    def test_repr_shows_runtime_type(self):
        """Should have readable repr."""
        runtime = ContainerRuntime(runtime_type="podman")
        repr_str = repr(runtime)
        
        assert "podman" in repr_str


# =============================================================================
# Tell Don't Ask Pattern Tests
# =============================================================================

class TestContainerRuntimeTellDontAsk:
    """Test resolve() method following Tell, Don't Ask principle."""

    def test_resolve_returns_docker_for_docker_runtime(self):
        """Should return 'docker' without needing detector."""
        runtime = ContainerRuntime.docker()
        
        result = runtime.resolve()
        
        assert result == "docker"

    def test_resolve_returns_podman_for_podman_runtime(self):
        """Should return 'podman' without needing detector."""
        runtime = ContainerRuntime.podman()
        
        result = runtime.resolve()
        
        assert result == "podman"

    def test_resolve_uses_detector_for_auto_runtime(self):
        """Should call detector function when runtime is 'auto'."""
        runtime = ContainerRuntime.auto()
        detector = Mock(return_value="podman")
        
        result = runtime.resolve(detector=detector)
        
        assert result == "podman"
        detector.assert_called_once()

    def test_resolve_raises_when_auto_without_detector(self):
        """Should raise ValueError when auto runtime but no detector provided."""
        runtime = ContainerRuntime.auto()
        
        with pytest.raises(ValueError, match="Detector function required"):
            runtime.resolve(detector=None)

    def test_resolve_propagates_detector_exceptions(self):
        """Should propagate exceptions from detector."""
        runtime = ContainerRuntime.auto()
        detector = Mock(side_effect=RuntimeError("No runtime found"))
        
        with pytest.raises(RuntimeError, match="No runtime found"):
            runtime.resolve(detector=detector)

    def test_resolve_with_detector_returning_docker(self):
        """Should use detector result when it returns 'docker'."""
        runtime = ContainerRuntime.auto()
        detector = Mock(return_value="docker")
        
        result = runtime.resolve(detector=detector)
        
        assert result == "docker"
        detector.assert_called_once()

    def test_resolve_encapsulates_decision_logic(self):
        """Should encapsulate all decision logic within the value object."""
        # This tests the "Tell, Don't Ask" principle:
        # - Client doesn't ask "are you auto?" and decide
        # - Client tells "resolve yourself" and provides dependencies
        
        docker_runtime = ContainerRuntime.docker()
        podman_runtime = ContainerRuntime.podman()
        auto_runtime = ContainerRuntime.auto()
        
        detector = Mock(return_value="podman")
        
        # All runtimes know how to resolve themselves
        assert docker_runtime.resolve() == "docker"
        assert podman_runtime.resolve() == "podman"
        assert auto_runtime.resolve(detector=detector) == "podman"

