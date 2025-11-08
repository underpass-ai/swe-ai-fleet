"""RehydrationStats value object."""

from dataclasses import dataclass


@dataclass(frozen=True)
class RehydrationStats:
    """Statistics about context rehydration.

    Provides metrics about the rehydration process for observability.
    """

    decisions_count: int
    decision_edges_count: int
    impacts_count: int
    events_count: int
    roles: tuple[str, ...]  # Tuple for immutability

    def __post_init__(self) -> None:
        """Validate stats."""
        if self.decisions_count < 0:
            raise ValueError("decisions_count cannot be negative")
        if self.decision_edges_count < 0:
            raise ValueError("decision_edges_count cannot be negative")
        if self.impacts_count < 0:
            raise ValueError("impacts_count cannot be negative")
        if self.events_count < 0:
            raise ValueError("events_count cannot be negative")

    @staticmethod
    def from_dict(stats_dict: dict[str, any]) -> "RehydrationStats":
        """Create RehydrationStats from dictionary.

        Args:
            stats_dict: Dictionary with stats keys

        Returns:
            RehydrationStats value object
        """
        return RehydrationStats(
            decisions_count=int(stats_dict.get("decisions", 0)),
            decision_edges_count=int(stats_dict.get("decision_edges", 0)),
            impacts_count=int(stats_dict.get("impacts", 0)),
            events_count=int(stats_dict.get("events", 0)),
            roles=tuple(stats_dict.get("roles", [])),
        )

    def to_dict(self) -> dict[str, any]:
        """Convert to dictionary representation.

        Returns:
            Dictionary with stats
        """
        return {
            "decisions": self.decisions_count,
            "decision_edges": self.decision_edges_count,
            "impacts": self.impacts_count,
            "events": self.events_count,
            "roles": list(self.roles),
        }






