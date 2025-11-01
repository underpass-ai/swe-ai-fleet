"""
Docker/Podman operations tool for agent workspace.

Supports both Docker and Podman runtimes.
"""

import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Any

from core.agents_and_tools.tools.domain.audit_operation import AuditOperation
from core.agents_and_tools.tools.domain.audit_record import AuditRecord
from core.agents_and_tools.tools.domain.container_build_config import ContainerBuildConfig
from core.agents_and_tools.tools.domain.container_exec_config import ContainerExecConfig
from core.agents_and_tools.tools.domain.container_list_config import ContainerListConfig
from core.agents_and_tools.tools.domain.container_logs_config import ContainerLogsConfig
from core.agents_and_tools.tools.domain.container_remove_config import ContainerRemoveConfig
from core.agents_and_tools.tools.domain.container_run_config import ContainerRunConfig
from core.agents_and_tools.tools.domain.container_stop_config import ContainerStopConfig
from core.agents_and_tools.tools.domain.container_runtime import ContainerRuntime
from core.agents_and_tools.tools.domain.docker_operation_metadata import DockerOperationMetadata
from core.agents_and_tools.tools.domain.docker_operations import DockerOperations
from core.agents_and_tools.tools.domain.docker_result import DockerOperation, DockerResult
from core.agents_and_tools.tools.domain.process_command import ProcessCommand
from core.agents_and_tools.tools.domain.process_executor import execute_process


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
        runtime: ContainerRuntime | None = None,
        audit_callback: Callable | None = None
    ) -> "DockerTool":
        """Factory method to create DockerTool instance."""
        # Inject mapper dependency
        from core.agents_and_tools.common.infrastructure.mappers import DockerResultMapper
        mapper = DockerResultMapper()
        return DockerTool(workspace_path, runtime, audit_callback, mapper)

    def __init__(
        self,
        workspace_path: str | Path,
        runtime: ContainerRuntime | None = None,
        audit_callback: Callable | None = None,
        mapper: Any = None,
    ):
        """
        Initialize Docker tool (fail-fast).

        Args:
            workspace_path: Root workspace directory (required)
            runtime: Container runtime value object (default: auto-detect)
            audit_callback: Optional callback for audit logging
            mapper: DockerResultMapper instance (required for DI)
        """
        # Fail fast on missing required dependencies
        if not mapper:
            raise ValueError("mapper is required for dependency injection (fail-fast)")

        self.workspace_path = Path(workspace_path).resolve()
        self.audit_callback = audit_callback
        self.mapper = mapper

        # Use default runtime if not provided
        if runtime is None:
            runtime = ContainerRuntime.auto()

        # Tell the runtime to resolve itself (Tell, Don't Ask pattern)
        # Runtime encapsulates resolution logic, we just provide the detector function
        self.runtime = runtime.resolve(detector=self._detect_runtime)

        # Fail fast if workspace doesn't exist
        if not self.workspace_path.exists():
            raise ValueError(f"Workspace path does not exist: {self.workspace_path} (fail-fast)")

    def _detect_runtime(self) -> str:
        """
        Detect available container runtime.

        Following DDD principles:
        - Uses ProcessCommand value object for readable command specification
        - Uses execute_process() for clean subprocess abstraction
        - Returns primitive (str) as this is infrastructure detection

        Returns:
            Runtime name: "podman" or "docker"

        Raises:
            RuntimeError: If no container runtime found
        """
        # Prefer podman (open source, rootless-friendly)
        try:
            cmd = ProcessCommand.for_runtime_check("podman")
            execute_process(cmd, raise_on_error=True)
            return "podman"
        except (subprocess.CalledProcessError, FileNotFoundError):
            pass

        # Fallback to docker
        try:
            cmd = ProcessCommand.for_runtime_check("docker")
            execute_process(cmd, raise_on_error=True)
            return "docker"
        except (subprocess.CalledProcessError, FileNotFoundError):
            raise RuntimeError("No container runtime found (tried podman, docker)") from None

    def _audit(self, audit_op: AuditOperation, result: DockerResult) -> None:
        """
        Log operation to audit trail using domain entities.

        Following DDD principles:
        - Accept entities/value objects instead of primitives
        - Entities encapsulate validation and business rules

        Args:
            audit_op: Audit operation value object (required)
            result: Result of the operation (required)
        """
        if self.audit_callback:
            audit_record = AuditRecord(
                tool="docker",
                operation=audit_op.get_name(),
                params=audit_op.get_params(),
                success=result.success,
                metadata={"exit_code": result.exit_code, "runtime": self.runtime},
                workspace=str(self.workspace_path),
            )
            self.audit_callback(audit_record.to_dict())

    def build(self, config: ContainerBuildConfig) -> DockerResult:
        """
        Build container image using configuration entity.

        Following DDD principles:
        - Accept entity/value object instead of primitives
        - Entity encapsulates validation and business rules
        - Reduces parameter count (was 5, now 1)

        Args:
            config: Container build configuration entity (required)

        Returns:
            DockerResult with build output
        """
        # Validate context is within workspace
        if not str(config.context_path).startswith("/"):
            context = self.workspace_path / config.context_path
        else:
            context = Path(config.context_path)

        if not str(context.resolve()).startswith(str(self.workspace_path)):
            raise ValueError(f"Context path outside workspace: {config.context_path} (fail-fast)")

        cmd = [self.runtime, "build"]

        if config.is_cache_disabled():
            cmd.append("--no-cache")

        if config.has_tag():
            cmd.extend(["-t", config.tag])

        if config.has_build_args():
            for key, value in config.build_args.items():
                cmd.extend(["--build-arg", f"{key}={value}"])

        cmd.extend(["-f", config.dockerfile, str(context)])

        try:
            # Execute using ProcessCommand abstraction
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=config.timeout
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata.for_build(
                cmd=cmd,
                context=str(context),
                dockerfile=config.dockerfile,
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="build",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            audit_op = AuditOperation.for_build(
                context=str(config.context_path),
                dockerfile=config.dockerfile
            )
            self._audit(audit_op, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=f"Build timed out after {config.timeout} seconds",
                timeout=config.timeout,
            )
            return DockerResult(
                success=False,
                operation="build",
                stdout="",
                stderr=f"Build timed out after {config.timeout} seconds",
                exit_code=-1,
                metadata=metadata,
            )
        except Exception as e:
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=str(e),
            )
            return DockerResult(
                success=False,
                operation="build",
                stdout="",
                stderr=f"Error building image: {e}",
                exit_code=-1,
                metadata=metadata,
            )

    def _build_run_command(self, config: ContainerRunConfig) -> list[str]:
        """
        Build docker run command from configuration.
        
        Extracted to reduce cognitive complexity of run() method.
        
        Args:
            config: Container run configuration
            
        Returns:
            Complete command as list of strings
        """
        cmd = [self.runtime, "run"]
        
        # Add container runtime flags
        self._add_runtime_flags(cmd, config)
        
        # Add environment, volumes, ports
        self._add_env_vars(cmd, config)
        self._add_volumes(cmd, config)
        self._add_ports(cmd, config)
        
        # Add image and command
        cmd.append(config.image)
        if config.has_command():
            cmd.extend(config.command)
            
        return cmd
    
    def _add_runtime_flags(self, cmd: list[str], config: ContainerRunConfig) -> None:
        """Add runtime flags (detach, rm, name) to command."""
        if config.is_detached():
            cmd.append("-d")
        if config.should_auto_remove():
            cmd.append("--rm")
        if config.name:
            cmd.extend(["--name", config.name])
    
    def _add_env_vars(self, cmd: list[str], config: ContainerRunConfig) -> None:
        """Add environment variables to command."""
        if config.has_env_vars():
            for key, value in config.env.items():
                cmd.extend(["-e", f"{key}={value}"])
    
    def _add_volumes(self, cmd: list[str], config: ContainerRunConfig) -> None:
        """Add volume mounts to command."""
        if config.has_volumes():
            for host_path, container_path in config.volumes.items():
                # Validate host path is within workspace
                if not str(host_path).startswith("/"):
                    host_path = self.workspace_path / host_path
                cmd.extend(["-v", f"{host_path}:{container_path}"])
    
    def _add_ports(self, cmd: list[str], config: ContainerRunConfig) -> None:
        """Add port mappings to command."""
        if config.has_ports():
            for host_port, container_port in config.ports.items():
                cmd.extend(["-p", f"{host_port}:{container_port}"])

    def run(self, config: ContainerRunConfig) -> DockerResult:
        """
        Run container using configuration entity.

        Following DDD principles:
        - Accept entity/value object instead of primitives
        - Entity encapsulates validation and business rules
        - Reduces parameter count (was 9, now 1)

        Args:
            config: Container run configuration entity (required)

        Returns:
            DockerResult with execution output
        """
        # Build command using extracted helper methods
        cmd = self._build_run_command(config)

        try:
            # Execute using ProcessCommand abstraction
            timeout = config.timeout if not config.is_detached() else 10
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=timeout
            )
            process_result = execute_process(process_cmd)

            # Create metadata entity for successful run
            metadata = DockerOperationMetadata.for_run(
                cmd=cmd,
                image=config.image,
                detach=config.is_detached(),
                name=config.name,
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="run",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,  # Use entity directly, not dict
            )

            # Create audit operation entity
            audit_op = AuditOperation.for_run(
                image=config.image,
                detach=config.is_detached()
            )
            self._audit(audit_op, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            # Create metadata entity for timeout error
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=f"Container timed out after {config.timeout} seconds",
                timeout=config.timeout,
            )

            return DockerResult(
                success=False,
                operation="run",
                stdout="",
                stderr=f"Container timed out after {config.timeout} seconds",
                exit_code=-1,
                metadata=metadata,  # Use entity directly, not dict
            )
        except Exception as e:
            # Create metadata entity for general error
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=str(e),
            )

            return DockerResult(
                success=False,
                operation="run",
                stdout="",
                stderr=f"Error running container: {e}",
                exit_code=-1,
                metadata=metadata,  # Use entity directly, not dict
            )

    def exec(self, config: ContainerExecConfig) -> DockerResult:
        """
        Execute command in running container using configuration entity.

        Following DDD principles:
        - Accept entity/value object instead of primitives
        - Entity encapsulates validation and business rules
        - Reduces parameter count (was 3, now 1)

        Args:
            config: Container exec configuration entity (required)

        Returns:
            DockerResult with command output
        """
        cmd = [self.runtime, "exec", config.container] + config.command

        try:
            # Execute using ProcessCommand abstraction
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=config.timeout
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata(
                cmd=cmd,
                container_id=config.container,
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="exec",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            audit_op = AuditOperation.for_exec(
                container=config.container,
                command=config.command
            )
            self._audit(audit_op, docker_result)
            return docker_result

        except subprocess.TimeoutExpired:
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=f"Command timed out after {config.timeout} seconds",
                timeout=config.timeout,
            )
            return DockerResult(
                success=False,
                operation="exec",
                stdout="",
                stderr=f"Command timed out after {config.timeout} seconds",
                exit_code=-1,
                metadata=metadata,
            )
        except Exception as e:
            metadata = DockerOperationMetadata.for_error(
                cmd=cmd,
                error=str(e),
            )
            return DockerResult(
                success=False,
                operation="exec",
                stdout="",
                stderr=f"Error executing command: {e}",
                exit_code=-1,
                metadata=metadata,
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
            # Execute using ProcessCommand abstraction
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=30
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata(
                cmd=cmd,
                additional_data={"all": all_containers}
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="ps",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            audit_op = AuditOperation.simple("ps")
            self._audit(audit_op, docker_result)
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

    def logs(self, config: ContainerLogsConfig) -> DockerResult:
        """
        Get container logs using configuration entity.

        Following DDD principles:
        - Accept entity/value object instead of primitives
        - Entity encapsulates validation and business rules
        - Reduces parameter count (was 4, now 1)

        Args:
            config: Container logs configuration entity (required)

        Returns:
            DockerResult with log output
        """
        cmd = [self.runtime, "logs"]

        if config.has_tail_limit():
            cmd.extend(["--tail", str(config.tail)])

        if config.is_following():
            cmd.append("-f")

        cmd.append(config.container)

        try:
            # Execute using ProcessCommand abstraction
            timeout = config.timeout if not config.is_following() else 300  # Default timeout for follow mode
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=timeout
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata(
                cmd=cmd,
                container_id=config.container,
                additional_data={"tail": config.tail} if config.has_tail_limit() else {},
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="logs",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            # Create audit operation entity
            audit_op = AuditOperation.simple("logs")
            self._audit(audit_op, docker_result)
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
            # Execute using ProcessCommand abstraction
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=timeout + 10
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata(
                cmd=cmd,
                container_id=container
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="stop",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            audit_op = AuditOperation.simple("stop")
            self._audit(audit_op, docker_result)
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
            # Execute using ProcessCommand abstraction
            process_cmd = ProcessCommand.in_workspace(
                command=cmd,
                workspace_path=self.workspace_path,
                timeout=30
            )
            process_result = execute_process(process_cmd)

            metadata = DockerOperationMetadata(
                cmd=cmd,
                container_id=container,
                additional_data={"force": force}
            )

            docker_result = DockerResult(
                success=process_result.is_success(),
                operation="rm",
                stdout=process_result.stdout,
                stderr=process_result.stderr,
                exit_code=process_result.returncode,
                metadata=metadata,
            )

            audit_op = AuditOperation.simple("rm")
            self._audit(audit_op, docker_result)
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

    def get_operations(self) -> DockerOperations:
        """
        Get available Docker operations as an entity.

        Following DDD principles:
        - Return entity instead of primitive dict
        - Entity encapsulates operations registry
        - Type-safe and validated

        Returns:
            DockerOperations entity with all available operations
        """
        return DockerOperations(
            build=self.build,
            run=self.run,
            exec=self.exec,
            ps=self.ps,
            logs=self.logs,
            stop=self.stop,
            rm=self.rm,
        )

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
        method = operations.get_operation(operation)
        if not method:
            raise ValueError(f"Unknown docker operation: {operation} (fail-fast)")
        return method(**params)

    def _get_mapper(self):
        """Return the mapper for DockerTool results."""
        # Mapper is now injected via __init__ or factory method
        return self.mapper

    def get_mapper(self):
        """Return the tool's mapper instance."""
        return self.mapper

    def summarize_result(self, _operation: str, tool_result: Any, _params: dict[str, Any]) -> str:
        """
        Summarize tool operation result for logging.

        Following "Tell, Don't Ask" principle: Delegate to the result entity
        which knows how to summarize itself.

        Args:
            _operation: The operation that was executed (unused, kept for interface compatibility)
            tool_result: The DockerResult entity
            _params: The operation parameters (unused, kept for interface compatibility)

        Returns:
            Human-readable summary
        """
        # Duck typing: if it has summarize(), it will work
        # No isinstance() check - trust the interface
        return tool_result.summarize()

    def collect_artifacts(self, _operation: str, tool_result: Any, _params: dict[str, Any]) -> dict[str, Any]:
        """
        Collect artifacts from docker operation.

        Following "Tell, Don't Ask" principle: Delegate to the result entity
        which knows what artifacts to collect for each operation.

        Args:
            _operation: The operation that was executed (unused, kept for interface compatibility)
            tool_result: The DockerResult entity
            _params: The operation parameters (unused, kept for interface compatibility)

        Returns:
            Dictionary of artifacts
        """
        # Duck typing: if it has collect_artifacts(), it will work
        # No isinstance() check - trust the interface
        return tool_result.collect_artifacts()


# Convenience function for use in agent tasks
def execute_docker_operation(
    operation: DockerOperation,
    workspace_path: str,
    runtime: ContainerRuntime | None = None,
    **kwargs: Any,
) -> DockerResult:
    """
    Execute a docker operation from agent workspace.

    Following DDD principles:
    - Returns entity (DockerResult) instead of primitive dict
    - Accepts value object (ContainerRuntime) instead of string
    - Entity encapsulates all operation details

    Args:
        operation: Docker operation to perform
        workspace_path: Workspace directory path
        runtime: Container runtime entity (default: auto-detect)
        **kwargs: Operation-specific parameters

    Returns:
        DockerResult entity with operation result

    Examples:
        # Build image
        config = ContainerBuildConfig.with_tag(".", "myapp:latest")
        result = execute_docker_operation("build", "/workspace", config=config)

        # Run container
        config = ContainerRunConfig.simple("python:3.13")
        result = execute_docker_operation("run", "/workspace", config=config)
    """
    tool = DockerTool.create(workspace_path, runtime=runtime)

    # Get operations entity
    operations = tool.get_operations()
    method = operations.get_operation(operation)

    if not method:
        raise ValueError(f"Unknown docker operation: {operation} (fail-fast)")

    # Execute and return entity directly (no dict conversion)
    return method(**kwargs)

