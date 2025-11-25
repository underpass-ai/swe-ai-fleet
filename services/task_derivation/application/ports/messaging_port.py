"""Port definition for publishing task-derivation domain events."""

from __future__ import annotations

from typing import Protocol

from task_derivation.domain.events.task_derivation_completed_event import (
    TaskDerivationCompletedEvent,
)
from task_derivation.domain.events.task_derivation_failed_event import (
    TaskDerivationFailedEvent,
)


class MessagingPort(Protocol):
    """Publishes typed domain events to the messaging fabric."""

    async def publish_task_derivation_completed(
        self,
        event: TaskDerivationCompletedEvent,
    ) -> None:
        """Publish success notification for downstream services."""
        ...

    async def publish_task_derivation_failed(
        self,
        event: TaskDerivationFailedEvent,
    ) -> None:
        """Publish failure notification with remediation details."""
        ...

