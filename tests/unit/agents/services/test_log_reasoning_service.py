"""Unit tests for LogReasoningApplicationService."""

import pytest

from core.agents_and_tools.agents.application.services.log_reasoning_service import (
    LogReasoningApplicationService,
)
from core.agents_and_tools.agents.domain.entities import ExecutionStep, ReasoningLogs
from core.agents_and_tools.agents.domain.entities.rbac import RoleFactory


# =============================================================================
# Constructor Tests
# =============================================================================

class TestLogReasoningServiceConstructor:
    """Test constructor fail-fast validation."""

    def test_rejects_empty_agent_id(self):
        """Should raise ValueError if agent_id is empty."""
        with pytest.raises(ValueError, match="agent_id cannot be empty"):
            LogReasoningApplicationService(agent_id="", role=RoleFactory.create_developer())

    def test_accepts_role_object(self):
        """Should accept Role object (type hints are not enforced at runtime)."""
        # Python doesn't enforce type hints at runtime, so we just verify it accepts Role objects
        service = LogReasoningApplicationService(agent_id="test-agent", role=RoleFactory.create_developer())
        assert service.role.get_name() == "developer"

    def test_accepts_valid_parameters(self):
        """Should create service with valid parameters."""
        service = LogReasoningApplicationService(agent_id="agent-123", role=RoleFactory.create_qa())

        assert service.agent_id == "agent-123"
        assert service.role.get_name() == "qa"  # Role is now a value object


# =============================================================================
# log_analysis Tests
# =============================================================================

class TestLogAnalysis:
    """Test log_analysis method."""

    def test_log_analysis_creates_analysis_thought(self):
        """Should create analysis thought with correct fields."""
        service = LogReasoningApplicationService(agent_id="agent-001", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_analysis(
            reasoning_log=reasoning_log,
            task="Fix bug in auth module",
            mode="full execution",
            iteration=0,
        )

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.agent_id == "agent-001"
        assert thought.role == "developer"  # role.get_name() returns lowercase
        assert thought.iteration == 0
        assert thought.thought_type == "analysis"
        assert "Fix bug in auth module" in thought.content
        assert "full execution" in thought.content

    def test_log_analysis_with_different_modes(self):
        """Should handle different execution modes."""
        service = LogReasoningApplicationService(agent_id="agent-002", role=RoleFactory.create_architect())
        reasoning_log = ReasoningLogs()

        # Test planning only mode
        service.log_analysis(reasoning_log, "Plan refactoring", "planning only")

        thought = reasoning_log.get_all()[0]
        assert "planning only" in thought.content

    def test_log_analysis_custom_iteration(self):
        """Should support custom iteration numbers."""
        service = LogReasoningApplicationService(agent_id="agent-003", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        service.log_analysis(reasoning_log, "Test task", "full execution", iteration=5)

        thought = reasoning_log.get_all()[0]
        assert thought.iteration == 5


# =============================================================================
# log_plan_decision Tests
# =============================================================================

class TestLogPlanDecision:
    """Test log_plan_decision method."""

    def test_log_plan_decision_with_steps(self):
        """Should log plan decision with steps and reasoning."""
        service = LogReasoningApplicationService(agent_id="agent-004", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        steps = [
            ExecutionStep(tool="files", operation="list_files", params={"path": "."}),
            ExecutionStep(tool="git", operation="status", params={}),
        ]

        service.log_plan_decision(
            reasoning_log=reasoning_log,
            plan_steps_count=2,
            plan_reasoning="List files then check git status",
            steps=steps,
            iteration=0,
        )

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "decision"
        assert "2 steps" in thought.content
        assert "List files then check git status" in thought.content
        assert thought.related_operations == ["files.list_files", "git.status"]

    def test_log_plan_decision_empty_plan(self):
        """Should handle empty plan."""
        service = LogReasoningApplicationService(agent_id="agent-005", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_plan_decision(
            reasoning_log=reasoning_log,
            plan_steps_count=0,
            plan_reasoning="No steps needed",
            steps=[],
        )

        thought = reasoning_log.get_all()[0]
        assert "0 steps" in thought.content
        assert thought.related_operations == []


# =============================================================================
# log_action Tests
# =============================================================================

class TestLogAction:
    """Test log_action method."""

    def test_log_action_records_step_details(self):
        """Should log action with step details."""
        service = LogReasoningApplicationService(agent_id="agent-006", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        step = ExecutionStep(
            tool="files",
            operation="read_file",
            params={"path": "src/main.py"}
        )

        service.log_action(reasoning_log, step, iteration=1)

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "action"
        assert thought.iteration == 1
        assert "files.read_file" in thought.content
        assert "src/main.py" in thought.content

    def test_log_action_with_no_params(self):
        """Should handle steps without parameters."""
        service = LogReasoningApplicationService(agent_id="agent-007", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        step = ExecutionStep(tool="git", operation="status", params=None)

        service.log_action(reasoning_log, step, iteration=2)

        thought = reasoning_log.get_all()[0]
        assert "git.status" in thought.content


# =============================================================================
# log_success_observation and log_failure_observation Tests
# =============================================================================

class TestLogObservations:
    """Test observation logging methods."""

    def test_log_success_observation(self):
        """Should log successful observation with confidence 1.0."""
        service = LogReasoningApplicationService(agent_id="agent-008", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_success_observation(
            reasoning_log=reasoning_log,
            summary="Found 5 files in src/ directory",
            iteration=1,
        )

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "observation"
        assert thought.iteration == 1
        assert thought.confidence == 1.0
        assert "✅" in thought.content
        assert "Found 5 files" in thought.content

    def test_log_failure_observation(self):
        """Should log failed observation with confidence 0.0."""
        service = LogReasoningApplicationService(agent_id="agent-009", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        service.log_failure_observation(
            reasoning_log=reasoning_log,
            error="File not found: missing.py",
            iteration=2,
        )

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "observation"
        assert thought.iteration == 2
        assert thought.confidence == 0.0
        assert "❌" in thought.content
        assert "File not found" in thought.content

    def test_log_failure_with_none_error(self):
        """Should handle None error message."""
        service = LogReasoningApplicationService(agent_id="agent-010", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_failure_observation(
            reasoning_log=reasoning_log,
            error=None,
            iteration=1,
        )

        thought = reasoning_log.get_all()[0]
        assert "Unknown error" in thought.content


# =============================================================================
# log_conclusion Tests
# =============================================================================

class TestLogConclusion:
    """Test log_conclusion method."""

    def test_log_conclusion_success(self):
        """Should log successful conclusion with confidence 1.0."""
        service = LogReasoningApplicationService(agent_id="agent-011", role=RoleFactory.create_architect())
        reasoning_log = ReasoningLogs()

        service.log_conclusion(
            reasoning_log=reasoning_log,
            success=True,
            operations_count=5,
            artifacts_keys=["file_content", "test_results"],
            iteration=6,
        )

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "conclusion"
        assert thought.iteration == 6
        assert thought.confidence == 1.0
        assert "completed successfully" in thought.content
        assert "5 operations" in thought.content
        assert "file_content" in thought.content
        assert "test_results" in thought.content

    def test_log_conclusion_failure(self):
        """Should log failed conclusion with confidence 0.5."""
        service = LogReasoningApplicationService(agent_id="agent-012", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_conclusion(
            reasoning_log=reasoning_log,
            success=False,
            operations_count=3,
            artifacts_keys=[],
            iteration=4,
        )

        thought = reasoning_log.get_all()[0]
        assert thought.confidence == 0.5
        assert "failed" in thought.content
        assert "3 operations" in thought.content


# =============================================================================
# log_error Tests
# =============================================================================

class TestLogError:
    """Test log_error method."""

    def test_log_error_creates_error_thought(self):
        """Should create error thought with iteration -1 and confidence 0.0."""
        service = LogReasoningApplicationService(agent_id="agent-013", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        service.log_error(reasoning_log, "RuntimeError: LLM API failed")

        assert reasoning_log.count() == 1
        thought = reasoning_log.get_all()[0]
        assert thought.thought_type == "error"
        assert thought.iteration == -1
        assert thought.confidence == 0.0
        assert "Fatal error" in thought.content
        assert "LLM API failed" in thought.content


# =============================================================================
# Integration Tests
# =============================================================================

class TestLogReasoningServiceIntegration:
    """Test service integration scenarios."""

    def test_complete_execution_flow(self):
        """Should handle complete execution flow with all thought types."""
        service = LogReasoningApplicationService(agent_id="agent-014", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        # 1. Analysis
        service.log_analysis(reasoning_log, "Fix bug", "full execution")

        # 2. Plan decision
        steps = [ExecutionStep(tool="files", operation="read_file", params={"path": "a.py"})]
        service.log_plan_decision(reasoning_log, 1, "Read file", steps)

        # 3. Action
        service.log_action(reasoning_log, steps[0], iteration=1)

        # 4. Success observation
        service.log_success_observation(reasoning_log, "Read 100 lines", iteration=1)

        # 5. Conclusion
        service.log_conclusion(reasoning_log, True, 1, ["file_content"], iteration=2)

        # Verify all logged
        assert reasoning_log.count() == 5
        thought_types = {t.thought_type for t in reasoning_log.get_all()}
        assert thought_types == {"analysis", "decision", "action", "observation", "conclusion"}

    def test_error_handling_flow(self):
        """Should handle error flow correctly."""
        service = LogReasoningApplicationService(agent_id="agent-015", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        # 1. Analysis
        service.log_analysis(reasoning_log, "Test task", "full execution")

        # 2. Action
        step = ExecutionStep(tool="files", operation="read_file", params={"path": "missing.py"})
        service.log_action(reasoning_log, step, iteration=1)

        # 3. Failure observation
        service.log_failure_observation(reasoning_log, "File not found", iteration=1)

        # 4. Fatal error
        service.log_error(reasoning_log, "Execution failed")

        # Verify
        assert reasoning_log.count() == 4
        failures = [t for t in reasoning_log.get_all() if t.confidence == 0.0]
        assert len(failures) == 2  # failure observation + error

    def test_multiple_iterations(self):
        """Should handle multiple iterations correctly."""
        service = LogReasoningApplicationService(agent_id="agent-016", role=RoleFactory.create_architect())
        reasoning_log = ReasoningLogs()

        # Iteration 0: Analysis
        service.log_analysis(reasoning_log, "Task", "full", iteration=0)

        # Iteration 1: Action + observation
        step1 = ExecutionStep(tool="files", operation="list_files", params={})
        service.log_action(reasoning_log, step1, iteration=1)
        service.log_success_observation(reasoning_log, "Listed files", iteration=1)

        # Iteration 2: Action + observation
        step2 = ExecutionStep(tool="files", operation="read_file", params={})
        service.log_action(reasoning_log, step2, iteration=2)
        service.log_success_observation(reasoning_log, "Read file", iteration=2)

        # Conclusion
        service.log_conclusion(reasoning_log, True, 2, ["files"], iteration=3)

        # Verify
        assert reasoning_log.count() == 6
        assert reasoning_log.get_by_iteration(0)[0].thought_type == "analysis"
        assert len(reasoning_log.get_by_iteration(1)) == 2  # action + observation
        assert len(reasoning_log.get_by_iteration(2)) == 2  # action + observation


# =============================================================================
# Stateless Service Tests
# =============================================================================

class TestServiceStatelessness:
    """Test that service is stateless."""

    def test_service_is_reusable_across_executions(self):
        """Should be reusable for multiple executions."""
        service = LogReasoningApplicationService(agent_id="agent-017", role=RoleFactory.create_developer())

        # First execution
        log1 = ReasoningLogs()
        service.log_analysis(log1, "Task 1", "full")
        service.log_conclusion(log1, True, 1, [], iteration=1)

        # Second execution
        log2 = ReasoningLogs()
        service.log_analysis(log2, "Task 2", "planning")
        service.log_conclusion(log2, False, 2, [], iteration=2)

        # Verify both are independent
        assert log1.count() == 2
        assert log2.count() == 2
        assert log1.get_all()[0].content != log2.get_all()[0].content

    def test_service_uses_same_agent_context(self):
        """Should use same agent_id and role for all logs."""
        service = LogReasoningApplicationService(agent_id="agent-018", role=RoleFactory.create_qa())
        reasoning_log = ReasoningLogs()

        service.log_analysis(reasoning_log, "Task", "full")
        service.log_error(reasoning_log, "Error")
        service.log_conclusion(reasoning_log, False, 0, [], iteration=1)

        # All should have same agent_id and role
        for thought in reasoning_log.get_all():
            assert thought.agent_id == "agent-018"
            assert thought.role == "qa"  # role.get_name() returns lowercase


# =============================================================================
# Edge Cases
# =============================================================================

class TestLogReasoningServiceEdgeCases:
    """Test edge cases and boundaries."""

    def test_log_action_with_complex_params(self):
        """Should handle steps with complex parameters."""
        service = LogReasoningApplicationService(agent_id="agent-019", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        step = ExecutionStep(
            tool="files",
            operation="search_in_files",
            params={
                "pattern": "BUG",
                "path": "src/",
                "recursive": True,
                "file_types": ["py", "js"]
            }
        )

        service.log_action(reasoning_log, step, iteration=1)

        thought = reasoning_log.get_all()[0]
        assert "search_in_files" in thought.content

    def test_log_conclusion_with_many_artifacts(self):
        """Should handle conclusions with many artifacts."""
        service = LogReasoningApplicationService(agent_id="agent-020", role=RoleFactory.create_architect())
        reasoning_log = ReasoningLogs()

        many_artifacts = [f"artifact_{i}" for i in range(20)]

        service.log_conclusion(
            reasoning_log,
            success=True,
            operations_count=20,
            artifacts_keys=many_artifacts,
            iteration=21,
        )

        thought = reasoning_log.get_all()[0]
        assert "20 operations" in thought.content
        assert "artifact_0" in thought.content

    def test_log_with_special_characters(self):
        """Should handle special characters in content."""
        service = LogReasoningApplicationService(agent_id="agent-021", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        service.log_analysis(
            reasoning_log,
            task="Fix bug in file with UTF-8: café ñ 中文",
            mode="full execution",
        )

        thought = reasoning_log.get_all()[0]
        assert "café" in thought.content
        assert "ñ" in thought.content
        assert "中文" in thought.content


# =============================================================================
# Thought Type Coverage
# =============================================================================

class TestAllThoughtTypes:
    """Test all thought types are supported."""

    def test_all_six_thought_types(self):
        """Should support all 6 thought types."""
        service = LogReasoningApplicationService(agent_id="agent-022", role=RoleFactory.create_developer())
        reasoning_log = ReasoningLogs()

        # 1. analysis
        service.log_analysis(reasoning_log, "Task", "full")

        # 2. decision
        steps = [ExecutionStep(tool="files", operation="list_files", params={})]
        service.log_plan_decision(reasoning_log, 1, "Plan", steps)

        # 3. action
        service.log_action(reasoning_log, steps[0], iteration=1)

        # 4. observation (success)
        service.log_success_observation(reasoning_log, "Success", iteration=1)

        # 5. conclusion
        service.log_conclusion(reasoning_log, True, 1, [], iteration=2)

        # 6. error
        service.log_error(reasoning_log, "Test error")

        # Verify all types
        thought_types = {t.thought_type for t in reasoning_log.get_all()}
        assert thought_types == {"analysis", "decision", "action", "observation", "conclusion", "error"}

