"""gRPC protobuf mappers for workflow service.

Converts domain entities to/from protobuf messages.
Following Hexagonal Architecture (Infrastructure responsibility).
"""

from google.protobuf.timestamp_pb2 import Timestamp

from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.role import Role
from services.workflow.domain.value_objects.task_id import TaskId


class GrpcWorkflowMapper:
    """Maps domain entities to/from protobuf messages.

    This is infrastructure responsibility:
    - Domain entities do NOT know about protobuf
    - Mappers live in infrastructure layer
    - Handle all type conversions (str, enum, timestamp)

    Following DDD:
    - No to_proto() / from_proto() in domain
    - Explicit mappers in infrastructure
    """

    @staticmethod
    def task_id_from_request(task_id_str: str) -> TaskId:
        """Convert request task_id string to TaskId value object.

        Args:
            task_id_str: Task ID from protobuf request

        Returns:
            TaskId value object

        Raises:
            ValueError: If task_id is invalid (fail-fast)
        """
        return TaskId(task_id_str)

    @staticmethod
    def role_from_request(role_str: str) -> Role:
        """Convert request role string to Role value object.

        Args:
            role_str: Role from protobuf request

        Returns:
            Role value object

        Raises:
            ValueError: If role is invalid (fail-fast)
        """
        return Role(role_str)

    @staticmethod
    def workflow_state_to_response(
        state: WorkflowState,
        response_class,
    ):
        """Convert WorkflowState to WorkflowStateResponse protobuf.

        Args:
            state: Domain entity
            response_class: Protobuf response class (from generated code)

        Returns:
            Populated protobuf response
        """
        # Create timestamp protobuf
        timestamp_pb = Timestamp()
        timestamp_pb.FromDatetime(state.updated_at)

        # Get last transition for audit info
        last_transition = state.get_last_transition()

        return response_class(
            task_id=str(state.task_id),
            story_id=str(state.story_id),
            current_state=state.current_state.value,
            role_in_charge=str(state.role_in_charge) if state.role_in_charge else "",
            required_action=str(state.required_action.value.value) if state.required_action else "",  # Action.value.value
            feedback=state.feedback or "",
            retry_count=state.retry_count,
            updated_at=timestamp_pb,
            is_terminal=state.is_terminal(),
            is_waiting_for_action=state.is_waiting_for_action(),
            rejection_count=state.get_rejection_count(),
            last_action=str(last_transition.action.value.value) if last_transition else "",  # Action.value.value
            last_actor_role=str(last_transition.actor_role) if last_transition else "",
        )

    @staticmethod
    def workflow_states_to_task_list(
        states: list[WorkflowState],
        task_info_class,
    ) -> list:
        """Convert list of WorkflowState to list of TaskInfo protobuf.

        Args:
            states: List of domain entities
            task_info_class: Protobuf TaskInfo class (from generated code)

        Returns:
            List of protobuf TaskInfo messages
        """
        task_infos = []

        for state in states:
            timestamp_pb = Timestamp()
            timestamp_pb.FromDatetime(state.updated_at)

            task_info = task_info_class(
                task_id=str(state.task_id),
                story_id=str(state.story_id),
                current_state=state.current_state.value,
                required_action=str(state.required_action.value.value) if state.required_action else "",  # Action.value.value
                feedback=state.feedback or "",
                retry_count=state.retry_count,
                rejection_count=state.get_rejection_count(),
                updated_at=timestamp_pb,
            )

            task_infos.append(task_info)

        return task_infos

