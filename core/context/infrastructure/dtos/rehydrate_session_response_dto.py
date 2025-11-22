"""DTO for RehydrateSession response (NATS message contract)."""

from dataclasses import dataclass

from core.context.infrastructure.dtos.rehydration_stats_dto import (
    RehydrationStatsDTO,
)


@dataclass(frozen=True)
class RehydrateSessionResponseDTO:
    """DTO representing RehydrateSession response for NATS messaging.

    This DTO lives in INFRASTRUCTURE because it represents the external
    contract (NATS message to other services).

    NO business validation here. Just data structure.
    """

    case_id: str
    status: str
    generated_at_ms: int
    packs_count: int
    stats: RehydrationStatsDTO

