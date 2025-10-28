"""Mapper for GitResult to GitExecutionResult."""

from core.agents_and_tools.agents.domain.entities.git_execution_result import GitExecutionResult
from core.agents_and_tools.tools import GitResult


class GitResultMapper:
    """Mapper for GitResult to domain entity."""

    def to_entity(self, result: GitResult) -> GitExecutionResult:
        """Convert GitResult to GitExecutionResult domain entity."""
        return GitExecutionResult(
            success=result.success,
            content=result.stdout,
            error=result.stderr,
            exit_code=result.exit_code,
            metadata=result.metadata,
        )

