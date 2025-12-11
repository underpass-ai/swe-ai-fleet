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
import time

import grpc
import nats
import ray
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
from services.ray_executor.gen import ray_executor_pb2, ray_executor_pb2_grpc
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
        """Execute deliberation on Ray cluster (for task derivation - requires plan_id).

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

            # Extract metadata from proto (contains original task_id from planning)
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

            # Validate task_id is present (REQUIRED for backlog review ceremonies)
            if not request.task_id or not request.task_id.strip():
                error_msg = (
                    "❌ CRITICAL ERROR: task_id is MISSING in ExecuteDeliberation request! "
                    "Backlog review ceremonies REQUIRE task_id in format 'ceremony-{id}:story-{id}:role-{role}'. "
                    f"Request: task_description='{request.task_description[:100] if request.task_description else 'N/A'}...', "
                    f"role={request.role}"
                )
                logger.error(error_msg)
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(error_msg)
                return ray_executor_pb2.ExecuteDeliberationResponse()

            # Execute use case
            result = await self._execute_deliberation.execute(deliberation_request)

            # Convert domain entity to protobuf
            # Include task_id in response root (REQUIRED for backlog review ceremonies)
            return ray_executor_pb2.ExecuteDeliberationResponse(
                task_id=request.task_id,  # Original task_id from request
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

    async def ExecuteBacklogReviewDeliberation(self, request, context):
        """Execute deliberation for backlog review (no plan_id required, only story_id).

        This method is specifically for backlog review ceremonies where we only have
        story_id and don't have a plan_id (unlike task derivation ceremonies).

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

            # Extract metadata from proto (contains original task_id from planning)
            metadata = None
            if request.constraints.metadata:
                metadata = dict(request.constraints.metadata)
            
            # Ensure story_id is in metadata (required for TaskExtractionResultConsumer)
            if metadata is None:
                metadata = {}
            if "story_id" not in metadata and request.constraints.story_id:
                metadata["story_id"] = request.constraints.story_id

            # For backlog review, plan_id is empty (not required)
            constraints = TaskConstraints(
                story_id=request.constraints.story_id,
                plan_id="",  # Empty for backlog review (not required)
                timeout_seconds=request.constraints.timeout_seconds or 300,
                max_retries=request.constraints.max_retries or 3,
                metadata=metadata,
            )

            # Validate task_id is present (REQUIRED for backlog review ceremonies)
            if not request.task_id or not request.task_id.strip():
                error_msg = (
                    "❌ CRITICAL ERROR: task_id is MISSING in ExecuteBacklogReviewDeliberation request! "
                    "Backlog review ceremonies REQUIRE task_id in format 'ceremony-{id}:story-{id}:role-{role}'. "
                    f"Request: task_description='{request.task_description[:100] if request.task_description else 'N/A'}...', "
                    f"role={request.role}, story_id={request.constraints.story_id if request.constraints else 'N/A'}"
                )
                logger.error(error_msg)
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(error_msg)
                return ray_executor_pb2.ExecuteDeliberationResponse()

            # Validate task_id format for backlog review
            if not (request.task_id.startswith("ceremony-") and ":story-" in request.task_id and ":role-" in request.task_id):
                error_msg = (
                    f"❌ CRITICAL ERROR: Invalid task_id format in ExecuteBacklogReviewDeliberation request! "
                    f"Expected format: 'ceremony-{{id}}:story-{{id}}:role-{{role}}', "
                    f"got: '{request.task_id}'. "
                    f"Request: task_description='{request.task_description[:100] if request.task_description else 'N/A'}...', "
                    f"role={request.role}"
                )
                logger.error(error_msg)
                context.set_code(grpc.StatusCode.INVALID_ARGUMENT)
                context.set_details(error_msg)
                return ray_executor_pb2.ExecuteDeliberationResponse()

            logger.info(f"✅ ExecuteBacklogReviewDeliberation: Valid task_id found: {request.task_id}")

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
            # Include task_id in response root (REQUIRED for backlog review ceremonies)
            return ray_executor_pb2.ExecuteDeliberationResponse(
                task_id=request.task_id,  # Original task_id from request
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
                # Handle both single-agent and multi-agent results
                from services.ray_executor.domain.entities import (
                    DeliberationResult,
                    MultiAgentDeliberationResult,
                )

                if isinstance(response.result, MultiAgentDeliberationResult):
                    # Multi-agent: return the best result for backward compatibility
                    # TODO: Add repeated DeliberationResult field to proto for all results
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
                                    # Add metadata about multi-agent deliberation
                                    "total_agents": str(response.result.total_agents),
                                    "completed_agents": str(response.result.completed_agents),
                                    "failed_agents": str(response.result.failed_agents),
                                    "average_score": str(response.result.average_score),
                                },
                            )
                        )
                        logger.info(
                            f"Multi-agent deliberation completed: "
                            f"{response.result.completed_agents}/{response.result.total_agents} agents, "
                            f"best score: {best_result.score:.2f}, "
                            f"average: {response.result.average_score:.2f}"
                        )
                elif isinstance(response.result, DeliberationResult):
                    # Single-agent: return as-is
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

    # Initialize Ray connection with runtime_env
    # This ensures that the 'core' module is available in Ray workers
    # Ray packages and distributes code to workers using working_dir
    # This packages /app (which contains both core/ and services/) and sends it to workers
    # The code is uploaded to Ray's GCS and then downloaded by workers when needed
    logger.info(f"🔗 Connecting to Ray cluster at: {ray_address}")
    try:
        # Read requirements to include in runtime_env
        # This ensures all dependencies (including nats-py) are available in Ray workers
        requirements_path = "/app/requirements.txt"
        pip_packages = []
        try:
            if os.path.exists(requirements_path):
                with open(requirements_path, 'r') as f:
                    pip_packages = [line.strip() for line in f if line.strip() and not line.startswith('#')]
                logger.info(f"📦 Found {len(pip_packages)} packages in requirements.txt")
                logger.debug(f"   Packages: {', '.join(pip_packages[:5])}...")
        except Exception as e:
            logger.warning(f"⚠️ Could not read requirements.txt: {e}")

        # Use working_dir to package /app and distribute to workers
        # Ray will upload /app to GCS and workers will download it to their working directory
        # When Ray downloads working_dir, it extracts it to a temp directory and sets it as CWD
        # IMPORTANT: Ray does NOT automatically add working_dir to PYTHONPATH in workers
        # We must explicitly set PYTHONPATH to include the working_dir (which contains core/)
        # The working_dir is extracted to a temp path, but Ray sets CWD to that path
        # So we use relative paths: . (current dir = working_dir) and ./core
        ray.init(
            address=ray_address,
            ignore_reinit_error=True,
            runtime_env={
                "working_dir": "/app",
                "pip": pip_packages if pip_packages else None,
                "env_vars": {
                    # Set PYTHONPATH to include working_dir (.) and core subdirectory
                    # Ray extracts working_dir to a temp path and sets CWD to it
                    # So relative paths work: . is the working_dir, ./core is the core module
                    "PYTHONPATH": ".:./core"
                }
            }
        )
        logger.info("✅ Ray connection established with runtime_env configured (working_dir=/app)")
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

    # ============================================================
    # BACKGROUND POLLING TASK
    # ============================================================

    async def poll_deliberations():
        """Background task to poll deliberation status and show LLM responses."""
        poll_interval = 2.0  # Poll every 2 seconds
        logger.info(f"🔄 Starting deliberation polling (interval: {poll_interval}s)")

        while True:
            try:
                await asyncio.sleep(poll_interval)

                # Get all active deliberations
                active_deliberations = [
                    (delib_id, delib_data)
                    for delib_id, delib_data in deliberations_registry.items()
                    if delib_data.get('status') == 'running'
                ]

                if not active_deliberations:
                    continue

                # Check status for each active deliberation
                for deliberation_id, deliberation_data in active_deliberations:
                    try:
                        status_response = await get_deliberation_status_usecase.execute(deliberation_id)

                        # Status check will trigger logging of LLM responses in ray_cluster_adapter
                        # via check_deliberation_status -> ray.get() -> logs
                        if status_response.status == "completed":
                            logger.debug(f"✅ Polling detected completion: {deliberation_id}")
                        elif status_response.status == "failed":
                            logger.warning(f"⚠️ Polling detected failure: {deliberation_id}: {status_response.error_message}")
                    except Exception as e:
                        logger.debug(f"Error polling deliberation {deliberation_id}: {e}")
                        continue

            except asyncio.CancelledError:
                logger.info("🛑 Polling task cancelled")
                break
            except Exception as e:
                logger.error(f"Error in polling task: {e}", exc_info=True)
                await asyncio.sleep(poll_interval)

    # Start polling task
    polling_task = asyncio.create_task(poll_deliberations())
    logger.info("✅ Deliberation polling started")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Ray Executor Service...")

        # Cancel polling task
        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            pass

        await server.stop(grace=5.0)

        # Close NATS connection
        if nats_client:
            await nats_client.close()

        # Shutdown Ray
        ray.shutdown()


if __name__ == '__main__':
    asyncio.run(serve())
