"""Use case: advance ceremony state when agent.response.completed is received."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from core.ceremony_engine.application.ports.persistence_port import PersistencePort
from core.ceremony_engine.application.services.ceremony_runner import CeremonyRunner
from core.ceremony_engine.domain.value_objects.transition_trigger import (
    TransitionTrigger,
)

logger = logging.getLogger(__name__)


@dataclass
class AdvanceCeremonyOnAgentCompletedUseCase:
    """Advance ceremony state after an agent completes (agent.response.completed).

    Loads ceremony instance(s) by correlation_id, then applies a state transition
    when the event payload contains a "trigger" (e.g. deliberation_done).
    Persistence and event publishing are delegated to CeremonyRunner.
    """

    persistence_port: PersistencePort
    ceremony_runner: CeremonyRunner

    def __post_init__(self) -> None:
        if not self.persistence_port:
            raise ValueError("persistence_port is required (fail-fast)")
        if not self.ceremony_runner:
            raise ValueError("ceremony_runner is required (fail-fast)")

    async def advance(
        self,
        correlation_id: str,
        task_id: str,
        payload: dict | None = None,
    ) -> None:
        """Load instance by correlation_id and apply transition if payload has trigger.

        Args:
            correlation_id: Correlation ID from the event (required).
            task_id: Task ID from the event (for logging).
            payload: Event payload; may contain "trigger" (e.g. deliberation_done).

        Raises:
            ValueError: If correlation_id is empty.
        """
        if not correlation_id or not correlation_id.strip():
            raise ValueError("correlation_id cannot be empty")

        instances = await self.persistence_port.find_instances_by_correlation_id(
            correlation_id
        )
        if not instances:
            logger.info(
                "No ceremony instances for correlation_id=%s task_id=%s",
                correlation_id,
                task_id,
            )
            return

        instance = instances[0]
        trigger_str = None
        if isinstance(payload, dict):
            raw = payload.get("trigger")
            if raw is not None:
                trigger_str = str(raw).strip() if raw else None

        if not trigger_str:
            logger.info(
                "No trigger in payload, skipping advancement correlation_id=%s task_id=%s",
                correlation_id,
                task_id,
            )
            return

        trigger = TransitionTrigger(trigger_str)
        updated = await self.ceremony_runner.transition_state(
            instance, trigger, context=None
        )
        logger.info(
            "Advanced ceremony instance_id=%s trigger=%s state=%s",
            updated.instance_id,
            trigger.value,
            updated.current_state,
        )
