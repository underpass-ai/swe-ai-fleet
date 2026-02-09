from __future__ import annotations

import logging
from typing import Any

import grpc
from google.protobuf.timestamp_pb2 import Timestamp

from services.ray_executor.application.usecases import (
    ExecuteDeliberationUseCase,
    GetActiveJobsUseCase,
    GetDeliberationStatusUseCase,
    GetStatsUseCase,
)
from services.ray_executor.domain.entities import DeliberationRequest
from services.ray_executor.domain.value_objects import AgentConfig, TaskConstraints
from services.ray_executor.gen import ray_executor_pb2, ray_executor_pb2_grpc

logger = logging.getLogger(__name__)


class RayExecutorServiceServicer(ray_executor_pb2_grpc.RayExecutorServiceServicer):
    """gRPC servicer for Ray Executor Service.

    This servicer is a thin adapter that:
    - Receives gRPC requests
    - Converts protobuf to domain entities
    - Delegates to use cases
    - Converts domain entities back to protobuf
    """

    def __init__(
        self,
        execute_deliberation_usecase: ExecuteDeliberationUseCase,
        get_deliberation_status_usecase: GetDeliberationStatusUseCase,
        get_stats_usecase: GetStatsUseCase,
        get_active_jobs_usecase: GetActiveJobsUseCase,
    ) -> None:
        """Initialize servicer with use cases."""
        self._execute_deliberation = execute_deliberation_usecase
        self._get_deliberation_status = get_deliberation_status_usecase
        self._get_stats = get_stats_usecase
        self._get_active_jobs = get_active_jobs_usecase

    @staticmethod
    def _build_agents(request: Any) -> tuple[AgentConfig, ...]:
        """Build agent configurations from protobuf request."""
        return tuple(
            AgentConfig(
                agent_id=agent.id,
                role=agent.role,
                model=agent.model,
                prompt_template=agent.prompt_template,
            )
            for agent in request.agents
        )

    @staticmethod
    def _extract_metadata_from_constraints(constraints: Any) -> dict | None:
        """Extract metadata dict from constraints, if present."""
        if constraints.metadata:
            return dict(constraints.metadata)
        return None

    @staticmethod
    def _ensure_story_id_in_metadata(
        constraints: Any,
        metadata: dict | None,
    ) -> dict:
        """Ensure story_id is present in metadata for backlog review flows."""
        if metadata is None:
            metadata = {}
        if "story_id" not in metadata and constraints.story_id:
            metadata["story_id"] = constraints.story_id
        return metadata

    @staticmethod
    def _build_backlog_review_constraints(
        request: Any,
        metadata: dict | None,
    ) -> TaskConstraints:
        """Build TaskConstraints for backlog review (no plan_id)."""
        return TaskConstraints(
            story_id=request.constraints.story_id,
            plan_id="",
            timeout_seconds=request.constraints.timeout_seconds or 300,
            max_retries=request.constraints.max_retries or 3,
            metadata=metadata,
        )

    @staticmethod
    def _build_execute_backlog_review_error_response_for_missing_task_id(
        request: Any,
        context: Any,
    ) -> ray_executor_pb2.ExecuteDeliberationResponse:
        task_description_preview = (
            request.task_description[:100] if request.task_description else "N/A"
        )
        story_id = request.constraints.story_id if request.constraints else "N/A"
        error_msg = (
            "❌ CRITICAL ERROR: task_id is MISSING in ExecuteBacklogReviewDeliberation request! "
            "Backlog review ceremonies REQUIRE task_id in format 'ceremony-{id}:story-{id}:role-{role}'. "
            f"Request: task_description='{task_description_preview}...', "
            f"role={request.role}, story_id={story_id}"
        )
        logger.error(error_msg)
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_msg)
        return ray_executor_pb2.ExecuteDeliberationResponse()

    @staticmethod
    def _build_execute_backlog_review_error_response_for_invalid_task_id_format(
        request: Any,
        context: Any,
    ) -> ray_executor_pb2.ExecuteDeliberationResponse:
        error_msg = (
            "❌ CRITICAL ERROR: Invalid task_id format in "
            "ExecuteBacklogReviewDeliberation request! "
            "Expected format: 'ceremony-{id}:story-{id}:role-{role}', "
            f"got: '{request.task_id}'. "
            "Request: "
            f"task_description='{request.task_description[:100] if request.task_description else 'N/A'}...', "
            f"role={request.role}"
        )
        logger.error(error_msg)
        context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
        context.set_details(error_msg)
        return ray_executor_pb2.ExecuteDeliberationResponse()

    async def ExecuteDeliberation(self, request, context):
        """Execute deliberation on Ray cluster (for task derivation - requires plan_id)."""
        try:
            agents = tuple(
                AgentConfig(
                    agent_id=agent.id,
                    role=agent.role,
                    model=agent.model,
                    prompt_template=agent.prompt_template,
                )
                for agent in request.agents
            )

            metadata = None
            if request.constraints.metadata:
                metadata = dict(request.constraints.metadata)

            constraints = TaskConstraints(
                story_id=request.constraints.story_id,
                plan_id=request.constraints.plan_id,
                timeout_seconds=request.constraints.timeout_seconds or 300,
                max_retries=request.constraints.max_retries or 3,
                metadata=metadata,
            )

            deliberation_request = DeliberationRequest(
                task_id=request.task_id,
                task_description=request.task_description,
                role=request.role,
                constraints=constraints,
                agents=agents,
                vllm_url=request.vllm_url,
                vllm_model=request.vllm_model,
            )

            if not request.task_id or not request.task_id.strip():
                task_description_preview = (
                    request.task_description[:100] if request.task_description else "N/A"
                )
                error_msg = (
                    "❌ CRITICAL ERROR: task_id is MISSING in ExecuteDeliberation request! "
                    "Backlog review ceremonies REQUIRE task_id in format "
                    "'ceremony-{id}:story-{id}:role-{role}'. "
                    f"Request: task_description='{task_description_preview}...', "
                    f"role={request.role}"
                )
                logger.error(error_msg)
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(error_msg)
                return ray_executor_pb2.ExecuteDeliberationResponse()

            result = await self._execute_deliberation.execute(deliberation_request)

            return ray_executor_pb2.ExecuteDeliberationResponse(
                task_id=request.task_id,
                deliberation_id=result.deliberation_id,
                status=result.status,
                message=result.message,
            )

        except ValueError as exc:  # Domain validation errors
            logger.error("Validation error: %s", exc)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return ray_executor_pb2.ExecuteDeliberationResponse()

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Unexpected error: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(exc)}")
            return ray_executor_pb2.ExecuteDeliberationResponse()

    async def ExecuteBacklogReviewDeliberation(self, request, context):
        """Execute deliberation for backlog review (no plan_id required, only story_id)."""
        try:
            agents = self._build_agents(request)

            raw_metadata = self._extract_metadata_from_constraints(request.constraints)
            metadata = self._ensure_story_id_in_metadata(request.constraints, raw_metadata)

            constraints = self._build_backlog_review_constraints(request, metadata)

            if not request.task_id or not request.task_id.strip():
                return self._build_execute_backlog_review_error_response_for_missing_task_id(
                    request, context
                )

            has_valid_task_id_prefix = request.task_id.startswith("ceremony-")
            has_story_segment = ":story-" in request.task_id
            has_role_segment = ":role-" in request.task_id
            if not (has_valid_task_id_prefix and has_story_segment and has_role_segment):
                return self._build_execute_backlog_review_error_response_for_invalid_task_id_format(
                    request, context
                )

            logger.info(
                "✅ ExecuteBacklogReviewDeliberation: Valid task_id found: %s",
                request.task_id,
            )

            deliberation_request = DeliberationRequest(
                task_id=request.task_id,
                task_description=request.task_description,
                role=request.role,
                constraints=constraints,
                agents=agents,
                vllm_url=request.vllm_url,
                vllm_model=request.vllm_model,
            )

            result = await self._execute_deliberation.execute(deliberation_request)

            return ray_executor_pb2.ExecuteDeliberationResponse(
                task_id=request.task_id,
                deliberation_id=result.deliberation_id,
                status=result.status,
                message=result.message,
            )

        except ValueError as exc:  # Domain validation errors
            logger.error("Validation error: %s", exc)
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(exc))
            return ray_executor_pb2.ExecuteDeliberationResponse()

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Unexpected error: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(exc)}")
            return ray_executor_pb2.ExecuteDeliberationResponse()

    async def GetDeliberationStatus(self, request, context):
        """Get status of a running deliberation."""
        try:
            response = await self._get_deliberation_status.execute(request.deliberation_id)

            proto_response = ray_executor_pb2.GetDeliberationStatusResponse(
                status=response.status,
            )

            if response.result:
                from services.ray_executor.domain.entities import (
                    DeliberationResult,
                    MultiAgentDeliberationResult,
                )

                if isinstance(response.result, MultiAgentDeliberationResult):
                    best_result = response.result.best_result
                    if best_result:
                        proto_response.result.CopyFrom(
                            ray_executor_pb2.DeliberationResult(
                                agent_id=best_result.agent_id,
                                proposal=best_result.proposal,
                                reasoning=best_result.reasoning,
                                score=best_result.score,
                                metadata={
                                    **best_result.metadata,
                                    "total_agents": str(response.result.total_agents),
                                    "completed_agents": str(response.result.completed_agents),
                                    "failed_agents": str(response.result.failed_agents),
                                    "average_score": str(response.result.average_score),
                                },
                            )
                        )
                        logger.info(
                            "Multi-agent deliberation completed: %s/%s agents, "
                            "best score: %.2f, average: %.2f",
                            response.result.completed_agents,
                            response.result.total_agents,
                            best_result.score,
                            response.result.average_score,
                        )
                elif isinstance(response.result, DeliberationResult):
                    proto_response.result.CopyFrom(
                        ray_executor_pb2.DeliberationResult(
                            agent_id=response.result.agent_id,
                            proposal=response.result.proposal,
                            reasoning=response.result.reasoning,
                            score=response.result.score,
                            metadata=response.result.metadata,
                        )
                    )

            if response.error_message:
                proto_response.error_message = response.error_message

            return proto_response

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error in GetDeliberationStatus: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return ray_executor_pb2.GetDeliberationStatusResponse()

    async def GetStatus(self, request, context):
        """Get service health and statistics."""
        try:
            stats, uptime_seconds = await self._get_stats.execute()

            return ray_executor_pb2.GetStatusResponse(
                status="healthy",
                uptime_seconds=int(uptime_seconds),
                stats=ray_executor_pb2.RayExecutorStats(
                    total_deliberations=stats.total_deliberations,
                    active_deliberations=stats.active_deliberations,
                    completed_deliberations=stats.completed_deliberations,
                    failed_deliberations=stats.failed_deliberations,
                    average_execution_time_ms=stats.average_execution_time_ms,
                ),
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error in GetStatus: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return ray_executor_pb2.GetStatusResponse(status="unhealthy")

    async def GetActiveJobs(self, request, context):
        """Get list of active Ray jobs."""
        try:
            jobs = await self._get_active_jobs.execute()

            proto_jobs = []
            for job_info in jobs:
                # Create start_time timestamp
                start_timestamp = Timestamp()
                start_timestamp.FromSeconds(job_info.start_time_seconds)

                proto_jobs.append(
                    ray_executor_pb2.JobInfo(
                        job_id=job_info.job_id,
                        name=job_info.name,
                        status=job_info.status,
                        submission_id=job_info.submission_id,
                        role=job_info.role,
                        task_id=job_info.task_id,
                        start_time=start_timestamp,
                        runtime=job_info.runtime,
                    )
                )

            logger.info("📊 Returning %d active jobs", len(proto_jobs))
            return ray_executor_pb2.GetActiveJobsResponse(jobs=proto_jobs)

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error in GetActiveJobs: %s", exc, exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(exc))
            return ray_executor_pb2.GetActiveJobsResponse()
