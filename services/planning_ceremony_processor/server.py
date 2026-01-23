"""Planning Ceremony Processor Service (gRPC server)."""

import asyncio
import logging
import os
import signal
import sys

import grpc
from nats.aio.client import Client as NATS

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../.."))

from core.ceremony_engine.application.use_cases.submit_deliberation_usecase import (
    SubmitDeliberationUseCase,
)
from core.ceremony_engine.application.use_cases.submit_task_extraction_usecase import (
    SubmitTaskExtractionUseCase,
)
from core.ceremony_engine.infrastructure.adapters.dual_persistence_adapter import (
    DualPersistenceAdapter,
)
from core.ceremony_engine.infrastructure.adapters.nats_messaging_adapter import (
    NATSMessagingAdapter,
)
from core.ceremony_engine.infrastructure.adapters.step_handlers.step_handler_registry import (
    StepHandlerRegistry,
)
from core.shared.idempotency.infrastructure.valkey_idempotency_adapter import (
    ValkeyIdempotencyAdapter,
)
from services.planning_ceremony_processor.application.usecases.start_planning_ceremony_usecase import (
    StartPlanningCeremonyUseCase,
)
from services.planning_ceremony_processor.infrastructure.adapters import (
    CeremonyDefinitionAdapter,
    EnvironmentConfig,
    RayExecutorAdapter,
)
from services.planning_ceremony_processor.infrastructure.grpc.planning_ceremony_servicer import (
    PlanningCeremonyProcessorServicer,
)

try:
    from services.planning_ceremony_processor.gen import planning_ceremony_pb2_grpc
except ImportError:
    planning_ceremony_pb2_grpc = None

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def _serve() -> None:
    if planning_ceremony_pb2_grpc is None:
        raise RuntimeError(
            "Planning ceremony protobuf stubs not available. "
            "Generate protobuf stubs before starting server."
        )

    config = EnvironmentConfig.from_env()
    grpc_address = os.getenv("PLANNING_CEREMONY_GRPC_ADDR", "0.0.0.0:50057")

    # NATS
    nc = NATS()
    await nc.connect(config.nats_url)
    js = nc.jetstream()
    messaging_adapter = NATSMessagingAdapter(nats_client=nc, jetstream=js)

    # Adapters
    definition_adapter = CeremonyDefinitionAdapter(config.ceremonies_dir)
    ray_executor_adapter = RayExecutorAdapter(
        grpc_address=config.ray_executor_url,
        vllm_url=config.vllm_url,
        vllm_model=config.vllm_model,
    )
    persistence_adapter = DualPersistenceAdapter(ceremonies_dir=config.ceremonies_dir)
    idempotency_adapter = ValkeyIdempotencyAdapter(
        host=config.valkey_host,
        port=config.valkey_port,
        db=config.valkey_db,
    )

    # Use cases and registry
    step_handler_registry = StepHandlerRegistry(
        SubmitDeliberationUseCase(ray_executor_adapter),
        SubmitTaskExtractionUseCase(ray_executor_adapter),
        messaging_adapter,
        idempotency_adapter,
    )
    start_use_case = StartPlanningCeremonyUseCase(
        definition_port=definition_adapter,
        step_handler_port=step_handler_registry,
        persistence_port=persistence_adapter,
        messaging_port=messaging_adapter,
    )

    server = grpc.aio.server()
    planning_ceremony_pb2_grpc.add_PlanningCeremonyProcessorServicer_to_server(
        PlanningCeremonyProcessorServicer(start_use_case),
        server,
    )
    server.add_insecure_port(grpc_address)

    await server.start()
    logger.info(f"Planning Ceremony Processor gRPC server started on {grpc_address}")

    stop_event = asyncio.Event()

    def _stop_signal(*_args) -> None:
        logger.info("Shutdown signal received")
        stop_event.set()

    signal.signal(signal.SIGINT, _stop_signal)
    signal.signal(signal.SIGTERM, _stop_signal)

    await stop_event.wait()
    await server.stop(grace=5)
    await ray_executor_adapter.close()
    idempotency_adapter.close()
    persistence_adapter.close()
    await nc.close()


def main() -> None:
    asyncio.run(_serve())


if __name__ == "__main__":
    main()
