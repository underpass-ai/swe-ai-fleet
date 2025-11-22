"""Unit tests for AgentResult domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities import (
    AgentResult,
    Artifacts,
    AuditTrails,
    Operations,
    ReasoningLogs,
)


class TestAgentResultCreation:
    """Test AgentResult entity creation."""

    def test_create_result_with_required_fields(self):
        """Test creating result with required fields."""
        operations = Operations()
        result = AgentResult(success=True, operations=operations)

        assert result.success is True
        assert result.operations == operations
        assert isinstance(result.artifacts, Artifacts)
        assert isinstance(result.audit_trail, AuditTrails)
        assert isinstance(result.reasoning_log, ReasoningLogs)
        assert result.error is None

    def test_create_result_with_all_fields(self):
        """Test creating result with all fields."""
        operations = Operations()
        artifacts = Artifacts()
        audit_trail = AuditTrails()
        reasoning_log = ReasoningLogs()
        error = "Task failed"

        result = AgentResult(
            success=False,
            operations=operations,
            artifacts=artifacts,
            audit_trail=audit_trail,
            reasoning_log=reasoning_log,
            error=error,
        )

        assert result.success is False
        assert result.operations == operations
        assert result.artifacts == artifacts
        assert result.audit_trail == audit_trail
        assert result.reasoning_log == reasoning_log
        assert result.error == error

    def test_create_result_with_default_collections(self):
        """Test creating result uses default factory for collections."""
        operations = Operations()
        result = AgentResult(success=True, operations=operations)

        # Default factories should create new empty collections
        assert result.artifacts.count() == 0
        assert result.audit_trail.count() == 0
        assert result.reasoning_log.count() == 0


class TestAgentResultImmutability:
    """Test AgentResult immutability."""

    def test_result_is_immutable(self):
        """Test result is frozen (immutable)."""
        operations = Operations()
        result = AgentResult(success=True, operations=operations)

        with pytest.raises(AttributeError):
            result.success = False  # type: ignore

        with pytest.raises(AttributeError):
            result.error = "New error"  # type: ignore


class TestAgentResultEquality:
    """Test AgentResult equality and comparison."""

    def test_results_with_same_values_are_equal(self):
        """Test results with identical values are equal."""
        operations = Operations()
        result1 = AgentResult(success=True, operations=operations, error=None)
        result2 = AgentResult(success=True, operations=operations, error=None)

        assert result1 == result2

    def test_results_with_different_success_are_not_equal(self):
        """Test results with different success values are not equal."""
        operations = Operations()
        result1 = AgentResult(success=True, operations=operations)
        result2 = AgentResult(success=False, operations=operations)

        assert result1 != result2

    def test_results_with_different_errors_are_not_equal(self):
        """Test results with different errors are not equal."""
        operations = Operations()
        result1 = AgentResult(success=False, operations=operations, error="Error 1")
        result2 = AgentResult(success=False, operations=operations, error="Error 2")

        assert result1 != result2

