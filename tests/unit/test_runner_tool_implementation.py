#!/usr/bin/env python3
"""
Additional unit tests for SWE AI Fleet Runner Tool

Tests the actual implementation methods to achieve 80% coverage.
"""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from swe_ai_fleet.tools.runner.runner_tool import (
    RunnerTool,
    TaskInfo,
    TaskSpec,
    TaskStatus,
    cancel,
    copy_artifacts,
    health,
    run_task,
    stream_logs,
)


class TestRunnerToolImplementation:
    """Test the actual implementation methods of RunnerTool"""

    @pytest.mark.asyncio
    async def test_run_local_task_success(self):
        """Test successful local task execution"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "-c", "print('Hello World')"],
            env={"TEST": "true"},
            mounts=[{"type": "bind", "source": "/tmp", "target": "/workspace"}],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/output"]},
            context={"case_id": "test-001", "task_id": "test-task"},
        )

        runner = RunnerTool(runtime="docker")
        task_id = "test-task-001"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        # Mock subprocess execution
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()

            # Create a proper async iterator
            async def async_iter():
                for line in [b"Hello World\n", b"Task completed\n"]:
                    yield line

            mock_process.stdout = async_iter()
            mock_process.wait = AsyncMock(return_value=0)
            mock_subprocess.return_value = mock_process

            await runner._run_local_task(task_info)

            assert task_info.status == TaskStatus.PASSED
            assert task_info.started_at is not None
            assert task_info.finished_at is not None
            assert len(task_info.logs) == 2
            assert "Hello World" in task_info.logs
            assert "Task completed" in task_info.logs

    @pytest.mark.asyncio
    async def test_run_local_task_failure(self):
        """Test failed local task execution"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "-c", "exit(1)"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool(runtime="docker")
        task_id = "test-task-002"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        # Mock subprocess execution with failure
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_process = AsyncMock()

            # Create a proper async iterator
            async def async_iter():
                for line in [b"Error occurred\n"]:
                    yield line

            mock_process.stdout = async_iter()
            mock_process.wait = AsyncMock(return_value=1)
            mock_subprocess.return_value = mock_process

            await runner._run_local_task(task_info)

            assert task_info.status == TaskStatus.FAILED
            assert task_info.started_at is not None
            assert task_info.finished_at is not None
            assert "Error occurred" in task_info.logs

    @pytest.mark.asyncio
    async def test_run_local_task_exception(self):
        """Test local task execution with exception"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "-c", "print('Hello')"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool(runtime="docker")
        task_id = "test-task-003"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        # Mock subprocess execution with exception
        with patch('asyncio.create_subprocess_exec') as mock_subprocess:
            mock_subprocess.side_effect = Exception("Subprocess failed")

            await runner._run_local_task(task_info)

            assert task_info.status == TaskStatus.ERROR
            assert task_info.finished_at is not None

    @pytest.mark.asyncio
    async def test_run_kubernetes_task(self):
        """Test Kubernetes task execution (not implemented)"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool(runtime="kubernetes")
        task_id = "test-task-004"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        with pytest.raises(NotImplementedError, match="Kubernetes execution not yet implemented"):
            await runner._run_kubernetes_task(task_info)

    @pytest.mark.asyncio
    async def test_stream_logs_success(self):
        """Test successful log streaming"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-005"
        task_info = TaskInfo(
            task_id=task_id,
            spec=spec,
            status=TaskStatus.RUNNING,
            logs=["Log line 1", "Log line 2"],
            artifacts={},
        )
        runner.tasks[task_id] = task_info

        logs = await runner.stream_logs(task_id)

        assert logs == ["Log line 1", "Log line 2"]
        assert logs is not task_info.logs  # Should be a copy

    @pytest.mark.asyncio
    async def test_stream_logs_not_found(self):
        """Test log streaming for non-existent task"""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task non-existent not found"):
            await runner.stream_logs("non-existent")

    @pytest.mark.asyncio
    async def test_await_result_success(self):
        """Test awaiting successful task result"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": ["/workspace/output.txt"]},
            context={"case_id": "test-001", "task_id": "test-task"},
        )

        runner = RunnerTool()
        task_id = "test-task-006"
        started_at = datetime.utcnow()
        finished_at = datetime.utcnow()

        task_info = TaskInfo(
            task_id=task_id,
            spec=spec,
            status=TaskStatus.PASSED,
            container_id="container-123",
            started_at=started_at,
            finished_at=finished_at,
            logs=["Task completed"],
            artifacts={},
        )
        runner.tasks[task_id] = task_info

        result = await runner.await_result(task_id)

        assert result.status == TaskStatus.PASSED
        assert result.exitCode == 0
        assert "logsRef" in result.captured
        assert "artifacts" in result.captured
        assert len(result.captured["artifacts"]) == 1
        assert result.metadata["containerId"] == "container-123"
        assert result.metadata["case_id"] == "test-001"
        assert result.metadata["task_id"] == "test-task"
        assert result.metadata["duration"] is not None

    @pytest.mark.asyncio
    async def test_await_result_timeout(self):
        """Test awaiting task result with timeout"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-007"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.RUNNING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        # Mock time to simulate timeout
        with patch('time.time') as mock_time:
            mock_time.side_effect = [0, 0.05, 0.15]  # Start, check, timeout

            result = await runner.await_result(task_id, timeout_sec=0.1)

            assert result.status == TaskStatus.TIMEOUT
            assert result.exitCode == 1

    @pytest.mark.asyncio
    async def test_await_result_not_found(self):
        """Test awaiting result for non-existent task"""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task non-existent not found"):
            await runner.await_result("non-existent")

    @pytest.mark.asyncio
    async def test_copy_artifacts(self):
        """Test artifact copying"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-008"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PASSED, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        artifact_ref = await runner.copy_artifacts(task_id, "/workspace/output.txt")

        assert artifact_ref == f"s3://fleet-builds/{task_id}/output.txt/"

    @pytest.mark.asyncio
    async def test_copy_artifacts_not_found(self):
        """Test artifact copying for non-existent task"""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task non-existent not found"):
            await runner.copy_artifacts("non-existent", "/path/to/file")

    @pytest.mark.asyncio
    async def test_cancel_running_task(self):
        """Test cancelling a running task"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-009"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.RUNNING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        cancelled = await runner.cancel(task_id)

        assert cancelled is True
        assert task_info.status == TaskStatus.ERROR
        assert task_info.finished_at is not None

    @pytest.mark.asyncio
    async def test_cancel_pending_task(self):
        """Test cancelling a pending task"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-010"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PENDING, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        cancelled = await runner.cancel(task_id)

        assert cancelled is True
        assert task_info.status == TaskStatus.ERROR

    @pytest.mark.asyncio
    async def test_cancel_completed_task(self):
        """Test cancelling a completed task"""
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner = RunnerTool()
        task_id = "test-task-011"
        task_info = TaskInfo(task_id=task_id, spec=spec, status=TaskStatus.PASSED, logs=[], artifacts={})
        runner.tasks[task_id] = task_info

        cancelled = await runner.cancel(task_id)

        assert cancelled is False
        assert task_info.status == TaskStatus.PASSED  # Should not change

    @pytest.mark.asyncio
    async def test_cancel_not_found(self):
        """Test cancelling non-existent task"""
        runner = RunnerTool()

        with pytest.raises(ValueError, match="Task non-existent not found"):
            await runner.cancel("non-existent")

    @pytest.mark.asyncio
    async def test_health_check(self):
        """Test health check functionality"""
        runner = RunnerTool(runtime="podman", registry="quay.io")

        # Add some tasks
        spec = TaskSpec(
            image="python:3.11",
            cmd=["python", "--version"],
            env={},
            mounts=[],
            timeouts={"overallSec": 60},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        runner.tasks["task-1"] = TaskInfo(
            task_id="task-1", spec=spec, status=TaskStatus.RUNNING, logs=[], artifacts={}
        )
        runner.tasks["task-2"] = TaskInfo(
            task_id="task-2", spec=spec, status=TaskStatus.PASSED, logs=[], artifacts={}
        )

        health_info = await runner.health()

        assert health_info["status"] == "healthy"
        assert health_info["runtime"] == "podman"
        assert health_info["registry"] == "quay.io"
        assert health_info["active_tasks"] == 1
        assert health_info["total_tasks"] == 2


class TestMCPToolFunctions:
    """Test the MCP tool interface functions"""

    @pytest.mark.asyncio
    async def test_run_task_mcp_function(self):
        """Test MCP run_task function"""
        spec_dict = {
            "image": "python:3.11",
            "cmd": ["python", "--version"],
            "env": {},
            "mounts": [],
            "timeouts": {"overallSec": 60},
            "resources": {"cpu": "1", "memory": "1Gi"},
            "artifacts": {"paths": []},
        }

        with patch('swe_ai_fleet.tools.runner.runner_tool.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.run_task = AsyncMock(return_value="test-task-001")

            task_id = await run_task(spec_dict)

            assert task_id == "test-task-001"
            mock_runner_class.assert_called_once()
            mock_runner.run_task.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_logs_mcp_function(self):
        """Test MCP stream_logs function"""
        with patch('swe_ai_fleet.tools.runner.runner_tool.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.stream_logs = AsyncMock(return_value=["Log line 1", "Log line 2"])

            logs = await stream_logs("test-task-001")

            assert logs == ["Log line 1", "Log line 2"]
            mock_runner_class.assert_called_once()
            mock_runner.stream_logs.assert_called_once_with("test-task-001")

    @pytest.mark.asyncio
    async def test_copy_artifacts_mcp_function(self):
        """Test MCP copy_artifacts function"""
        with patch('swe_ai_fleet.tools.runner.runner_tool.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.copy_artifacts = AsyncMock(return_value="s3://bucket/artifact/")

            artifact_ref = await copy_artifacts("test-task-001", "/workspace/output.txt")

            assert artifact_ref == "s3://bucket/artifact/"
            mock_runner_class.assert_called_once()
            mock_runner.copy_artifacts.assert_called_once_with("test-task-001", "/workspace/output.txt")

    @pytest.mark.asyncio
    async def test_cancel_mcp_function(self):
        """Test MCP cancel function"""
        with patch('swe_ai_fleet.tools.runner.runner_tool.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.cancel = AsyncMock(return_value=True)

            cancelled = await cancel("test-task-001")

            assert cancelled is True
            mock_runner_class.assert_called_once()
            mock_runner.cancel.assert_called_once_with("test-task-001")

    @pytest.mark.asyncio
    async def test_health_mcp_function(self):
        """Test MCP health function"""
        with patch('swe_ai_fleet.tools.runner.runner_tool.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner
            mock_runner.health = AsyncMock(return_value={"status": "healthy"})

            health_info = await health()

            assert health_info["status"] == "healthy"
            mock_runner_class.assert_called_once()
            mock_runner.health.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
