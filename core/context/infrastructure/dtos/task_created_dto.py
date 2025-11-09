"""DTO for planning.task.created event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskCreatedDTO:
    """DTO representing planning.task.created event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).
    """

    task_id: str
    plan_id: str
    title: str
    type: str
    status: str

