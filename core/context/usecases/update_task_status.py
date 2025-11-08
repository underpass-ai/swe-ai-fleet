# core/context/usecases/update_task_status.py
from dataclasses import dataclass
from typing import Any

from core.context.domain.task import Task
from core.context.domain.graph_label import GraphLabel
from core.context.infrastructure.mappers.task_mapper import TaskMapper
from core.context.ports.graph_command_port import GraphCommandPort


@dataclass
class UpdateTaskStatusUseCase:
    """Use case for updating Task status in Neo4j (formerly UpdateSubtaskStatusUseCase).

    This use case follows Hexagonal Architecture:
    - Receives event payload (dict)
    - Uses mapper to convert to domain entity
    - Updates Neo4j via port
    """

    writer: GraphCommandPort

    def execute(self, payload: dict[str, Any]) -> None:
        """Update task status.

        Args:
            payload: Event payload with {task_id, status, plan_id?}
        """
        # Use mapper to convert payload to domain entity
        task = TaskMapper.from_status_update_payload(payload)

        # Update task properties in Neo4j
        # Note: This updates the node properties, not the full entity
        self.writer.update_node_properties(
            label=GraphLabel.TASK,
            node_id=task.task_id.to_string(),
            properties=task.to_graph_properties()
        )
