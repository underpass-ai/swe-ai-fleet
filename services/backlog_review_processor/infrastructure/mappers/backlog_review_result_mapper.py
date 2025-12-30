"""Mapper for BacklogReviewResult domain entity from NATS event payloads.

Infrastructure layer mapper for converting NATS event payloads to
BacklogReviewResult domain entities.

Following Hexagonal Architecture:
- Infrastructure concern: external format (NATS bytes/JSON/DTO) → domain entity
- Separates external format from domain model
- Handles all parsing and validation logic
- Fail-fast validation with proper error handling
"""

import logging
from datetime import UTC, datetime
from typing import Any

from backlog_review_processor.domain.entities.backlog_review_result import (
    BacklogReviewResult,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)
from backlog_review_processor.infrastructure.mappers.agent_response_mapper import (
    AgentResponseMapper,
)

logger = logging.getLogger(__name__)


class BacklogReviewResultMapper:
    """Mapper that converts NATS event payloads to BacklogReviewResult domain entity.

    Responsibility:
    - NATS bytes/JSON/DTO → BacklogReviewResult domain entity
    - Parse task_id to extract ceremony_id, story_id, and role
    - Handle timestamp conversion
    - Validate all fields (fail-fast)
    - Extract proposal data

    This is infrastructure-level mapping logic.
    Separates external format (NATS/JSON) from domain model.
    """

    @staticmethod
    def from_nats_bytes(message_data: bytes) -> BacklogReviewResult:
        """Convert NATS message bytes to BacklogReviewResult domain entity.

        Args:
            message_data: Raw NATS message bytes (JSON)

        Returns:
            BacklogReviewResult domain entity

        Raises:
            json.JSONDecodeError: If JSON is malformed
            ValueError: If task_id format is invalid or required data is missing
            KeyError: If required field missing in payload
        """
        # First convert to DTO
        agent_response = AgentResponseMapper.from_nats_bytes(message_data)

        # Then convert DTO to domain entity
        return BacklogReviewResultMapper.from_agent_response_dto(agent_response)

    @staticmethod
    def from_nats_json(payload: dict[str, Any]) -> BacklogReviewResult:
        """Convert NATS JSON payload to BacklogReviewResult domain entity.

        Args:
            payload: JSON payload from NATS message (already parsed from bytes)

        Returns:
            BacklogReviewResult domain entity

        Raises:
            ValueError: If task_id format is invalid or required data is missing
            KeyError: If required field missing in payload
        """
        # First convert to DTO
        agent_response = AgentResponseMapper.from_nats_json(payload)

        # Then convert DTO to domain entity
        return BacklogReviewResultMapper.from_agent_response_dto(agent_response)

    @staticmethod
    def from_agent_response_dto(agent_response: Any) -> BacklogReviewResult:
        """Convert AgentResponsePayload DTO to BacklogReviewResult domain entity.

        Args:
            agent_response: AgentResponsePayload DTO

        Returns:
            BacklogReviewResult domain entity

        Raises:
            ValueError: If task_id format is invalid or required data is missing
        """
        # Extract and validate task_id
        task_id = agent_response.task_id
        if not task_id:
            raise ValueError("task_id is required in agent response")

        # Parse task_id (format: "ceremony-{id}:story-{id}:role-{role}")
        # Format validation
        if not task_id.startswith("ceremony-"):
            raise ValueError(f"Invalid task_id format (expected ceremony-*): {task_id}")

        parts = task_id.split(":")
        if len(parts) != 3:
            raise ValueError(
                f"Invalid task_id format (expected 3 parts, got {len(parts)}): {task_id}"
            )

        if not (
            parts[0].startswith("ceremony-")
            and parts[1].startswith("story-")
            and parts[2].startswith("role-")
        ):
            raise ValueError(
                f"Invalid task_id format (expected ceremony-*:story-*:role-*): {task_id}"
            )

        # Extract identifiers
        ceremony_id_str = parts[0].replace("ceremony-", "")
        story_id_str = parts[1].replace("story-", "")
        role_str = parts[2].replace("role-", "")

        # Create value objects (these validate themselves)
        ceremony_id = BacklogReviewCeremonyId(ceremony_id_str)
        story_id = StoryId(story_id_str)

        try:
            role = BacklogReviewRole(role_str)
        except ValueError as e:
            raise ValueError(f"Invalid role in task_id: {role_str}") from e

        # Extract proposal content
        proposal_data = agent_response.proposal or {}

        # Extract and convert timestamp
        timestamp_str = agent_response.timestamp
        if timestamp_str:
            try:
                reviewed_at = datetime.fromisoformat(timestamp_str.replace("Z", "+00:00"))
            except Exception as e:
                logger.warning(
                    f"Failed to parse timestamp '{timestamp_str}', using current time: {e}"
                )
                reviewed_at = datetime.now(UTC)
        else:
            reviewed_at = datetime.now(UTC)

        # Extract agent_id (with default fallback)
        agent_id = agent_response.agent_id or "unknown"

        # Create domain entity (entity validates itself in __post_init__)
        return BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id=agent_id,
            role=role,
            proposal=proposal_data,
            reviewed_at=reviewed_at,
        )
