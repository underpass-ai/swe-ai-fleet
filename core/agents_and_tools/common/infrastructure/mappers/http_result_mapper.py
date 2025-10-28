"""Mapper for HttpResult to HttpExecutionResult."""

from core.agents_and_tools.agents.domain.entities.http_execution_result import HttpExecutionResult
from core.agents_and_tools.tools import HttpResult


class HttpResultMapper:
    """Mapper for HttpResult to domain entity."""

    def to_entity(self, result: HttpResult) -> HttpExecutionResult:
        """Convert HttpResult to HttpExecutionResult domain entity."""
        return HttpExecutionResult(
            success=result.success,
            content=str(result.body) if result.body else None,
            error=result.error,
            status_code=result.status_code,
            metadata=result.metadata,
        )

