"""Unit tests for DockerOperations entity."""

from unittest.mock import Mock

import pytest
from core.agents_and_tools.tools.domain.docker_operations import DockerOperations

# =============================================================================
# Test Fixtures
# =============================================================================

@pytest.fixture
def mock_operations():
    """Create mock operation functions."""
    return {
        "build": Mock(),
        "run": Mock(),
        "exec": Mock(),
        "ps": Mock(),
        "logs": Mock(),
        "stop": Mock(),
        "rm": Mock(),
    }


# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestDockerOperationsConstructorValidation:
    """Test constructor fail-fast validation."""

    def test_rejects_non_callable_build(self, mock_operations):
        """Should raise ValueError if build is not callable."""
        with pytest.raises(ValueError, match="build must be callable"):
            DockerOperations(
                build="not_callable",  # String instead of callable
                run=mock_operations["run"],
                exec=mock_operations["exec"],
                ps=mock_operations["ps"],
                logs=mock_operations["logs"],
                stop=mock_operations["stop"],
                rm=mock_operations["rm"],
            )

    def test_rejects_non_callable_run(self, mock_operations):
        """Should raise ValueError if run is not callable."""
        with pytest.raises(ValueError, match="run must be callable"):
            DockerOperations(
                build=mock_operations["build"],
                run=None,  # None instead of callable
                exec=mock_operations["exec"],
                ps=mock_operations["ps"],
                logs=mock_operations["logs"],
                stop=mock_operations["stop"],
                rm=mock_operations["rm"],
            )

    def test_rejects_non_callable_exec(self, mock_operations):
        """Should raise ValueError if exec is not callable."""
        with pytest.raises(ValueError, match="exec must be callable"):
            DockerOperations(
                build=mock_operations["build"],
                run=mock_operations["run"],
                exec=123,  # Int instead of callable
                ps=mock_operations["ps"],
                logs=mock_operations["logs"],
                stop=mock_operations["stop"],
                rm=mock_operations["rm"],
            )

    def test_accepts_all_valid_callables(self, mock_operations):
        """Should create instance when all operations are callable."""
        ops = DockerOperations(
            build=mock_operations["build"],
            run=mock_operations["run"],
            exec=mock_operations["exec"],
            ps=mock_operations["ps"],
            logs=mock_operations["logs"],
            stop=mock_operations["stop"],
            rm=mock_operations["rm"],
        )

        assert callable(ops.build)
        assert callable(ops.run)
        assert callable(ops.exec)
        assert callable(ops.ps)
        assert callable(ops.logs)
        assert callable(ops.stop)
        assert callable(ops.rm)


# =============================================================================
# Immutability Tests
# =============================================================================

class TestDockerOperationsImmutability:
    """Test that DockerOperations is immutable (frozen=True)."""

    def test_cannot_modify_build(self, mock_operations):
        """Should prevent modification of build field."""
        ops = DockerOperations(**mock_operations)

        with pytest.raises(Exception):  # FrozenInstanceError
            ops.build = Mock()

    def test_cannot_modify_run(self, mock_operations):
        """Should prevent modification of run field."""
        ops = DockerOperations(**mock_operations)

        with pytest.raises(Exception):  # FrozenInstanceError
            ops.run = Mock()


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestDockerOperationsBusinessLogic:
    """Test domain logic methods."""

    def test_to_dict_returns_all_operations(self, mock_operations):
        """Should return dict with all 7 operations."""
        ops = DockerOperations(**mock_operations)

        operations_dict = ops.to_dict()

        assert len(operations_dict) == 7
        assert "build" in operations_dict
        assert "run" in operations_dict
        assert "exec" in operations_dict
        assert "ps" in operations_dict
        assert "logs" in operations_dict
        assert "stop" in operations_dict
        assert "rm" in operations_dict

    def test_to_dict_returns_same_callables(self, mock_operations):
        """Should return same callable instances."""
        ops = DockerOperations(**mock_operations)

        operations_dict = ops.to_dict()

        assert operations_dict["build"] is mock_operations["build"]
        assert operations_dict["run"] is mock_operations["run"]
        assert operations_dict["exec"] is mock_operations["exec"]

    def test_get_operation_returns_callable_when_exists(self, mock_operations):
        """Should return callable when operation exists."""
        ops = DockerOperations(**mock_operations)

        build_op = ops.get_operation("build")

        assert build_op is mock_operations["build"]
        assert callable(build_op)

    def test_get_operation_returns_none_when_not_exists(self, mock_operations):
        """Should return None when operation doesn't exist."""
        ops = DockerOperations(**mock_operations)

        result = ops.get_operation("invalid_operation")

        assert result is None

    def test_has_operation_returns_true_when_exists(self, mock_operations):
        """Should return True for existing operations."""
        ops = DockerOperations(**mock_operations)

        assert ops.has_operation("build") is True
        assert ops.has_operation("run") is True
        assert ops.has_operation("exec") is True
        assert ops.has_operation("ps") is True
        assert ops.has_operation("logs") is True
        assert ops.has_operation("stop") is True
        assert ops.has_operation("rm") is True

    def test_has_operation_returns_false_when_not_exists(self, mock_operations):
        """Should return False for non-existing operations."""
        ops = DockerOperations(**mock_operations)

        assert ops.has_operation("push") is False
        assert ops.has_operation("pull") is False
        assert ops.has_operation("invalid") is False

    def test_list_operations_returns_all_names(self, mock_operations):
        """Should return list of all operation names."""
        ops = DockerOperations(**mock_operations)

        operation_names = ops.list_operations()

        assert len(operation_names) == 7
        assert "build" in operation_names
        assert "run" in operation_names
        assert "exec" in operation_names
        assert "ps" in operation_names
        assert "logs" in operation_names
        assert "stop" in operation_names
        assert "rm" in operation_names

    def test_count_operations_returns_seven(self, mock_operations):
        """Should return count of 7 operations."""
        ops = DockerOperations(**mock_operations)

        assert ops.count_operations() == 7


# =============================================================================
# Integration Tests
# =============================================================================

class TestDockerOperationsIntegration:
    """Test integration with actual function references."""

    def test_accepts_lambda_functions(self):
        """Should accept lambda functions as operations."""
        ops = DockerOperations(
            build=lambda: "build",
            run=lambda: "run",
            exec=lambda: "exec",
            ps=lambda: "ps",
            logs=lambda: "logs",
            stop=lambda: "stop",
            rm=lambda: "rm",
        )

        assert ops.build() == "build"
        assert ops.run() == "run"

    def test_accepts_method_references(self):
        """Should accept method references."""
        class DummyTool:
            def build(self): return "build"
            def run(self): return "run"
            def exec_cmd(self): return "exec"
            def ps(self): return "ps"
            def logs(self): return "logs"
            def stop(self): return "stop"
            def rm(self): return "rm"

        tool = DummyTool()
        ops = DockerOperations(
            build=tool.build,
            run=tool.run,
            exec=tool.exec_cmd,
            ps=tool.ps,
            logs=tool.logs,
            stop=tool.stop,
            rm=tool.rm,
        )

        assert ops.build() == "build"
        assert ops.run() == "run"
        assert ops.get_operation("exec")() == "exec"

    def test_can_call_operations_via_get_operation(self, mock_operations):
        """Should be able to call operations retrieved via get_operation()."""
        mock_operations["build"].return_value = "build_result"
        ops = DockerOperations(**mock_operations)

        build_op = ops.get_operation("build")
        result = build_op()

        assert result == "build_result"
        mock_operations["build"].assert_called_once()

