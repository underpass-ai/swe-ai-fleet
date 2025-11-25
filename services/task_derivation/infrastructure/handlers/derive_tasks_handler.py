"""Handler for task.derivation.requested events."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from task_derivation.application.usecases.derive_tasks_usecase import (
    DeriveTasksUseCase,
)
from task_derivation.infrastructure.mappers.task_derivation_request_mapper import (
    TaskDerivationRequestMapper,
)

logger = logging.getLogger(__name__)


async def derive_tasks_handler(
    payload: Mapping[str, Any],
    use_case: DeriveTasksUseCase,
) -> None:
    """Handle task.derivation.requested event.

    Following Hexagonal Architecture:
    - Handler is in infrastructure layer (inbound adapter)
    - Uses mapper to convert payload → domain VO
    - Delegates business logic to use case
    - No business logic in handler

    Args:
        payload: Raw NATS event payload (dict)
        use_case: DeriveTasksUseCase instance (injected)

    Raises:
        ValueError: If payload is invalid (mapper validation)
        Exception: If use case execution fails
    """
    try:
        logger.info(
            "Handling task.derivation.requested: plan_id=%s, story_id=%s",
            payload.get("plan_id"),
            payload.get("story_id"),
        )

        # Map payload to domain VO (infrastructure → domain boundary)
        mapper = TaskDerivationRequestMapper()
        request = mapper.from_event(payload)

        # Delegate to use case (application layer)
        request_id = await use_case.execute(request)

        logger.info(
            "Task derivation job submitted: request_id=%s, plan_id=%s",
            request_id.value,
            request.plan_id.value,
        )

    except ValueError as exc:
        logger.error("Invalid derivation request payload: %s", exc)
        raise  # Re-raise for consumer to handle (ack/nak)

    except Exception as exc:
        logger.exception(
            "Error handling task.derivation.requested: %s",
            exc,
        )
        raise  # Re-raise for consumer to handle (ack/nak)

