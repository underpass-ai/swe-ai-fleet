"""Get deliberation status use case."""

import logging
import time

from services.ray_executor.application.usecases.deliberation_registry_entry import (
    DeliberationRegistryEntry,
)
from services.ray_executor.application.usecases.deliberation_status_response import (
    DeliberationStatusResponse,
)
from services.ray_executor.domain.entities.deliberation_status import (
    DeliberationStatus,
)
from services.ray_executor.domain.ports import RayClusterPort, StatsTrackerPort

logger = logging.getLogger(__name__)


class GetDeliberationStatusUseCase:
    """Use case for getting the status of a running deliberation.

    This use case checks the status of a deliberation on the Ray cluster
    and updates statistics when deliberations complete.

    Responsibilities:
    - Query Ray cluster for deliberation status
    - Track completion metrics
    - Return status and result

    Following Hexagonal Architecture:
    - Depends only on ports (interfaces)
    - All dependencies injected via constructor
    """

    def __init__(
        self,
        ray_cluster: RayClusterPort,
        stats_tracker: StatsTrackerPort,
        deliberations_registry: dict[str, DeliberationRegistryEntry],
    ) -> None:
        """Initialize use case with dependencies.

        Args:
            ray_cluster: Port for Ray cluster interaction
            stats_tracker: Shared statistics dictionary
            deliberations_registry: Registry of active deliberations
        """
        self._ray_cluster = ray_cluster
        self._stats = stats_tracker
        self._deliberations: dict[str, DeliberationRegistryEntry] = (
            deliberations_registry
        )

    async def execute(
        self,
        deliberation_id: str,
    ) -> DeliberationStatusResponse:
        """Execute the status check use case.

        Args:
            deliberation_id: Unique deliberation identifier

        Returns:
            DeliberationStatusResponse with current status
        """
        # Check if deliberation exists in registry
        if deliberation_id not in self._deliberations:
            return DeliberationStatusResponse(
                status=DeliberationStatus.NOT_FOUND.value,
                error_message=f"Deliberation {deliberation_id} not found",
            )

        deliberation: DeliberationRegistryEntry = self._deliberations[deliberation_id]

        try:
            # Query Ray cluster for status
            status, result, error_message = await self._ray_cluster.check_deliberation_status(
                deliberation_id
            )

            normalized_status = DeliberationStatus(status)

            # Update deliberation registry
            if normalized_status is DeliberationStatus.COMPLETED:
                deliberation["status"] = DeliberationStatus.COMPLETED.value
                deliberation["result"] = result
                deliberation["end_time"] = time.time()

                # Update statistics
                execution_time = deliberation["end_time"] - deliberation["start_time"]
                self._stats.decrement_active()
                self._stats.record_completed(execution_time)

                logger.info(
                    f"✅ Deliberation completed: {deliberation_id} "
                    f"(took {execution_time:.2f}s)"
                )

                return DeliberationStatusResponse(
                    status=DeliberationStatus.COMPLETED.value,
                    result=result,
                )

            if normalized_status is DeliberationStatus.FAILED:
                deliberation["status"] = DeliberationStatus.FAILED.value
                deliberation["error"] = error_message
                self._stats.decrement_active()
                self._stats.record_failed()

                return DeliberationStatusResponse(
                    status=DeliberationStatus.FAILED.value,
                    error_message=error_message,
                )

            # Still running or submitted
            return DeliberationStatusResponse(
                status=normalized_status.value,
            )

        except Exception as e:
            logger.error(f"❌ Error checking deliberation status: {e}")
            deliberation["status"] = DeliberationStatus.FAILED.value
            deliberation["error"] = str(e)
            self._stats.decrement_active()
            self._stats.record_failed()

            return DeliberationStatusResponse(
                status=DeliberationStatus.FAILED.value,
                error_message=str(e),
            )

