"""Get active jobs use case."""

import logging
import time

from services.ray_executor.domain.entities import JobInfo

logger = logging.getLogger(__name__)


class GetActiveJobsUseCase:
    """Use case for retrieving active Ray jobs.

    This use case queries the deliberations registry and constructs
    JobInfo entities for currently running deliberations.

    Responsibilities:
    - Filter for running deliberations only
    - Calculate runtime
    - Build JobInfo entities

    Following Hexagonal Architecture:
    - Pure business logic, no infrastructure dependencies
    - Returns domain entities (JobInfo)
    """

    def __init__(
        self,
        deliberations_registry: dict,
    ):
        """Initialize use case with dependencies.

        Args:
            deliberations_registry: Registry of active deliberations
        """
        self._deliberations = deliberations_registry

    async def execute(self) -> list[JobInfo]:
        """Execute the active jobs retrieval use case.

        Returns:
            List of JobInfo entities for running deliberations
        """
        jobs = []
        current_time = time.time()

        for deliberation_id, delib_info in self._deliberations.items():
            # Only include running jobs
            if delib_info.get('status') != 'running':
                continue

            # Calculate runtime
            start_time = delib_info.get('start_time', current_time)
            runtime_seconds = int(current_time - start_time)
            minutes = runtime_seconds // 60
            seconds = runtime_seconds % 60
            runtime_str = f"{minutes}m {seconds}s"

            # Create JobInfo entity
            job_info = JobInfo(
                job_id=deliberation_id,
                name=f"vllm-agent-job-{deliberation_id}",
                status="RUNNING",
                submission_id=deliberation_id,
                role=delib_info.get('role', 'UNKNOWN'),
                task_id=delib_info.get('task_id', 'unknown'),
                start_time_seconds=int(start_time),
                runtime=runtime_str,
            )

            jobs.append(job_info)

        logger.info(f"📊 Returning {len(jobs)} active jobs")
        return jobs

