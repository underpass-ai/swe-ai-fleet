#!/usr/bin/env python3
"""
Ray Executor Service - Entry Point

Microservice for executing deliberations on Ray cluster.
Follows Hexagonal Architecture (Ports & Adapters).

Responsibilities:
- Initialize infrastructure (Ray, NATS, gRPC)
- Wire dependencies (dependency injection)
- Delegate business logic to use cases
"""

import asyncio
import logging
import os
import sys
import time

import grpc
import nats
import ray
from services.ray_executor.gen import ray_executor_pb2, ray_executor_pb2_grpc
from google.protobuf.timestamp_pb2 import Timestamp
from grpc import aio as grpc_aio

# Import hexagonal architecture components
from services.ray_executor.application.usecases import (
    ExecuteDeliberationUseCase,
    GetActiveJobsUseCase,
    GetDeliberationStatusUseCase,
    GetStatsUseCase,
)
from services.ray_executor.domain.entities import (
    DeliberationRequest,
)
from services.ray_executor.domain.value_objects import (
    AgentConfig,
    TaskConstraints,
)
from services.ray_executor.infrastructure.adapters import (
    NATSPublisherAdapter,
    RayClusterAdapter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


class RayExecutorServiceServicer(ray_executor_pb2_grpc.RayExecutorServiceServicer):
    """gRPC servicer for Ray Executor Service.

    This servicer is a thin adapter that:
    - Receives gRPC requests
    - Converts protobuf to domain entities
    - Delegates to use cases
    - Converts domain entities back to protobuf

    Following Hexagonal Architecture:
    - Infrastructure adapter (gRPC → use cases)
    - All dependencies injected via constructor
    - No business logic here, only translation
    """

    def __init__(
        self,
        execute_deliberation_usecase: ExecuteDeliberationUseCase,
        get_deliberation_status_usecase: GetDeliberationStatusUseCase,
        get_stats_usecase: GetStatsUseCase,
        get_active_jobs_usecase: GetActiveJobsUseCase,
    ):
        """Initialize servicer with use cases.

        Args:
            execute_deliberation_usecase: Use case for executing deliberations
            get_deliberation_status_usecase: Use case for status checks
            get_stats_usecase: Use case for retrieving statistics
            get_active_jobs_usecase: Use case for getting active jobs
        """
        self._execute_deliberation = execute_deliberation_usecase
        self._get_deliberation_status = get_deliberation_status_usecase
        self._get_stats = get_stats_usecase
        self._get_active_jobs = get_active_jobs_usecase

    async def ExecuteDeliberation(self, request, context):
        """Execute deliberation on Ray cluster.

        Translates gRPC request → domain entity → use case → gRPC response
        """
        try:
            # Convert protobuf to domain entities
            agents = tuple(
                AgentConfig(
                    agent_id=agent.id,
                    role=agent.role,
                    model=agent.model,
                    prompt_template=agent.prompt_template,
                )
                for agent in request.agents
            )

            constraints = TaskConstraints(
                story_id=request.constraints.story_id,
                plan_id=request.constraints.plan_id,
                timeout_seconds=request.constraints.timeout_seconds or 300,
                max_retries=request.constraints.max_retries or 3,
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

            # Execute use case
            result = await self._execute_deliberation.execute(deliberation_request)

            # Convert domain entity to protobuf
            return ray_executor_pb2.ExecuteDeliberationResponse(
                deliberation_id=result.deliberation_id,
                status=result.status,
                message=result.message,
            )

        except ValueError as e:
            # Domain validation errors
            logger.error(f"Validation error: {e}")
            context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
            context.set_details(str(e))
            return ray_executor_pb2.ExecuteDeliberationResponse()

        except Exception as e:
            # Unexpected errors
            logger.error(f"Unexpected error: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(f"Internal error: {str(e)}")
            return ray_executor_pb2.ExecuteDeliberationResponse()

    async def GetDeliberationStatus(self, request, context):
        """Get status of a running deliberation.

        Translates gRPC request → use case → gRPC response
        """
        try:
            # Execute use case
            response = await self._get_deliberation_status.execute(request.deliberation_id)

            # Convert domain entity to protobuf
            proto_response = ray_executor_pb2.GetDeliberationStatusResponse(
                status=response.status,
            )

            if response.result:
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

        except Exception as e:
            logger.error(f"Error in GetDeliberationStatus: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ray_executor_pb2.GetDeliberationStatusResponse()

    async def GetStatus(self, request, context):
        """Get service health and statistics.

        Translates gRPC request → use case → gRPC response
        """
        try:
            # Execute use case
            stats, uptime_seconds = await self._get_stats.execute()

            # Convert domain entity to protobuf
            return ray_executor_pb2.GetStatusResponse(
                status="healthy",
                uptime_seconds=uptime_seconds,
                stats=ray_executor_pb2.RayExecutorStats(
                    total_deliberations=stats.total_deliberations,
                    active_deliberations=stats.active_deliberations,
                    completed_deliberations=stats.completed_deliberations,
                    failed_deliberations=stats.failed_deliberations,
                    average_execution_time_ms=stats.average_execution_time_ms,
                ),
            )

        except Exception as e:
            logger.error(f"Error in GetStatus: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ray_executor_pb2.GetStatusResponse(status="unhealthy")

    async def GetActiveJobs(self, request, context):
        """Get list of active Ray jobs.

        Translates gRPC request → use case → gRPC response
        """
        try:
            # Execute use case
            jobs = await self._get_active_jobs.execute()

            # Convert domain entities to protobuf
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

            logger.info(f"📊 Returning {len(proto_jobs)} active jobs")
            return ray_executor_pb2.GetActiveJobsResponse(jobs=proto_jobs)

        except Exception as e:
            logger.error(f"Error in GetActiveJobs: {e}", exc_info=True)
            context.set_code(grpc.StatusCode.INTERNAL)
            context.set_details(str(e))
            return ray_executor_pb2.GetActiveJobsResponse()


async def serve():
    """Start the gRPC server with dependency injection."""
    port = int(os.getenv('GRPC_PORT', '50056'))
    ray_address = os.getenv('RAY_ADDRESS', 'ray://ray-gpu-head-svc.ray.svc.cluster.local:10001')
    nats_url = os.getenv('NATS_URL', 'nats://nats.swe-ai-fleet.svc.cluster.local:4222')
    enable_nats = os.getenv('ENABLE_NATS', 'true').lower() == 'true'

    logger.info(f"🚀 Starting Ray Executor Service on port {port}")

    # ============================================================
    # INFRASTRUCTURE INITIALIZATION
    # ============================================================

    # Initialize Ray connection
    logger.info(f"🔗 Connecting to Ray cluster at: {ray_address}")
    try:
        ray.init(address=ray_address, ignore_reinit_error=True)
        logger.info("✅ Ray connection established")
    except Exception as e:
        logger.error(f"❌ Failed to connect to Ray: {e}")
        raise

    # Initialize NATS connection (optional)
    nats_client = None
    jetstream = None
    if enable_nats:
        try:
            logger.info(f"🔗 Connecting to NATS at: {nats_url}")
            nats_client = await nats.connect(nats_url)
            jetstream = nats_client.jetstream()
            logger.info("✅ NATS connection established for streaming")
        except Exception as e:
            logger.error(f"❌ Failed to connect to NATS: {e}")
            # Don't raise - NATS is optional

    # ============================================================
    # SHARED STATE (IN-MEMORY)
    # ============================================================

    start_time = time.time()

    # Statistics tracking
    stats_tracker = {
        'total_deliberations': 0,
        'active_deliberations': 0,
        'completed_deliberations': 0,
        'failed_deliberations': 0,
        'execution_times': []
    }

    # Deliberations registry
    deliberations_registry: dict = {}

    # ============================================================
    # DEPENDENCY INJECTION (HEXAGONAL ARCHITECTURE)
    # ============================================================

    # Create infrastructure adapters (implement ports)
    ray_cluster_adapter = RayClusterAdapter(
        deliberations_registry=deliberations_registry,
    )

    nats_publisher_adapter = NATSPublisherAdapter(
        jetstream=jetstream,
    )

    # Create use cases (inject ports)
    execute_deliberation_usecase = ExecuteDeliberationUseCase(
        ray_cluster=ray_cluster_adapter,
        nats_publisher=nats_publisher_adapter,
        stats_tracker=stats_tracker,
    )

    get_deliberation_status_usecase = GetDeliberationStatusUseCase(
        ray_cluster=ray_cluster_adapter,
        stats_tracker=stats_tracker,
        deliberations_registry=deliberations_registry,
    )

    get_stats_usecase = GetStatsUseCase(
        stats_tracker=stats_tracker,
        start_time=start_time,
    )

    get_active_jobs_usecase = GetActiveJobsUseCase(
        deliberations_registry=deliberations_registry,
    )

    # Create gRPC servicer (inject use cases)
    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=execute_deliberation_usecase,
        get_deliberation_status_usecase=get_deliberation_status_usecase,
        get_stats_usecase=get_stats_usecase,
        get_active_jobs_usecase=get_active_jobs_usecase,
    )

    # ============================================================
    # START gRPC SERVER
    # ============================================================

    server = grpc_aio.server()
    ray_executor_pb2_grpc.add_RayExecutorServiceServicer_to_server(servicer, server)

    listen_addr = f'[::]:{port}'
    server.add_insecure_port(listen_addr)

    logger.info(f"✅ Ray Executor Service listening on {listen_addr}")
    logger.info(f"   Ray cluster: {ray_address}")
    if nats_client:
        logger.info(f"   NATS: {nats_url} ✓")
    else:
        logger.info("   NATS: disabled")

    await server.start()

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Ray Executor Service...")
        await server.stop(grace=5.0)

        # Close NATS connection
        if nats_client:
            await nats_client.close()

        # Shutdown Ray
        ray.shutdown()


if __name__ == '__main__':
    asyncio.run(serve())
