"""gRPC servicer for Workflow Orchestration Service.

Implements WorkflowOrchestrationService from protobuf spec.
Following Hexagonal Architecture.
"""

import logging
from datetime import datetime

import grpc

from core.agents_and_tools.agents.domain.entities.rbac.action import Action, ActionEnum
from services.workflow.application.usecases.execute_workflow_action_usecase import (
    ExecuteWorkflowActionUseCase,
)
from services.workflow.application.usecases.get_pending_tasks_usecase import (
    GetPendingTasksUseCase,
)
from services.workflow.application.usecases.get_workflow_state_usecase import (
    GetWorkflowStateUseCase,
)
from services.workflow.domain.exceptions.workflow_transition_error import (
    WorkflowTransitionError,
)
from services.workflow.infrastructure.mappers.grpc_workflow_mapper import GrpcWorkflowMapper

logger = logging.getLogger(__name__)


class WorkflowOrchestrationServicer:
    """gRPC servicer for Workflow Orchestration Service.

    Implements all RPCs defined in workflow.proto:
    - GetWorkflowState: Query current task state
    - RequestValidation: Execute workflow action
    - GetPendingTasks: List tasks for a role
    - ClaimTask: Claim a task (transitions to active state)

    Following Hexagonal Architecture:
    - Infrastructure layer (gRPC-specific)
    - Calls application use cases
    - Handles protobuf serialization/deserialization via mappers
    - Dependency injection (receives use cases in constructor)
    """

    def __init__(
        self,
        get_workflow_state: GetWorkflowStateUseCase,
        execute_workflow_action: ExecuteWorkflowActionUseCase,
        get_pending_tasks: GetPendingTasksUseCase,
        workflow_pb2,
        workflow_pb2_grpc,
    ) -> None:
        """Initialize servicer with use cases.

        Args:
            get_workflow_state: Get workflow state use case
            execute_workflow_action: Execute workflow action use case
            get_pending_tasks: Get pending tasks use case
            workflow_pb2: Generated protobuf module
            workflow_pb2_grpc: Generated gRPC servicer module
        """
        self._get_workflow_state = get_workflow_state
        self._execute_workflow_action = execute_workflow_action
        self._get_pending_tasks = get_pending_tasks
        self._pb2 = workflow_pb2
        self._pb2_grpc = workflow_pb2_grpc

    async def GetWorkflowState(self, request, context):
        """Get current workflow state for a task.

        RPC: GetWorkflowState
        """
        try:
            # Convert request to domain object
            task_id = GrpcWorkflowMapper.task_id_from_request(request.task_id)

            # Execute use case
            state = await self._get_workflow_state.execute(task_id)

            if state is None:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Task {request.task_id} not found in workflow")
                return self._pb2.WorkflowStateResponse()

            # Convert domain entity to protobuf
            return GrpcWorkflowMapper.workflow_state_to_response(
                state=state,
                response_class=self._pb2.WorkflowStateResponse,
            )

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return self._pb2.WorkflowStateResponse()

        except Exception as e:
            logger.error(f"Error in GetWorkflowState: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return self._pb2.WorkflowStateResponse()

    async def RequestValidation(self, request, context):
        """Execute a workflow action (validation request).

        RPC: RequestValidation
        Used by validators (Architect, QA, PO) to approve/reject work.
        """
        try:
            # Convert request to domain objects
            task_id = GrpcWorkflowMapper.task_id_from_request(request.task_id)
            role = GrpcWorkflowMapper.role_from_request(request.validator_role)

            # Parse action from request (convert to Action value object)
            action = Action(value=ActionEnum(request.action))
            timestamp = datetime.now()
            feedback = request.feedback if request.feedback else None

            # Execute use case
            new_state = await self._execute_workflow_action.execute(
                task_id=task_id,
                action=action,
                actor_role=role,
                timestamp=timestamp,
                feedback=feedback,
            )

            # Convert result to protobuf
            return self._pb2.RequestValidationResponse(
                success=True,
                new_state=new_state.current_state.value,
                message=f"Action {request.action} executed successfully",
            )

        except WorkflowTransitionError as e:
            # Business rule violation (not allowed)
            return self._pb2.RequestValidationResponse(
                success=False,
                new_state="",
                message=str(e),
            )

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return self._pb2.RequestValidationResponse(success=False, message=str(e))

        except Exception as e:
            logger.error(f"Error in RequestValidation: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return self._pb2.RequestValidationResponse(success=False, message="Internal error")

    async def GetPendingTasks(self, request, context):
        """Get pending tasks for a role.

        RPC: GetPendingTasks
        Used by Orchestrator to find tasks ready for assignment.
        """
        try:
            # Convert request to domain object
            role = GrpcWorkflowMapper.role_from_request(request.role)
            limit = request.limit if request.limit > 0 else 100

            # Execute use case
            states = await self._get_pending_tasks.execute(role=role, limit=limit)

            # Convert domain entities to protobuf
            task_infos = GrpcWorkflowMapper.workflow_states_to_task_list(
                states=states,
                task_info_class=self._pb2.TaskInfo,
            )

            return self._pb2.PendingTasksResponse(
                tasks=task_infos,
                total_count=len(task_infos),
            )

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return self._pb2.PendingTasksResponse(tasks=[], total_count=0)

        except Exception as e:
            logger.error(f"Error in GetPendingTasks: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return self._pb2.PendingTasksResponse(tasks=[], total_count=0)

    async def ClaimTask(self, request, context):
        """Claim a task (transition to active work state).

        RPC: ClaimTask
        Used by agents to claim TODO tasks and start working.
        """
        try:
            # Convert request to domain objects
            task_id = GrpcWorkflowMapper.task_id_from_request(request.task_id)
            role = GrpcWorkflowMapper.role_from_request(request.agent_role)

            # CLAIM_TASK action (Action value object)
            action = Action(value=ActionEnum.CLAIM_TASK)
            timestamp = datetime.now()

            # Execute use case
            new_state = await self._execute_workflow_action.execute(
                task_id=task_id,
                action=action,
                actor_role=role,
                timestamp=timestamp,
                feedback=None,
            )

            return self._pb2.ClaimTaskResponse(
                success=True,
                new_state=new_state.current_state.value,
                message=f"Task {request.task_id} claimed by {request.agent_role}",
            )

        except WorkflowTransitionError as e:
            # Business rule violation (task not available for claim)
            return self._pb2.ClaimTaskResponse(
                success=False,
                new_state="",
                message=str(e),
            )

        except ValueError as e:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return self._pb2.ClaimTaskResponse(success=False, message=str(e))

        except Exception as e:
            logger.error(f"Error in ClaimTask: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details("Internal server error")
            return self._pb2.ClaimTaskResponse(success=False, message="Internal error")

