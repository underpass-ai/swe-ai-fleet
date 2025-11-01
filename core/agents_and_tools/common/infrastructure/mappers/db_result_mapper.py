"""Mapper for DbResult to DbExecutionResult."""

from core.agents_and_tools.agents.domain.entities import DbExecutionResult
from core.agents_and_tools.tools import DbResult


class DbResultMapper:
    """Mapper for DbResult to domain entity."""

    def to_entity(self, result: DbResult) -> DbExecutionResult:
        """Convert DbResult to DbExecutionResult domain entity."""
        return DbExecutionResult(
            success=result.success,
            content=str(result.data) if result.data else None,
            error=result.error,
            metadata=result.metadata,
        )

