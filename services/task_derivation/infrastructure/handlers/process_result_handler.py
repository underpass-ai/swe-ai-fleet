"""Handler for agent.response.completed events (task derivation results)."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.domain.value_objects.identifiers.plan_id import PlanId
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)

logger = logging.getLogger(__name__)


def _extract_identifiers(payload: Mapping[str, Any]) -> tuple[str | None, str | None]:
    """Extract plan_id and story_id from multiple payload shapes.

    Supports:
    - Legacy/canonical payload with top-level identifiers
    - Ray payload where identifiers may be under constraints + metadata
    """
    plan_id_raw = payload.get("plan_id")
    story_id_raw = payload.get("story_id")

    constraints = payload.get("constraints")
    if isinstance(constraints, Mapping):
        if not plan_id_raw:
            plan_id_raw = constraints.get("plan_id")
        if not story_id_raw:
            story_id_raw = constraints.get("story_id")

        metadata = constraints.get("metadata")
        if isinstance(metadata, Mapping):
            if not story_id_raw:
                story_id_raw = metadata.get("story_id")
            if not plan_id_raw:
                plan_id_raw = metadata.get("plan_id")

    return (
        str(plan_id_raw) if plan_id_raw else None,
        str(story_id_raw) if story_id_raw else None,
    )


def _extract_llm_text(payload: Mapping[str, Any]) -> str:
    """Extract LLM response text from supported event payloads."""
    result = payload.get("result")
    proposal: Any

    if isinstance(result, Mapping) and "proposal" in result:
        proposal = result.get("proposal")
    else:
        proposal = payload.get("proposal")

    if isinstance(proposal, Mapping):
        return str(proposal.get("content", "")).strip()
    if isinstance(proposal, str):
        return proposal.strip()
    return ""


async def process_result_handler(
    payload: Mapping[str, Any],
    use_case: ProcessTaskDerivationResultUseCase,
) -> None:
    """Handle agent.response.completed event (task derivation result).

    Following Hexagonal Architecture:
    - Handler is in infrastructure layer (inbound adapter)
    - Uses mapper to convert LLM text → domain VOs
    - Extracts identifiers from payload
    - Delegates business logic to use case
    - No business logic in handler

    Args:
        payload: Raw NATS event payload (dict)
        use_case: ProcessTaskDerivationResultUseCase instance (injected)

    Raises:
        ValueError: If payload is invalid (missing identifiers)
        Exception: If use case execution fails
    """
    try:
        plan_id_raw, story_id_raw = _extract_identifiers(payload)

        if not plan_id_raw:
            raise ValueError("plan_id missing from derivation result payload")
        if not story_id_raw:
            raise ValueError("story_id missing from derivation result payload")

        logger.info(
            "Handling agent.response.completed: plan_id=%s, story_id=%s",
            plan_id_raw,
            story_id_raw,
        )

        # Extract identifiers (infrastructure → domain boundary)
        plan_id = PlanId(str(plan_id_raw))
        story_id = StoryId(str(story_id_raw))
        role = ContextRole(payload.get("role", "DEVELOPER"))

        # Extract LLM response text
        llm_text = _extract_llm_text(payload)

        if not llm_text:
            raise ValueError("LLM proposal text is empty in derivation result")

        # Map LLM text to domain VOs (infrastructure → domain boundary)
        mapper = LLMTaskDerivationMapper()
        task_nodes = mapper.from_llm_text(llm_text)

        if not task_nodes:
            raise ValueError("No tasks parsed from LLM response")

        # Delegate to use case (application layer)
        await use_case.execute(
            plan_id=plan_id,
            story_id=story_id,
            role=role,
            task_nodes=task_nodes,
        )

        logger.info(
            "Task derivation result processed: plan_id=%s, tasks=%d",
            plan_id.value,
            len(task_nodes),
        )

    except ValueError as exc:
        logger.error("Invalid derivation result payload: %s", exc)
        raise  # Re-raise for consumer to handle (ack/nak)

    except Exception as exc:
        logger.exception(
            "Error handling agent.response.completed: %s",
            exc,
        )
        raise  # Re-raise for consumer to handle (ack/nak)
