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
from typing import Any

import nats
import ray
from grpc import aio as grpc_aio

from services.ray_executor.application.usecases import (
    ExecuteDeliberationUseCase,
    GetActiveJobsUseCase,
    GetDeliberationStatusUseCase,
    GetStatsUseCase,
)
from services.ray_executor.config import load_ray_executor_config
from services.ray_executor.gen import ray_executor_pb2_grpc
from services.ray_executor.grpc_servicer import RayExecutorServiceServicer
from services.ray_executor.infrastructure.adapters import (
    NATSPublisherAdapter,
    RayClusterAdapter,
)
from services.ray_executor.infrastructure.deliberation_registry_entry import (
    RayDeliberationRegistryEntry,
)
from services.ray_executor.infrastructure.adapters.in_memory_stats_tracker import (
    InMemoryStatsTrackerAdapter,
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger(__name__)


def _load_pip_packages(requirements_path: str) -> list[str]:
    """Load pip packages from requirements file (synchronous helper).

    This helper is intentionally synchronous and called from async context to keep
    startup logic simple while avoiding direct file I/O inside async functions
    for static analyzers.
    """
    pip_packages: list[str] = []
    if not os.path.exists(requirements_path):
        return pip_packages

    try:
        with open(requirements_path) as f:
            pip_packages = [
                line.strip()
                for line in f
                if line.strip() and not line.startswith("#")
            ]
        logger.info("📦 Found %d packages in requirements.txt", len(pip_packages))
        if pip_packages:
            logger.debug("   Packages: %s...", ", ".join(pip_packages[:5]))
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.warning("⚠️ Could not read requirements.txt: %s", exc)

    return pip_packages


def _init_ray_connection(ray_address: str) -> None:
    """Initialize Ray connection with runtime_env for workers."""
    logger.info("🔗 Connecting to Ray cluster at: %s", ray_address)
    try:
        requirements_path = "/app/requirements.txt"
        pip_packages = _load_pip_packages(requirements_path)

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
                },
            },
        )
        logger.info(
            "✅ Ray connection established with runtime_env configured (working_dir=/app)",
        )
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("❌ Failed to connect to Ray: %s", exc)
        raise


async def _init_nats_connection(
    nats_url: str,
    enable_nats: bool,
) -> tuple[Any | None, Any | None]:
    """Initialize optional NATS connection and JetStream context."""
    if not enable_nats:
        return None, None

    nats_client = None
    jetstream = None
    try:
        logger.info("🔗 Connecting to NATS at: %s", nats_url)
        nats_client = await nats.connect(nats_url)
        jetstream = nats_client.jetstream()
        logger.info("✅ NATS connection established for streaming")
    except Exception as exc:  # pragma: no cover - defensive logging
        logger.error("❌ Failed to connect to NATS: %s", exc)
        # NATS is optional; do not raise

    return nats_client, jetstream


def _create_shared_state() -> tuple[float, dict[str, Any], dict[str, RayDeliberationRegistryEntry]]:
    """Create in-memory shared state for stats and deliberations."""
    start_time = time.time()
    stats_tracker: dict[str, Any] = {
        "total_deliberations": 0,
        "active_deliberations": 0,
        "completed_deliberations": 0,
        "failed_deliberations": 0,
        "execution_times": [],
    }
    deliberations_registry: dict[str, RayDeliberationRegistryEntry] = {}
    return start_time, stats_tracker, deliberations_registry


def _build_use_cases_and_servicer(
    stats_tracker: dict[str, Any],
    deliberations_registry: dict[str, Any],
    jetstream: Any | None,
) -> tuple[RayExecutorServiceServicer, GetDeliberationStatusUseCase]:
    """Wire adapters, use cases, and gRPC servicer."""
    ray_cluster_adapter = RayClusterAdapter(
        deliberations_registry=deliberations_registry,
    )

    nats_publisher_adapter = NATSPublisherAdapter(
        jetstream=jetstream,
    )

    stats_tracker_adapter = InMemoryStatsTrackerAdapter(stats=stats_tracker)

    execute_deliberation_usecase = ExecuteDeliberationUseCase(
        ray_cluster=ray_cluster_adapter,
        nats_publisher=nats_publisher_adapter,
        stats_tracker=stats_tracker,
    )

    get_deliberation_status_usecase = GetDeliberationStatusUseCase(
        ray_cluster=ray_cluster_adapter,
        stats_tracker=stats_tracker_adapter,
        deliberations_registry=deliberations_registry,
    )

    get_stats_usecase = GetStatsUseCase(
        stats_tracker=stats_tracker,
        start_time=stats_tracker.get("start_time", 0.0),
    )

    get_active_jobs_usecase = GetActiveJobsUseCase(
        deliberations_registry=deliberations_registry,
    )

    servicer = RayExecutorServiceServicer(
        execute_deliberation_usecase=execute_deliberation_usecase,
        get_deliberation_status_usecase=get_deliberation_status_usecase,
        get_stats_usecase=get_stats_usecase,
        get_active_jobs_usecase=get_active_jobs_usecase,
    )

    return servicer, get_deliberation_status_usecase


async def _poll_deliberations(
    deliberations_registry: dict[str, Any],
    get_deliberation_status_usecase: GetDeliberationStatusUseCase,
    poll_interval: float = 2.0,
) -> None:
    """Background task to poll deliberation status and log LLM responses."""
    logger.info("🔄 Starting deliberation polling (interval: %ss)", poll_interval)

    while True:
        try:
            await asyncio.sleep(poll_interval)

            active_deliberations = [
                (delib_id, delib_data)
                for delib_id, delib_data in deliberations_registry.items()
                if delib_data.get("status") == "running"
            ]

            if not active_deliberations:
                continue

            await _process_active_deliberations(
                active_deliberations=active_deliberations,
                get_deliberation_status_usecase=get_deliberation_status_usecase,
            )

        except asyncio.CancelledError:
            logger.info("🛑 Polling task cancelled")
            raise
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.error("Error in polling task: %s", exc, exc_info=True)
            await asyncio.sleep(poll_interval)


async def _process_active_deliberations(
    active_deliberations: list[tuple[str, dict[str, Any]]],
    get_deliberation_status_usecase: GetDeliberationStatusUseCase,
) -> None:
    """Process each active deliberation and log its status."""
    for deliberation_id, _ in active_deliberations:
        try:
            status_response = await get_deliberation_status_usecase.execute(
                deliberation_id,
            )
            if status_response.status == "completed":
                logger.debug("✅ Polling detected completion: %s", deliberation_id)
            elif status_response.status == "failed":
                logger.warning(
                    "⚠️ Polling detected failure: %s: %s",
                    deliberation_id,
                    status_response.error_message,
                )
        except Exception as exc:  # pragma: no cover - defensive logging
            logger.debug(
                "Error polling deliberation %s: %s",
                deliberation_id,
                exc,
            )
            continue


async def serve():
    """Start the gRPC server with dependency injection."""
    config = load_ray_executor_config()
    port = config.port
    ray_address = config.ray_address
    nats_url = config.nats_url
    enable_nats = config.enable_nats

    logger.info("🚀 Starting Ray Executor Service on port %s", port)

    # Initialize infrastructure
    _init_ray_connection(ray_address)
    nats_client, jetstream = await _init_nats_connection(nats_url, enable_nats)

    # Shared state
    start_time, stats_tracker, deliberations_registry = _create_shared_state()
    stats_tracker["start_time"] = start_time

    # Dependency injection: use cases and servicer
    servicer, get_deliberation_status_usecase = _build_use_cases_and_servicer(
        stats_tracker=stats_tracker,
        deliberations_registry=deliberations_registry,
        jetstream=jetstream,
    )

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

    # Start polling task
    polling_task = asyncio.create_task(
        _poll_deliberations(
            deliberations_registry=deliberations_registry,
            get_deliberation_status_usecase=get_deliberation_status_usecase,
        ),
    )
    logger.info("✅ Deliberation polling started")

    try:
        await server.wait_for_termination()
    except KeyboardInterrupt:
        logger.info("🛑 Shutting down Ray Executor Service...")

        # Cancel polling task and wait for it without propagating CancelledError
        polling_task.cancel()
        await asyncio.gather(polling_task, return_exceptions=True)

        await server.stop(grace=5.0)

        # Close NATS connection
        if nats_client:
            await nats_client.close()

        # Shutdown Ray
        ray.shutdown()


if __name__ == '__main__':
    asyncio.run(serve())
