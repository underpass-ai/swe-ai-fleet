"""PublishStepHandler: Publishes events/outputs.

Following Hexagonal Architecture:
- This is an infrastructure adapter
- Executes publish steps (publish events to NATS, etc.)
- Returns domain value objects (StepResult)
"""

from core.ceremony_engine.application.ports.messaging_port import MessagingPort
from core.ceremony_engine.domain.value_objects.context_key import ContextKey
from core.ceremony_engine.domain.value_objects.execution_context import ExecutionContext
from core.ceremony_engine.domain.value_objects.step import Step
from core.ceremony_engine.domain.value_objects.step_result import StepResult
from core.ceremony_engine.infrastructure.adapters.step_handlers.base_step_handler import (
    BaseStepHandler,
)
from core.shared.events.helpers import create_event_envelope
from core.shared.idempotency.idempotency_port import IdempotencyPort
from core.shared.idempotency.idempotency_state import IdempotencyState


class PublishStepHandler(BaseStepHandler):
    """Handler for publish_step steps.

    Publishes events or outputs to messaging infrastructure.

    Config requirements:
    - subject: NATS subject to publish to
    - event_type: Event type name
    - payload_template: Template for event payload (optional, uses context if not provided)

    Following Hexagonal Architecture:
    - This is infrastructure (adapter)
    - Publishes events via MessagingPort
    """

    def __init__(
        self,
        messaging_port: MessagingPort,
        idempotency_port: IdempotencyPort,
        in_progress_ttl_seconds: int = 300,
        stale_max_age_seconds: int = 600,
        completed_ttl_seconds: int | None = None,
    ) -> None:
        if not messaging_port:
            raise ValueError("messaging_port is required (fail-fast)")
        if not idempotency_port:
            raise ValueError("idempotency_port is required (fail-fast)")
        self._messaging_port = messaging_port
        self._idempotency_port = idempotency_port
        self._in_progress_ttl_seconds = in_progress_ttl_seconds
        self._stale_max_age_seconds = stale_max_age_seconds
        self._completed_ttl_seconds = completed_ttl_seconds

    async def execute(
        self,
        step: Step,
        context: ExecutionContext,
    ) -> StepResult:
        """Execute publish step.

        Args:
            step: Step to execute
            context: Execution context (should contain MessagingPort if available)

        Returns:
            StepResult with publish status

        Raises:
            ValueError: If config is invalid
        """
        # Validate config
        self._validate_config(step, required_keys=["subject", "event_type"])

        # Extract config
        subject = step.config["subject"]
        event_type = step.config["event_type"]
        payload_template = step.config.get("payload_template", {})
        if payload_template is None:
            payload_template = {}

        # Build payload from template and context
        publish_data = context.get_mapping(ContextKey.PUBLISH_DATA) or {}
        payload = {**payload_template, **publish_data}

        inputs = context.get_mapping(ContextKey.INPUTS)
        if not isinstance(inputs, dict):
            raise ValueError("publish_step requires inputs in ExecutionContext")
        ceremony_id = inputs.get("ceremony_id")
        correlation_id = inputs.get("correlation_id")
        if not isinstance(ceremony_id, str) or not ceremony_id.strip():
            raise ValueError("publish_step requires non-empty ceremony_id in inputs")
        if correlation_id is not None and not isinstance(correlation_id, str):
            raise ValueError("publish_step correlation_id must be a string if provided")

        envelope = create_event_envelope(
            event_type=event_type,
            payload=payload,
            producer="ceremony-engine",
            entity_id=ceremony_id,
            operation=f"step:{step.id.value}",
            correlation_id=correlation_id,
        )
        should_skip = await self._idempotency_should_skip(envelope.idempotency_key)
        if not should_skip:
            await self._messaging_port.publish_event(subject=subject, envelope=envelope)
            await self._idempotency_port.mark_completed(
                envelope.idempotency_key, self._completed_ttl_seconds
            )

        output = {
            "subject": subject,
            "event_type": event_type,
            "payload": payload,
            "published": not should_skip,
            "idempotency_key": envelope.idempotency_key,
        }

        return self._create_success_result(output)

    async def _idempotency_should_skip(self, idempotency_key: str) -> bool:
        status = await self._idempotency_port.check_status(idempotency_key)
        if status == IdempotencyState.COMPLETED:
            return True
        if status == IdempotencyState.IN_PROGRESS:
            is_stale = await self._idempotency_port.is_stale(
                idempotency_key, self._stale_max_age_seconds
            )
            if not is_stale:
                return True
            await self._idempotency_port.mark_in_progress(
                idempotency_key, self._in_progress_ttl_seconds
            )
            return False
        marked = await self._idempotency_port.mark_in_progress(
            idempotency_key, self._in_progress_ttl_seconds
        )
        if not marked:
            final_status = await self._idempotency_port.check_status(idempotency_key)
            if final_status in {IdempotencyState.COMPLETED, IdempotencyState.IN_PROGRESS}:
                return True
        return False
