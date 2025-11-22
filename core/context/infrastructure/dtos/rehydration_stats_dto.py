"""DTO for rehydration statistics."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RehydrationStatsDTO:
    """DTO for rehydration statistics."""

    decisions: int
    decision_edges: int
    impacts: int
    events: int
    roles: list[str]

