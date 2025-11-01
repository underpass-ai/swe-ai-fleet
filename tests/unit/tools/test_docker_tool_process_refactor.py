"""Unit tests for docker_tool.py process execution refactoring."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from core.agents_and_tools.tools.docker_tool import DockerTool
from core.agents_and_tools.tools.domain.container_build_config import ContainerBuildConfig
from core.agents_and_tools.tools.domain.container_exec_config import ContainerExecConfig
from core.agents_and_tools.tools.domain.container_logs_config import ContainerLogsConfig
from core.agents_and_tools.tools.domain.container_run_config import ContainerRunConfig
from core.agents_and_tools.tools.domain.process_result import ProcessResult


# =============================================================================
# Test _detect_runtime with ProcessCommand
# =============================================================================

class TestDockerToolDetectRuntime:
    """Test runtime detection using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_detects_podman_successfully(self, mock_execute, tmp_path):
        """Should detect podman when available."""
        # Mock successful podman check
        mock_result = ProcessResult(
            stdout="podman version 4.0",
            stderr="",
            returncode=0,
            command=["podman", "version"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)

        assert tool.runtime == "podman"
        # Verify ProcessCommand was created and executed
        mock_execute.assert_called_once()
        call_args = mock_execute.call_args[0][0]
        assert call_args.command == ["podman", "version"]
        assert call_args.timeout == 5
        assert call_args.should_check_returncode() is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_fallsback_to_docker_when_podman_unavailable(self, mock_execute, tmp_path):
        """Should fallback to docker when podman unavailable."""
        import subprocess

        # First call (podman) fails, second call (docker) succeeds
        mock_docker_result = ProcessResult(
            stdout="Docker version 20.10",
            stderr="",
            returncode=0,
            command=["docker", "version"]
        )

        mock_execute.side_effect = [
            subprocess.CalledProcessError(127, ["podman"]),
            mock_docker_result
        ]

        tool = DockerTool.create(tmp_path)

        assert tool.runtime == "docker"
        assert mock_execute.call_count == 2

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_raises_when_no_runtime_found(self, mock_execute, tmp_path):
        """Should raise RuntimeError when neither podman nor docker available."""
        import subprocess

        # Both podman and docker fail
        mock_execute.side_effect = subprocess.CalledProcessError(127, ["cmd"])

        with pytest.raises(RuntimeError, match="No container runtime found"):
            DockerTool.create(tmp_path)


# =============================================================================
# Test build() with ProcessCommand
# =============================================================================

class TestDockerToolBuild:
    """Test container build using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute build using ProcessCommand abstraction."""
        # Setup
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        mock_result = ProcessResult(
            stdout="Successfully built abc123",
            stderr="",
            returncode=0,
            command=["podman", "build", "-f", "Dockerfile", "."]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig.simple(context_path=".")

        # Execute
        result = tool.build(config)

        # Verify ProcessCommand was used
        mock_execute.assert_called()
        call_args = mock_execute.call_args[0][0]
        assert "build" in call_args.command
        assert call_args.working_directory == tmp_path
        assert call_args.timeout == 600  # Default build timeout

        # Verify result
        assert result.is_success() is True
        assert result.operation == "build"

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_build_with_tag_and_no_cache(self, mock_execute, tmp_path):
        """Should pass tag and no-cache flags to command."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        mock_result = ProcessResult(
            stdout="Built",
            stderr="",
            returncode=0,
            command=["podman", "build"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerBuildConfig(
            context_path=".",
            tag="myapp:v1.0",
            no_cache=True,
            timeout=300
        )

        result = tool.build(config)

        # Verify command includes tag and no-cache
        call_args = mock_execute.call_args[0][0]
        assert "-t" in call_args.command
        assert "myapp:v1.0" in call_args.command
        assert "--no-cache" in call_args.command
        assert call_args.timeout == 300


# =============================================================================
# Test run() with ProcessCommand
# =============================================================================

class TestDockerToolRun:
    """Test container run using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute run using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="Hello World",
            stderr="",
            returncode=0,
            command=["podman", "run", "python:3.13"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="python:3.13",
            command=["python", "-c", "print('Hello')"],
            timeout=60
        )

        result = tool.run(config)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert "run" in call_args.command
        assert "python:3.13" in call_args.command
        assert call_args.timeout == 60
        assert call_args.working_directory == tmp_path

        # Verify result
        assert result.is_success() is True
        assert result.operation == "run"

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_detached_uses_shorter_timeout(self, mock_execute, tmp_path):
        """Should use 10s timeout for detached containers."""
        mock_result = ProcessResult(
            stdout="container_id_123",
            stderr="",
            returncode=0,
            command=["podman", "run", "-d"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="nginx",
            detach=True,
            timeout=300  # Should be overridden to 10s for detached
        )

        result = tool.run(config)

        # Verify timeout is 10s for detached
        call_args = mock_execute.call_args[0][0]
        assert call_args.timeout == 10

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_run_with_environment_and_volumes(self, mock_execute, tmp_path):
        """Should pass environment variables and volumes."""
        mock_result = ProcessResult(
            stdout="",
            stderr="",
            returncode=0,
            command=["podman", "run"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerRunConfig(
            image="app:latest",
            env={"DEBUG": "true", "PORT": "8080"},
            volumes={"/data": "/app/data"},
            ports={"8080": "80"}
        )

        result = tool.run(config)

        # Verify command includes env, volumes, and ports
        call_args = mock_execute.call_args[0][0]
        command_str = " ".join(call_args.command)
        assert "-e DEBUG=true" in command_str
        assert "-e PORT=8080" in command_str
        assert "-v /data:/app/data" in command_str
        assert "-p 8080:80" in command_str


# =============================================================================
# Test exec() with ProcessCommand
# =============================================================================

class TestDockerToolExec:
    """Test container exec using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_exec_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute exec using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="root",
            stderr="",
            returncode=0,
            command=["podman", "exec", "webserver", "whoami"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerExecConfig(
            container="webserver",
            command=["whoami"],
            timeout=30
        )

        result = tool.exec(config)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert "exec" in call_args.command
        assert "webserver" in call_args.command
        assert "whoami" in call_args.command
        assert call_args.timeout == 30

        # Verify result
        assert result.is_success() is True
        assert result.stdout == "root"

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_exec_with_complex_command(self, mock_execute, tmp_path):
        """Should handle complex multi-arg commands."""
        mock_result = ProcessResult(
            stdout="file1.txt\nfile2.txt",
            stderr="",
            returncode=0,
            command=["podman", "exec", "app", "ls", "-la", "/data"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerExecConfig(
            container="app",
            command=["ls", "-la", "/data"]
        )

        result = tool.exec(config)

        # Verify all command parts included
        call_args = mock_execute.call_args[0][0]
        assert call_args.command[-3:] == ["ls", "-la", "/data"]


# =============================================================================
# Test ps() with ProcessCommand
# =============================================================================

class TestDockerToolPs:
    """Test container listing using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_ps_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute ps using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="CONTAINER ID\ncontainer1\ncontainer2",
            stderr="",
            returncode=0,
            command=["podman", "ps"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.ps(all_containers=False)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert call_args.command == [tool.runtime, "ps"]
        assert call_args.timeout == 30

        # Verify result
        assert result.is_success() is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_ps_all_includes_flag(self, mock_execute, tmp_path):
        """Should include -a flag when all_containers=True."""
        mock_result = ProcessResult(
            stdout="CONTAINER ID",
            stderr="",
            returncode=0,
            command=["podman", "ps", "-a"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.ps(all_containers=True)

        # Verify -a flag included
        call_args = mock_execute.call_args[0][0]
        assert "-a" in call_args.command


# =============================================================================
# Test logs() with ProcessCommand
# =============================================================================

class TestDockerToolLogs:
    """Test container logs using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute logs using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="Log line 1\nLog line 2",
            stderr="",
            returncode=0,
            command=["podman", "logs", "webserver"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="webserver")

        result = tool.logs(config)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert "logs" in call_args.command
        assert "webserver" in call_args.command
        assert call_args.timeout == 60  # Default timeout

        # Verify result
        assert result.is_success() is True
        assert "Log line 1" in result.stdout

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_with_tail_limit(self, mock_execute, tmp_path):
        """Should include --tail flag when tail specified."""
        mock_result = ProcessResult(
            stdout="Last 10 lines",
            stderr="",
            returncode=0,
            command=["podman", "logs", "--tail", "10", "app"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="app", tail=10)

        result = tool.logs(config)

        # Verify --tail included
        call_args = mock_execute.call_args[0][0]
        assert "--tail" in call_args.command
        assert "10" in call_args.command

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_logs_follow_mode(self, mock_execute, tmp_path):
        """Should use extended timeout for follow mode."""
        mock_result = ProcessResult(
            stdout="Following logs...",
            stderr="",
            returncode=0,
            command=["podman", "logs", "-f", "app"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        config = ContainerLogsConfig(container="app", follow=True)

        result = tool.logs(config)

        # Verify -f flag and extended timeout
        call_args = mock_execute.call_args[0][0]
        assert "-f" in call_args.command
        assert call_args.timeout == 300  # Extended timeout for follow


# =============================================================================
# Test stop() with ProcessCommand
# =============================================================================

class TestDockerToolStop:
    """Test container stop using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_stop_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute stop using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="webserver",
            stderr="",
            returncode=0,
            command=["podman", "stop", "-t", "10", "webserver"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.stop(container="webserver", timeout=10)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert "stop" in call_args.command
        assert "-t" in call_args.command
        assert "10" in call_args.command
        assert "webserver" in call_args.command
        assert call_args.timeout == 20  # timeout + 10 buffer

        # Verify result
        assert result.is_success() is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_stop_with_custom_timeout(self, mock_execute, tmp_path):
        """Should use custom timeout with buffer."""
        mock_result = ProcessResult(
            stdout="app",
            stderr="",
            returncode=0,
            command=["podman", "stop", "-t", "30", "app"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.stop(container="app", timeout=30)

        # Verify timeout has buffer
        call_args = mock_execute.call_args[0][0]
        assert call_args.timeout == 40  # 30 + 10 buffer


# =============================================================================
# Test rm() with ProcessCommand
# =============================================================================

class TestDockerToolRm:
    """Test container removal using ProcessCommand abstraction."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_rm_executes_with_process_command(self, mock_execute, tmp_path):
        """Should execute rm using ProcessCommand abstraction."""
        mock_result = ProcessResult(
            stdout="webserver",
            stderr="",
            returncode=0,
            command=["podman", "rm", "webserver"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.rm(container="webserver", force=False)

        # Verify ProcessCommand was used
        call_args = mock_execute.call_args[0][0]
        assert "rm" in call_args.command
        assert "webserver" in call_args.command
        assert "-f" not in call_args.command
        assert call_args.timeout == 30

        # Verify result
        assert result.is_success() is True

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_rm_with_force(self, mock_execute, tmp_path):
        """Should include -f flag when force=True."""
        mock_result = ProcessResult(
            stdout="app",
            stderr="",
            returncode=0,
            command=["podman", "rm", "-f", "app"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)
        result = tool.rm(container="app", force=True)

        # Verify -f flag included
        call_args = mock_execute.call_args[0][0]
        assert "-f" in call_args.command


# =============================================================================
# Integration Tests
# =============================================================================

class TestDockerToolProcessCommandIntegration:
    """Test integration of ProcessCommand across all operations."""

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_all_operations_use_process_command(self, mock_execute, tmp_path):
        """Should verify all operations use ProcessCommand abstraction."""
        (tmp_path / "Dockerfile").write_text("FROM alpine")

        mock_result = ProcessResult(
            stdout="success",
            stderr="",
            returncode=0,
            command=["podman", "test"]
        )
        mock_execute.return_value = mock_result

        tool = DockerTool.create(tmp_path)

        # Test build
        tool.build(ContainerBuildConfig.simple("."))
        assert mock_execute.called

        # Test run
        mock_execute.reset_mock()
        tool.run(ContainerRunConfig(image="test"))
        assert mock_execute.called

        # Test exec
        mock_execute.reset_mock()
        tool.exec(ContainerExecConfig(container="test", command=["ls"]))
        assert mock_execute.called

        # Test ps
        mock_execute.reset_mock()
        tool.ps()
        assert mock_execute.called

        # Test logs
        mock_execute.reset_mock()
        tool.logs(ContainerLogsConfig(container="test"))
        assert mock_execute.called

        # Test stop
        mock_execute.reset_mock()
        tool.stop("test")
        assert mock_execute.called

        # Test rm
        mock_execute.reset_mock()
        tool.rm("test")
        assert mock_execute.called

    @patch("core.agents_and_tools.tools.docker_tool.execute_process")
    def test_process_result_correctly_converted_to_docker_result(self, mock_execute, tmp_path):
        """Should correctly convert ProcessResult to DockerResult."""
        mock_process_result = ProcessResult(
            stdout="output data",
            stderr="warning message",
            returncode=0,
            command=["podman", "ps"]
        )
        mock_execute.return_value = mock_process_result

        tool = DockerTool.create(tmp_path)
        docker_result = tool.ps()

        # Verify conversion
        assert docker_result.stdout == "output data"
        assert docker_result.stderr == "warning message"
        assert docker_result.exit_code == 0
        assert docker_result.is_success() is True
        assert docker_result.operation == "ps"

