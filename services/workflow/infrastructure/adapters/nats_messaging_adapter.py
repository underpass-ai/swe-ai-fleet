"""NATS messaging adapter for event publishing.

Implements MessagingPort using NATS JetStream.
Following Hexagonal Architecture (Adapter).
"""

import json
import logging

from core.shared.events import create_event_envelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from nats.aio.client import Client as NATS
from nats.js import JetStreamContext

from services.workflow.application.ports.messaging_port import MessagingPort
from services.workflow.domain.entities.workflow_state import WorkflowState
from services.workflow.domain.value_objects.nats_subjects import NatsSubjects
from services.workflow.infrastructure.mappers.workflow_event_mapper import WorkflowEventMapper

logger = logging.getLogger(__name__)


class NatsMessagingAdapter(MessagingPort):
    """NATS messaging adapter for publishing workflow events.

    Events published:
    - workflow.state.changed: State transition occurred
    - workflow.task.assigned: Task ready for a role
    - workflow.validation.required: Validator should review work
    - workflow.task.completed: Task reached terminal state

    Following Hexagonal Architecture:
    - This is an ADAPTER (infrastructure implementation)
    - Implements MessagingPort (application port)
    - Contains NATS-specific logic
    """

    def __init__(self, nats_client: NATS, jetstream: JetStreamContext) -> None:
        """Initialize adapter with NATS client.

        Args:
            nats_client: NATS client
            jetstream: JetStream context
        """
        self._nats = nats_client
        self._js = jetstream

    async def publish_state_changed(
        self,
        workflow_state: WorkflowState,
        event_type: str,
    ) -> None:
        """Publish workflow state changed event with EventEnvelope.

        Subject: workflow.state.changed
        Uses mapper to convert domain entity to event payload.

        Args:
            workflow_state: New workflow state
            event_type: Event type identifier
        """
        # Mapper converts domain entity to dict (infrastructure responsibility)
        payload = WorkflowEventMapper.to_state_changed_payload(
            workflow_state=workflow_state,
            event_type=event_type,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="workflow.state.changed",
            payload=payload,
            producer="workflow-service",
            entity_id=workflow_state.task_id,
            operation="state_changed",
        )

        # Serialize envelope to JSON using infrastructure mapper
        await self._js.publish(
            subject=str(NatsSubjects.WORKFLOW_STATE_CHANGED),
            payload=json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8"),
        )

        logger.info(
            f"Published workflow.state.changed: {workflow_state.task_id} "
            f"→ {workflow_state.get_current_state_value()}, "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}"
        )

    async def publish_task_assigned(
        self,
        task_id: str,
        story_id: str,
        role: str,
        action_required: str,
    ) -> None:
        """Publish task assigned event with EventEnvelope.

        Subject: workflow.task.assigned
        Uses mapper to create event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            role: Role that should act
            action_required: Action required
        """
        payload = WorkflowEventMapper.to_task_assigned_payload(
            task_id=task_id,
            story_id=story_id,
            role=role,
            action_required=action_required,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="workflow.task.assigned",
            payload=payload,
            producer="workflow-service",
            entity_id=task_id,
            operation="task_assigned",
        )

        # Serialize envelope to JSON using infrastructure mapper
        await self._js.publish(
            subject=str(NatsSubjects.WORKFLOW_TASK_ASSIGNED),
            payload=json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8"),
        )

        logger.info(
            f"Published workflow.task.assigned: {task_id} → {role}, "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}"
        )

    async def publish_validation_required(
        self,
        task_id: str,
        story_id: str,
        validator_role: str,
        artifact_type: str,
    ) -> None:
        """Publish validation required event with EventEnvelope.

        Subject: workflow.validation.required
        Uses mapper to create event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            validator_role: Role that should validate
            artifact_type: What to validate (design, tests, story)
        """
        payload = WorkflowEventMapper.to_validation_required_payload(
            task_id=task_id,
            story_id=story_id,
            validator_role=validator_role,
            artifact_type=artifact_type,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="workflow.validation.required",
            payload=payload,
            producer="workflow-service",
            entity_id=task_id,
            operation="validation_required",
        )

        # Serialize envelope to JSON using infrastructure mapper
        await self._js.publish(
            subject=str(NatsSubjects.WORKFLOW_VALIDATION_REQUIRED),
            payload=json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8"),
        )

        logger.info(
            f"Published workflow.validation.required: {task_id} → {validator_role} ({artifact_type}), "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}"
        )

    async def publish_task_completed(
        self,
        task_id: str,
        story_id: str,
        final_state: str,
    ) -> None:
        """Publish task completed event with EventEnvelope.

        Subject: workflow.task.completed
        Uses mapper to create event payload.

        Args:
            task_id: Task identifier
            story_id: Story identifier
            final_state: Terminal state (done, cancelled)
        """
        payload = WorkflowEventMapper.to_task_completed_payload(
            task_id=task_id,
            story_id=story_id,
            final_state=final_state,
        )

        # Create event envelope with idempotency key
        envelope = create_event_envelope(
            event_type="workflow.task.completed",
            payload=payload,
            producer="workflow-service",
            entity_id=task_id,
            operation="task_completed",
        )

        # Serialize envelope to JSON using infrastructure mapper
        await self._js.publish(
            subject=str(NatsSubjects.WORKFLOW_TASK_COMPLETED),
            payload=json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8"),
        )

        logger.info(
            f"Published workflow.task.completed: {task_id} → {final_state}, "
            f"idempotency_key={envelope.idempotency_key[:16]}..., "
            f"correlation_id={envelope.correlation_id}"
        )

