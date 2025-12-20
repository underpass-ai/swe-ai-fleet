"""
Backlog Review Processor Service - Converts backlog review deliberations into tasks.

Event-Driven Service:
- Listens to planning.backlog_review.deliberations.complete events
- Submits task extraction jobs to Ray Executor
- Processes task extraction results and creates tasks in Planning Service
"""

import asyncio
import logging
import os
import signal

from nats.aio.client import Client as NATS
from backlog_review_processor.application.usecases.accumulate_deliberations_usecase import (
    AccumulateDeliberationsUseCase,
)
from backlog_review_processor.application.usecases.extract_tasks_from_deliberations_usecase import (
    ExtractTasksFromDeliberationsUseCase,
)
from backlog_review_processor.infrastructure.adapters.environment_config_adapter import (
    EnvironmentConfig,
)
from backlog_review_processor.infrastructure.adapters.neo4j_adapter import (
    Neo4jStorageAdapter,
)
from backlog_review_processor.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)
from backlog_review_processor.infrastructure.adapters.planning_service_adapter import (
    PlanningServiceAdapter,
)
from backlog_review_processor.infrastructure.adapters.ray_executor_adapter import (
    RayExecutorAdapter,
)
from backlog_review_processor.infrastructure.consumers.backlog_review_result_consumer import (
    BacklogReviewResultConsumer,
)
from backlog_review_processor.infrastructure.consumers.deliberations_complete_consumer import (
    DeliberationsCompleteConsumer,
)
from backlog_review_processor.infrastructure.consumers.task_extraction_result_consumer import (
    TaskExtractionResultConsumer,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


async def main():
    """Main entry point for Backlog Review Processor Service."""
    logger.info("🚀 Starting Backlog Review Processor Service...")

    # Load configuration from environment
    config = EnvironmentConfig.from_env()
    nats_url = config.nats_url
    planning_service_url = config.planning_service_url
    ray_executor_url = config.ray_executor_url
    vllm_url = config.vllm_url
    vllm_model = config.vllm_model

    logger.info("Configuration:")
    logger.info(f"  NATS URL: {nats_url}")
    logger.info(f"  Planning Service: {planning_service_url}")
    logger.info(f"  Ray Executor: {ray_executor_url}")
    logger.info(f"  vLLM URL: {vllm_url}")
    logger.info(f"  vLLM Model: {vllm_model}")
    logger.info(f"  Neo4j URI: {config.neo4j_uri}")

    # Initialize NATS client
    nc = NATS()
    try:
        await nc.connect(nats_url)
        logger.info("✓ Connected to NATS")
    except Exception as e:
        logger.error(f"Failed to connect to NATS: {e}", exc_info=True)
        raise

    js = nc.jetstream()

    # Initialize adapters
    messaging_adapter = NATSMessagingAdapter(nats_client=nc, jetstream=js)
    logger.info("✓ NATSMessagingAdapter initialized")

    storage_adapter = Neo4jStorageAdapter(config=config.get_neo4j_config())
    logger.info("✓ Neo4jStorageAdapter initialized")

    planning_adapter = PlanningServiceAdapter(
        grpc_address=planning_service_url,
        timeout_seconds=30.0,
    )
    logger.info(f"✓ PlanningServiceAdapter initialized: {planning_service_url}")

    ray_executor_adapter = RayExecutorAdapter(
        grpc_address=ray_executor_url,
        vllm_url=vllm_url,
        vllm_model=vllm_model,
    )
    logger.info(f"✓ RayExecutorAdapter initialized: {ray_executor_url}")

    logger.info("✓ Adapters initialized")

    # Initialize use cases
    accumulate_deliberations_uc = AccumulateDeliberationsUseCase(
        messaging=messaging_adapter,
        storage=storage_adapter,
        planning=planning_adapter,
    )

    extract_tasks_uc = ExtractTasksFromDeliberationsUseCase(
        ray_executor=ray_executor_adapter,
    )

    logger.info("✓ Use cases initialized")

    # Initialize consumers
    backlog_review_result_consumer = BacklogReviewResultConsumer(
        nats_client=nc,
        jetstream=js,
        accumulate_deliberations=accumulate_deliberations_uc,
    )

    deliberations_complete_consumer = DeliberationsCompleteConsumer(
        nats_client=nc,
        jetstream=js,
        extract_tasks_usecase=extract_tasks_uc,
    )

    task_extraction_result_consumer = TaskExtractionResultConsumer(
        nats_client=nc,
        jetstream=js,
        planning=planning_adapter,
        messaging=messaging_adapter,
        max_deliveries=3,  # Max delivery attempts before DLQ
    )

    logger.info("✓ Consumers initialized")

    # Start consumers
    try:
        await backlog_review_result_consumer.start()
        logger.info(
            "✓ BacklogReviewResultConsumer started "
            "(listening to agent.response.completed for backlog review)"
        )

        await deliberations_complete_consumer.start()
        logger.info(
            "✓ DeliberationsCompleteConsumer started "
            "(listening to planning.backlog_review.deliberations.complete)"
        )

        await task_extraction_result_consumer.start()
        logger.info(
            "✓ TaskExtractionResultConsumer started "
            "(listening to agent.response.completed for task extraction)"
        )

        logger.info("✅ Task Extraction Service is running")

        # Wait for shutdown signal
        shutdown_event = asyncio.Event()

        def signal_handler():
            logger.info("Received shutdown signal")
            shutdown_event.set()

        signal.signal(signal.SIGINT, lambda s, f: signal_handler())
        signal.signal(signal.SIGTERM, lambda s, f: signal_handler())

        await shutdown_event.wait()

    except Exception as e:
        logger.error(f"Error in service: {e}", exc_info=True)
        raise
    finally:
        # Cleanup
        logger.info("Shutting down Backlog Review Processor Service...")

        await backlog_review_result_consumer.stop()
        logger.info("✓ BacklogReviewResultConsumer stopped")

        await deliberations_complete_consumer.stop()
        logger.info("✓ DeliberationsCompleteConsumer stopped")

        await task_extraction_result_consumer.stop()
        logger.info("✓ TaskExtractionResultConsumer stopped")

        await planning_adapter.close()
        await ray_executor_adapter.close()

        storage_adapter.close()
        logger.info("✓ Neo4j connection closed")

        await nc.close()
        logger.info("✓ NATS connection closed")

        logger.info("✅ Backlog Review Processor Service stopped")


if __name__ == "__main__":
    asyncio.run(main())

