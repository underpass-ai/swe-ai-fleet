"""Unit tests for ExecutionConstraints domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.execution_constraints import ExecutionConstraints


class TestExecutionConstraintsCreation:
    """Test ExecutionConstraints entity creation."""

    def test_create_with_defaults(self):
        """Test creating constraints with default values."""
        constraints = ExecutionConstraints()

        assert constraints.max_operations == 100
        assert constraints.abort_on_error is True
        assert constraints.iterative is False
        assert constraints.max_iterations == 10

    def test_create_with_custom_values(self):
        """Test creating constraints with custom values."""
        constraints = ExecutionConstraints(
            max_operations=50,
            abort_on_error=False,
            iterative=True,
            max_iterations=20,
        )

        assert constraints.max_operations == 50
        assert constraints.abort_on_error is False
        assert constraints.iterative is True
        assert constraints.max_iterations == 20

    def test_create_with_partial_custom_values(self):
        """Test creating constraints with partial custom values."""
        constraints = ExecutionConstraints(max_operations=200, iterative=True)

        assert constraints.max_operations == 200
        assert constraints.abort_on_error is True  # default
        assert constraints.iterative is True
        assert constraints.max_iterations == 10  # default


class TestExecutionConstraintsImmutability:
    """Test ExecutionConstraints immutability."""

    def test_constraints_are_immutable(self):
        """Test constraints are frozen (immutable)."""
        constraints = ExecutionConstraints()

        with pytest.raises(AttributeError):
            constraints.max_operations = 50  # type: ignore

        with pytest.raises(AttributeError):
            constraints.abort_on_error = False  # type: ignore


class TestExecutionConstraintsEquality:
    """Test ExecutionConstraints equality and comparison."""

    def test_constraints_with_same_values_are_equal(self):
        """Test constraints with identical values are equal."""
        constraints1 = ExecutionConstraints(
            max_operations=50,
            abort_on_error=False,
            iterative=True,
            max_iterations=20,
        )
        constraints2 = ExecutionConstraints(
            max_operations=50,
            abort_on_error=False,
            iterative=True,
            max_iterations=20,
        )

        assert constraints1 == constraints2

    def test_constraints_with_different_values_are_not_equal(self):
        """Test constraints with different values are not equal."""
        constraints1 = ExecutionConstraints(max_operations=50)
        constraints2 = ExecutionConstraints(max_operations=100)

        assert constraints1 != constraints2

