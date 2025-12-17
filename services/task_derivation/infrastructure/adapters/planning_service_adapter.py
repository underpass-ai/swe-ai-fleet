"""gRPC adapter for Planning Service, implementing PlanningPort."""

from __future__ import annotations

import logging

import grpc
from grpc import aio
from task_derivation.application.ports.planning_port import PlanningPort
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.identifiers.task_id import TaskId
from task_derivation.domain.value_objects.task_derivation.commands.task_creation_command import (
    TaskCreationCommand,
)
from task_derivation.domain.value_objects.task_derivation.context.plan_context import (
    PlanContext,
)
from task_derivation.domain.value_objects.task_derivation.dependency.dependency_edge import (
    DependencyEdge,
)
from task_derivation.domain.value_objects.task_derivation.summary.task_summary import (
    TaskSummary,
)
from task_derivation.gen import task_derivation_pb2, task_derivation_pb2_grpc
from task_derivation.infrastructure.mappers.planning_grpc_mapper import (
    PlanningGrpcMapper,
)

logger = logging.getLogger(__name__)


class PlanningServiceAdapter(PlanningPort):
    """Concrete adapter bridging PlanningPort with gRPC service."""

    def __init__(
        self,
        address: str,
        *,
        timeout_seconds: float = 5.0,
        mapper: PlanningGrpcMapper | None = None,
        stub: task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub | None = None,
    ) -> None:
        if not address or not address.strip():
            raise ValueError("PlanningServiceAdapter address cannot be empty")

        self._address = address
        self._timeout = timeout_seconds
        self._mapper = mapper or PlanningGrpcMapper()

        self._channel: aio.Channel | None = None
        if stub is not None:
            self._stub = stub
        else:
            if task_derivation_pb2_grpc is None:
                raise RuntimeError(
                    "task_derivation_pb2_grpc is not available. "
                    "Generate protobuf stubs before instantiating PlanningServiceAdapter."
                )
            self._channel = grpc.aio.insecure_channel(address)
            self._stub = task_derivation_pb2_grpc.TaskDerivationPlanningServiceStub(
                self._channel
            )

    async def close(self) -> None:
        """Close gRPC resources if this adapter owns the channel."""
        if self._channel is not None:
            await self._channel.close()

    async def get_plan(self, plan_id: PlanId) -> PlanContext:
        request = task_derivation_pb2.GetPlanContextRequest(plan_id=plan_id.value)
        response = await self._stub.GetPlanContext(request, timeout=self._timeout)

        # Access proto field directly (no reflection)
        if not response.plan_context:
            raise ValueError("Planning service returned empty plan_context")

        context = self._mapper.plan_context_from_proto(response.plan_context)
        logger.info("Fetched plan context for %s", plan_id.value)
        return context

    async def create_tasks(
        self,
        commands: tuple[TaskCreationCommand, ...],
    ) -> tuple[TaskId, ...]:
        proto_commands = [
            self._mapper.task_creation_command_to_proto(
                command, self._pb2.TaskCreationCommand
            )
            for command in commands
        ]
        request = self._pb2.CreateTasksRequest(commands=proto_commands)
        response = await self._stub.CreateTasks(request, timeout=self._timeout)

        # Direct access to proto field (no reflection)
        task_ids = tuple(TaskId(task_id) for task_id in response.task_ids)
        logger.info("Persisted %s derived tasks", len(task_ids))
        return task_ids

    async def list_story_tasks(self, story_id: StoryId) -> tuple[TaskSummary, ...]:
        request = self._pb2.ListStoryTasksRequest(story_id=story_id.value)
        response = await self._stub.ListStoryTasks(request, timeout=self._timeout)

        # Direct access to proto field (no reflection)
        return self._mapper.task_summary_list_from_proto(response.tasks)

    async def save_task_dependencies(
        self,
        plan_id: PlanId,
        story_id: StoryId,
        dependencies: tuple[DependencyEdge, ...],
    ) -> None:
        if not dependencies:
            logger.info("No dependencies to persist for plan %s", plan_id.value)
            return

        # Use mapper to convert all edges
        proto_edges = self._mapper.dependency_edges_to_proto(
            dependencies, self._pb2.DependencyEdge
        )

        request = self._pb2.SaveTaskDependenciesRequest(
            plan_id=plan_id.value,
            story_id=story_id.value,
            edges=proto_edges,
        )
        await self._stub.SaveTaskDependencies(request, timeout=self._timeout)
        logger.info(
            "Persisted %s dependencies for plan %s", len(proto_edges), plan_id.value
        )

    @property
    def _pb2(self):
        if task_derivation_pb2 is None:
            raise RuntimeError(
                "task_derivation_pb2 module not available. Generate protobuf stubs first."
            )
        return task_derivation_pb2

