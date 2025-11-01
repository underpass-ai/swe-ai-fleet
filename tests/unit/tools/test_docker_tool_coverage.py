"""Unit tests for docker_tool.py uncovered lines - error paths and helpers."""

import subprocess
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.agents_and_tools.tools.docker_tool import DockerTool
from core.agents_and_tools.tools.domain.container_build_config import ContainerBuildConfig
from core.agents_and_tools.tools.domain.container_exec_config import ContainerExecConfig
from core.agents_and_tools.tools.domain.container_logs_config import ContainerLogsConfig
from core.agents_and_tools.tools.domain.container_run_config import ContainerRunConfig
from core.agents_and_tools.tools.domain.process_result import ProcessResult


# Helper to create valid ProcessResult for tests
def create_mock_process_result(stdout="", stderr="", returncode=0):
    """Create a valid ProcessResult for testing."""
    return ProcessResult(
        stdout=stdout,
        stderr=stderr,
        returncode=returncode,
        command=["podman", "test"]  # Valid command required
    )


# =============================================================================
# Build Error Path Tests
# =============================================================================

class TestDockerToolBuildErrorPaths:
    """Test build() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_handles_timeout_error(self, mock_execute, tmp_path):
        """Should handle subprocess TimeoutExpired."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        # First call for runtime detection succeeds, second call times out
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            subprocess.TimeoutExpired(cmd=["podman", "build"], timeout=600),  # Build timeout
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig(context_path=".", timeout=600)

        result = tool.build(config)

        assert result.is_success() is False
        assert "timed out" in result.stderr.lower()
        assert result.exit_code == -1

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_handles_general_exception(self, mock_execute, tmp_path):
        """Should handle general exceptions during build."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        # First call for runtime detection succeeds, second call raises
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Unexpected error"),  # Build error
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig.simple(".")

        result = tool.build(config)

        assert result.is_success() is False
        assert "Error building image" in result.stderr
        assert result.exit_code == -1

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_validates_context_within_workspace(self, mock_execute, tmp_path):
        """Should reject context path outside workspace."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig(context_path="/etc")  # Outside workspace

        with pytest.raises(ValueError, match="Context path outside workspace"):
            tool.build(config)

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_with_relative_context_path(self, mock_execute, tmp_path):
        """Should handle relative context paths."""
        (tmp_path / "app").mkdir()
        (tmp_path / "app" / "Dockerfile").write_text("FROM alpine")

        mock_result = ProcessResult(
            stdout="Built",
            stderr="",
            returncode=0,
            command=["podman", "build"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig(context_path="app")

        result = tool.build(config)

        assert result.is_success() is True


# =============================================================================
# Run Error Path Tests
# =============================================================================

class TestDockerToolRunErrorPaths:
    """Test run() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_handles_timeout_error(self, mock_execute, tmp_path):
        """Should handle subprocess TimeoutExpired."""
        # First call for runtime detection succeeds, second call times out
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            subprocess.TimeoutExpired(cmd=["podman", "run"], timeout=300),  # Run timeout
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", timeout=300)

        result = tool.run(config)

        assert result.is_success() is False
        assert "timed out" in result.stderr.lower()
        assert result.exit_code == -1

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_handles_general_exception(self, mock_execute, tmp_path):
        """Should handle general exceptions during run."""
        # First call for runtime detection succeeds, second call raises
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Container runtime error"),  # Run error
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="test:latest")

        result = tool.run(config)

        assert result.is_success() is False
        assert "Error running container" in result.stderr
        assert result.exit_code == -1


# =============================================================================
# Run Helper Method Tests
# =============================================================================

class TestDockerToolRunHelperMethods:
    """Test run() helper methods for command building."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_runtime_flags_includes_detach(self, mock_execute, tmp_path):
        """Should add -d flag for detached containers."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", detach=True, rm=False, name=None)

        tool.run(config)

        # Verify -d flag in command
        call_args = mock_execute.call_args[0][0]
        assert "-d" in call_args.command

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_runtime_flags_includes_rm(self, mock_execute, tmp_path):
        """Should add --rm flag for auto-remove."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", rm=True)

        tool.run(config)

        # Verify --rm flag in command
        call_args = mock_execute.call_args[0][0]
        assert "--rm" in call_args.command

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_runtime_flags_includes_name(self, mock_execute, tmp_path):
        """Should add --name flag when name provided."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", name="webserver")

        tool.run(config)

        # Verify --name flag in command
        call_args = mock_execute.call_args[0][0]
        assert "--name" in call_args.command
        assert "webserver" in call_args.command

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_volumes_with_relative_path(self, mock_execute, tmp_path):
        """Should convert relative host paths to absolute."""
        (tmp_path / "data").mkdir()
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="nginx",
            volumes={"data": "/app/data"}  # Relative path
        )

        tool.run(config)

        # Verify volume mount in command
        call_args = mock_execute.call_args[0][0]
        command_str = " ".join(call_args.command)
        assert "-v" in command_str
        assert "/app/data" in command_str


# =============================================================================
# Exec Error Path Tests
# =============================================================================

class TestDockerToolExecErrorPaths:
    """Test exec() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_exec_handles_timeout_error(self, mock_execute, tmp_path):
        """Should handle subprocess TimeoutExpired."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            subprocess.TimeoutExpired(cmd=["podman", "exec"], timeout=60),  # Exec timeout
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerExecConfig(container="test", command=["ls"])

        result = tool.exec(config)

        assert result.is_success() is False
        assert "timed out" in result.stderr.lower()
        assert result.exit_code == -1

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_exec_handles_general_exception(self, mock_execute, tmp_path):
        """Should handle general exceptions during exec."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Container not found"),  # Exec error
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerExecConfig(container="nonexistent", command=["ls"])

        result = tool.exec(config)

        assert result.is_success() is False
        assert "Error executing command" in result.stderr
        assert result.exit_code == -1


# =============================================================================
# PS Error Path Tests
# =============================================================================

class TestDockerToolPsErrorPaths:
    """Test ps() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_ps_handles_exception(self, mock_execute, tmp_path):
        """Should handle exceptions during ps."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Runtime not available"),  # PS error
        ]

        tool = DockerTool.create(tmp_path)

        result = tool.ps()

        assert result.is_success() is False
        assert "Error listing containers" in result.stderr
        assert result.exit_code == -1


# =============================================================================
# Logs Error Path Tests
# =============================================================================

class TestDockerToolLogsErrorPaths:
    """Test logs() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_handles_timeout_error(self, mock_execute, tmp_path):
        """Should handle subprocess TimeoutExpired."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            subprocess.TimeoutExpired(cmd=["podman", "logs"], timeout=60),  # Logs timeout
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="test")

        result = tool.logs(config)

        assert result.is_success() is False
        assert "timed out" in result.stderr.lower()

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_handles_general_exception(self, mock_execute, tmp_path):
        """Should handle general exceptions during logs."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Container not found"),  # Logs error
        ]

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="nonexistent")

        result = tool.logs(config)

        assert result.is_success() is False
        assert "Error getting logs" in result.stderr


# =============================================================================
# Stop Error Path Tests
# =============================================================================

class TestDockerToolStopErrorPaths:
    """Test stop() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_stop_handles_exception(self, mock_execute, tmp_path):
        """Should handle exceptions during stop."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Container not running"),  # Stop error
        ]

        tool = DockerTool.create(tmp_path)

        result = tool.stop(container="test")

        assert result.is_success() is False
        assert "Error stopping container" in result.stderr
        assert result.exit_code == -1


# =============================================================================
# Remove Error Path Tests
# =============================================================================

class TestDockerToolRmErrorPaths:
    """Test rm() error handling paths."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_rm_handles_exception(self, mock_execute, tmp_path):
        """Should handle exceptions during rm."""
        mock_execute.side_effect = [
            create_mock_process_result(),  # Runtime detection
            Exception("Container not found"),  # RM error
        ]

        tool = DockerTool.create(tmp_path)

        result = tool.rm(container="nonexistent")

        assert result.is_success() is False
        assert "Error removing container" in result.stderr
        assert result.exit_code == -1


# =============================================================================
# Mapper and Audit Callback Tests
# =============================================================================

class TestDockerToolMapperAndAudit:
    """Test mapper access and audit callback."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_get_mapper_returns_mapper(self, mock_execute, tmp_path):
        """Should return mapper instance."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        mapper = tool.get_mapper()

        assert mapper is not None

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_audit_callback_called_on_build(self, mock_execute, tmp_path):
        """Should call audit callback when provided."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")
        mock_result = create_mock_process_result(stdout="Built")
        mock_execute.return_value = mock_result

        audit_callback = Mock()
        tool = DockerTool.create(tmp_path, audit_callback=audit_callback)

        config = ContainerBuildConfig.simple(".")
        tool.build(config)

        # Verify callback was called
        audit_callback.assert_called_once()
        call_args = audit_callback.call_args[0][0]
        assert call_args["tool"] == "docker"
        assert call_args["success"] is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_audit_callback_called_on_run(self, mock_execute, tmp_path):
        """Should call audit callback on run."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        audit_callback = Mock()
        tool = DockerTool.create(tmp_path, audit_callback=audit_callback)

        config = ContainerRunConfig(image="nginx")
        tool.run(config)

        audit_callback.assert_called_once()

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_audit_callback_called_on_exec(self, mock_execute, tmp_path):
        """Should call audit callback on exec."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        audit_callback = Mock()
        tool = DockerTool.create(tmp_path, audit_callback=audit_callback)

        config = ContainerExecConfig(container="test", command=["ls"])
        tool.exec(config)

        audit_callback.assert_called_once()

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_audit_callback_called_on_logs(self, mock_execute, tmp_path):
        """Should call audit callback on logs."""
        mock_result = create_mock_process_result(stdout="logs")
        mock_execute.return_value = mock_result

        audit_callback = Mock()
        tool = DockerTool.create(tmp_path, audit_callback=audit_callback)

        config = ContainerLogsConfig(container="test")
        tool.logs(config)

        audit_callback.assert_called_once()


# =============================================================================
# Helper Method Coverage Tests
# =============================================================================

class TestDockerToolHelperMethods:
    """Test coverage for helper methods."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_env_vars_adds_multiple_variables(self, mock_execute, tmp_path):
        """Should add multiple environment variables."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="app",
            env={"VAR1": "value1", "VAR2": "value2", "DEBUG": "true"}
        )

        tool.run(config)

        call_args = mock_execute.call_args[0][0]
        command_str = " ".join(call_args.command)
        assert "-e VAR1=value1" in command_str
        assert "-e VAR2=value2" in command_str
        assert "-e DEBUG=true" in command_str

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_volumes_adds_multiple_mounts(self, mock_execute, tmp_path):
        """Should add multiple volume mounts."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="app",
            volumes={"/data": "/app/data", "/logs": "/app/logs"}
        )

        tool.run(config)

        call_args = mock_execute.call_args[0][0]
        command_str = " ".join(call_args.command)
        assert "-v /data:/app/data" in command_str
        assert "-v /logs:/app/logs" in command_str

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_add_ports_adds_multiple_mappings(self, mock_execute, tmp_path):
        """Should add multiple port mappings."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="app",
            ports={"8080": "80", "8443": "443"}
        )

        tool.run(config)

        call_args = mock_execute.call_args[0][0]
        command_str = " ".join(call_args.command)
        assert "-p 8080:80" in command_str
        assert "-p 8443:443" in command_str

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_run_command_orchestrates_all_helpers(self, mock_execute, tmp_path):
        """Should orchestrate all helper methods in _build_run_command."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="nginx:latest",
            detach=True,
            rm=True,
            name="webserver",
            env={"PORT": "8080"},
            volumes={"/data": "/app/data"},
            ports={"8080": "80"},
            command=["nginx", "-g", "daemon off;"]
        )

        tool.run(config)

        # Verify complete command structure
        call_args = mock_execute.call_args[0][0]
        cmd = call_args.command

        assert cmd[0] in ["podman", "docker"]
        assert "run" in cmd
        assert "-d" in cmd
        assert "--rm" in cmd
        assert "--name" in cmd
        assert "webserver" in cmd
        assert "-e" in cmd
        assert "-v" in cmd
        assert "-p" in cmd
        assert "nginx:latest" in cmd
        assert "nginx" in cmd


# =============================================================================
# Summarize and Collect Artifacts Tests (duck typing)
# =============================================================================

class TestDockerToolSummarizeAndCollect:
    """Test summarize_result and collect_artifacts methods."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_summarize_result_delegates_to_entity(self, mock_execute, tmp_path):
        """Should delegate summarization to result entity."""
        mock_result = create_mock_process_result(stdout="Built")
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        (tmp_path / "Dockerfile").write_text("FROM alpine")
        config = ContainerBuildConfig.simple(".")

        docker_result = tool.build(config)

        # Verify duck typing works (no isinstance check)
        summary = tool.summarize_result("build", docker_result, {})

        assert isinstance(summary, str)
        assert "built" in summary.lower()

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_collect_artifacts_delegates_to_entity(self, mock_execute, tmp_path):
        """Should delegate artifact collection to result entity."""
        mock_result = create_mock_process_result(stdout="container_123")
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", detach=True, name="web")

        docker_result = tool.run(config)

        # Verify duck typing works (no isinstance check)
        artifacts = tool.collect_artifacts("run", docker_result, {})

        assert isinstance(artifacts, dict)
        assert "container_id" in artifacts


# =============================================================================
# Edge Case Tests
# =============================================================================

class TestDockerToolEdgeCases:
    """Test edge cases and boundary conditions."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_with_empty_env_dict(self, mock_execute, tmp_path):
        """Should handle empty env dict."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx", env={})

        result = tool.run(config)

        assert result.is_success() is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_with_no_optional_params(self, mock_execute, tmp_path):
        """Should handle config with only required params."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(image="nginx")  # Minimal config

        result = tool.run(config)

        call_args = mock_execute.call_args[0][0]
        cmd = call_args.command

        # Should have basic structure
        assert "run" in cmd
        assert "nginx" in cmd

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_with_follow_mode(self, mock_execute, tmp_path):
        """Should handle follow mode for logs."""
        mock_result = create_mock_process_result(stdout="logs")
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="test", follow=True, timeout=120)

        result = tool.logs(config)

        call_args = mock_execute.call_args[0][0]
        assert "-f" in call_args.command
        assert call_args.timeout == 300  # Extended timeout for follow

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_ps_with_all_containers_flag(self, mock_execute, tmp_path):
        """Should add -a flag when all_containers=True."""
        mock_result = create_mock_process_result()
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)

        result = tool.ps(all_containers=True)

        call_args = mock_execute.call_args[0][0]
        assert "-a" in call_args.command

