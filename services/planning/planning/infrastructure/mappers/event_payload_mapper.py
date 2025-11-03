"""Mapper: Domain events → NATS JSON payloads."""

from datetime import UTC, datetime
from typing import Any

from planning.domain import Comment, DecisionId, Reason, StoryId, StoryState, Title, UserName


class EventPayloadMapper:
    """
    Mapper: Build NATS event payloads from domain data.

    Infrastructure Layer Responsibility:
    - Domain should not know about NATS event format
    - Event structure centralized in one place
    - Easy to version and evolve event schema
    """

    @staticmethod
    def story_created_payload(
        story_id: StoryId,
        title: Title,
        created_by: UserName,
    ) -> dict[str, Any]:
        """
        Build payload for story.created event.

        Args:
            story_id: Domain StoryId value object.
            title: Domain Title value object.
            created_by: Domain UserName value object.

        Returns:
            Event payload dict.
        """
        return {
            "event_type": "story.created",
            "story_id": story_id.value,  # Adapter converts to primitive for JSON
            "title": title.value,  # Adapter converts to primitive for JSON
            "created_by": created_by.value,  # Adapter converts to primitive for JSON
            "timestamp": EventPayloadMapper._current_timestamp(),
        }

    @staticmethod
    def story_transitioned_payload(
        story_id: StoryId,
        from_state: StoryState,
        to_state: StoryState,
        transitioned_by: UserName,
    ) -> dict[str, Any]:
        """
        Build payload for story.transitioned event.

        Args:
            story_id: Domain StoryId value object.
            from_state: Previous StoryState value object.
            to_state: New StoryState value object.
            transitioned_by: Domain UserName value object.

        Returns:
            Event payload dict.
        """
        return {
            "event_type": "story.transitioned",
            "story_id": story_id.value,  # Adapter converts to primitive for JSON
            "from_state": from_state.to_string(),  # Tell, Don't Ask
            "to_state": to_state.to_string(),  # Tell, Don't Ask
            "transitioned_by": transitioned_by.value,  # Adapter converts to primitive for JSON
            "timestamp": EventPayloadMapper._current_timestamp(),
        }

    @staticmethod
    def decision_approved_payload(
        story_id: StoryId,
        decision_id: DecisionId,
        approved_by: UserName,
        comment: Comment | None = None,
    ) -> dict[str, Any]:
        """
        Build payload for decision.approved event.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            approved_by: Domain UserName value object.
            comment: Optional Comment value object.

        Returns:
            Event payload dict.
        """
        return {
            "event_type": "decision.approved",
            "story_id": story_id.value,  # Adapter converts to primitive for JSON
            "decision_id": decision_id.value,  # Adapter converts to primitive for JSON
            "approved_by": approved_by.value,  # Adapter converts to primitive for JSON
            "comment": comment.value if comment else None,  # Adapter converts to primitive for JSON
            "timestamp": EventPayloadMapper._current_timestamp(),
        }

    @staticmethod
    def decision_rejected_payload(
        story_id: StoryId,
        decision_id: DecisionId,
        rejected_by: UserName,
        reason: Reason,
    ) -> dict[str, Any]:
        """
        Build payload for decision.rejected event.

        Args:
            story_id: Domain StoryId value object.
            decision_id: Domain DecisionId value object.
            rejected_by: Domain UserName value object.
            reason: Domain Reason value object.

        Returns:
            Event payload dict.
        """
        return {
            "event_type": "decision.rejected",
            "story_id": story_id.value,  # Adapter converts to primitive for JSON
            "decision_id": decision_id.value,  # Adapter converts to primitive for JSON
            "rejected_by": rejected_by.value,  # Adapter converts to primitive for JSON
            "reason": reason.value,  # Adapter converts to primitive for JSON
            "timestamp": EventPayloadMapper._current_timestamp(),
        }

    @staticmethod
    def _current_timestamp() -> str:
        """Get current UTC timestamp in ISO format."""
        return datetime.now(UTC).isoformat() + "Z"

