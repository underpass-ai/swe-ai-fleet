"""gRPC adapters for planning ceremony processor."""

from services.planning_ceremony_processor.infrastructure.grpc.planning_ceremony_servicer import (
    PlanningCeremonyProcessorServicer,
)

__all__ = ["PlanningCeremonyProcessorServicer"]
