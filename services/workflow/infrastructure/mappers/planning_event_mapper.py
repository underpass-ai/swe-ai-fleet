"""Mapper for Planning Service events.

Converts NATS messages to DTOs.
Following Hexagonal Architecture (infrastructure responsibility).
"""

import json
import logging
from typing import Any

from core.shared.events.infrastructure import parse_required_envelope

from services.workflow.application.dto.planning_event_dto import (
    PlanningStoryTransitionedDTO,
)

logger = logging.getLogger(__name__)


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
        Requires EventEnvelope (no legacy fallback).

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
        data: dict[str, Any] = json.loads(message_data.decode("utf-8"))

        envelope = parse_required_envelope(data)

        logger.debug(
            f"📥 [EventEnvelope] Parsed planning story transition: "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}, "
            f"event_type={envelope.event_type}"
        )

        return PlanningEventMapper.from_payload(envelope.payload)

    @staticmethod
    def from_payload(payload: dict[str, Any]) -> PlanningStoryTransitionedDTO:
        """Convert an EventEnvelope payload to PlanningStoryTransitionedDTO.

        Args:
            payload: Envelope payload dict.

        Returns:
            PlanningStoryTransitionedDTO

        Raises:
            KeyError: If required field missing (fail-fast)
            ValueError: If data is invalid (fail-fast)
        """
        story_id = payload["story_id"]
        from_state = payload["from_state"]
        to_state = payload["to_state"]
        tasks = payload["tasks"]
        timestamp = payload["timestamp"]

        if not isinstance(tasks, list):
            raise ValueError(f"Expected tasks to be list, got {type(tasks)}")

        return PlanningStoryTransitionedDTO(
            story_id=story_id,
            from_state=from_state,
            to_state=to_state,
            tasks=tasks,
            timestamp=timestamp,
        )

