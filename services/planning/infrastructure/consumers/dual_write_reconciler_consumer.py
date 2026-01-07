"""Consumer for planning.dualwrite.reconcile.requested events.

Inbound Adapter (Infrastructure):
- Listens to planning.dualwrite.reconcile.requested NATS events
- Triggers reconciliation of failed Neo4j writes
- Event-driven reconciliation for eventual consistency
"""

import asyncio
import json
import logging

from core.shared.events.infrastructure import parse_required_envelope
from planning.application.services.dual_write_reconciliation_service import (
    DualWriteReconciliationService,
)
from planning.domain.value_objects.nats_durable import NATSDurable
from planning.domain.value_objects.nats_stream import NATSStream
from planning.domain.value_objects.nats_subject import NATSSubject

logger = logging.getLogger(__name__)


class DualWriteReconcilerConsumer:
    """Consumer for planning.dualwrite.reconcile.requested events.

    Following Hexagonal Architecture:
    - Inbound adapter (infrastructure)
    - Listens to external events (NATS)
    - Converts DTO → operation data (anti-corruption layer)
    - Delegates to reconciliation service (application layer)

    Responsibilities:
    - Subscribe to planning.dualwrite.reconcile.requested
    - Parse NATS message payload
    - Extract operation_id, operation_type, operation_data
    - Call DualWriteReconciliationService
    - Handle errors and ACK/NAK
    """

    def __init__(
        self,
        nats_client,
        jetstream,
        reconciliation_service: DualWriteReconciliationService,
    ):
        """Initialize consumer with dependencies.

        Args:
            nats_client: NATS client connection
            jetstream: NATS JetStream context
            reconciliation_service: Service for reconciling dual write operations
        """
        self._nc = nats_client
        self._js = jetstream
        self._reconciliation_service = reconciliation_service
        self._subscription = None
        self._polling_task = None

    async def start(self) -> None:
        """Start consuming planning.dualwrite.reconcile.requested events.

        Uses PULL subscription for reliability and load balancing.
        """
        try:
            # Create PULL subscription (durable)
            self._subscription = await self._js.pull_subscribe(
                subject=str(NATSSubject.DUALWRITE_RECONCILE_REQUESTED),
                durable="planning-dualwrite-reconciler",
                stream=str(NATSStream.PLANNING_EVENTS),
            )

            logger.info(
                "✓ DualWriteReconcilerConsumer: subscription created (DURABLE)"
            )

            # Start background polling task
            self._polling_task = asyncio.create_task(self._poll_messages())

        except Exception as e:
            logger.error(
                f"Failed to start DualWriteReconcilerConsumer: {e}", exc_info=True
            )
            raise

    async def _poll_messages(self) -> None:
        """Poll for messages continuously."""
        logger.info("🔄 DualWriteReconcilerConsumer: polling started")

        while True:
            try:
                # Fetch messages (batch=1, timeout=5s)
                msgs = await self._subscription.fetch(batch=1, timeout=5)

                for msg in msgs:
                    await self._handle_message(msg)

            except TimeoutError:
                # No messages available - continue polling
                continue

            except Exception as e:
                logger.error(f"Error polling messages: {e}", exc_info=True)
                await asyncio.sleep(5)  # Backoff on error

    async def _handle_message(self, msg) -> None:
        """Handle individual planning.dualwrite.reconcile.requested message.

        Args:
            msg: NATS message
        """
        try:
            # 1. Parse JSON payload (DTO - external format)
            data = json.loads(msg.data.decode())

            # 2. Require EventEnvelope (no legacy fallback)
            envelope = parse_required_envelope(data)
            correlation_id = envelope.correlation_id
            idempotency_key = envelope.idempotency_key
            payload = envelope.payload

            logger.info(
                f"📥 [EventEnvelope] Received reconcile request: "
                f"operation_id={payload.get('operation_id')}, "
                f"operation_type={payload.get('operation_type')}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..., "
                f"event_type={envelope.event_type}, "
                f"producer={envelope.producer}"
            )

            # 3. Extract operation data (anti-corruption layer)
            operation_id = payload["operation_id"]
            operation_type = payload["operation_type"]
            operation_data = payload["operation_data"]

            if not operation_id:
                raise ValueError("Missing required field: operation_id")

            if not operation_type:
                raise ValueError("Missing required field: operation_type")

            if not operation_data:
                raise ValueError("Missing required field: operation_data")

            # 4. Call reconciliation service (application layer)
            await self._reconciliation_service.reconcile_operation(
                operation_id=operation_id,
                operation_type=operation_type,
                operation_data=operation_data,
            )

            logger.info(
                f"✅ Reconciliation completed: operation_id={operation_id}, "
                f"operation_type={operation_type}. "
                f"correlation_id={correlation_id}, "
                f"idempotency_key={idempotency_key[:16]}..."
            )

            # 5. ACK message (success)
            await msg.ack()

        except ValueError as e:
            # Invalid envelope / invalid payload format: permanent error (drop).
            logger.error(
                f"Dropping invalid EventEnvelope for reconcile request: {e}",
                exc_info=True,
            )
            await msg.ack()

        except KeyError as e:
            # Missing required field in payload
            logger.warning(f"Invalid event payload (missing {e})", exc_info=True)
            await msg.nak()  # Retry

        except Exception as e:
            # Unexpected error (including reconciliation failures)
            logger.error(f"Error processing reconcile request: {e}", exc_info=True)
            await msg.nak()  # Retry

    async def stop(self) -> None:
        """Stop consumer and cleanup resources."""
        if self._polling_task:
            self._polling_task.cancel()
            try:
                await self._polling_task
            except asyncio.CancelledError:
                logger.info("DualWriteReconcilerConsumer polling task cancelled")
                raise  # Re-raise CancelledError to properly propagate cancellation

        logger.info("DualWriteReconcilerConsumer stopped")
