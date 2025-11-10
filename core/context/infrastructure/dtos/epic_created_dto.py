"""DTO for planning.epic.created event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class EpicCreatedDTO:
    """DTO representing planning.epic.created event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).
    """

    epic_id: str
    project_id: str
    title: str
    description: str
    status: str
    created_at_ms: int

