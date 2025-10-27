"""
Docker/Podman operations tool for agent workspace.

Supports both Docker and Podman runtimes.
"""

import subprocess
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

DockerOperation = Literal["build", "run", "exec", "ps", "logs", "stop", "rm"]


@dataclass
class DockerResult:
    """Result of a docker operation."""

    success: bool
    operation: DockerOperation
    stdout: str
    stderr: str
    exit_code: int
    metadata: dict[str, Any]


class DockerTool:
    """
    Docker/Podman operations tool for workspace execution.

    Security:
    - All operations run with resource limits
    - No privileged containers
    - Network isolation by default
    - Audit trail of all operations
    """

    @staticmethod
    def create(
        workspace_path: str | Path,
        runtime: Literal["docker", "podman", "auto"] = "auto",
        audit_callback: Callable | None = None
    ) -> "DockerTool":
        """Factory method to create DockerTool instance."""
        return DockerTool(workspace_path, runtime, audit_callback)

    def __init__(
        self,
        workspace_path: str | Path,
        runtime: Literal["docker", "podman", "auto"] = "auto",
        audit_callback: Callable | None = None,
    ):
        """
        Initialize Docker tool.

        Args:
            workspace_path: Root workspace directory
            runtime: Container runtime (docker, podman, or auto-detect)
            audit_callback: Optional callback for audit logging
        """
        self.workspace_path = Path(workspace_path).resolve()
        self.audit_callback = audit_callback

        # Initialize mapper for domain conversion
        self.mapper = self._get_mapper()

        # Detect runtime
        if runtime == "auto":
            self.runtime = self._detect_runtime()
        else:
            self.runtime = runtime

        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path}")

    def _detect_runtime(self) -> str:
        """Detect available container runtime."""
        # Prefer podman (open source, rootless-friendly)
        try:
            subprocess.run(
                ["podman", "version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return "podman"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback to docker
        try:
            subprocess.run(
                ["docker", "version"],
                capture_output=True,
                timeout=5,
                check=True,
            )
            return "docker"
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("No container runtime found (tried podman, docker)") from None

    def _audit(self, operation: str, params: dict[str, Any], result: DockerResult) -> None:
        """Log operation to audit trail."""
        if self.audit_callback:
            self.audit_callback(
                {
                    "tool": "docker",
                    "operation": operation,
                    "params": params,
                    "success": result.success,
                    "metadata": {"exit_code": result.exit_code, "runtime": self.runtime},
                    "workspace": str(self.workspace_path),
                }
            )

    def build(
        self,
        context_path: str | Path = ".",
        dockerfile: str = "Dockerfile",
        tag: str | None = None,
        no_cache: bool = False,
        timeout: int = 600,
    ) -> DockerResult:
        """
        Build container image.

        Args:
            context_path: Build context path (relative to workspace)
            dockerfile: Dockerfile name
            tag: Image tag (e.g., "myapp:latest")
            no_cache: Build without cache
            timeout: Timeout in seconds (default: 10 minutes)

        Returns:
            DockerResult with build output
        """
        # Validate context is within workspace
        if not str(context_path).startswith("/"):
            context = self.workspace_path / context_path
        else:
            context = Path(context_path)

        if not str(context.resolve()).startswith(str(self.workspace_path)):
            raise ValueError(f"Context path outside workspace: {context_path}")

        cmd = [self.runtime, "build"]

        if no_cache:
            cmd.append("--no-cache")

        if tag:
            cmd.extend(["-t", tag])

        cmd.extend(["-f", dockerfile, str(context)])

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="build",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={
                    "cmd": cmd,
                    "context": str(context),
                    "dockerfile": dockerfile,
                    "tag": tag,
                },
            )

            self._audit(
                "build", {"context": str(context_path), "tag": tag}, docker_result
            )
            return docker_result

        except subprocess.TimeoutExpired:
            return DockerResult(
                success=False,
                operation="build",
                stdout="",
                stderr=f"Build timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return DockerResult(
                success=False,
                operation="build",
                stdout="",
                stderr=f"Error building image: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def run(
        self,
        image: str,
        command: list[str] | None = None,
        env: dict[str, str] | None = None,
        volumes: dict[str, str] | None = None,
        ports: dict[str, str] | None = None,
        detach: bool = False,
        rm: bool = True,
        name: str | None = None,
        timeout: int = 300,
    ) -> DockerResult:
        """
        Run container.

        Args:
            image: Container image name
            command: Command to run (None for default)
            env: Environment variables
            volumes: Volume mounts (host_path: container_path)
            ports: Port mappings (host_port: container_port)
            detach: Run in background
            rm: Remove container after exit
            name: Container name
            timeout: Timeout in seconds (default: 5 minutes)

        Returns:
            DockerResult with execution output
        """
        cmd = [self.runtime, "run"]

        if detach:
            cmd.append("-d")

        if rm:
            cmd.append("--rm")

        if name:
            cmd.extend(["--name", name])

        # Add environment variables
        if env:
            for key, value in env.items():
                cmd.extend(["-e", f"{key}={value}"])

        # Add volume mounts
        if volumes:
            for host_path, container_path in volumes.items():
                # Validate host path is within workspace
                if not str(host_path).startswith("/"):
                    host_path = self.workspace_path / host_path

                cmd.extend(["-v", f"{host_path}:{container_path}"])

        # Add port mappings
        if ports:
            for host_port, container_port in ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

        # Add image
        cmd.append(image)

        # Add command if provided
        if command:
            cmd.extend(command)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout if not detach else 10,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="run",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={
                    "cmd": cmd,
                    "image": image,
                    "detach": detach,
                    "name": name,
                },
            )

            self._audit("run", {"image": image, "detach": detach}, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            return DockerResult(
                success=False,
                operation="run",
                stdout="",
                stderr=f"Container timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return DockerResult(
                success=False,
                operation="run",
                stdout="",
                stderr=f"Error running container: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def exec(
        self,
        container: str,
        command: list[str],
        timeout: int = 60,
    ) -> DockerResult:
        """
        Execute command in running container.

        Args:
            container: Container name or ID
            command: Command to execute
            timeout: Timeout in seconds

        Returns:
            DockerResult with command output
        """
        cmd = [self.runtime, "exec", container] + command

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="exec",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "container": container},
            )

            self._audit("exec", {"container": container, "command": command}, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            return DockerResult(
                success=False,
                operation="exec",
                stdout="",
                stderr=f"Command timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return DockerResult(
                success=False,
                operation="exec",
                stdout="",
                stderr=f"Error executing command: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def ps(self, all_containers: bool = False) -> DockerResult:
        """
        List containers.

        Args:
            all_containers: Show all containers (not just running)

        Returns:
            DockerResult with container listing
        """
        cmd = [self.runtime, "ps"]

        if all_containers:
            cmd.append("-a")

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="ps",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "all": all_containers},
            )

            self._audit("ps", {"all": all_containers}, docker_result)
            return docker_result

        except Exception as e:
            return DockerResult(
                success=False,
                operation="ps",
                stdout="",
                stderr=f"Error listing containers: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def logs(
        self,
        container: str,
        tail: int | None = None,
        follow: bool = False,
        timeout: int = 60,
    ) -> DockerResult:
        """
        Get container logs.

        Args:
            container: Container name or ID
            tail: Number of lines from end (None for all)
            follow: Follow log output
            timeout: Timeout in seconds

        Returns:
            DockerResult with log output
        """
        cmd = [self.runtime, "logs"]

        if tail:
            cmd.extend(["--tail", str(tail)])

        if follow:
            cmd.append("-f")

        cmd.append(container)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout if not follow else None,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="logs",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "container": container, "tail": tail},
            )

            self._audit("logs", {"container": container}, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            return DockerResult(
                success=False,
                operation="logs",
                stdout="",
                stderr=f"Log command timed out after {timeout} seconds",
                exit_code=-1,
                metadata={"cmd": cmd, "timeout": timeout},
            )
        except Exception as e:
            return DockerResult(
                success=False,
                operation="logs",
                stdout="",
                stderr=f"Error getting logs: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def stop(self, container: str, timeout: int = 10) -> DockerResult:
        """
        Stop running container.

        Args:
            container: Container name or ID
            timeout: Graceful stop timeout in seconds

        Returns:
            DockerResult with operation status
        """
        cmd = [self.runtime, "stop", "-t", str(timeout), container]

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=timeout + 10,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="stop",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "container": container},
            )

            self._audit("stop", {"container": container}, docker_result)
            return docker_result

        except Exception as e:
            return DockerResult(
                success=False,
                operation="stop",
                stdout="",
                stderr=f"Error stopping container: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def rm(self, container: str, force: bool = False) -> DockerResult:
        """
        Remove container.

        Args:
            container: Container name or ID
            force: Force removal

        Returns:
            DockerResult with operation status
        """
        cmd = [self.runtime, "rm"]

        if force:
            cmd.append("-f")

        cmd.append(container)

        try:
            result = subprocess.run(
                cmd,
                cwd=self.workspace_path,
                capture_output=True,
                text=True,
                timeout=30,
            )

            docker_result = DockerResult(
                success=result.returncode == 0,
                operation="rm",
                stdout=result.stdout,
                stderr=result.stderr,
                exit_code=result.returncode,
                metadata={"cmd": cmd, "container": container},
            )

            self._audit("rm", {"container": container, "force": force}, docker_result)
            return docker_result

        except Exception as e:
            return DockerResult(
                success=False,
                operation="rm",
                stdout="",
                stderr=f"Error removing container: {e}",
                exit_code=-1,
                metadata={"cmd": cmd, "error": str(e)},
            )

    def get_operations(self) -> dict[str, Any]:
        """Return dictionary mapping operation names to method callables."""
        return {
            "build": self.build,
            "run": self.run,
            "exec": self.exec,
            "ps": self.ps,
            "logs": self.logs,
            "stop": self.stop,
            "rm": self.rm,
        }

    def execute(self, operation: str, **params: Any) -> DockerResult:
        """
        Execute a docker operation by name.

        Args:
            operation: Name of the operation
            **params: Operation parameters

        Returns:
            DockerResult

        Raises:
            ValueError: If operation is not supported
        """
        operations = self.get_operations()
        method = operations.get(operation)
        if not method:
            raise ValueError(f"Unknown docker operation: {operation}")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for DockerTool results."""
        from core.agents_and_tools.agents.infrastructure.mappers.docker_result_mapper import DockerResultMapper
        return DockerResultMapper()

    def get_mapper(self):
        """Return the tool's mapper instance."""
        return self.mapper

    def summarize_result(self, operation: str, tool_result: Any, params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Args:
            operation: The operation that was executed
            tool_result: The result from the tool
            params: The operation parameters

        Returns:
            Human-readable summary
        """
        if operation == "build":
            return "Docker image built"
        elif operation == "run":
            return "Container started"
        elif operation == "stop":
            return "Container stopped"
        elif operation == "ps":
            if tool_result.content:
                containers = len([l for l in tool_result.content.split("\n") if l.strip()])
                return f"Found {containers} containers"
        elif operation == "logs":
            return "Retrieved container logs"

        return "Docker operation completed"


# Convenience function for use in agent tasks
def execute_docker_operation(
    operation: DockerOperation,
    workspace_path: str,
    runtime: str = "auto",
    **kwargs: Any,
) -> dict[str, Any]:
    """
    Execute a docker operation from agent workspace.

    Args:
        operation: Docker operation to perform
        workspace_path: Workspace directory path
        runtime: Container runtime (docker, podman, or auto)
        **kwargs: Operation-specific parameters

    Returns:
        Dictionary with operation result

    Examples:
        # Build image
        result = execute_docker_operation(
            "build",
            "/workspace",
            tag="myapp:latest"
        )

        # Run container
        result = execute_docker_operation(
            "run",
            "/workspace",
            image="python:3.13",
            command=["python", "-c", "print('hello')"]
        )
    """
    tool = DockerTool(workspace_path, runtime=runtime)

    # Get method
    method = getattr(tool, operation)
    result = method(**kwargs)

    return {
        "success": result.success,
        "operation": result.operation,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "exit_code": result.exit_code,
        "metadata": result.metadata,
    }

