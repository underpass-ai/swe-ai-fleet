from __future__ import annotations

"""Unit tests for NATSPublisherAdapter."""

import asyncio
import json
from typing import Any

import pytest

import services.ray_executor.infrastructure.adapters.nats_publisher_adapter as adapter_module


class _FakeJetStream:
    def __init__(self) -> None:
        self.published: list[tuple[str, bytes]] = []
        self.should_fail: bool = False

    async def publish(self, subject: str, payload: bytes) -> None:  # type: ignore[no-untyped-def]
        await asyncio.sleep(0.001)  # Small delay to make function properly async
        if self.should_fail:
            raise RuntimeError("publish failed")
        self.published.append((subject, payload))


@pytest.mark.asyncio
async def test_publish_stream_event_skips_when_no_jetstream() -> None:
    """publish_stream_event should return early when JetStream is None."""
    adapter = adapter_module.NATSPublisherAdapter(jetstream=None)

    # Should not raise even though there is no JetStream context
    await adapter.publish_stream_event(
        event_type="token",
        agent_id="agent-1",
        data={"chunk": "data"},
    )


@pytest.mark.asyncio
async def test_publish_stream_event_happy_path_publishes_event() -> None:
    """publish_stream_event should build and publish a JSON event."""
    js = _FakeJetStream()
    adapter = adapter_module.NATSPublisherAdapter(jetstream=js)

    await adapter.publish_stream_event(
        event_type="token",
        agent_id="agent-1",
        data={"chunk": "data", "extra": "value"},
    )

    assert len(js.published) == 1
    subject, payload = js.published[0]

    assert subject == "vllm.streaming.agent-1"

    event = json.loads(payload.decode())
    assert event["type"] == "token"
    assert event["agent_id"] == "agent-1"
    assert event["chunk"] == "data"
    assert event["extra"] == "value"
    assert isinstance(event["timestamp"], (int, float))


@pytest.mark.asyncio
async def test_publish_stream_event_logs_warning_on_publish_error() -> None:
    """publish_stream_event should swallow publish errors (streaming is optional)."""
    js = _FakeJetStream()
    js.should_fail = True
    adapter = adapter_module.NATSPublisherAdapter(jetstream=js)

    # Should not raise even if publish fails
    await adapter.publish_stream_event(
        event_type="token",
        agent_id="agent-1",
        data={"chunk": "data"},
    )


@pytest.mark.asyncio
async def test_publish_deliberation_result_skips_when_no_jetstream() -> None:
    """publish_deliberation_result should return early when JetStream is None."""
    adapter = adapter_module.NATSPublisherAdapter(jetstream=None)

    await adapter.publish_deliberation_result(
        deliberation_id="delib-1",
        task_id="task-1",
        status="completed",
    )


@pytest.mark.asyncio
async def test_publish_deliberation_result_happy_path_minimal_event() -> None:
    """publish_deliberation_result should publish base event without result/error."""
    js = _FakeJetStream()
    adapter = adapter_module.NATSPublisherAdapter(jetstream=js)

    await adapter.publish_deliberation_result(
        deliberation_id="delib-1",
        task_id="task-1",
        status="completed",
    )

    assert len(js.published) == 1
    subject, payload = js.published[0]

    assert subject == "orchestration.deliberation.completed"

    event = json.loads(payload.decode())
    assert event["event_type"] == "deliberation.completed"
    assert event["deliberation_id"] == "delib-1"
    assert event["task_id"] == "task-1"
    assert event["status"] == "completed"
    assert isinstance(event["timestamp"], (int, float))
    assert "result" not in event
    assert "error" not in event


@pytest.mark.asyncio
async def test_publish_deliberation_result_includes_result_and_error() -> None:
    """publish_deliberation_result should include result and error when provided."""
    js = _FakeJetStream()
    adapter = adapter_module.NATSPublisherAdapter(jetstream=js)

    result_payload: dict[str, Any] = {"score": 0.9, "proposal": "Use microservices"}

    await adapter.publish_deliberation_result(
        deliberation_id="delib-1",
        task_id="task-1",
        status="failed",
        result=result_payload,
        error="boom",
    )

    assert len(js.published) == 1
    _, payload = js.published[0]

    event = json.loads(payload.decode())
    assert event["status"] == "failed"
    assert event["result"] == result_payload
    assert event["error"] == "boom"


@pytest.mark.asyncio
async def test_publish_deliberation_result_raises_on_publish_error() -> None:
    """publish_deliberation_result should propagate publish errors (critical)."""
    js = _FakeJetStream()
    js.should_fail = True
    adapter = adapter_module.NATSPublisherAdapter(jetstream=js)

    with pytest.raises(RuntimeError, match="publish failed"):
        await adapter.publish_deliberation_result(
            deliberation_id="delib-1",
            task_id="task-1",
            status="completed",
        )

