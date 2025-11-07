"""Mapper for Planning Service events.

Converts NATS messages to DTOs.
Following Hexagonal Architecture (infrastructure responsibility).
"""

import json
from typing import Any

from services.workflow.application.dto.planning_event_dto import (
    PlanningStoryTransitionedDTO,
)


class PlanningEventMapper:
    """Maps Planning Service NATS events to DTOs.

    This is infrastructure responsibility:
    - DTOs do NOT know about JSON/NATS
    - Mappers live in infrastructure layer
    - Handle all deserialization (bytes → dict → DTO)

    Following DDD:
    - No from_dict() / to_dict() in DTOs
    - Explicit mappers in infrastructure
    - Fail-fast on invalid data
    """

    @staticmethod
    def from_nats_message(message_data: bytes) -> PlanningStoryTransitionedDTO:
        """Convert NATS message to PlanningStoryTransitionedDTO.

        Deserializes JSON payload and validates structure.
        Mapper responsibility: Handle external format → internal DTO.

        Args:
            message_data: Raw NATS message bytes

        Returns:
            PlanningStoryTransitionedDTO

        Raises:
            KeyError: If required field missing (fail-fast)
            ValueError: If data is invalid (fail-fast)
            json.JSONDecodeError: If JSON is malformed
        """
        # Deserialize JSON
        payload: dict[str, Any] = json.loads(message_data.decode("utf-8"))

        # Extract required fields (fail-fast if missing)
        story_id = payload["story_id"]
        from_state = payload["from_state"]
        to_state = payload["to_state"]
        tasks = payload["tasks"]
        timestamp = payload["timestamp"]

        # Validate tasks is a list
        if not isinstance(tasks, list):
            raise ValueError(f"Expected tasks to be list, got {type(tasks)}")

        # Create DTO (DTO validates invariants in __post_init__)
        return PlanningStoryTransitionedDTO(
            story_id=story_id,
            from_state=from_state,
            to_state=to_state,
            tasks=tasks,
            timestamp=timestamp,
        )

