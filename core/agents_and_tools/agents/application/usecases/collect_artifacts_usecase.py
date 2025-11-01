"""Use case for collecting artifacts from tool operation results."""

from typing import Any

from core.agents_and_tools.agents.domain.entities import Artifact
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class CollectArtifactsUseCase:
    """
    Use case for collecting artifacts from tool operation results.

    This use case handles the business logic for:
    - Extracting artifacts from tool results
    - Mapping them to domain entities
    - Returning structured artifact collections

    Following DDD + Hexagonal Architecture:
    - Delegates to ToolExecutionPort (domain abstraction)
    - Uses ArtifactMapper (infrastructure) to convert to entities
    - Returns domain entities (Artifact)
    """

    def __init__(
        self,
        tool_execution_port: ToolExecutionPort,
        artifact_mapper: ArtifactMapper,
    ):
        """
        Initialize the use case with all dependencies (fail-fast).

        Args:
            tool_execution_port: Port for tool execution (required)
            artifact_mapper: Mapper for artifacts (required)

        Note:
            All dependencies must be provided. This ensures full testability.
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not artifact_mapper:
            raise ValueError("artifact_mapper is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.artifact_mapper = artifact_mapper

    def execute(
        self,
        tool_name: str,
        operation: str,
        tool_result: Any,
        params: dict[str, Any],
    ) -> dict[str, Artifact]:
        """
        Collect artifacts from a tool operation result.

        Args:
            tool_name: Name of the tool that was executed
            operation: Operation that was executed
            tool_result: Result from the tool (domain entity)
            params: Parameters used in the operation

        Returns:
            Dictionary mapping artifact names to Artifact entities
        """
        # Get tool instance from port
        tool = self.tool_execution_port.get_tool_by_name(tool_name)
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method (returns dict of values)
        artifacts_dict = tool.collect_artifacts(
            operation,
            tool_result,
            params,
        )

        # Convert dict to dict of Artifact entities using mapper
        return self.artifact_mapper.to_entity_dict(artifacts_dict)

