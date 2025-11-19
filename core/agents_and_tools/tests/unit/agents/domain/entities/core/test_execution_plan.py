"""Unit tests for ExecutionPlan domain entity."""

import pytest
from core.agents_and_tools.agents.domain.entities.core.execution_plan import ExecutionPlan


class TestExecutionPlanCreation:
    """Test ExecutionPlan entity creation."""

    def test_create_plan_with_steps(self):
        """Test creating plan with steps."""
        steps = [
            {"tool": "files", "operation": "read_file", "params": {"path": "/test.txt"}},
            {"tool": "git", "operation": "commit", "params": {"message": "test"}},
        ]
        plan = ExecutionPlan(steps=steps)

        assert plan.steps == steps
        assert plan.reasoning is None

    def test_create_plan_with_reasoning(self):
        """Test creating plan with reasoning."""
        steps = [{"tool": "files", "operation": "read_file"}]
        reasoning = "Read the configuration file first"
        plan = ExecutionPlan(steps=steps, reasoning=reasoning)

        assert plan.steps == steps
        assert plan.reasoning == reasoning

    def test_create_plan_with_empty_steps(self):
        """Test creating plan with empty steps."""
        plan = ExecutionPlan(steps=[])

        assert plan.steps == []
        assert len(plan.steps) == 0


class TestExecutionPlanImmutability:
    """Test ExecutionPlan immutability."""

    def test_plan_is_immutable(self):
        """Test plan is frozen (immutable)."""
        steps = [{"tool": "files", "operation": "read_file"}]
        plan = ExecutionPlan(steps=steps)

        with pytest.raises(AttributeError):
            plan.reasoning = "new reasoning"  # type: ignore


class TestExecutionPlanEquality:
    """Test ExecutionPlan equality and comparison."""

    def test_plans_with_same_values_are_equal(self):
        """Test plans with identical values are equal."""
        steps = [{"tool": "files", "operation": "read_file"}]
        reasoning = "Test reasoning"
        plan1 = ExecutionPlan(steps=steps, reasoning=reasoning)
        plan2 = ExecutionPlan(steps=steps, reasoning=reasoning)

        assert plan1 == plan2

    def test_plans_with_different_steps_are_not_equal(self):
        """Test plans with different steps are not equal."""
        steps1 = [{"tool": "files", "operation": "read_file"}]
        steps2 = [{"tool": "git", "operation": "commit"}]
        plan1 = ExecutionPlan(steps=steps1)
        plan2 = ExecutionPlan(steps=steps2)

        assert plan1 != plan2

    def test_plans_with_different_reasoning_are_not_equal(self):
        """Test plans with different reasoning are not equal."""
        steps = [{"tool": "files", "operation": "read_file"}]
        plan1 = ExecutionPlan(steps=steps, reasoning="Reason 1")
        plan2 = ExecutionPlan(steps=steps, reasoning="Reason 2")

        assert plan1 != plan2

