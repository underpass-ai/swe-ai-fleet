"""Use case to synchronize Project from Planning Service to Context graph."""

import logging

from core.context.domain.project import Project
from core.context.ports.graph_command_port import GraphCommandPort

logger = logging.getLogger(__name__)


class SynchronizeProjectFromPlanningUseCase:
    """Synchronize a Project from Planning Service to Context graph.

    Bounded Context: Context Service
    Trigger: planning.project.created event from Planning Service

    Responsibility:
    - Receive Project entity (domain pure)
    - Persist in graph via Port
    - Application-level logging

    Does NOT know about: DTOs, NATS, Neo4j
    Only knows about: Entities, VOs, Ports (domain + abstractions)

    Following Hexagonal Architecture:
    - Application layer orchestrates domain logic
    - Depends on ports (interfaces), not adapters
    - Pure business logic, no infrastructure concerns
    """

    def __init__(self, graph_command: GraphCommandPort):
        """Initialize use case with dependency injection via Port.

        Args:
            graph_command: Port for graph persistence (interface, not implementation)
        """
        self._graph = graph_command

    async def execute(self, project: Project) -> None:
        """Execute project synchronization.

        Args:
            project: Domain entity to persist

        Raises:
            Exception: If persistence fails (propagated from adapter)
        """
        # Tell, Don't Ask: entity provides its own log context
        log_ctx = project.get_log_context()
        log_ctx["use_case"] = "SynchronizeProjectFromPlanning"

        logger.info(
            f"Synchronizing project: {project.project_id.to_string()}",
            extra=log_ctx,
        )

        # Persist via Port (hexagonal boundary)
        await self._graph.save_project(project)

        logger.info(
            f"✓ Project synchronized: {project.project_id.to_string()}",
            extra=log_ctx,
        )

