"""Unit tests for RunnerTool."""

import os
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.agents_and_tools.tools.runner.runner_tool import (
    RunnerTool,
    TaskInfo,
    TaskResult,
    TaskSpec,
    TaskStatus,
)


class TestRunnerToolInitialization:
    """Test RunnerTool initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        runner = RunnerTool()

        assert runner.runtime in ("docker", "podman")
        assert runner.registry == "localhost"
        assert runner.tasks == {}

    def test_init_with_custom_runtime(self):
        """Test initialization with custom runtime."""
        runner = RunnerTool(runtime="docker", registry="registry.example.com")

        assert runner.runtime == "docker"
        assert runner.registry == "registry.example.com"


class TestStreamLogs:
    """Test stream_logs method."""

    @pytest.mark.asyncio
    async def test_stream_logs_success(self):
        """Test successful log streaming."""
        runner = RunnerTool()
        task_id = "test-task-001"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(
            task_id=task_id, spec=task_spec, status=TaskStatus.RUNNING, logs=["log1", "log2"]
        )
        runner.tasks[task_id] = task_info

        logs = await runner.stream_logs(task_id)

        assert logs == ["log1", "log2"]

    @pytest.mark.asyncio
    async def test_stream_logs_raises_on_invalid_task_id(self):
        """Test that ValueError is raised for invalid task_id."""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task invalid-task not found"):
            await runner.stream_logs("invalid-task")

    @pytest.mark.asyncio
    async def test_stream_logs_returns_empty_list_when_no_logs(self):
        """Test that empty list is returned when task has no logs."""
        runner = RunnerTool()
        task_id = "test-task-002"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.PENDING, logs=[])
        runner.tasks[task_id] = task_info

        logs = await runner.stream_logs(task_id)

        assert logs == []


class TestCopyArtifacts:
    """Test copy_artifacts method."""

    @pytest.mark.asyncio
    async def test_copy_artifacts_success(self):
        """Test successful artifact copying."""
        runner = RunnerTool()
        task_id = "test-task-001"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.PASSED)
        runner.tasks[task_id] = task_info

        artifact_path = await runner.copy_artifacts(task_id, "/workspace/output/test.txt")

        assert artifact_path.startswith("s3://fleet-builds/")
        assert task_id in artifact_path
        assert "test.txt" in artifact_path

    @pytest.mark.asyncio
    async def test_copy_artifacts_raises_on_invalid_task_id(self):
        """Test that ValueError is raised for invalid task_id."""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task invalid-task not found"):
            await runner.copy_artifacts("invalid-task", "/path/to/artifact")

    @pytest.mark.asyncio
    async def test_copy_artifacts_extracts_filename_from_path(self):
        """Test that filename is extracted from path."""
        runner = RunnerTool()
        task_id = "test-task-002"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.PASSED)
        runner.tasks[task_id] = task_info

        artifact_path = await runner.copy_artifacts(
            task_id, "/very/long/path/to/report.json"
        )

        assert "report.json" in artifact_path


class TestCancel:
    """Test cancel method."""

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        """Test cancelling a pending task."""
        runner = RunnerTool()
        task_id = "test-task-001"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["sleep", "10"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.PENDING)
        runner.tasks[task_id] = task_info

        result = await runner.cancel(task_id)

        assert result is True
        assert task_info.status == TaskStatus.ERROR
        assert task_info.finished_at is not None

    @pytest.mark.asyncio
    async def test_cancel_running_task(self):
        """Test cancelling a running task."""
        runner = RunnerTool()
        task_id = "test-task-002"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["sleep", "10"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.RUNNING)
        runner.tasks[task_id] = task_info

        result = await runner.cancel(task_id)

        assert result is True
        assert task_info.status == TaskStatus.ERROR

    @pytest.mark.asyncio
    async def test_cancel_completed_task_returns_false(self):
        """Test cancelling a completed task returns False."""
        runner = RunnerTool()
        task_id = "test-task-003"
        task_spec = TaskSpec(
            image="test-image",
            cmd=["echo", "done"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        task_info = TaskInfo(task_id=task_id, spec=task_spec, status=TaskStatus.PASSED)
        runner.tasks[task_id] = task_info

        result = await runner.cancel(task_id)

        assert result is False
        assert task_info.status == TaskStatus.PASSED  # Status unchanged

    @pytest.mark.asyncio
    async def test_cancel_raises_on_invalid_task_id(self):
        """Test that ValueError is raised for invalid task_id."""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task invalid-task not found"):
            await runner.cancel("invalid-task")


class TestHealth:
    """Test health method."""

    @pytest.mark.asyncio
    async def test_health_with_no_tasks(self):
        """Test health check with no tasks."""
        runner = RunnerTool()

        health_info = await runner.health()

        assert health_info["status"] == "healthy"
        assert health_info["runtime"] in ("docker", "podman")
        assert health_info["registry"] == "localhost"
        assert health_info["active_tasks"] == 0
        assert health_info["total_tasks"] == 0

    @pytest.mark.asyncio
    async def test_health_with_running_tasks(self):
        """Test health check with running tasks."""
        runner = RunnerTool()

        # Add some tasks with different statuses
        task_spec = TaskSpec(
            image="test-image",
            cmd=["sleep", "10"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )
        runner.tasks["task-1"] = TaskInfo(
            task_id="task-1", spec=task_spec, status=TaskStatus.RUNNING
        )
        runner.tasks["task-2"] = TaskInfo(
            task_id="task-2", spec=task_spec, status=TaskStatus.PENDING
        )
        runner.tasks["task-3"] = TaskInfo(
            task_id="task-3", spec=task_spec, status=TaskStatus.PASSED
        )

        health_info = await runner.health()

        assert health_info["status"] == "healthy"
        assert health_info["active_tasks"] == 1  # Only RUNNING tasks count
        assert health_info["total_tasks"] == 3

    @pytest.mark.asyncio
    async def test_health_with_custom_registry(self):
        """Test health check with custom registry."""
        runner = RunnerTool(registry="registry.example.com")

        health_info = await runner.health()

        assert health_info["registry"] == "registry.example.com"


class TestDetectRuntime:
    """Test _detect_runtime method."""

    def test_detect_runtime_with_explicit_runtime(self):
        """Test that explicit runtime is returned."""
        runner = RunnerTool(runtime="kubernetes")

        assert runner.runtime == "kubernetes"

    @patch.dict(os.environ, {"KUBERNETES_SERVICE_HOST": "10.0.0.1"})
    def test_detect_runtime_kubernetes(self):
        """Test Kubernetes runtime detection."""
        runner = RunnerTool(runtime="auto")

        assert runner.runtime == "kubernetes"

    @patch("subprocess.run")
    @patch.dict(os.environ, {}, clear=True)
    def test_detect_runtime_docker(self, mock_subprocess):
        """Test Docker runtime detection."""
        mock_subprocess.return_value = MagicMock()

        runner = RunnerTool(runtime="auto")

        assert runner.runtime == "docker"
        mock_subprocess.assert_called_once()

    @patch("subprocess.run")
    @patch.dict(os.environ, {}, clear=True)
    def test_detect_runtime_fallback_to_docker(self, mock_subprocess):
        """Test fallback to docker when runtime detection fails."""
        mock_subprocess.side_effect = FileNotFoundError()

        runner = RunnerTool(runtime="auto")

        assert runner.runtime == "docker"


class TestRunTask:
    """Test run_task method."""

    @pytest.mark.asyncio
    async def test_run_task_creates_task_with_docker_runtime(self):
        """Test that run_task creates task and uses docker runtime."""
        runner = RunnerTool(runtime="docker")
        spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={"VAR": "value"},
            mounts=[{"type": "bind", "source": "/tmp", "target": "/workspace"}],
            timeouts={"overallSec": 60},
            resources={"cpu": "1"},
            artifacts={"paths": ["/workspace/output"]},
            context={"case_id": "test-001"},
        )

        # Mock _run_local_task to avoid actual container execution
        runner._run_local_task = AsyncMock()

        task_id = await runner.run_task(spec)

        assert task_id in runner.tasks
        task_info = runner.tasks[task_id]
        assert task_info.spec == spec
        assert task_info.status == TaskStatus.PENDING
        runner._run_local_task.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_task_uses_kubernetes_runtime(self):
        """Test that run_task uses kubernetes runtime when configured."""
        runner = RunnerTool(runtime="kubernetes")
        spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )

        # Mock _run_kubernetes_task with AsyncMock
        runner._run_kubernetes_task = AsyncMock()

        task_id = await runner.run_task(spec)

        assert task_id in runner.tasks
        runner._run_kubernetes_task.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_run_task_raises_not_implemented_for_kubernetes(self):
        """Test that run_task raises NotImplementedError for kubernetes."""
        runner = RunnerTool(runtime="kubernetes")
        spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={},
        )

        with pytest.raises(NotImplementedError, match="Kubernetes execution not yet implemented"):
            await runner.run_task(spec)


class TestAwaitResult:
    """Test await_result method."""

    @pytest.mark.asyncio
    async def test_await_result_completed_task(self):
        """Test awaiting result for already completed task."""
        runner = RunnerTool()
        task_id = "test-task-001"
        spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={"paths": ["/workspace/output.json"]},
            context={"case_id": "test-001", "task_id": "task-001"},
        )
        started_at = datetime.now(UTC)
        finished_at = datetime.now(UTC)
        task_info = TaskInfo(
            task_id=task_id,
            spec=spec,
            status=TaskStatus.PASSED,
            started_at=started_at,
            finished_at=finished_at,
        )
        runner.tasks[task_id] = task_info

        result = await runner.await_result(task_id)

        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.PASSED
        assert result.exit_code == 0
        assert "logsRef" in result.captured
        assert len(result.captured["artifacts"]) == 1
        assert result.metadata["case_id"] == "test-001"
        assert result.metadata["task_id"] == "task-001"

    @pytest.mark.asyncio
    async def test_await_result_with_timeout(self):
        """Test awaiting result with timeout."""
        runner = RunnerTool()
        task_id = "test-task-002"
        spec = TaskSpec(
            image="test-image",
            cmd=["sleep", "10"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={"paths": []},
        )
        task_info = TaskInfo(
            task_id=task_id, spec=spec, status=TaskStatus.RUNNING
        )
        runner.tasks[task_id] = task_info

        # Wait briefly, then mark as completed
        import asyncio

        async def complete_task():
            await asyncio.sleep(0.1)
            task_info.status = TaskStatus.PASSED
            task_info.started_at = datetime.now(UTC)
            task_info.finished_at = datetime.now(UTC)

        # Complete task after short delay
        asyncio.create_task(complete_task())

        result = await runner.await_result(task_id, timeout_sec=5)

        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.PASSED

    @pytest.mark.asyncio
    async def test_await_result_timeout_expires(self):
        """Test that timeout is enforced."""
        runner = RunnerTool()
        task_id = "test-task-003"
        spec = TaskSpec(
            image="test-image",
            cmd=["sleep", "10"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={"paths": []},
        )
        task_info = TaskInfo(
            task_id=task_id, spec=spec, status=TaskStatus.RUNNING
        )
        runner.tasks[task_id] = task_info

        result = await runner.await_result(task_id, timeout_sec=0.1)

        assert isinstance(result, TaskResult)
        assert result.status == TaskStatus.TIMEOUT

    @pytest.mark.asyncio
    async def test_await_result_raises_on_invalid_task_id(self):
        """Test that ValueError is raised for invalid task_id."""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task invalid-task not found"):
            await runner.await_result("invalid-task")

    @pytest.mark.asyncio
    async def test_await_result_failed_task(self):
        """Test awaiting result for failed task."""
        runner = RunnerTool()
        task_id = "test-task-004"
        spec = TaskSpec(
            image="test-image",
            cmd=["false"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={"paths": []},
        )
        started_at = datetime.now(UTC)
        finished_at = datetime.now(UTC)
        task_info = TaskInfo(
            task_id=task_id,
            spec=spec,
            status=TaskStatus.FAILED,
            started_at=started_at,
            finished_at=finished_at,
        )
        runner.tasks[task_id] = task_info

        result = await runner.await_result(task_id)

        assert result.status == TaskStatus.FAILED
        assert result.exit_code == 1

    @pytest.mark.asyncio
    async def test_await_result_without_started_finished_times(self):
        """Test awaiting result when task has no started/finished times."""
        runner = RunnerTool()
        task_id = "test-task-005"
        spec = TaskSpec(
            image="test-image",
            cmd=["echo", "test"],
            env={},
            mounts=[],
            timeouts={},
            resources={},
            artifacts={"paths": []},
        )
        task_info = TaskInfo(
            task_id=task_id, spec=spec, status=TaskStatus.PASSED
        )
        runner.tasks[task_id] = task_info

        result = await runner.await_result(task_id)

        assert result.status == TaskStatus.PASSED
        assert result.metadata["duration"] is None
        assert result.metadata["startedAt"] is None
        assert result.metadata["finishedAt"] is None


class TestMCPToolInterfaceFunctions:
    """Test MCP tool interface functions."""

    @pytest.mark.asyncio
    async def test_run_task_mcp_function(self):
        """Test run_task MCP interface function."""
        from core.agents_and_tools.tools.runner.runner_tool import run_task

        spec_dict = {
            "image": "test-image",
            "cmd": ["echo", "test"],
            "env": {},
            "mounts": [],
            "timeouts": {},
            "resources": {},
            "artifacts": {"paths": []},
        }

        # Mock RunnerTool.run_task to avoid actual execution
        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.run_task"
        with patch(patch_path, new_callable=AsyncMock) as mock_run:
            mock_run.return_value = "test-task-id"
            task_id = await run_task(spec_dict)

            assert task_id == "test-task-id"
            mock_run.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_stream_logs_mcp_function(self):
        """Test stream_logs MCP interface function."""
        from core.agents_and_tools.tools.runner.runner_tool import stream_logs

        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.stream_logs"
        with patch(patch_path, new_callable=AsyncMock) as mock_stream:
            mock_stream.return_value = ["log1", "log2"]
            logs = await stream_logs("test-task-id")

            assert logs == ["log1", "log2"]
            mock_stream.assert_awaited_once_with("test-task-id")

    @pytest.mark.asyncio
    async def test_await_result_mcp_function(self):
        """Test await_result MCP interface function."""

        from core.agents_and_tools.tools.runner.runner_tool import await_result

        mock_result = TaskResult(
            status=TaskStatus.PASSED,
            exit_code=0,
            captured={"logsRef": "s3://logs"},
            metadata={"duration": 10},
        )

        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.await_result"
        with patch(patch_path, new_callable=AsyncMock) as mock_await:
            mock_await.return_value = mock_result
            result_dict = await await_result("test-task-id", timeout_sec=30)

            assert isinstance(result_dict, dict)
            assert result_dict["status"] == TaskStatus.PASSED
            assert result_dict["exit_code"] == 0
            mock_await.assert_awaited_once_with("test-task-id", 30)

    @pytest.mark.asyncio
    async def test_copy_artifacts_mcp_function(self):
        """Test copy_artifacts MCP interface function."""
        from core.agents_and_tools.tools.runner.runner_tool import copy_artifacts

        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.copy_artifacts"
        with patch(patch_path, new_callable=AsyncMock) as mock_copy:
            mock_copy.return_value = "s3://fleet-builds/task-id/file.txt"
            artifact_path = await copy_artifacts("test-task-id", "/path/to/file.txt")

            assert artifact_path == "s3://fleet-builds/task-id/file.txt"
            mock_copy.assert_awaited_once_with("test-task-id", "/path/to/file.txt")

    @pytest.mark.asyncio
    async def test_cancel_mcp_function(self):
        """Test cancel MCP interface function."""
        from core.agents_and_tools.tools.runner.runner_tool import cancel

        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.cancel"
        with patch(patch_path, new_callable=AsyncMock) as mock_cancel:
            mock_cancel.return_value = True
            result = await cancel("test-task-id")

            assert result is True
            mock_cancel.assert_awaited_once_with("test-task-id")

    @pytest.mark.asyncio
    async def test_health_mcp_function(self):
        """Test health MCP interface function."""
        from core.agents_and_tools.tools.runner.runner_tool import health

        expected_health = {
            "status": "healthy",
            "runtime": "docker",
            "registry": "localhost",
            "active_tasks": 0,
            "total_tasks": 0,
        }

        patch_path = "core.agents_and_tools.tools.runner.runner_tool.RunnerTool.health"
        with patch(patch_path, new_callable=AsyncMock) as mock_health:
            mock_health.return_value = expected_health
            health_info = await health()

            assert health_info == expected_health
            mock_health.assert_awaited_once()

