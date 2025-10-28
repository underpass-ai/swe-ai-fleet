"""Mapper for DockerResult to DockerExecutionResult."""

from core.agents_and_tools.agents.domain.entities import DockerExecutionResult
from core.agents_and_tools.tools import DockerResult


class DockerResultMapper:
    """Mapper for DockerResult to domain entity."""

    def to_entity(self, result: DockerResult) -> DockerExecutionResult:
        """Convert DockerResult to DockerExecutionResult domain entity."""
        return DockerExecutionResult(
            success=result.success,
            content=result.stdout,
            error=result.stderr,
            exit_code=result.exit_code,
            metadata=result.metadata,
        )

