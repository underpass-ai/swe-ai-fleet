"""Job information entity."""

from dataclasses import dataclass


@dataclass(frozen=True)
class JobInfo:
    """Information about an active Ray job.

    Represents a currently running deliberation job on the Ray cluster.

    Attributes:
        job_id: Unique Ray job identifier
        name: Human-readable job name
        status: Current job status (RUNNING, PENDING, etc.)
        submission_id: Submission ID (deliberation_id)
        role: Role of the agent executing the job
        task_id: Task identifier being executed
        start_time_seconds: Unix timestamp when job started
        runtime: Human-readable runtime string (e.g. "5m 23s")
    """

    job_id: str
    name: str
    status: str
    submission_id: str
    role: str
    task_id: str
    start_time_seconds: int
    runtime: str

    def __post_init__(self) -> None:
        """Validate job info invariants."""
        if not self.job_id:
            raise ValueError("job_id cannot be empty")

        if not self.submission_id:
            raise ValueError("submission_id cannot be empty")

        if self.start_time_seconds < 0:
            raise ValueError("start_time_seconds cannot be negative")

