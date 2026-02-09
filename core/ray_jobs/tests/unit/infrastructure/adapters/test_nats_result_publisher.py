"""Unit tests for NATSResultPublisher."""

import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from core.ray_jobs.domain import AgentResult
from core.ray_jobs.infrastructure.adapters.nats_result_publisher import (
    EVENT_TYPE_AGENT_RESPONSE_COMPLETED,
    NATSResultPublisher,
    PRODUCER_RAY_EXECUTOR,
)


def _decode_envelope(payload: bytes) -> tuple[dict, dict]:
    """Decode EventEnvelope and return (envelope, inner payload)."""
    raw = json.loads(payload.decode())
    assert "event_type" in raw
    assert "payload" in raw
    return raw, raw["payload"]


@pytest.fixture
def publisher():
    """Create NATSResultPublisher instance."""
    return NATSResultPublisher(nats_url="nats://localhost:4222")


@pytest.fixture
def success_result():
    """Create success AgentResult."""
    return AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={"content": "Test proposal"},
        model="test-model",
    )


@pytest.fixture
def failure_result():
    """Create failure AgentResult."""
    return AgentResult.failure_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=500,
        error=Exception("Test error"),
        model="test-model",
    )


@pytest.mark.asyncio
async def test_connect_success(publisher):
    """Test successful connection to NATS."""
    # Arrange
    mock_client = AsyncMock()
    mock_js = Mock()

    with patch("nats.connect", return_value=mock_client):
        mock_client.jetstream = Mock(return_value=mock_js)

        # Act
        await publisher.connect()

        # Assert
        assert publisher._client == mock_client
        assert publisher._js == mock_js


@pytest.mark.asyncio
async def test_connect_no_url(publisher):
    """Test that connect skips when no URL provided."""
    # Arrange
    publisher_no_url = NATSResultPublisher(nats_url=None)

    # Act
    await publisher_no_url.connect()

    # Assert
    assert publisher_no_url._client is None
    assert publisher_no_url._js is None


@pytest.mark.asyncio
async def test_close(publisher):
    """Test closing NATS connection."""
    # Arrange
    mock_client = AsyncMock()
    publisher._client = mock_client
    publisher._js = Mock()

    # Act
    await publisher.close()

    # Assert
    mock_client.close.assert_awaited_once()
    assert publisher._client is None
    assert publisher._js is None


@pytest.mark.asyncio
async def test_close_no_client(publisher):
    """Test closing when no client exists."""
    # Arrange
    publisher._client = None

    # Act - should not raise
    await publisher.close()


@pytest.mark.asyncio
async def test_publish_success_standard_event(publisher, success_result):
    """Test publishing success result as standard event."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_success(success_result)

    # Assert
    mock_js.publish.assert_awaited_once()
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.completed"
    envelope, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert envelope["event_type"] == EVENT_TYPE_AGENT_RESPONSE_COMPLETED
    assert envelope["producer"] == PRODUCER_RAY_EXECUTOR
    assert "idempotency_key" in envelope
    assert "correlation_id" in envelope
    assert payload_dict["task_id"] == "task-123"
    assert payload_dict["agent_id"] == "agent-001"


@pytest.mark.asyncio
async def test_publish_success_task_extraction_canonical(publisher):
    """Test publishing task extraction result as canonical event."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 123
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Create task extraction result with proposal
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": '{"tasks": [{"title": "Task 1", "description": "Desc 1", "estimated_hours": 8, "deliberation_indices": [0]}]}'
        },
        model="test-model",
    )

    constraints = {
        "metadata": {
            "task_type": "TASK_EXTRACTION",
            "story_id": "ST-001",
            "ceremony_id": "BRC-12345",
        }
    }

    # Act
    await publisher.publish_success(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints=constraints,
    )

    # Assert
    mock_js.publish.assert_awaited_once()
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.completed.task-extraction"
    envelope, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert envelope["event_type"] == EVENT_TYPE_AGENT_RESPONSE_COMPLETED
    assert payload_dict["task_id"] == "task-123:task-extraction"
    assert payload_dict["story_id"] == "ST-001"
    assert payload_dict["ceremony_id"] == "BRC-12345"
    assert "tasks" in payload_dict
    assert len(payload_dict["tasks"]) == 1


@pytest.mark.asyncio
async def test_publish_success_task_extraction_by_task_type(publisher):
    """Test task extraction detection by metadata.task_type."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": '{"tasks": [{"title": "Task 1", "description": "Desc", "estimated_hours": 8, "deliberation_indices": []}]}'
        },
        model="test-model",
    )

    # Act
    await publisher.publish_success(
        success_result,
        constraints={"metadata": {"task_type": "TASK_EXTRACTION"}},
    )

    # Assert
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.completed.task-extraction"


@pytest.mark.asyncio
async def test_publish_success_backlog_review_role(publisher, success_result):
    """Test publishing backlog review role event."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_success(
        success_result,
        constraints={"metadata": {"task_type": "BACKLOG_REVIEW_ROLE"}},
    )

    # Assert
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.completed.backlog-review.role"


@pytest.mark.asyncio
async def test_publish_success_with_num_agents(publisher, success_result):
    """Test publishing with num_agents."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_success(success_result, num_agents=3)

    # Assert
    call_args = mock_js.publish.call_args
    _, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert payload_dict["num_agents"] == 3


@pytest.mark.asyncio
async def test_publish_success_with_original_task_id(publisher, success_result):
    """Test publishing with original_task_id."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_success(
        success_result,
        original_task_id="original-task-123",
    )

    # Assert
    call_args = mock_js.publish.call_args
    _, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert payload_dict["task_id"] == "original-task-123"


@pytest.mark.asyncio
async def test_publish_success_no_nats_url(publisher, success_result):
    """Test that publish skips when no NATS URL."""
    # Arrange
    publisher_no_url = NATSResultPublisher(nats_url=None)

    # Act - should not raise
    await publisher_no_url.publish_success(success_result)


@pytest.mark.asyncio
async def test_publish_success_auto_connect(publisher, success_result):
    """Test that publish auto-connects if not connected."""
    # Arrange
    mock_client = AsyncMock()
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)

    with patch("nats.connect", return_value=mock_client):
        mock_client.jetstream = Mock(return_value=mock_js)

        # Act
        await publisher.publish_success(success_result)

        # Assert
        mock_js.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_success_connection_failure(publisher, success_result):
    """Test that publish handles connection failure gracefully."""
    # Arrange
    with patch("nats.connect", side_effect=Exception("Connection failed")):
        # Act - should not raise, just return
        await publisher.publish_success(success_result)


@pytest.mark.asyncio
async def test_publish_success_exception_handling(publisher, success_result):
    """Test that publish handles exceptions."""
    # Arrange
    mock_js = AsyncMock()
    mock_js.publish = AsyncMock(side_effect=Exception("Publish failed"))
    publisher._js = mock_js

    # Act & Assert
    with pytest.raises(Exception, match="Publish failed"):
        await publisher.publish_success(success_result)


@pytest.mark.asyncio
async def test_publish_success_task_extraction_invalid_json(publisher):
    """Test task extraction with invalid JSON in proposal."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": "Invalid JSON content"
        },
        model="test-model",
    )

    constraints = {
        "metadata": {
            "task_type": "TASK_EXTRACTION",
            "story_id": "ST-001",
            "ceremony_id": "BRC-12345",
        }
    }

    # Act
    await publisher.publish_success(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints=constraints,
    )

    # Assert - should still publish with empty tasks array (inside envelope)
    call_args = mock_js.publish.call_args
    _, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert payload_dict["tasks"] == []


@pytest.mark.asyncio
async def test_publish_failure(publisher, failure_result):
    """Test publishing failure result."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_ack.stream = "test-stream"
    mock_ack.seq = 456
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_failure(failure_result)

    # Assert
    mock_js.publish.assert_awaited_once()
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.failed"
    envelope, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert envelope["event_type"] == "agent.response.failed"
    assert envelope["producer"] == PRODUCER_RAY_EXECUTOR
    assert "idempotency_key" in envelope
    assert "correlation_id" in envelope
    assert payload_dict["task_id"] == "task-123"
    assert payload_dict["status"] == "failed"
    assert payload_dict["error"] is not None


@pytest.mark.asyncio
async def test_publish_failure_with_num_agents(publisher, failure_result):
    """Test publishing failure with num_agents."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_failure(failure_result, num_agents=3)

    # Assert
    call_args = mock_js.publish.call_args
    _, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert payload_dict["num_agents"] == 3


@pytest.mark.asyncio
async def test_publish_failure_with_original_task_id(publisher, failure_result):
    """Test publishing failure with original_task_id."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    # Act
    await publisher.publish_failure(failure_result, original_task_id="original-task-123")

    # Assert
    call_args = mock_js.publish.call_args
    _, payload_dict = _decode_envelope(call_args.kwargs["payload"])
    assert payload_dict["metadata"]["task_id"] == "original-task-123"


@pytest.mark.asyncio
async def test_publish_failure_no_nats_url(publisher, failure_result):
    """Test that publish_failure skips when no NATS URL."""
    # Arrange
    publisher_no_url = NATSResultPublisher(nats_url=None)

    # Act - should not raise
    await publisher_no_url.publish_failure(failure_result)


@pytest.mark.asyncio
async def test_publish_failure_auto_connect(publisher, failure_result):
    """Test that publish_failure auto-connects if not connected."""
    # Arrange
    mock_client = AsyncMock()
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)

    with patch("nats.connect", return_value=mock_client):
        mock_client.jetstream = Mock(return_value=mock_js)

        # Act
        await publisher.publish_failure(failure_result)

        # Assert
        mock_js.publish.assert_awaited_once()


@pytest.mark.asyncio
async def test_publish_failure_exception_handling(publisher, failure_result):
    """Test that publish_failure handles exceptions."""
    # Arrange
    mock_js = AsyncMock()
    mock_js.publish = AsyncMock(side_effect=Exception("Publish failed"))
    publisher._js = mock_js

    # Act & Assert
    with pytest.raises(Exception, match="Publish failed"):
        await publisher.publish_failure(failure_result)


@pytest.mark.asyncio
async def test_determine_subject_task_extraction(publisher):
    """Test subject determination for task extraction."""
    # Act
    subject = publisher._determine_subject("TASK_EXTRACTION")

    # Assert
    assert subject == "agent.response.completed.task-extraction"


@pytest.mark.asyncio
async def test_determine_subject_backlog_review_role(publisher):
    """Test subject determination for backlog review role."""
    # Act
    subject = publisher._determine_subject("BACKLOG_REVIEW_ROLE")

    # Assert
    assert subject == "agent.response.completed.backlog-review.role"


@pytest.mark.asyncio
async def test_determine_subject_default(publisher):
    """Test default subject determination."""
    # Act
    subject = publisher._determine_subject("TASK_DERIVATION")

    # Assert
    assert subject == "agent.response.completed"


@pytest.mark.asyncio
async def test_determine_subject_none(publisher):
    """Test subject determination with None task_type."""
    # Act
    subject = publisher._determine_subject(None)

    # Assert
    assert subject == "agent.response.completed"


@pytest.mark.asyncio
async def test_determine_subject_backlog_review_from_task_type(publisher):
    """Test task_type routes backlog review role events to canonical subject."""
    # Act
    subject = publisher._determine_subject("BACKLOG_REVIEW_ROLE")

    # Assert
    assert subject == "agent.response.completed.backlog-review.role"


@pytest.mark.asyncio
async def test_publish_success_backlog_review_semantic_fallback(publisher):
    """Test publishing backlog review event based on task_type."""
    # Arrange
    mock_js = AsyncMock()
    mock_ack = Mock()
    mock_js.publish = AsyncMock(return_value=mock_ack)
    publisher._js = mock_js

    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="ray-job-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={"content": "Architect review"},
        model="test-model",
    )
    constraints = {
        "metadata": {
            "task_type": "BACKLOG_REVIEW_ROLE",
        }
    }

    # Act
    await publisher.publish_success(
        success_result,
        constraints=constraints,
    )

    # Assert
    call_args = mock_js.publish.call_args
    assert call_args.kwargs["subject"] == "agent.response.completed.backlog-review.role"


@pytest.mark.asyncio
async def test_is_task_extraction_by_task_id(publisher):
    """Test task extraction detection by task_type."""
    # Act
    is_task_extraction = publisher._is_task_extraction("TASK_EXTRACTION", None)

    # Assert
    assert is_task_extraction is True


@pytest.mark.asyncio
async def test_is_task_extraction_by_metadata(publisher):
    """Test task extraction detection by metadata."""
    # Arrange
    constraints = {
        "metadata": {
            "task_type": "TASK_EXTRACTION",
        }
    }

    # Act
    task_type = publisher._extract_task_type(constraints)
    is_task_extraction = publisher._is_task_extraction(task_type, constraints)

    # Assert
    assert is_task_extraction is True


@pytest.mark.asyncio
async def test_is_task_extraction_false(publisher):
    """Test task extraction detection returns False for non-extraction."""
    # Arrange
    constraints = {
        "metadata": {
            "task_type": "OTHER",
        }
    }

    # Act
    task_type = publisher._extract_task_type(constraints)
    is_task_extraction = publisher._is_task_extraction(task_type, constraints)

    # Assert
    assert is_task_extraction is False


@pytest.mark.asyncio
async def test_log_llm_response_with_dict_proposal(publisher):
    """Test logging LLM response with dict proposal."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": "Test content"
        },
        model="test-model",
    )

    # Act - should not raise
    publisher._log_llm_response(success_result)


@pytest.mark.asyncio
async def test_log_llm_response_with_string_proposal(publisher):
    """Test logging LLM response with string proposal."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal="Test content",  # String proposal
        model="test-model",
    )

    # Act - should not raise
    publisher._log_llm_response(success_result)


@pytest.mark.asyncio
async def test_log_llm_response_no_proposal(publisher):
    """Test logging LLM response with no proposal."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal=None,
        model="test-model",
    )

    # Act - should not raise
    publisher._log_llm_response(success_result)

@pytest.mark.asyncio
async def test_build_canonical_task_extraction_event_with_proposal_string(publisher):
    """Test building canonical event when proposal is a string."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    # Note: AgentResult.proposal is dict[str, Any] | None, not str
    # So we use dict with content as string
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": '{"tasks": [{"title": "Task 1"}]}'
        },
        model="test-model",
    )

    # Act
    event = publisher._build_canonical_task_extraction_event(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints={
            "metadata": {
                "story_id": "ST-001",
                "ceremony_id": "BRC-12345",
            }
        },
    )

    # Assert
    assert event["task_id"] == "task-123:task-extraction"
    assert event["story_id"] == "ST-001"
    assert event["ceremony_id"] == "BRC-12345"
    assert len(event["tasks"]) == 1

@pytest.mark.asyncio
async def test_build_canonical_task_extraction_event_no_proposal(publisher):
    """Test building canonical event when proposal is None."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal=None,
        model="test-model",
    )

    # Act
    event = publisher._build_canonical_task_extraction_event(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints=None,
    )

    # Assert
    assert event["tasks"] == []
    assert event["task_id"] == "task-123:task-extraction"

@pytest.mark.asyncio
async def test_build_canonical_task_extraction_event_no_metadata(publisher):
    """Test building canonical event when constraints has no metadata."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": '{"tasks": []}'
        },
        model="test-model",
    )

    # Act
    event = publisher._build_canonical_task_extraction_event(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints={},  # No metadata
    )

    # Assert
    assert event["story_id"] is None
    assert event["ceremony_id"] is None

@pytest.mark.asyncio
async def test_build_canonical_task_extraction_event_non_dict_constraints(publisher):
    """Test building canonical event when constraints is not a dict."""
    # Arrange
    from core.ray_jobs.domain import AgentResult
    success_result = AgentResult.success_result(
        task_id="task-123",
        agent_id="agent-001",
        role="ARCHITECT",
        duration_ms=1000,
        proposal={
            "content": '{"tasks": []}'
        },
        model="test-model",
    )

    # Act
    event = publisher._build_canonical_task_extraction_event(
        success_result,
        original_task_id="task-123:task-extraction",
        constraints="not a dict",  # Invalid type
    )

    # Assert
    assert event["story_id"] is None
    assert event["ceremony_id"] is None

@pytest.mark.asyncio
async def test_build_result_dict_with_original_task_id(publisher, success_result):
    """Test building result dict with original_task_id."""
    # Act
    result_dict, task_id = publisher._build_result_dict(
        success_result,
        num_agents=3,
        original_task_id="original-task-123",
        constraints=None,
    )

    # Assert
    assert task_id == "original-task-123"
    assert result_dict["task_id"] == "original-task-123"
    assert result_dict["num_agents"] == 3

@pytest.mark.asyncio
async def test_build_result_dict_with_constraints(publisher, success_result):
    """Test building result dict with constraints."""
    # Arrange
    constraints = {"metadata": {"key": "value"}}

    # Act
    result_dict, _ = publisher._build_result_dict(
        success_result,
        num_agents=None,
        original_task_id=None,
        constraints=constraints,
    )

    # Assert
    assert result_dict["constraints"] == constraints

@pytest.mark.asyncio
async def test_ensure_connected_already_connected(publisher):
    """Test _ensure_connected when already connected."""
    # Arrange
    mock_js = Mock()
    publisher._js = mock_js
    publisher.nats_url = "nats://localhost:4222"

    # Act
    result = await publisher._ensure_connected()

    # Assert
    assert result is True

@pytest.mark.asyncio
async def test_ensure_connected_no_url(publisher):
    """Test _ensure_connected when no NATS URL."""
    # Arrange
    publisher.nats_url = None

    # Act
    result = await publisher._ensure_connected()

    # Assert
    assert result is False

@pytest.mark.asyncio
async def test_ensure_connected_auto_connect_success(publisher):
    """Test _ensure_connected auto-connects successfully."""
    # Arrange
    publisher.nats_url = "nats://localhost:4222"
    publisher._js = None

    mock_client = AsyncMock()
    mock_js = Mock()
    with patch("nats.connect", return_value=mock_client):
        mock_client.jetstream = Mock(return_value=mock_js)

        # Act
        result = await publisher._ensure_connected()

        # Assert
        assert result is True
        assert publisher._js == mock_js

@pytest.mark.asyncio
async def test_ensure_connected_auto_connect_failure(publisher):
    """Test _ensure_connected handles connection failure."""
    # Arrange
    publisher.nats_url = "nats://localhost:4222"
    publisher._js = None

    with patch("nats.connect", side_effect=Exception("Connection failed")):
        # Act
        result = await publisher._ensure_connected()

        # Assert
        assert result is False

@pytest.mark.asyncio
async def test_ensure_connected_js_none_after_connect(publisher):
    """Test _ensure_connected when _js is None after connect."""
    # Arrange
    publisher.nats_url = "nats://localhost:4222"
    publisher._js = None

    mock_client = AsyncMock()
    mock_client.jetstream = Mock(return_value=None)  # Returns None
    with patch("nats.connect", return_value=mock_client):
        # Act
        result = await publisher._ensure_connected()

        # Assert
        assert result is False
