"""Mapper for PlanningEvent entity - Infrastructure layer."""

from typing import Any

from core.context.domain.entity_ids.actor_id import ActorId
from core.context.domain.planning_event import PlanningEvent


class PlanningEventMapper:
    """Mapper for PlanningEvent conversions (formerly PlanningEventDTO)."""

    @staticmethod
    def from_redis_data(data: dict[str, Any]) -> PlanningEvent:
        """Create PlanningEvent from Redis/Valkey data.

        Args:
            data: Dictionary from Redis with event data

        Returns:
            PlanningEvent domain entity

        Raises:
            KeyError: If required fields are missing
            ValueError: If data is invalid
        """
        return PlanningEvent(
            id=data["id"],
            event=data["event"],
            actor_id=ActorId(value=data["actor"]),
            payload=dict(data.get("payload", {})),  # Defensive copy
            ts_ms=int(data.get("ts_ms", 0)),
        )

    @staticmethod
    def to_dict(event: PlanningEvent) -> dict[str, Any]:
        """Convert PlanningEvent to dictionary representation.

        Args:
            event: PlanningEvent domain entity

        Returns:
            Dictionary with primitive types
        """
        return {
            "id": event.id,
            "event": event.event,
            "actor": event.get_actor_id(),
            "payload": dict(event.payload),  # Copy
            "ts_ms": event.ts_ms,
        }

