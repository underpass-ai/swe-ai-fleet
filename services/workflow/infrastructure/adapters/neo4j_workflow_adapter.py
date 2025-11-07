"""Neo4j adapter for workflow state persistence.

Implements WorkflowStateRepositoryPort using Neo4j graph database.
Following Hexagonal Architecture (Adapter).
"""

from datetime import datetime

from core.shared.domain import Action, ActionEnum
from neo4j import AsyncDriver

from services.workflow.application.ports.workflow_state_repository_port import (
    WorkflowStateRepositoryPort,
)
from services.workflow.domain.entities.state_transition import StateTransition
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.story_id import StoryId
from services.workflow.domain.value_objects.task_id import TaskId
from services.workflow.domain.value_objects.workflow_state_enum import WorkflowStateEnum
from services.workflow.infrastructure.adapters.neo4j_queries import Neo4jWorkflowQueries
from services.workflow.infrastructure.mappers.state_transition_mapper import (
    StateTransitionMapper,
)


class Neo4jWorkflowAdapter(WorkflowStateRepositoryPort):
    """Neo4j adapter for workflow state persistence.

    Schema:
        (:Task)-[:HAS_WORKFLOW_STATE]->(:WorkflowState)
        (:WorkflowState)-[:HAS_TRANSITION]->(:StateTransition)

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure implementation)
    - Implements WorkflowStateRepositoryPort (application port)
    - Contains Neo4j-specific logic (Cypher queries, serialization)
    """

    def __init__(self, driver: AsyncDriver) -> None:
        """Initialize adapter with Neo4j driver.

        Args:
            driver: Neo4j async driver
        """
        self._driver = driver

    async def get_state(self, task_id: TaskId) -> WorkflowState | None:
        """Get workflow state for a task.

        Fail-fast: Neo4j exceptions propagate immediately (no silent failures).

        Args:
            task_id: Task identifier

        Returns:
            WorkflowState if found, None if not exists

        Raises:
            Neo4jError: Connection or query errors (fail-fast)
            ValueError: Invalid data in database (fail-fast)
        """
        # Fail-fast: No try/except, exceptions propagate immediately
        async with self._driver.session() as session:
            result = await session.run(
                str(Neo4jWorkflowQueries.GET_WORKFLOW_STATE),
                task_id=str(task_id)
            )
            record = await result.single()

            if record is None:
                return None  # Not found is valid (not an error)

            ws_node = dict(record["ws"])
            transition_nodes = [dict(t) for t in record["transitions"] if t is not None]

            return self._from_neo4j(ws_node, transition_nodes)

    async def save_state(self, state: WorkflowState) -> None:
        """Save workflow state.

        Creates or updates WorkflowState node and appends new transitions.
        Fail-fast: Neo4j exceptions propagate immediately (no silent failures).

        Args:
            state: Workflow state to persist

        Raises:
            Neo4jError: Connection or query errors (fail-fast)
        """
        # Serialize history using mapper (infrastructure responsibility)
        transitions_data = StateTransitionMapper.to_dict_list(state.history)

        async with self._driver.session() as session:
            await session.run(
                str(Neo4jWorkflowQueries.SAVE_WORKFLOW_STATE),
                task_id=str(state.task_id),
                story_id=str(state.story_id),
                current_state=state.get_current_state_value(),
                role_in_charge=state.get_role_in_charge_value(),
                required_action=state.get_required_action_value(),
                feedback=state.feedback,
                updated_at=state.updated_at.isoformat(),
                retry_count=state.retry_count,
                transitions=transitions_data,
            )

    async def get_pending_by_role(self, role: str, limit: int = 100) -> list[WorkflowState]:
        """Get pending tasks for a role.

        Args:
            role: Role identifier
            limit: Maximum number of results

        Returns:
            List of WorkflowState instances
        """
        async with self._driver.session() as session:
            result = await session.run(
                str(Neo4jWorkflowQueries.GET_PENDING_BY_ROLE),
                role=role,
                limit=limit
            )
            records = await result.data()

            states = []
            for record in records:
                ws_node = dict(record["ws"])
                transition_nodes = [dict(t) for t in record["transitions"] if t is not None]
                states.append(self._from_neo4j(ws_node, transition_nodes))

            return states

    async def get_all_by_story(self, story_id: StoryId) -> list[WorkflowState]:
        """Get all workflow states for a story.

        Args:
            story_id: Story identifier

        Returns:
            List of WorkflowState instances
        """
        async with self._driver.session() as session:
            result = await session.run(
                str(Neo4jWorkflowQueries.GET_ALL_BY_STORY),
                story_id=str(story_id)
            )
            records = await result.data()

            states = []
            for record in records:
                ws_node = dict(record["ws"])
                transition_nodes = [dict(t) for t in record["transitions"] if t is not None]
                states.append(self._from_neo4j(ws_node, transition_nodes))

            return states

    async def delete_state(self, task_id: TaskId) -> None:
        """Delete workflow state.

        Args:
            task_id: Task identifier
        """
        async with self._driver.session() as session:
            await session.run(
                str(Neo4jWorkflowQueries.DELETE_WORKFLOW_STATE),
                task_id=str(task_id)
            )

    def _from_neo4j(
        self,
        ws_node: dict,
        transition_nodes: list[dict],
    ) -> WorkflowState:
        """Convert Neo4j nodes to WorkflowState domain entity.

        This is the mapper logic (infrastructure responsibility).
        Domain entities do NOT know about Neo4j.

        Fail-fast: Invalid data raises immediately (ValueError, KeyError).

        Args:
            ws_node: WorkflowState node properties
            transition_nodes: StateTransition node properties

        Returns:
            WorkflowState domain entity

        Raises:
            KeyError: Missing required field (fail-fast)
            ValueError: Invalid enum/format (fail-fast)
        """
        # Fail-fast: Validate required fields exist
        required_fields = ["task_id", "story_id", "current_state", "updated_at"]
        for field in required_fields:
            if field not in ws_node:
                raise ValueError(
                    f"Missing required field '{field}' in WorkflowState node for task {ws_node.get('task_id', 'UNKNOWN')}"
                )

        # Parse transitions (fail-fast: invalid data raises ValueError)
        transitions = []
        for t_node in transition_nodes:
            transitions.append(
                StateTransition(
                    from_state=t_node["from_state"],
                    to_state=t_node["to_state"],
                    action=Action(value=ActionEnum(t_node["action"])),  # Fail-fast if invalid
                    actor_role=Role(t_node["actor_role"]),  # Fail-fast if invalid
                    timestamp=datetime.fromisoformat(t_node["timestamp"]),  # Fail-fast if invalid
                    feedback=t_node.get("feedback"),
                )
            )

        # Parse role_in_charge (fail-fast if invalid)
        role_in_charge = None
        if ws_node.get("role_in_charge"):
            role_in_charge = Role(ws_node["role_in_charge"])

        # Parse required_action (fail-fast if invalid)
        required_action = None
        if ws_node.get("required_action"):
            required_action = Action(value=ActionEnum(ws_node["required_action"]))

        # Fail-fast: Invalid enum values or missing fields raise immediately
        return WorkflowState(
            task_id=TaskId(ws_node["task_id"]),
            story_id=StoryId(ws_node["story_id"]),
            current_state=WorkflowStateEnum(ws_node["current_state"]),
            role_in_charge=role_in_charge,
            required_action=required_action,
            history=tuple(transitions),
            feedback=ws_node.get("feedback"),
            updated_at=datetime.fromisoformat(ws_node["updated_at"]),
            retry_count=ws_node.get("retry_count", 0),
        )

