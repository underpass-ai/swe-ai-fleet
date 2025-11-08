"""Unit tests for AuditOperation value object."""

import pytest
from core.agents_and_tools.tools.domain.audit_operation import AuditOperation

# =============================================================================
# Constructor Validation Tests (Fail-Fast)
# =============================================================================

class TestAuditOperationConstructorValidation:
    """Test constructor fail-fast validation."""

    def test_rejects_empty_operation_name(self):
        """Should raise ValueError if operation_name is empty."""
        with pytest.raises(ValueError, match="operation_name is required and cannot be empty"):
            AuditOperation(operation_name="", operation_params={})

    def test_rejects_whitespace_only_operation_name(self):
        """Should raise ValueError if operation_name is whitespace only."""
        with pytest.raises(ValueError, match="operation_name is required and cannot be empty"):
            AuditOperation(operation_name="   ", operation_params={})

    def test_rejects_none_operation_params(self):
        """Should raise ValueError if operation_params is None."""
        with pytest.raises(ValueError, match="operation_params is required"):
            AuditOperation(operation_name="run", operation_params=None)

    def test_rejects_non_dict_operation_params(self):
        """Should raise ValueError if operation_params is not a dict."""
        with pytest.raises(ValueError, match="operation_params must be a dictionary"):
            AuditOperation(operation_name="run", operation_params=["param1", "param2"])

    def test_accepts_valid_operation(self):
        """Should create instance when all fields are valid."""
        op = AuditOperation(
            operation_name="build",
            operation_params={"context": ".", "dockerfile": "Dockerfile"}
        )

        assert op.operation_name == "build"
        assert op.operation_params == {"context": ".", "dockerfile": "Dockerfile"}

    def test_accepts_empty_params_dict(self):
        """Should accept empty dict for operation_params."""
        op = AuditOperation(operation_name="ps", operation_params={})

        assert op.operation_params == {}


# =============================================================================
# Immutability Tests
# =============================================================================

class TestAuditOperationImmutability:
    """Test that AuditOperation is immutable (frozen=True)."""

    def test_cannot_modify_operation_name(self):
        """Should prevent modification of operation_name field."""
        op = AuditOperation(operation_name="run", operation_params={})

        with pytest.raises(Exception):  # FrozenInstanceError
            op.operation_name = "build"

    def test_cannot_modify_operation_params(self):
        """Should prevent modification of operation_params field."""
        op = AuditOperation(operation_name="run", operation_params={"image": "nginx"})

        with pytest.raises(Exception):  # FrozenInstanceError
            op.operation_params = {}


# =============================================================================
# Business Logic Tests
# =============================================================================

class TestAuditOperationBusinessLogic:
    """Test domain logic methods."""

    def test_get_name_returns_operation_name(self):
        """Should return operation name."""
        op = AuditOperation(operation_name="build", operation_params={})

        assert op.get_name() == "build"

    def test_get_params_returns_operation_params(self):
        """Should return operation parameters."""
        params = {"image": "nginx", "tag": "latest"}
        op = AuditOperation(operation_name="build", operation_params=params)

        assert op.get_params() == params
        assert op.get_params()["image"] == "nginx"

    def test_has_params_returns_true_when_params_present(self):
        """Should return True when params dict is not empty."""
        op = AuditOperation(operation_name="run", operation_params={"image": "nginx"})

        assert op.has_params() is True

    def test_has_params_returns_false_when_params_empty(self):
        """Should return False when params dict is empty."""
        op = AuditOperation(operation_name="ps", operation_params={})

        assert op.has_params() is False


# =============================================================================
# Factory Methods Tests
# =============================================================================

class TestAuditOperationFactoryMethods:
    """Test factory methods for creating AuditOperation instances."""

    def test_for_run_creates_run_operation(self):
        """Should create run operation with correct params."""
        op = AuditOperation.for_run(image="nginx:latest", detach=True)

        assert op.get_name() == "run"
        assert op.get_params() == {"image": "nginx:latest", "detach": True}

    def test_for_run_with_non_detached(self):
        """Should create run operation with detach=False."""
        op = AuditOperation.for_run(image="alpine", detach=False)

        assert op.get_params()["detach"] is False

    def test_for_build_creates_build_operation(self):
        """Should create build operation with correct params."""
        op = AuditOperation.for_build(context=".", dockerfile="Dockerfile")

        assert op.get_name() == "build"
        assert op.get_params() == {"context": ".", "dockerfile": "Dockerfile"}

    def test_for_exec_creates_exec_operation(self):
        """Should create exec operation with correct params."""
        op = AuditOperation.for_exec(container="webserver", command=["sh", "-c", "echo test"])

        assert op.get_name() == "exec"
        assert op.get_params()["container"] == "webserver"
        assert op.get_params()["command"] == ["sh", "-c", "echo test"]

    def test_simple_creates_operation_with_no_params(self):
        """Should create operation with empty params."""
        op = AuditOperation.simple("ps")

        assert op.get_name() == "ps"
        assert op.get_params() == {}
        assert op.has_params() is False


# =============================================================================
# Edge Cases Tests
# =============================================================================

class TestAuditOperationEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_accepts_complex_nested_params(self):
        """Should accept complex nested parameters."""
        complex_params = {
            "image": "myapp:v1.0",
            "env": {"ENV": "production", "DEBUG": "false"},
            "volumes": {"/host": "/container"},
            "config": {"nested": {"deep": "value"}},
        }

        op = AuditOperation(operation_name="run", operation_params=complex_params)

        assert op.get_params() == complex_params
        assert op.get_params()["env"]["ENV"] == "production"

    def test_equality_of_identical_operations(self):
        """Should be equal when all fields are the same."""
        op1 = AuditOperation(operation_name="build", operation_params={"context": "."})
        op2 = AuditOperation(operation_name="build", operation_params={"context": "."})

        assert op1 == op2

    def test_inequality_when_name_differs(self):
        """Should not be equal when operation_name differs."""
        op1 = AuditOperation(operation_name="build", operation_params={})
        op2 = AuditOperation(operation_name="run", operation_params={})

        assert op1 != op2

    def test_inequality_when_params_differ(self):
        """Should not be equal when operation_params differ."""
        op1 = AuditOperation(operation_name="run", operation_params={"image": "nginx"})
        op2 = AuditOperation(operation_name="run", operation_params={"image": "apache"})

        assert op1 != op2

    def test_factory_and_constructor_produce_equal_instances(self):
        """Should be equal whether created via factory or constructor."""
        op1 = AuditOperation.for_run(image="nginx", detach=False)
        op2 = AuditOperation(operation_name="run", operation_params={"image": "nginx", "detach": False})

        assert op1 == op2

