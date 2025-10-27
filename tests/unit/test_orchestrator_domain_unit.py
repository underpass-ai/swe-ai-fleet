"""Unit tests for orchestrator domain objects."""

from typing import Any

import pytest
from core.orchestrator.domain.agents.agent import Agent
from core.orchestrator.domain.agents.role import Role
from core.orchestrator.domain.check_results import (
    CheckResult,
    CheckSuiteResult,
    DryrunCheckResult,
    LintCheckResult,
    PolicyCheckResult,
)
from core.orchestrator.domain.tasks import (
    Task,
    TaskConstraints,
    TaskExecutionResult,
    TaskSpec,
    TaskStatus,
)
from core.orchestrator.domain.tasks.services import TaskSelectionService


class ConcreteCheckResult(CheckResult):
    """Concrete implementation for testing abstract CheckResult."""
    
    def __init__(self, ok: bool, issues: list[str]):
        super().__init__(ok=ok)
        self.issues = issues
    
    def get_issues(self) -> list[str]:
        return self.issues
    
    def get_score(self) -> float:
        return 1.0 if self.ok and not self.issues else 0.0
    
    def _get_specific_data(self) -> dict[str, Any]:
        return {"issues": self.issues}


class TestCheckResult:
    """Test CheckResult abstract base class."""
    
    def test_check_result_instantiation(self):
        """Test that CheckResult can be instantiated through concrete implementation."""
        result = ConcreteCheckResult(ok=True, issues=[])
        assert result.ok is True
        assert isinstance(result, CheckResult)
    
    def test_check_result_to_dict(self):
        """Test CheckResult to_dict method."""
        result = ConcreteCheckResult(ok=True, issues=["issue1"])
        expected = {"ok": True, "issues": ["issue1"]}
        assert result.to_dict() == expected


class TestAgent:
    """Test Agent abstract class."""
    
    def test_agent_is_abstract(self):
        """Test that Agent methods raise NotImplementedError."""
        agent = Agent()
        with pytest.raises(NotImplementedError):
            agent.generate("task", TaskConstraints(rubric={}, architect_rubric={}), True)
        with pytest.raises(NotImplementedError):
            agent.critique("proposal", {})
        with pytest.raises(NotImplementedError):
            agent.revise("content", "feedback")


class TestRole:
    """Test Role domain object."""
    
    def test_role_creation(self):
        """Test role creation with basic properties."""
        role = Role(name="developer", capabilities=["coding", "testing"])
        assert role.name == "developer"
        assert role.capabilities == ["coding", "testing"]
    
    def test_role_default_capabilities(self):
        """Test role creation with default None capabilities."""
        role = Role(name="devops")
        assert role.name == "devops"
        assert role.capabilities is None
    
    def test_role_properties(self):
        """Test role type checking properties."""
        devops_role = Role(name="devops")
        dev_role = Role(name="developer")
        arch_role = Role(name="architect")
        
        assert devops_role.is_devops
        assert not devops_role.is_developer
        assert not devops_role.is_architect
        
        assert dev_role.is_developer
        assert not dev_role.is_devops
        assert not dev_role.is_architect
        
        assert arch_role.is_architect
        assert not arch_role.is_devops
        assert not arch_role.is_developer
    
    def test_role_capability_check(self):
        """Test role capability checking."""
        role = Role(name="developer", capabilities=["coding", "testing"])
        assert role.has_capability("coding")
        assert role.has_capability("testing")
        assert not role.has_capability("devops")
    
    def test_role_from_string(self):
        """Test role creation from string."""
        role = Role.from_string("devops", ["deployment", "monitoring"])
        assert role.name == "devops"
        assert role.capabilities == ["deployment", "monitoring"]
        
        role2 = Role.from_string("developer")
        assert role2.name == "developer"
        assert role2.capabilities is None
    
    def test_role_string_representation(self):
        """Test role string representation."""
        role = Role(name="devops")
        assert str(role) == "devops"
    
    def test_role_has_capability_with_none_capabilities(self):
        """Test role capability checking when capabilities is None."""
        role = Role(name="developer")  # capabilities is None by default
        assert not role.has_capability("coding")


class TestTask:
    """Test Task domain object."""
    
    def test_task_creation(self):
        """Test task creation with basic properties."""
        task = Task(description="Deploy web service", id="task-1", priority=5)
        assert task.description == "Deploy web service"
        assert task.id == "task-1"
        assert task.priority == 5
    
    def test_task_default_values(self):
        """Test task creation with default values."""
        task = Task(description="Simple task")
        assert task.description == "Simple task"
        assert task.id is None
        assert task.priority == 0
    
    def test_task_from_string(self):
        """Test task creation from string."""
        task = Task.from_string("Deploy app", task_id="deploy-1")
        assert task.description == "Deploy app"
        assert task.id == "deploy-1"
        assert task.priority == 0  # default value
    
    def test_task_properties(self):
        """Test task properties and methods."""
        task = Task(description="Test task")
        empty_task = Task(description="")
        
        assert not task.is_empty
        assert empty_task.is_empty
        assert str(task) == "Test task"
        assert len(task) == 9  # length of "Test task"


class TestTaskStatus:
    """Test TaskStatus enum."""
    
    def test_task_status_values(self):
        """Test task status enum values."""
        assert TaskStatus.READY.value == "READY"
        assert TaskStatus.IN_PROGRESS.value == "IN_PROGRESS"
        assert TaskStatus.DONE.value == "DONE"
        assert TaskStatus.FAILED.value == "FAILED"
        assert TaskStatus.CANCELLED.value == "CANCELLED"
    
    def test_task_status_properties(self):
        """Test task status properties."""
        assert TaskStatus.READY.is_executable
        assert TaskStatus.IN_PROGRESS.is_executable
        assert not TaskStatus.DONE.is_executable
        
        assert TaskStatus.DONE.is_final
        assert TaskStatus.FAILED.is_final
        assert TaskStatus.CANCELLED.is_final
        assert not TaskStatus.READY.is_final
        
        assert TaskStatus.DONE.is_success
        assert not TaskStatus.FAILED.is_success
        
        assert TaskStatus.FAILED.is_failure
        assert not TaskStatus.CANCELLED.is_failure  # CANCELLED is not considered failure
        assert not TaskStatus.DONE.is_failure
    
    def test_task_status_transitions(self):
        """Test task status transition validation."""
        # Valid transitions from READY
        assert TaskStatus.READY.can_transition_to(TaskStatus.IN_PROGRESS)
        assert TaskStatus.READY.can_transition_to(TaskStatus.CANCELLED)
        
        # Valid transitions from IN_PROGRESS
        assert TaskStatus.IN_PROGRESS.can_transition_to(TaskStatus.DONE)
        assert TaskStatus.IN_PROGRESS.can_transition_to(TaskStatus.FAILED)
        assert TaskStatus.IN_PROGRESS.can_transition_to(TaskStatus.CANCELLED)
        
        # Valid transitions from FAILED (can retry)
        assert TaskStatus.FAILED.can_transition_to(TaskStatus.READY)
        
        # Invalid transitions
        assert not TaskStatus.READY.can_transition_to(TaskStatus.DONE)
        assert not TaskStatus.IN_PROGRESS.can_transition_to(TaskStatus.READY)
        assert not TaskStatus.DONE.can_transition_to(TaskStatus.READY)
        assert not TaskStatus.CANCELLED.can_transition_to(TaskStatus.READY)
    
    def test_task_status_from_string(self):
        """Test task status creation from string."""
        assert TaskStatus.from_string("READY") == TaskStatus.READY
        assert TaskStatus.from_string("ready") == TaskStatus.READY
        assert TaskStatus.from_string("IN_PROGRESS") == TaskStatus.IN_PROGRESS
        
        with pytest.raises(ValueError):
            TaskStatus.from_string("INVALID")
    
    def test_task_status_string_representation(self):
        """Test task status string representation."""
        assert str(TaskStatus.READY) == "READY"
        assert str(TaskStatus.DONE) == "DONE"


class TestTaskSpec:
    """Test TaskSpec domain object."""
    
    def test_task_spec_creation(self):
        """Test task spec creation."""
        spec = TaskSpec(
            tool="kubectl",
            args=["apply", "-f", "manifest.yaml"],
            env={"KUBECONFIG": "/path/to/kubeconfig"},
            timeout_sec=300
        )
        assert spec.tool == "kubectl"
        assert spec.args == ["apply", "-f", "manifest.yaml"]
        assert spec.env == {"KUBECONFIG": "/path/to/kubeconfig"}
        assert spec.timeout_sec == 300
    
    def test_task_spec_to_dict(self):
        """Test task spec to dictionary conversion."""
        spec = TaskSpec(
            tool="echo",
            args=["hello"],
            env={},
            timeout_sec=60
        )
        result = spec.to_dict()
        expected = {
            "tool": "echo",
            "args": ["hello"],
            "env": {},
            "timeout_sec": 60
        }
        assert result == expected
    
    def test_task_spec_factory_method(self):
        """Test task spec factory method."""
        spec = TaskSpec.create_simple_task("Deploy service", timeout_sec=120)
        assert spec.tool == "echo"
        assert spec.args == ["Working on Deploy service"]
        assert spec.env == {}
        assert spec.timeout_sec == 120


class TestTaskExecutionResult:
    """Test TaskExecutionResult domain object."""
    
    def test_task_execution_result_creation(self):
        """Test task execution result creation."""
        result = TaskExecutionResult(
            task_id="task-1",
            status=TaskStatus.DONE,
            artifacts_dir="/artifacts/task-1",
            exit_code=0
        )
        assert result.task_id == "task-1"
        assert result.status == TaskStatus.DONE
        assert result.artifacts_dir == "/artifacts/task-1"
        assert result.exit_code == 0
    
    def test_task_execution_result_properties(self):
        """Test task execution result properties."""
        success_result = TaskExecutionResult(
            task_id="task-1",
            status=TaskStatus.DONE,
            artifacts_dir="/artifacts/task-1",
            exit_code=0
        )
        
        failed_result = TaskExecutionResult(
            task_id="task-2",
            status=TaskStatus.FAILED,
            artifacts_dir="/artifacts/task-2",
            exit_code=1
        )
        
        assert success_result.is_successful
        assert not success_result.is_failed
        
        assert failed_result.is_failed
        assert not failed_result.is_successful
    
    def test_task_execution_result_to_dict(self):
        """Test task execution result to dictionary conversion."""
        result = TaskExecutionResult(
            task_id="task-1",
            status=TaskStatus.DONE,
            artifacts_dir="/artifacts/task-1",
            exit_code=0
        )
        expected = {
            "status": "DONE",
            "task_id": "task-1",
            "artifacts": "/artifacts/task-1",
            "exit_code": 0
        }
        assert result.to_dict() == expected
    
    def test_task_execution_result_from_runner_result(self):
        """Test task execution result creation from runner result."""
        runner_result = {
            "exit_code": 0,
            "artifacts_dir": "/artifacts/task-1"
        }
        
        result = TaskExecutionResult.from_runner_result("task-1", runner_result)
        assert result.task_id == "task-1"
        assert result.status == TaskStatus.DONE
        assert result.artifacts_dir == "/artifacts/task-1"
        assert result.exit_code == 0
        
        # Test failure case
        failed_runner_result = {
            "exit_code": 1,
            "artifacts_dir": "/artifacts/task-2"
        }
        
        failed_result = TaskExecutionResult.from_runner_result("task-2", failed_runner_result)
        assert failed_result.status == TaskStatus.FAILED
        assert failed_result.exit_code == 1


class TestTaskConstraints:
    """Test TaskConstraints domain object."""
    
    def test_task_constraints_creation(self):
        """Test task constraints creation."""
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3},
            cluster_spec={"nodes": 3},
            additional_constraints={"timeout": 300}
        )
        assert constraints.rubric == {"quality": "high"}
        assert constraints.architect_rubric == {"k": 3}
        assert constraints.cluster_spec == {"nodes": 3}
        assert constraints.additional_constraints == {"timeout": 300}
    
    def test_task_constraints_default_values(self):
        """Test task constraints with default values."""
        constraints = TaskConstraints(rubric={}, architect_rubric={})
        assert constraints.cluster_spec is None
        assert constraints.additional_constraints is None
    
    def test_task_constraints_methods(self):
        """Test task constraints methods."""
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 5},
            cluster_spec={"nodes": 3}
        )
        
        assert constraints.get_rubric() == {"quality": "high"}
        assert constraints.get_architect_rubric() == {"k": 5}
        assert constraints.get_cluster_spec() == {"nodes": 3}
        assert constraints.get_k_value() == 5
    
    def test_task_constraints_default_k_value(self):
        """Test task constraints default k value."""
        constraints = TaskConstraints(rubric={}, architect_rubric={})
        assert constraints.get_k_value() == 3  # default value
    
    def test_task_constraints_to_dict(self):
        """Test task constraints to dictionary conversion."""
        constraints = TaskConstraints(
            rubric={"quality": "high"},
            architect_rubric={"k": 3},
            cluster_spec={"nodes": 3},
            additional_constraints={"timeout": 300}
        )
        
        result = constraints.to_dict()
        expected = {
            "rubric": {"quality": "high"},
            "architect_rubric": {"k": 3},
            "cluster_spec": {"nodes": 3},
            "timeout": 300
        }
        assert result == expected
    
    def test_task_constraints_from_dict(self):
        """Test task constraints creation from dictionary."""
        data = {
            "rubric": {"quality": "high"},
            "architect_rubric": {"k": 3},
            "cluster_spec": {"nodes": 3},
            "timeout": 300
        }
        
        constraints = TaskConstraints.from_dict(data)
        assert constraints.rubric == {"quality": "high"}
        assert constraints.architect_rubric == {"k": 3}
        assert constraints.cluster_spec == {"nodes": 3}
        assert constraints.additional_constraints == {"timeout": 300}


class TestTaskSelectionService:
    """Test TaskSelectionService domain service."""
    
    def test_filter_ready_tasks(self):
        """Test filtering ready tasks."""
        # Create mock tasks with different statuses
        class MockTask:
            def __init__(self, task_id: str, status: str):
                self.id = task_id
                self.status = status
        
        tasks = [
            MockTask("task-1", "READY"),
            MockTask("task-2", "IN_PROGRESS"),
            MockTask("task-3", "DONE"),
            MockTask("task-4", "FAILED"),
        ]
        
        ready_tasks = TaskSelectionService.filter_ready_tasks(tasks)
        assert len(ready_tasks) == 2
        assert ready_tasks[0].id == "task-1"
        assert ready_tasks[1].id == "task-2"
    
    def test_select_task_no_candidates(self):
        """Test task selection with no ready candidates."""
        class MockTask:
            def __init__(self, task_id: str, status: str):
                self.id = task_id
                self.status = status
        
        tasks = [
            MockTask("task-1", "DONE"),
            MockTask("task-2", "FAILED"),
        ]
        
        selected = TaskSelectionService.select_task(tasks)
        assert selected is None
    
    def test_select_task_pick_first(self):
        """Test task selection picking first ready task."""
        class MockTask:
            def __init__(self, task_id: str, status: str):
                self.id = task_id
                self.status = status
        
        tasks = [
            MockTask("task-1", "READY"),
            MockTask("task-2", "READY"),
        ]
        
        selected = TaskSelectionService.select_task(tasks, pick_first=True)
        assert selected.id == "task-1"
    
    def test_select_task_pick_by_priority(self):
        """Test task selection using priority logic."""
        class MockTask:
            def __init__(self, task_id: str, status: str):
                self.id = task_id
                self.status = status
        
        tasks = [
            MockTask("task-1", "READY"),
            MockTask("task-2", "READY"),
        ]
        
        selected = TaskSelectionService.select_task(tasks, pick_first=False)
        assert selected.id == "task-1"  # Should pick first one (simple priority logic)


class TestCheckResults:
    """Test CheckResult concrete implementations."""
    
    def test_concrete_check_result(self):
        """Test concrete check result implementation."""
        result = ConcreteCheckResult(ok=True, issues=[])
        assert result.ok is True
        assert result.get_issues() == []
        assert result.get_score() == 1.0
        assert result.to_dict() == {"ok": True, "issues": []}
        
        failed_result = ConcreteCheckResult(ok=False, issues=["error1", "error2"])
        assert failed_result.ok is False
        assert failed_result.get_issues() == ["error1", "error2"]
        assert failed_result.get_score() == 0.0
        assert failed_result.to_dict() == {"ok": False, "issues": ["error1", "error2"]}
    
    def test_lint_check_result(self):
        """Test lint check result."""
        success_result = LintCheckResult.success()
        assert success_result.ok is True
        assert success_result.issues == []
        assert success_result.get_score() == 1.0
        
        failure_result = LintCheckResult.failure(["syntax error"])
        assert failure_result.ok is False
        assert failure_result.issues == ["syntax error"]
        assert failure_result.get_score() == 0.0
    
    def test_dryrun_check_result(self):
        """Test dryrun check result."""
        success_result = DryrunCheckResult.success()
        assert success_result.ok is True
        assert success_result.errors == []
        assert success_result.get_score() == 1.0
        
        failure_result = DryrunCheckResult.failure(["validation error"])
        assert failure_result.ok is False
        assert failure_result.errors == ["validation error"]
        assert failure_result.get_score() == 0.0
    
    def test_policy_check_result(self):
        """Test policy check result."""
        success_result = PolicyCheckResult.success()
        assert success_result.ok is True
        assert success_result.violations == []
        assert success_result.get_score() == 1.0
        
        failure_result = PolicyCheckResult.failure(["policy violation"])
        assert failure_result.ok is False
        assert failure_result.violations == ["policy violation"]
        assert failure_result.get_score() == 0.0
    
    def test_check_suite_result(self):
        """Test check suite result."""
        lint_result = LintCheckResult.success()
        dryrun_result = DryrunCheckResult.success()
        policy_result = PolicyCheckResult.success()
        
        suite = CheckSuiteResult(
            lint=lint_result,
            dryrun=dryrun_result,
            policy=policy_result
        )
        
        assert suite.overall_score == 1.0
        assert suite.is_perfect is True
        assert suite.has_issues is False
        assert suite.get_all_issues() == {"lint": [], "dryrun": [], "policy": []}
        
        # Test with issues
        lint_with_issues = LintCheckResult.failure(["syntax error"])
        suite_with_issues = CheckSuiteResult(
            lint=lint_with_issues,
            dryrun=dryrun_result,
            policy=policy_result
        )
        
        assert suite_with_issues.overall_score == 2.0 / 3.0
        assert suite_with_issues.is_perfect is False
        assert suite_with_issues.has_issues is True
