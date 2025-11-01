"""Get deliberation status use case."""

import logging
import time
from dataclasses import dataclass

from services.ray_executor.domain.entities import DeliberationResult
from services.ray_executor.domain.ports import RayClusterPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeliberationStatusResponse:
    """Response with deliberation status.

    Attributes:
        status: Current status ("running", "completed", "failed", "not_found")
        result: Deliberation result if completed, None otherwise
        error_message: Error message if failed, None otherwise
    """

    status: str
    result: DeliberationResult | None = None
    error_message: str | None = None


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
        stats_tracker: dict,
        deliberations_registry: dict,
    ):
        """Initialize use case with dependencies.

        Args:
            ray_cluster: Port for Ray cluster interaction
            stats_tracker: Shared statistics dictionary
            deliberations_registry: Registry of active deliberations
        """
        self._ray_cluster = ray_cluster
        self._stats = stats_tracker
        self._deliberations = deliberations_registry

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
                status="not_found",
                error_message=f"Deliberation {deliberation_id} not found",
            )

        deliberation = self._deliberations[deliberation_id]

        try:
            # Query Ray cluster for status
            status, result, error_message = await self._ray_cluster.check_deliberation_status(
                deliberation_id
            )

            # Update deliberation registry
            if status == "completed":
                deliberation['status'] = 'completed'
                deliberation['result'] = result
                deliberation['end_time'] = time.time()

                # Update statistics
                execution_time = deliberation['end_time'] - deliberation['start_time']
                self._stats['execution_times'].append(execution_time)
                self._stats['active_deliberations'] -= 1
                self._stats['completed_deliberations'] += 1

                logger.info(
                    f"✅ Deliberation completed: {deliberation_id} "
                    f"(took {execution_time:.2f}s)"
                )

                return DeliberationStatusResponse(
                    status="completed",
                    result=result,
                )

            elif status == "failed":
                deliberation['status'] = 'failed'
                deliberation['error'] = error_message
                self._stats['active_deliberations'] -= 1
                self._stats['failed_deliberations'] += 1

                return DeliberationStatusResponse(
                    status="failed",
                    error_message=error_message,
                )

            else:
                # Still running
                return DeliberationStatusResponse(
                    status="running",
                )

        except Exception as e:
            logger.error(f"❌ Error checking deliberation status: {e}")
            deliberation['status'] = 'failed'
            deliberation['error'] = str(e)
            self._stats['active_deliberations'] -= 1
            self._stats['failed_deliberations'] += 1

            return DeliberationStatusResponse(
                status="failed",
                error_message=str(e),
            )

