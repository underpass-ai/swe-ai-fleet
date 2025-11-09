"""DTO for planning.project.created event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class ProjectCreatedDTO:
    """DTO representing planning.project.created event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).

    NO business validation here. Just data structure.
    Validation happens when mapping to domain entities.
    """

    project_id: str
    name: str
    description: str
    status: str
    owner: str
    created_at_ms: int

