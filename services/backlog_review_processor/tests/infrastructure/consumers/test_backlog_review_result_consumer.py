"""Unit tests for BacklogReviewResultConsumer (strict EventEnvelope required)."""

from __future__ import annotations

import json
import sys
from dataclasses import dataclass
from enum import Enum
from types import ModuleType
from unittest.mock import AsyncMock

import pytest

from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper


def _install_fake_gen_module() -> None:
    """Install a minimal fake generated module for AgentResponsePayload DTOs.

    BacklogReviewResultMapper depends on backlog_review_processor.gen.agent_response_payload
    which is generated at build time in some environments. Unit tests must not depend on it.
    """
    gen_pkg = ModuleType("backlog_review_processor.gen")
    agent_mod = ModuleType("backlog_review_processor.gen.agent_response_payload")

    class Status(str, Enum):
        completed = "completed"
        failed = "failed"

    @dataclass(frozen=True)
    class Metadata:
        story_id: str | None = None
        ceremony_id: str | None = None
        task_type: str | None = None
        task_id: str | None = None
        num_agents: int | None = None

    @dataclass(frozen=True)
    class Constraints:
        story_id: str | None = None
        plan_id: str | None = None
        timeout_seconds: int | None = None
        max_retries: int | None = None
        metadata: Metadata | None = None

    @dataclass(frozen=True)
    class AgentResponsePayload:
        task_id: str
        status: Status
        agent_id: str | None = None
        role: str | None = None
        num_agents: int | None = None
        proposal: object | None = None
        duration_ms: int | None = None
        timestamp: str | None = None
        constraints: Constraints | None = None
        artifacts: object | None = None
        summary: object | None = None
        metrics: object | None = None
        workspace_report: object | None = None

    agent_mod.AgentResponsePayload = AgentResponsePayload
    agent_mod.Constraints = Constraints
    agent_mod.Metadata = Metadata
    agent_mod.Status = Status

    sys.modules["backlog_review_processor.gen"] = gen_pkg
    sys.modules["backlog_review_processor.gen.agent_response_payload"] = agent_mod


@pytest.mark.asyncio
async def test_handle_message_requires_envelope_and_executes_usecase() -> None:
    _install_fake_gen_module()

    from backlog_review_processor.infrastructure.consumers.backlog_review_result_consumer import (
        BacklogReviewResultConsumer,
    )

    accumulate = AsyncMock()
    consumer = BacklogReviewResultConsumer(
        nats_client=AsyncMock(),
        jetstream=AsyncMock(),
        accumulate_deliberations=accumulate,
    )

    agent_payload = {
        "task_id": "ceremony-BRC-123:story-ST-456:role-ARCHITECT",
        "status": "completed",
        "agent_id": "agent-1",
        "role": "ARCHITECT",
        "proposal": {"feedback": "ok"},
        "timestamp": "2025-12-30T10:00:00Z",
    }

    envelope = EventEnvelope(
        event_type="agent.response.completed",
        payload=agent_payload,
        idempotency_key="idemp-123",
        correlation_id="corr-456",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="ray-executor",
    )

    msg = AsyncMock()
    msg.data = json.dumps(EventEnvelopeMapper.to_dict(envelope)).encode("utf-8")
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.subject = "agent.response.completed"

    await consumer._handle_message(msg)

    accumulate.execute.assert_awaited_once()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_drops_message_without_envelope() -> None:
    _install_fake_gen_module()

    from backlog_review_processor.infrastructure.consumers.backlog_review_result_consumer import (
        BacklogReviewResultConsumer,
    )

    accumulate = AsyncMock()
    consumer = BacklogReviewResultConsumer(
        nats_client=AsyncMock(),
        jetstream=AsyncMock(),
        accumulate_deliberations=accumulate,
    )

    msg = AsyncMock()
    msg.data = json.dumps({"task_id": "x"}).encode("utf-8")
    msg.ack = AsyncMock()
    msg.nak = AsyncMock()
    msg.subject = "agent.response.completed"

    await consumer._handle_message(msg)

    accumulate.execute.assert_not_awaited()
    msg.ack.assert_awaited_once()
    msg.nak.assert_not_awaited()

