"""gRPC servicer implementing TaskDerivationPlanningService for Planning."""

from __future__ import annotations

import logging
from uuid import uuid4

from core.shared.domain.value_objects.content.task_description import TaskDescription
from core.shared.domain.value_objects.task_attributes.duration import Duration
from core.shared.domain.value_objects.task_attributes.priority import Priority
from planning.application.ports.storage_port import StoragePort
from planning.application.usecases.create_task_usecase import CreateTaskUseCase
from planning.application.usecases.list_tasks_usecase import ListTasksUseCase
from planning.domain.entities.plan import Plan
from planning.domain.entities.task import Task
from planning.domain.value_objects.actors.role_mapper import RoleMapper
from planning.domain.value_objects.content.dependency_reason import DependencyReason
from planning.domain.value_objects.content.title import Title
from planning.domain.value_objects.identifiers.plan_id import PlanId
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.requests.create_task_request import CreateTaskRequest
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.domain.value_objects.task_derivation.dependency_edge import DependencyEdge
from planning.gen import task_derivation_pb2, task_derivation_pb2_grpc

import grpc

logger = logging.getLogger(__name__)


class TaskDerivationPlanningServiceServicer(
    task_derivation_pb2_grpc.TaskDerivationPlanningServiceServicer
):
    """Expose Planning operations required by Task Derivation Service."""

    def __init__(
        self,
        *,
        storage: StoragePort,
        create_task_uc: CreateTaskUseCase,
        list_tasks_uc: ListTasksUseCase,
    ) -> None:
        self._storage = storage
        self._create_task_uc = create_task_uc
        self._list_tasks_uc = list_tasks_uc

    async def GetPlanContext(self, request, context):  # noqa: N802 - gRPC interface naming
        """Return immutable plan context for task derivation prompts."""
        try:
            plan_id = PlanId(request.plan_id)
            plan = await self._storage.get_plan(plan_id)
            if not plan:
                context.set_code(grpc.StatusCode.NOT_FOUND)
                context.set_details(f"Plan not found: {plan_id.value}")
                return task_derivation_pb2.GetPlanContextResponse()

            return task_derivation_pb2.GetPlanContextResponse(
                plan_context=self._plan_to_proto(plan)
            )

        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return task_derivation_pb2.GetPlanContextResponse()

        except Exception as exc:  # pragma: no cover - defensive
            logger.error("GetPlanContext failed: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return task_derivation_pb2.GetPlanContextResponse()

    async def CreateTasks(self, request, context):  # noqa: N802 - gRPC interface naming
        """Create tasks in bulk and return generated task IDs."""
        try:
            created_task_ids: list[str] = []
            for command in request.commands:
                create_request = self._command_to_create_task_request(command)
                task = await self._create_task_uc.execute(create_request)
                created_task_ids.append(task.task_id.value)

            return task_derivation_pb2.CreateTasksResponse(task_ids=created_task_ids)

        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return task_derivation_pb2.CreateTasksResponse(task_ids=[])

        except Exception as exc:  # pragma: no cover - defensive
            logger.error("CreateTasks failed: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return task_derivation_pb2.CreateTasksResponse(task_ids=[])

    async def ListStoryTasks(self, request, context):  # noqa: N802 - gRPC interface naming
        """List existing tasks for one story."""
        try:
            story_id = StoryId(request.story_id)
            tasks = await self._list_tasks_uc.execute(
                story_id=story_id,
                plan_id=None,
                limit=1000,
                offset=0,
            )
            return task_derivation_pb2.ListStoryTasksResponse(
                tasks=[self._task_to_summary_proto(task) for task in tasks]
            )

        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return task_derivation_pb2.ListStoryTasksResponse(tasks=[])

        except Exception as exc:  # pragma: no cover - defensive
            logger.error("ListStoryTasks failed: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return task_derivation_pb2.ListStoryTasksResponse(tasks=[])

    async def SaveTaskDependencies(self, request, context):  # noqa: N802 - gRPC interface naming
        """Persist task dependency graph edges."""
        try:
            # Keep fail-fast validation for required IDs even if not used directly here.
            PlanId(request.plan_id)
            StoryId(request.story_id)

            dependencies = tuple(
                DependencyEdge(
                    from_task_id=TaskId(edge.from_task_id),
                    to_task_id=TaskId(edge.to_task_id),
                    reason=DependencyReason(edge.reason.strip() or "Dependency inferred"),
                )
                for edge in request.edges
            )

            if dependencies:
                await self._storage.save_task_dependencies(dependencies)

            return task_derivation_pb2.SaveTaskDependenciesResponse(success=True)

        except ValueError as exc:
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return task_derivation_pb2.SaveTaskDependenciesResponse(success=False)

        except Exception as exc:  # pragma: no cover - defensive
            logger.error("SaveTaskDependencies failed: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return task_derivation_pb2.SaveTaskDependenciesResponse(success=False)

    @staticmethod
    def _plan_to_proto(plan: Plan) -> task_derivation_pb2.PlanContext:
        technical_notes = plan.technical_notes.strip() or "Not specified"
        roles = list(plan.roles) if plan.roles else ["DEV"]

        return task_derivation_pb2.PlanContext(
            plan_id=plan.plan_id.value,
            story_id=plan.story_ids[0].value,
            title=plan.title.value,
            description=plan.description.value,
            acceptance_criteria=list(plan.acceptance_criteria),
            technical_notes=technical_notes,
            roles=roles,
        )

    @staticmethod
    def _command_to_create_task_request(command) -> CreateTaskRequest:
        title = Title(command.title)
        description = TaskDescription(command.description.strip() or command.title)
        assigned_role = RoleMapper.from_string(command.assigned_role or "DEV")
        estimated_hours = Duration.from_optional(command.estimated_hours)
        priority = Priority.from_optional(command.priority)

        return CreateTaskRequest(
            story_id=StoryId(command.story_id),
            task_id=TaskId(f"T-{uuid4()}"),
            title=title,
            description=description,
            task_type=TaskType.DEVELOPMENT,
            assigned_to=assigned_role,
            estimated_hours=estimated_hours,
            priority=priority,
            plan_id=PlanId(command.plan_id) if command.plan_id else None,
        )

    @staticmethod
    def _task_to_summary_proto(task: Task) -> task_derivation_pb2.TaskSummary:
        return task_derivation_pb2.TaskSummary(
            task_id=task.task_id.value,
            title=task.title,
            priority=task.priority,
            assigned_role=task.assigned_to or "DEV",
        )
