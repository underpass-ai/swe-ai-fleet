"""Mapper for converting domain events to NATS event payloads."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)
from task_derivation.infrastructure.dto.task_derivation_completed_payload import (
    TaskDerivationCompletedPayload,
)
from task_derivation.infrastructure.dto.task_derivation_failed_payload import (
    TaskDerivationFailedPayload,
)


@dataclass(frozen=True)
class NatsEventMapper:
    """Pure mapper for domain events → NATS event payloads.

    This mapper handles conversions between:
    - Domain Events (TaskDerivationCompletedEvent, TaskDerivationFailedEvent)
    - Infrastructure DTOs (TaskDerivationCompletedPayload, TaskDerivationFailedPayload)
    - Serialized dicts for NATS publishing

    No I/O, no state mutation, no reflection. Just data transformation.
    """

    @staticmethod
    def to_completed_payload(
        event: TaskDerivationCompletedEvent,
    ) -> TaskDerivationCompletedPayload:
        """Convert domain event to completed payload DTO.

        Args:
            event: Domain event with completion details

        Returns:
            Infrastructure DTO ready for NATS publishing

        Raises:
            ValueError: If event data is invalid
        """
        if not event:
            raise ValueError("event cannot be None")

        return TaskDerivationCompletedPayload(
            plan_id=event.plan_id.value,
            story_id=event.story_id.value,
            task_count=event.task_count,
            status="success",
            occurred_at=event.occurred_at.isoformat(),
        )

    @staticmethod
    def to_failed_payload(
        event: TaskDerivationFailedEvent,
    ) -> TaskDerivationFailedPayload:
        """Convert domain event to failed payload DTO.

        Args:
            event: Domain event with failure details

        Returns:
            Infrastructure DTO ready for NATS publishing

        Raises:
            ValueError: If event data is invalid
        """
        if not event:
            raise ValueError("event cannot be None")

        return TaskDerivationFailedPayload(
            plan_id=event.plan_id.value,
            story_id=event.story_id.value,
            status="failed",
            reason=event.reason,
            requires_manual_review=event.requires_manual_review,
            occurred_at=event.occurred_at.isoformat(),
        )

    @staticmethod
    def payload_to_dict(payload: TaskDerivationCompletedPayload | TaskDerivationFailedPayload) -> dict:
        """Convert DTO to serializable dict.

        Args:
            payload: Infrastructure DTO

        Returns:
            Dictionary ready for JSON serialization
        """
        if not payload:
            raise ValueError("payload cannot be None")

        return asdict(payload)

