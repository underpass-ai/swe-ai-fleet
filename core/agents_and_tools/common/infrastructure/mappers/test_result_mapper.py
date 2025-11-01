"""Mapper for TestResult to TestExecutionResult."""

from core.agents_and_tools.agents.domain.entities import TestExecutionResult
from core.agents_and_tools.tools import TestResult


class TestResultMapper:
    """Mapper for TestResult to domain entity."""

    def to_entity(self, result: TestResult) -> TestExecutionResult:
        """Convert TestResult to TestExecutionResult domain entity."""
        return TestExecutionResult(
            success=result.success,
            content=result.stdout,
            error=result.stderr,
            exit_code=result.exit_code,
            metadata=result.metadata,
        )

