"""Docker operation result entity."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from core.agents_and_tools.tools.domain.docker_operation_metadata import DockerOperationMetadata

DockerOperation = Literal["build", "run", "exec", "ps", "logs", "stop", "rm"]


@dataclass(frozen=True)
class DockerResult:
    """
    Immutable entity representing the result of a docker operation.

    Following DDD principles:
    - Immutable (frozen=True)
    - Fail-fast validation in __post_init__
    - No side effects
    - Self-contained business logic
    - Accepts value objects (metadata) instead of primitives
    """

    success: bool
    operation: DockerOperation
    stdout: str
    stderr: str
    exit_code: int
    metadata: DockerOperationMetadata

    def __post_init__(self) -> None:
        """
        Validate entity invariants (fail-fast).

        Note: We validate values, not types. Python's type system and duck typing
        handle type checking. If wrong types are passed, they'll fail naturally
        when methods are called.

        Raises:
            ValueError: If any invariant is violated
        """
        if not self.operation:
            raise ValueError("operation is required and cannot be empty (fail-fast)")

        if self.stdout is None:
            raise ValueError("stdout is required (use empty string if no output) (fail-fast)")

        if self.stderr is None:
            raise ValueError("stderr is required (use empty string if no error) (fail-fast)")

        if self.metadata is None:
            raise ValueError("metadata is required (fail-fast)")

    def is_success(self) -> bool:
        """
        Check if the operation was successful.

        Returns:
            True if operation succeeded, False otherwise
        """
        return self.success and self.exit_code == 0

    def has_errors(self) -> bool:
        """
        Check if the operation produced errors.

        Returns:
            True if there are errors in stderr, False otherwise
        """
        return bool(self.stderr and self.stderr.strip())

    def get_output(self) -> str:
        """
        Get combined output from stdout and stderr.

        Returns:
            Combined output string
        """
        parts = []
        if self.stdout:
            parts.append(f"STDOUT:\n{self.stdout}")
        if self.stderr:
            parts.append(f"STDERR:\n{self.stderr}")
        return "\n\n".join(parts) if parts else "No output"

    def summarize(self) -> str:
        """
        Generate human-readable summary of the operation result.

        Following "Tell, Don't Ask" principle: The entity knows how to
        summarize itself based on its operation type, instead of clients
        asking "what operation is this?" and deciding externally.

        Returns:
            Human-readable summary string
        """
        # Strategy pattern: map operations to summary methods
        summary_methods = {
            "build": self._summarize_build,
            "run": self._summarize_run,
            "exec": self._summarize_exec,
            "ps": self._summarize_ps,
            "logs": self._summarize_logs,
            "stop": self._summarize_stop,
            "rm": self._summarize_rm,
        }

        summary_method = summary_methods.get(self.operation)
        if summary_method:
            return summary_method()

        # Fallback for unknown operations
        return f"Docker operation '{self.operation}' completed"

    def _summarize_build(self) -> str:
        """Summarize build operation."""
        return "Docker image built successfully" if self.is_success() else "Docker image build failed"

    def _summarize_run(self) -> str:
        """Summarize run operation."""
        if not self.is_success():
            return "Container failed to run"
        if self.metadata.detach:
            return f"Container started in background: {self.metadata.name or 'unnamed'}"
        return "Container executed successfully"

    def _summarize_exec(self) -> str:
        """Summarize exec operation."""
        return "Command executed successfully in container" if self.is_success() else "Command execution failed in container"

    def _summarize_ps(self) -> str:
        """Summarize ps operation."""
        if self.is_success() and self.stdout:
            containers = len([line for line in self.stdout.split("\n") if line.strip()])
            return f"Found {containers} container(s)"
        return "Listed containers"

    def _summarize_logs(self) -> str:
        """Summarize logs operation."""
        return "Retrieved container logs" if self.is_success() else "Failed to retrieve container logs"

    def _summarize_stop(self) -> str:
        """Summarize stop operation."""
        return "Container stopped successfully" if self.is_success() else "Failed to stop container"

    def _summarize_rm(self) -> str:
        """Summarize rm operation."""
        return "Container removed successfully" if self.is_success() else "Failed to remove container"

    def collect_artifacts(self) -> dict[str, Any]:
        """
        Collect artifacts from the operation result.

        Following "Tell, Don't Ask" principle: The entity knows what artifacts
        are relevant for each operation type, instead of clients asking
        "what operation is this?" and deciding externally.

        Returns:
            Dictionary of artifacts specific to the operation
        """
        # Strategy pattern: map operations to artifact collection methods
        collection_methods = {
            "build": self._collect_build_artifacts,
            "run": self._collect_run_artifacts,
            "ps": self._collect_ps_artifacts,
            "logs": self._collect_logs_artifacts,
            "exec": self._collect_exec_artifacts,
        }

        collection_method = collection_methods.get(self.operation)
        if collection_method:
            return collection_method()

        # No artifacts for unknown operations
        return {}

    def _collect_build_artifacts(self) -> dict[str, Any]:
        """Collect artifacts from build operation."""
        from typing import Any

        artifacts: dict[str, Any] = {}
        if self.is_success() and self.metadata.image:
            artifacts["docker_image"] = self.metadata.image
        if self.metadata.additional_data.get("context"):
            artifacts["build_context"] = self.metadata.additional_data["context"]
        return artifacts

    def _collect_run_artifacts(self) -> dict[str, Any]:
        """Collect artifacts from run operation."""
        from typing import Any

        artifacts: dict[str, Any] = {}
        if not self.is_success():
            return artifacts

        # For detached containers, stdout contains container ID
        if self.metadata.detach and self.stdout.strip():
            artifacts["container_id"] = self.stdout.strip()
        if self.metadata.image:
            artifacts["image"] = self.metadata.image
        if self.metadata.name:
            artifacts["container_name"] = self.metadata.name
        return artifacts

    def _collect_ps_artifacts(self) -> dict[str, Any]:
        """Collect artifacts from ps operation."""
        from typing import Any

        artifacts: dict[str, Any] = {}
        if self.is_success() and self.stdout:
            # Count containers from output
            containers = len([line for line in self.stdout.split("\n") if line.strip()])
            artifacts["containers_count"] = containers
        return artifacts

    def _collect_logs_artifacts(self) -> dict[str, Any]:
        """Collect artifacts from logs operation."""
        from typing import Any

        artifacts: dict[str, Any] = {}
        if self.is_success():
            # Log output is the artifact
            artifacts["logs"] = self.stdout
            if self.metadata.container_id:
                artifacts["container"] = self.metadata.container_id
        return artifacts

    def _collect_exec_artifacts(self) -> dict[str, Any]:
        """Collect artifacts from exec operation."""
        from typing import Any

        artifacts: dict[str, Any] = {}
        if self.is_success():
            # Command output
            artifacts["command_output"] = self.stdout
            if self.metadata.container_id:
                artifacts["container"] = self.metadata.container_id
        return artifacts

