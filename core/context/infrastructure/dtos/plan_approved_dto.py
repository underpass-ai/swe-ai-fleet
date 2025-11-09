"""DTO for planning.plan.approved event (external contract)."""

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanApprovedDTO:
    """DTO representing planning.plan.approved event from Planning Service.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS event from another bounded context).
    """

    story_id: str
    plan_id: str
    approved_by: str
    timestamp: str

