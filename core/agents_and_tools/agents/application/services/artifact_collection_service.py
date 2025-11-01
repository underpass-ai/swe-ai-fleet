"""Application service for artifact collection."""

from __future__ import annotations

from core.agents_and_tools.agents.application.dtos.step_execution_dto import StepExecutionDTO
from core.agents_and_tools.agents.domain.entities import Artifact, ExecutionStep
from core.agents_and_tools.agents.infrastructure.mappers.artifact_mapper import ArtifactMapper
from core.agents_and_tools.common.domain.ports.tool_execution_port import ToolExecutionPort


class ArtifactCollectionApplicationService:
    """
    Application service for collecting artifacts from tool executions.

    This service coordinates artifact collection by:
    1. Delegating to tool-specific collection methods
    2. Mapping raw artifact data to Artifact entities

    Following DDD principles:
    - Service operates on domain entities (ExecutionStep, Artifact)
    - Coordinates infrastructure concerns (tool access, mapping)
    - Stateless
    """

    def __init__(
        self,
        tool_execution_port: ToolExecutionPort,
        artifact_mapper: ArtifactMapper,
    ):
        """
        Initialize artifact collection service.

        Args:
            tool_execution_port: Port for accessing tools (required)
            artifact_mapper: Mapper for converting to Artifact entities (required)
        """
        if not tool_execution_port:
            raise ValueError("tool_execution_port is required (fail-fast)")
        if not artifact_mapper:
            raise ValueError("artifact_mapper is required (fail-fast)")

        self.tool_execution_port = tool_execution_port
        self.artifact_mapper = artifact_mapper

    def collect(
        self,
        step: ExecutionStep,
        result: StepExecutionDTO,
    ) -> dict[str, Artifact]:
        """
        Collect artifacts from step execution.

        Args:
            step: The execution step that was executed
            result: The step execution result

        Returns:
            Dictionary mapping artifact names to Artifact entities
        """
        # Get the tool instance
        tool = self.tool_execution_port.get_tool_by_name(step.tool)
        if not tool:
            return {}

        # Delegate to tool's collect_artifacts method (returns dict of raw values)
        artifacts_dict = tool.collect_artifacts(
            step.operation,
            result.result,
            step.params or {},
        )

        # Convert raw dict to dict of Artifact entities using mapper
        return self.artifact_mapper.to_entity_dict(artifacts_dict)

