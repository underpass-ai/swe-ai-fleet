#!/usr/bin/env python3
"""
Unit tests for SWE AI Fleet Runner Tool

Tests the TaskSpec/TaskResult contract and RunnerTool functionality
with proper mocking to avoid actual container execution.
"""

from datetime import datetime

import pytest
from core.agents_and_tools.tools.runner.runner_tool import (
    RunnerTool,
    TaskInfo,
    TaskResult,
    TaskSpec,
    TaskStatus,
)


class TestTaskStatus:
    """Test TaskStatus enum"""

    def test_task_status_values(self):
        """Test TaskStatus enum values"""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.PASSED.value == "passed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.ERROR.value == "error"
        assert TaskStatus.TIMEOUT.value == "timeout"


class TestTaskSpec:
    """Test TaskSpec dataclass"""

    def test_task_spec_creation(self):
        """Test TaskSpec creation with all required fields"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={"PYTHONPATH": "/workspace"},
            mounts=[{"type": "bind", "source": "/tmp", "target": "/workspace"}],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/output"]},
        )

        assert spec.image == "python:3.11"
        assert spec.cmd == ["python", "--version"]
        assert spec.env == {"PYTHONPATH": "/workspace"}
        assert len(spec.mounts) == 1
        assert spec.timeouts == {"overallSec": 60}
        assert spec.resources == {"cpu": "1", "memory": "1Gi"}
        assert spec.artifacts == {"paths": ["/workspace/output"]}
        assert spec.context is None

    def test_task_spec_with_context(self):
        """Test TaskSpec creation with context"""
        context = {"case_id": "test-001", "role": "developer"}
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
            context=context,
        )

        assert spec.context == context


class TestTaskResult:
    """Test TaskResult dataclass"""

    def test_task_result_creation(self):
        """Test TaskResult creation"""
        result = TaskResult(
            status=TaskStatus.PASSED,
            exitCode=0,
            captured={"stdout": "Python 3.11.0", "stderr": ""},
            metadata={"duration": 1.5, "case_id": "test-001"},
        )

        assert result.status == TaskStatus.PASSED
        assert result.exitCode == 0
        assert result.captured == {"stdout": "Python 3.11.0", "stderr": ""}
        assert result.metadata == {"duration": 1.5, "case_id": "test-001"}


class TestTaskInfo:
    """Test TaskInfo dataclass"""

    def test_task_info_creation(self):
        """Test TaskInfo creation"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        task_info = TaskInfo(task_id="test-task-001", spec=spec, status=TaskStatus.PENDING)

        assert task_info.task_id == "test-task-001"
        assert task_info.spec == spec
        assert task_info.status == TaskStatus.PENDING
        assert task_info.container_id is None
        assert task_info.started_at is None
        assert task_info.finished_at is None
        assert task_info.logs is None
        assert task_info.artifacts is None


class TestRunnerTool:
    """Test RunnerTool class"""

    def test_runner_tool_init_with_runtime(self):
        """Test RunnerTool initialization with specific runtime"""
        runner = RunnerTool(runtime="docker", registry="docker.io")

        assert runner.runtime == "docker"
        assert runner.registry == "docker.io"
        assert runner.tasks == {}

    def test_runner_tool_init_with_docker(self):
        """Test RunnerTool initialization with Docker runtime"""
        runner = RunnerTool(runtime="docker", registry="docker.io")

        assert runner.runtime == "docker"
        assert runner.registry == "docker.io"
        assert runner.tasks == {}

    def test_runner_tool_init_with_kubernetes(self):
        """Test RunnerTool initialization with Kubernetes runtime"""
        runner = RunnerTool(runtime="kubernetes", registry="registry.k8s.io")

        assert runner.runtime == "kubernetes"
        assert runner.registry == "registry.k8s.io"
        assert runner.tasks == {}

    def test_task_storage(self):
        """Test task storage in RunnerTool"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool(runtime="docker")
        task_id = "test-task-001"
        runner.tasks[task_id] = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.RUNNING)

        # Test direct access to tasks
        assert task_id in runner.tasks
        assert runner.tasks[task_id].task_id == task_id
        assert runner.tasks[task_id].status == TaskStatus.RUNNING

    def test_task_spec_validation(self):
        """Test TaskSpec validation and structure"""
        # Test minimal valid spec
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        assert isinstance(spec.image, str)
        assert isinstance(spec.cmd, list)
        assert isinstance(spec.env, dict)
        assert isinstance(spec.mounts, list)
        assert isinstance(spec.timeouts, dict)
        assert isinstance(spec.resources, dict)
        assert isinstance(spec.artifacts, dict)

    def test_task_result_validation(self):
        """Test TaskResult validation and structure"""
        result = TaskResult(
            status=TaskStatus.PASSED,
            exitCode=0,
            captured={"stdout": "test output", "stderr": ""},
            metadata={"duration": 1.0},
        )

        assert isinstance(result.status, TaskStatus)
        assert isinstance(result.exitCode, int)
        assert isinstance(result.captured, dict)
        assert isinstance(result.metadata, dict)
        assert result.exitCode == 0
        assert result.status == TaskStatus.PASSED

    def test_task_info_validation(self):
        """Test TaskInfo validation and structure"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        task_info = TaskInfo(
            task_id="test-task-001",
            spec=spec,
            status=TaskStatus.PENDING,
            container_id="container-123",
            started_at=datetime.now(),
            finished_at=None,
            logs=["log line 1", "log line 2"],
            artifacts={"output": "/workspace/output.txt"},
        )

        assert isinstance(task_info.task_id, str)
        assert isinstance(task_info.spec, TaskSpec)
        assert isinstance(task_info.status, TaskStatus)
        assert isinstance(task_info.logs, list)
        assert isinstance(task_info.artifacts, dict)
        assert task_info.container_id == "container-123"
        assert task_info.started_at is not None
        assert task_info.finished_at is None

    def test_mount_validation(self):
        """Test mount specification validation"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[
                {"type": "bind", "source": "/tmp/test", "target": "/workspace"},
                {"type": "volume", "source": "test-volume", "target": "/data"},
            ],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        assert len(spec.mounts) == 2
        assert spec.mounts[0]["type"] == "bind"
        assert spec.mounts[0]["source"] == "/tmp/test"
        assert spec.mounts[0]["target"] == "/workspace"
        assert spec.mounts[1]["type"] == "volume"
        assert spec.mounts[1]["source"] == "test-volume"
        assert spec.mounts[1]["target"] == "/data"

    def test_resource_validation(self):
        """Test resource specification validation"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "2", "memory": "4Gi", "gpu": "1"},
            artifacts={"paths": []},
        )

        assert spec.resources["cpu"] == "2"
        assert spec.resources["memory"] == "4Gi"
        assert spec.resources["gpu"] == "1"

    def test_timeout_validation(self):
        """Test timeout specification validation"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 300, "setupSec": 30, "teardownSec": 10},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        assert spec.timeouts["overallSec"] == 300
        assert spec.timeouts["setupSec"] == 30
        assert spec.timeouts["teardownSec"] == 10

    def test_artifact_validation(self):
        """Test artifact specification validation"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={
                "paths": ["/workspace/output", "/workspace/logs"],
                "patterns": ["*.log", "*.json"],
                "exclude": ["*.tmp"],
            },
        )

        assert len(spec.artifacts["paths"]) == 2
        assert "/workspace/output" in spec.artifacts["paths"]
        assert "/workspace/logs" in spec.artifacts["paths"]
        assert "patterns" in spec.artifacts
        assert "exclude" in spec.artifacts

    def test_context_validation(self):
        """Test context specification validation"""
        context = {
            "case_id": "test-case-001",
            "task_id": "test-task-001",
            "role": "developer",
            "phase": "implementation",
            "priority": "high",
        }

        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
            context=context,
        )

        assert spec.context == context
        assert spec.context["case_id"] == "test-case-001"
        assert spec.context["role"] == "developer"
        assert spec.context["priority"] == "high"


class TestRunnerToolIntegration:
    """Integration tests for RunnerTool data structures"""

    def test_complete_task_spec(self):
        """Test complete TaskSpec with all fields"""
        context = {
            "case_id": "integration-test-001",
            "task_id": "python-unit-tests",
            "role": "developer",
            "phase": "testing",
            "priority": "medium",
            "dependencies": ["setup-env", "install-deps"],
        }

        spec = TaskSpec(
            image="python:3.11-bookworm",
            cmd=["python", "-m", "pytest", "tests/", "-v"],
            env={"PYTHONPATH": "/workspace", "PYTEST_CURRENT_TEST": "true", "CI": "true"},
            mounts=[
                {"type": "bind", "source": "/tmp/test-workspace", "target": "/workspace"},
                {"type": "volume", "source": "test-cache", "target": "/cache"},
            ],
            timeouts={"overallSec": 600, "setupSec": 60, "teardownSec": 30},
            resources={"cpu": "2", "memory": "4Gi", "gpu": "0"},
            artifacts={
                "paths": ["/workspace/test-results", "/workspace/coverage"],
                "patterns": ["*.xml", "*.json", "*.html"],
                "exclude": ["*.tmp", "*.log"],
            },
            context=context,
        )

        # Validate all fields
        assert spec.image == "python:3.11-bookworm"
        assert len(spec.cmd) == 5  # ['python', '-m', 'pytest', 'tests/', '-v']
        assert "pytest" in spec.cmd
        assert len(spec.env) == 3
        assert spec.env["CI"] == "true"
        assert len(spec.mounts) == 2
        assert len(spec.timeouts) == 3
        assert spec.timeouts["overallSec"] == 600
        assert len(spec.resources) == 3
        assert spec.resources["memory"] == "4Gi"
        assert len(spec.artifacts["paths"]) == 2
        assert len(spec.context) == 6
        assert spec.context["role"] == "developer"

    def test_task_result_scenarios(self):
        """Test different TaskResult scenarios"""

        # Successful execution
        success_result = TaskResult(
            status=TaskStatus.PASSED,
            exitCode=0,
            captured={
                "stdout": "All tests passed!\n",
                "stderr": "",
                "logs": ["Starting tests...", "Running 15 tests", "All passed!"],
            },
            metadata={
                "duration": 45.2,
                "case_id": "test-001",
                "task_id": "unit-tests",
                "role": "developer",
                "resources_used": {"cpu": "1.8", "memory": "2.1Gi"},
            },
        )

        assert success_result.status == TaskStatus.PASSED
        assert success_result.exitCode == 0
        assert "All tests passed" in success_result.captured["stdout"]
        assert success_result.metadata["duration"] == 45.2

        # Failed execution
        failed_result = TaskResult(
            status=TaskStatus.FAILED,
            exitCode=1,
            captured={
                "stdout": "",
                "stderr": "Test failed: AssertionError\n",
                "logs": ["Starting tests...", "Test failed!"],
            },
            metadata={
                "duration": 12.5,
                "case_id": "test-002",
                "task_id": "integration-tests",
                "role": "developer",
                "error_type": "AssertionError",
            },
        )

        assert failed_result.status == TaskStatus.FAILED
        assert failed_result.exitCode == 1
        assert "AssertionError" in failed_result.captured["stderr"]
        assert failed_result.metadata["error_type"] == "AssertionError"

        # Timeout execution
        timeout_result = TaskResult(
            status=TaskStatus.TIMEOUT,
            exitCode=124,
            captured={
                "stdout": "Running long test...\n",
                "stderr": "",
                "logs": ["Starting tests...", "Running long test..."],
            },
            metadata={
                "duration": 300.0,
                "case_id": "test-003",
                "task_id": "long-running-tests",
                "role": "developer",
                "timeout_reason": "overallSec exceeded",
            },
        )

        assert timeout_result.status == TaskStatus.TIMEOUT
        assert timeout_result.exitCode == 124
        assert timeout_result.metadata["timeout_reason"] == "overallSec exceeded"

    def test_task_info_lifecycle(self):
        """Test TaskInfo lifecycle states"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        # Initial state
        task_info = TaskInfo(task_id="lifecycle-test-001", spec=spec, status=TaskStatus.PENDING)

        assert task_info.status == TaskStatus.PENDING
        assert task_info.started_at is None
        assert task_info.finished_at is None
        assert task_info.container_id is None

        # Running state
        task_info.status = TaskStatus.RUNNING
        task_info.started_at = datetime.now()
        task_info.container_id = "container-abc123"
        task_info.logs = ["Container started", "Command executing"]

        assert task_info.status == TaskStatus.RUNNING
        assert task_info.started_at is not None
        assert task_info.container_id == "container-abc123"
        assert len(task_info.logs) == 2

        # Completed state
        task_info.status = TaskStatus.PASSED
        task_info.finished_at = datetime.now()
        task_info.logs.append("Command completed successfully")
        task_info.artifacts = {"output": "/workspace/result.txt"}

        assert task_info.status == TaskStatus.PASSED
        assert task_info.finished_at is not None
        assert len(task_info.logs) == 3
        assert task_info.artifacts["output"] == "/workspace/result.txt"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
