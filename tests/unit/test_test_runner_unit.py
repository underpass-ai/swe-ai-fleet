#!/usr/bin/env python3
"""
Unit tests for SWE AI Fleet Runner Tool test_runner.py

Tests the demonstration functions and test scenarios in test_runner.py
with proper mocking to avoid actual container execution.
"""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from core.agents_and_tools.tools.runner.runner_tool import TaskSpec, TaskStatus
from core.agents_and_tools.tools.runner.test_runner import (
    demo_basic_task,
    demo_go_task,
    demo_health_check,
    demo_main,
    demo_task_cancellation,
)


class TestTestRunnerFunctions:
    """Test the test functions in test_runner.py"""

    @pytest.mark.asyncio
    async def test_demo_basic_task_structure(self):
        """Test the structure and logic of demo_basic_task function"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()

            # Create a simple test script
            test_script = workspace_path / "test.py"
            test_script.write_text("""
import sys
print("Hello from Python!")
print("Python version:", sys.version)
print("Working directory:", sys.path[0])
""")

            # Mock the RunnerTool methods
            with patch('core.agents_and_tools.tools.runner.test_runner.RunnerTool') as mock_runner_class:
                mock_runner = MagicMock()
                mock_runner_class.return_value = mock_runner

                # Mock async methods
                mock_runner.run_task = AsyncMock(return_value="test-task-001")
                mock_runner.stream_logs = AsyncMock(
                    return_value=["Hello from Python!", "Python version: 3.11.0"]
                )
                mock_runner.await_result = AsyncMock(
                    return_value=MagicMock(
                        status=TaskStatus.PASSED,
                        exitCode=0,
                        metadata={"duration": 1.5, "case_id": "test-case-001"},
                    )
                )

                # Test the function
                result = await demo_basic_task()

                # Verify the result
                assert result is True

                # Verify RunnerTool was called
                mock_runner_class.assert_called_once()
                mock_runner.run_task.assert_called_once()
                mock_runner.stream_logs.assert_called_once()
                mock_runner.await_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_go_task_structure(self):
        """Test the structure and logic of demo_go_task function"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()

            # Create a simple Go test
            go_file = workspace_path / "demo_main.go"
            go_file.write_text("""
package demo_main

import "fmt"

func demo_main() {
    fmt.Println("Hello from Go!")
    fmt.Println("This is a test program")
}
""")

            # Mock the RunnerTool methods
            with patch('core.agents_and_tools.tools.runner.test_runner.RunnerTool') as mock_runner_class:
                mock_runner = MagicMock()
                mock_runner_class.return_value = mock_runner

                # Mock async methods
                mock_runner.run_task = AsyncMock(return_value="go-task-001")
                mock_runner.await_result = AsyncMock(
                    return_value=MagicMock(status=TaskStatus.PASSED, exitCode=0)
                )

                # Test the function
                result = await demo_go_task()

                # Verify the result
                assert result is True

                # Verify RunnerTool was called
                mock_runner_class.assert_called_once()
                mock_runner.run_task.assert_called_once()
                mock_runner.await_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_health_check_structure(self):
        """Test the structure and logic of demo_health_check function"""
        # Mock the RunnerTool methods
        with patch('core.agents_and_tools.tools.runner.test_runner.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner

            # Mock async methods
            mock_runner.health = AsyncMock(
                return_value={
                    'status': 'healthy',
                    'runtime': 'docker',
                    'registry': 'localhost',
                    'active_tasks': 0,
                }
            )

            # Test the function
            result = await demo_health_check()

            # Verify the result
            assert result is True

            # Verify RunnerTool was called
            mock_runner_class.assert_called_once()
            mock_runner.health.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_health_check_unhealthy(self):
        """Test demo_health_check with unhealthy status"""
        # Mock the RunnerTool methods
        with patch('core.agents_and_tools.tools.runner.test_runner.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner

            # Mock async methods
            mock_runner.health = AsyncMock(
                return_value={
                    'status': 'unhealthy',
                    'runtime': 'docker',
                    'registry': 'localhost',
                    'active_tasks': 0,
                }
            )

            # Test the function
            result = await demo_health_check()

            # Verify the result
            assert result is False

    @pytest.mark.asyncio
    async def test_demo_task_cancellation_structure(self):
        """Test the structure and logic of demo_task_cancellation function"""
        # Mock the RunnerTool methods
        with patch('core.agents_and_tools.tools.runner.test_runner.RunnerTool') as mock_runner_class:
            mock_runner = MagicMock()
            mock_runner_class.return_value = mock_runner

            # Mock async methods
            mock_runner.run_task = AsyncMock(return_value="cancel-task-001")
            mock_runner.cancel = AsyncMock(return_value=True)
            mock_runner.await_result = AsyncMock(return_value=MagicMock(status=TaskStatus.ERROR, exitCode=1))

            # Mock asyncio.sleep to avoid actual delay
            with patch('core.agents_and_tools.tools.runner.test_runner.asyncio.sleep') as mock_sleep:
                mock_sleep.return_value = AsyncMock()

                # Test the function
                result = await demo_task_cancellation()

                # Verify the result
                assert result is True

                # Verify RunnerTool was called
                mock_runner_class.assert_called_once()
                mock_runner.run_task.assert_called_once()
                mock_runner.cancel.assert_called_once()
                mock_runner.await_result.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_main_function_structure(self):
        """Test the demo_main function structure and logic"""
        # Mock all test functions
        with (
            patch('core.agents_and_tools.tools.runner.test_runner.demo_basic_task') as mock_basic,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_go_task') as mock_go,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_health_check') as mock_health,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_task_cancellation') as mock_cancel,
        ):
            # Mock async functions
            mock_basic.return_value = AsyncMock(return_value=True)
            mock_go.return_value = AsyncMock(return_value=True)
            mock_health.return_value = AsyncMock(return_value=True)
            mock_cancel.return_value = AsyncMock(return_value=True)

            # Test the demo_main function
            await demo_main()

            # Verify all test functions were called
            mock_basic.assert_called_once()
            mock_go.assert_called_once()
            mock_health.assert_called_once()
            mock_cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_main_function_with_failures(self):
        """Test the demo_main function with some test failures"""
        # Mock all test functions with mixed results
        with (
            patch('core.agents_and_tools.tools.runner.test_runner.demo_basic_task') as mock_basic,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_go_task') as mock_go,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_health_check') as mock_health,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_task_cancellation') as mock_cancel,
        ):
            # Mock async functions with mixed results
            mock_basic.return_value = AsyncMock(return_value=True)
            mock_go.return_value = AsyncMock(return_value=False)
            mock_health.return_value = AsyncMock(return_value=True)
            mock_cancel.return_value = AsyncMock(return_value=False)

            # Test the demo_main function
            await demo_main()

            # Verify all test functions were called
            mock_basic.assert_called_once()
            mock_go.assert_called_once()
            mock_health.assert_called_once()
            mock_cancel.assert_called_once()

    @pytest.mark.asyncio
    async def test_demo_main_function_with_exceptions(self):
        """Test the demo_main function with exceptions"""
        # Mock all test functions with exceptions
        with (
            patch('core.agents_and_tools.tools.runner.test_runner.demo_basic_task') as mock_basic,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_go_task') as mock_go,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_health_check') as mock_health,
            patch('core.agents_and_tools.tools.runner.test_runner.demo_task_cancellation') as mock_cancel,
        ):
            # Mock async functions with exceptions
            mock_basic.return_value = AsyncMock(side_effect=Exception("Test error"))
            mock_go.return_value = AsyncMock(return_value=True)
            mock_health.return_value = AsyncMock(return_value=True)
            mock_cancel.return_value = AsyncMock(return_value=True)

            # Test the demo_main function
            await demo_main()

            # Verify all test functions were called
            mock_basic.assert_called_once()
            mock_go.assert_called_once()
            mock_health.assert_called_once()
            mock_cancel.assert_called_once()


class TestTestRunnerIntegration:
    """Integration tests for test_runner.py functions"""

    def test_task_spec_creation_in_demo_basic_task(self):
        """Test TaskSpec creation logic in demo_basic_task"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()

            # Create a simple test script
            test_script = workspace_path / "test.py"
            test_script.write_text("print('Hello')")

            # Test TaskSpec creation logic
            spec = TaskSpec(
                image="localhost/swe-ai-fleet-runner:latest",
                cmd=["/bin/bash", "-lc", "agent-task"],
                env={"TASK": "unit", "LANG": "python", "TEST_CMD": f"python3 {test_script.name}"},
                mounts=[{"type": "bind", "source": str(workspace_path), "target": "/workspace"}],
                timeouts={"overallSec": 60},
                resources={"cpu": "1", "memory": "1Gi"},
                artifacts={"paths": ["/workspace/test-reports"]},
                context={"case_id": "test-case-001", "task_id": "test-python-unit", "role": "developer"},
            )

            # Verify TaskSpec structure
            assert spec.image == "localhost/swe-ai-fleet-runner:latest"
            assert spec.cmd == ["/bin/bash", "-lc", "agent-task"]
            assert spec.env["TASK"] == "unit"
            assert spec.env["LANG"] == "python"
            assert spec.env["TEST_CMD"] == f"python3 {test_script.name}"
            assert len(spec.mounts) == 1
            assert spec.mounts[0]["type"] == "bind"
            assert spec.mounts[0]["target"] == "/workspace"
            assert spec.timeouts["overallSec"] == 60
            assert spec.resources["cpu"] == "1"
            assert spec.resources["memory"] == "1Gi"
            assert spec.artifacts["paths"] == ["/workspace/test-reports"]
            assert spec.context["case_id"] == "test-case-001"
            assert spec.context["role"] == "developer"

    def test_task_spec_creation_in_demo_go_task(self):
        """Test TaskSpec creation logic in demo_go_task"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()

            # Create a simple Go test
            go_file = workspace_path / "demo_main.go"
            go_file.write_text("package demo_main\n\nfunc demo_main() {\n    println(\"Hello\")\n}")

            # Test TaskSpec creation logic
            spec = TaskSpec(
                image="localhost/swe-ai-fleet-runner:latest",
                cmd=["/bin/bash", "-lc", "agent-task"],
                env={"TASK": "unit", "LANG": "go", "GO_TEST_CMD": f"go run {go_file.name}"},
                mounts=[{"type": "bind", "source": str(workspace_path), "target": "/workspace"}],
                timeouts={"overallSec": 60},
                resources={"cpu": "1", "memory": "1Gi"},
                artifacts={"paths": ["/workspace/test-reports"]},
            )

            # Verify TaskSpec structure
            assert spec.image == "localhost/swe-ai-fleet-runner:latest"
            assert spec.cmd == ["/bin/bash", "-lc", "agent-task"]
            assert spec.env["TASK"] == "unit"
            assert spec.env["LANG"] == "go"
            assert spec.env["GO_TEST_CMD"] == f"go run {go_file.name}"
            assert len(spec.mounts) == 1
            assert spec.mounts[0]["type"] == "bind"
            assert spec.mounts[0]["target"] == "/workspace"
            assert spec.timeouts["overallSec"] == 60
            assert spec.resources["cpu"] == "1"
            assert spec.resources["memory"] == "1Gi"
            assert spec.artifacts["paths"] == ["/workspace/test-reports"]

    def test_task_spec_creation_in_demo_task_cancellation(self):
        """Test TaskSpec creation logic in demo_task_cancellation"""
        # Test TaskSpec creation logic
        spec = TaskSpec(
            image="localhost/swe-ai-fleet-runner:latest",
            cmd=["/bin/bash", "-lc", "sleep 10"],
            env={"TASK": "unit", "LANG": "python"},
            mounts=[],
            timeouts={"overallSec": 5},
            resources={"cpu": "1", "memory": "1Gi"},
            artifacts={"paths": []},
        )

        # Verify TaskSpec structure
        assert spec.image == "localhost/swe-ai-fleet-runner:latest"
        assert spec.cmd == ["/bin/bash", "-lc", "sleep 10"]
        assert spec.env["TASK"] == "unit"
        assert spec.env["LANG"] == "python"
        assert len(spec.mounts) == 0
        assert spec.timeouts["overallSec"] == 5
        assert spec.resources["cpu"] == "1"
        assert spec.resources["memory"] == "1Gi"
        assert spec.artifacts["paths"] == []

    def test_file_creation_logic(self):
        """Test file creation logic in test functions"""
        with tempfile.TemporaryDirectory() as temp_dir:
            workspace_path = Path(temp_dir) / "workspace"
            workspace_path.mkdir()

            # Test Python file creation
            test_script = workspace_path / "test.py"
            test_script.write_text("""
import sys
print("Hello from Python!")
print("Python version:", sys.version)
print("Working directory:", sys.path[0])
""")

            assert test_script.exists()
            content = test_script.read_text()
            assert "Hello from Python!" in content
            assert "sys.version" in content

            # Test Go file creation
            go_file = workspace_path / "demo_main.go"
            go_file.write_text("""
package demo_main

import "fmt"

func demo_main() {
    fmt.Println("Hello from Go!")
    fmt.Println("This is a test program")
}
""")

            assert go_file.exists()
            content = go_file.read_text()
            assert "package demo_main" in content
            assert "Hello from Go!" in content


if __name__ == "__demo_main__":
    pytest.demo_main([__file__, "-v"])
