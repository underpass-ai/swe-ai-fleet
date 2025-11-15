"""Tests for TaskDerivationRequestConsumer."""

from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from task_derivation.infrastructure.consumers.task_derivation_request_consumer import (
    TaskDerivationRequestConsumer,
)


class DummySubscription:
    def __init__(self, message):
        self._message = message

    async def fetch(self, batch: int, timeout: int):
        await asyncio.sleep(0)
        return [self._message]


class DummyMsg:
    def __init__(self, payload: dict[str, str], deliveries: int = 1):
        self.data = json.dumps(payload).encode("utf-8")
        self.metadata = SimpleNamespace(num_delivered=deliveries)
        self.ack = AsyncMock()
        self.nak = AsyncMock()


@pytest.mark.asyncio
async def test_request_consumer_acknowledges_on_success(monkeypatch) -> None:
    usecase = AsyncMock()
    msg = DummyMsg(
        {
            "plan_id": "plan-1",
            "story_id": "story-1",
            "roles": ["DEVELOPER"],
            "requested_by": "user",
        }
    )

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
    )

    consumer._subscription = DummySubscription(msg)

    async def run_once():
        await consumer._handle_message(msg)

    await run_once()

    msg.ack.assert_awaited_once()
    usecase.execute.assert_awaited()


@pytest.mark.asyncio
async def test_request_consumer_ack_on_validation_error() -> None:
    usecase = AsyncMock()
    msg = DummyMsg({"story_id": "story-1", "requested_by": "user"})

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
    )

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    usecase.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_request_consumer_naks_until_max_deliveries() -> None:
    usecase = AsyncMock()
    usecase.execute.side_effect = RuntimeError("boom")
    msg = DummyMsg(
        {
            "plan_id": "plan-1",
            "story_id": "story-1",
            "roles": ["DEVELOPER"],
            "requested_by": "user",
        },
        deliveries=1,
    )

    consumer = TaskDerivationRequestConsumer(
        nats_client=None,
        jetstream=None,
        derive_tasks_usecase=usecase,
        max_deliveries=2,
    )

    await consumer._handle_message(msg)

    msg.nak.assert_awaited_once()

    msg.metadata.num_delivered = 2
    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()

