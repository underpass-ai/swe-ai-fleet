"""Tests for TaskDerivationResultConsumer."""

from __future__ import annotations

import json
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from task_derivation.application.usecases.process_task_derivation_result_usecase import (
    ProcessTaskDerivationResultUseCase,
)
from task_derivation.infrastructure.consumers.task_derivation_result_consumer import (
    TaskDerivationResultConsumer,
)
from task_derivation.infrastructure.mappers.llm_task_derivation_mapper import (
    LLMTaskDerivationMapper,
)


class DummyMsg:
    def __init__(self, payload: dict[str, object], deliveries: int = 1):
        self.data = json.dumps(payload).encode("utf-8")
        self.metadata = SimpleNamespace(num_delivered=deliveries)
        self.ack = AsyncMock()
        self.nak = AsyncMock()


@pytest.mark.asyncio
async def test_result_consumer_invokes_usecase_and_acknowledges(monkeypatch) -> None:
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    messaging_port = AsyncMock()
    mapper = LLMTaskDerivationMapper()
    mapper.from_llm_text = lambda text: ()  # type: ignore[assignment]
    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": "TITLE: Task\nDESCRIPTION: Do work\nKEYWORDS: work"},
    }
    msg = DummyMsg(payload)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
        llm_mapper=LLMTaskDerivationMapper(),
    )

    # Monkeypatch mapper to avoid randomness
    consumer._llm_mapper = mapper

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    usecase.execute.assert_awaited()


@pytest.mark.asyncio
async def test_result_consumer_publishes_failure_on_mapper_error() -> None:
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    messaging_port = AsyncMock()
    mapper = LLMTaskDerivationMapper()

    def _raise(_: str):
        raise ValueError("bad format")

    mapper.from_llm_text = _raise  # type: ignore[assignment]

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": ""},
    }
    msg = DummyMsg(payload)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
        llm_mapper=mapper,
    )

    await consumer._handle_message(msg)

    msg.ack.assert_awaited_once()
    messaging_port.publish_task_derivation_failed.assert_awaited()
    usecase.execute.assert_not_awaited()


@pytest.mark.asyncio
async def test_result_consumer_retries_then_acknowledges() -> None:
    usecase = AsyncMock(spec=ProcessTaskDerivationResultUseCase)
    usecase.execute.side_effect = RuntimeError("transient")
    messaging_port = AsyncMock()
    mapper = LLMTaskDerivationMapper()
    mapper.from_llm_text = lambda text: ()  # type: ignore[assignment]

    payload = {
        "plan_id": "plan-1",
        "story_id": "story-1",
        "role": "DEVELOPER",
        "result": {"proposal": "TITLE: Task\nDESCRIPTION: Body\nKEYWORDS: test"},
    }
    msg = DummyMsg(payload, deliveries=1)

    consumer = TaskDerivationResultConsumer(
        nats_client=None,
        jetstream=None,
        process_usecase=usecase,
        messaging_port=messaging_port,
        llm_mapper=mapper,
        max_deliveries=2,
    )

    await consumer._handle_message(msg)
    msg.nak.assert_awaited_once()

    msg.metadata.num_delivered = 2
    await consumer._handle_message(msg)
    msg.ack.assert_awaited_once()

