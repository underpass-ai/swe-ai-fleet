"""Unit tests for DeliberationsCompleteProgressConsumer."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock, patch

import pytest
from core.shared.events.event_envelope import EventEnvelope
from core.shared.events.infrastructure import EventEnvelopeMapper
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.value_objects.actors.user_name import UserName
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.review.agent_deliberation import AgentDeliberation
from planning.domain.value_objects.review.story_review_result import StoryReviewResult
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
    BacklogReviewCeremonyStatusEnum,
)
from planning.domain.value_objects.statuses.backlog_review_role import BacklogReviewRole
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)


def _envelope_json(payload: dict[str, object]) -> str:
    envelope = EventEnvelope(
        event_type="planning.backlog_review.deliberations.complete",
        payload=payload,
        idempotency_key="idemp-test-planning.deliberations.complete",
        correlation_id="corr-test-planning.deliberations.complete",
        timestamp="2025-12-30T10:00:00+00:00",
        producer="planning-tests",
    )
    return json.dumps(EventEnvelopeMapper.to_dict(envelope))


@pytest.fixture
def mock_nats_client():
    """Mock NATS client."""
    return Mock()


@pytest.fixture
def mock_jetstream():
    """Mock JetStream context."""
    return AsyncMock()


@pytest.fixture
def mock_storage():
    """Mock StoragePort."""
    return AsyncMock()


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_storage):
    """Create DeliberationsCompleteProgressConsumer instance."""
    from planning.infrastructure.consumers.deliberations_complete_progress_consumer import (
        DeliberationsCompleteProgressConsumer,
    )

    return DeliberationsCompleteProgressConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        storage=mock_storage,
    )


@pytest.fixture
def ceremony_id():
    """Create test ceremony ID."""
    return BacklogReviewCeremonyId("BRC-12345")


@pytest.fixture
def story_id():
    """Create test story ID."""
    return StoryId("ST-001")


@pytest.fixture
def ceremony_with_all_reviews(ceremony_id, story_id):
    """Create ceremony with all role reviews complete."""
    # Create review result with all 3 roles
    review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=None,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(
            AgentDeliberation(
                agent_id="agent-architect-001",
                role=BacklogReviewRole.ARCHITECT,
                proposal={"content": "Architect proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-qa-001",
                role=BacklogReviewRole.QA,
                proposal={"content": "QA proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-devops-001",
                role=BacklogReviewRole.DEVOPS,
                proposal={"content": "DevOps proposal"},
                deliberated_at=datetime.now(UTC),
            ),
        ),
    )

    return BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(review_result,),
    )


@pytest.mark.asyncio
async def test_handle_message_acks_when_ceremony_not_found(
    consumer, mock_storage, ceremony_id, story_id
):
    """Test that _handle_message() ACKs when ceremony not found."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )
    mock_storage.get_backlog_review_ceremony.return_value = None

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_storage.get_backlog_review_ceremony.assert_awaited_once_with(ceremony_id)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_acks_when_review_result_not_found(
    consumer, mock_storage, ceremony_id, story_id
):
    """Test that _handle_message() ACKs when review result not found."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )

    # Ceremony without review results
    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(),
    )
    mock_storage.get_backlog_review_ceremony.return_value = ceremony

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    # Should not save ceremony (no review result found)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_acks_when_not_all_roles_complete(
    consumer, mock_storage, ceremony_id, story_id
):
    """Test that _handle_message() ACKs when not all roles have deliberations."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )

    # Review result with only ARCHITECT role
    review_result = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=None,
        architect_feedback="Architect feedback",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(
            AgentDeliberation(
                agent_id="agent-architect-001",
                role=BacklogReviewRole.ARCHITECT,
                proposal={"content": "Architect proposal"},
                deliberated_at=datetime.now(UTC),
            ),
        ),
    )

    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id,),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(review_result,),
    )
    mock_storage.get_backlog_review_ceremony.return_value = ceremony

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    # Should not save ceremony (not all roles complete)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_transitions_to_reviewing_when_all_stories_complete(
    consumer, mock_storage, ceremony_with_all_reviews, ceremony_id, story_id
):
    """Test that _handle_message() transitions ceremony to REVIEWING when all stories complete."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )
    mock_storage.get_backlog_review_ceremony.return_value = ceremony_with_all_reviews

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_storage.save_backlog_review_ceremony.assert_awaited_once()
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    assert saved_ceremony.status.is_reviewing()
    assert saved_ceremony.ceremony_id == ceremony_id
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_does_not_transition_when_stories_incomplete(
    consumer, mock_storage, ceremony_id, story_id
):
    """Test that _handle_message() does not transition when other stories incomplete."""
    # Arrange
    story_id_2 = StoryId("ST-002")
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )

    # Ceremony with 2 stories, only first one has all reviews
    review_result_1 = StoryReviewResult(
        story_id=story_id,
        plan_preliminary=None,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(
            AgentDeliberation(
                agent_id="agent-architect-001",
                role=BacklogReviewRole.ARCHITECT,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-qa-001",
                role=BacklogReviewRole.QA,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-devops-001",
                role=BacklogReviewRole.DEVOPS,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
        ),
    )

    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id, story_id_2),  # 2 stories
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(review_result_1,),  # Only 1 story has reviews
    )
    mock_storage.get_backlog_review_ceremony.return_value = ceremony

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.ack.assert_awaited_once()
    # Should not save ceremony (not all stories complete)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_ceremony_id(consumer):
    """Test that _handle_message() NAKs when ceremony_id is missing."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json({"story_id": "ST-001"})

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_story_id(consumer):
    """Test that _handle_message() NAKs when story_id is missing."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json({"ceremony_id": "BRC-12345"})

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_invalid_json(consumer):
    """Test that _handle_message() handles invalid JSON."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    # Make decode return invalid JSON that will cause JSONDecodeError in json.loads()
    mock_msg.data.decode.return_value = "invalid json"

    # Act
    await consumer._handle_message(mock_msg)

    # Assert - JSONDecodeError is a subclass of ValueError, so it's caught and ACKed
    # (not NAKed, because validation errors shouldn't be retried)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_value_error(consumer, mock_storage, ceremony_id):
    """Test that _handle_message() ACKs when ValueError is raised during VO creation."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    # Use valid format IDs but make storage raise ValueError
    # This simulates a ValueError being raised somewhere in the processing
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": "BRC-12345", "story_id": "ST-001"}
    )
    # Make storage.get_backlog_review_ceremony raise ValueError
    mock_storage.get_backlog_review_ceremony.side_effect = ValueError("Storage validation error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert - ValueError is caught in the except ValueError block and ACKed
    # (not NAKed, because validation errors shouldn't be retried)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_storage_error(consumer, mock_storage, ceremony_id, story_id):
    """Test that _handle_message() NAKs when storage raises exception."""
    # Arrange
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = _envelope_json(
        {"ceremony_id": ceremony_id.value, "story_id": story_id.value}
    )
    mock_storage.get_backlog_review_ceremony.side_effect = Exception("Storage error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert
    mock_msg.nak.assert_awaited_once()  # NAK for retry


@pytest.mark.asyncio
async def test_start_creates_subscription_and_starts_polling(consumer, mock_jetstream):
    """Test that start() creates subscription and starts polling task."""
    # Arrange
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    # Act
    await consumer.start()

    # Assert
    mock_jetstream.pull_subscribe.assert_awaited_once()
    assert consumer._polling_task is not None

    # Cleanup
    consumer._polling_task.cancel()
    # Note: We don't await the task here to avoid CancelledError propagation.
    # The task will be properly cleaned up when the test completes.


@pytest.mark.asyncio
async def test_start_raises_exception_on_failure(consumer, mock_jetstream):
    """Test that start() raises exception when subscription fails."""
    # Arrange
    mock_jetstream.pull_subscribe.side_effect = Exception("NATS connection failed")

    # Act & Assert
    with pytest.raises(Exception, match="NATS connection failed"):
        await consumer.start()

    # Assert
    assert consumer._polling_task is None


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(consumer):
    """Test that _poll_messages() handles TimeoutError and continues."""
    # Arrange
    mock_subscription = AsyncMock()
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # Make function properly async
        if call_count == 1:
            raise TimeoutError("No messages")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Act & Assert
    with pytest.raises(asyncio.CancelledError):
        await consumer._poll_messages()

    # Assert
    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_messages_handles_generic_error(consumer):
    """Test that _poll_messages() handles generic errors with backoff."""
    # Arrange
    mock_subscription = AsyncMock()
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # Make function properly async
        if call_count == 1:
            raise ConnectionError("Connection error")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Mock sleep to avoid delays
    with patch(
        "planning.infrastructure.consumers.deliberations_complete_progress_consumer.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        # Act & Assert
        with pytest.raises(asyncio.CancelledError):
            await consumer._poll_messages()

    # Assert
    assert call_count >= 1


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(consumer):
    """Test that stop() cancels the polling task."""
    # Arrange
    async def fake_polling():
        await asyncio.sleep(100)

    consumer._polling_task = asyncio.create_task(fake_polling())

    # Act & Assert
    with pytest.raises(asyncio.CancelledError):
        await consumer.stop()

    # Assert
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_no_polling_task(consumer):
    """Test that stop() handles case where no polling task exists."""
    consumer._polling_task = None

    # Act - Should not raise
    await consumer.stop()

    # Assert
    assert consumer._polling_task is None


def test_all_stories_reviewed_returns_false_when_fewer_results(consumer, ceremony_id):
    """Test that _all_stories_reviewed() returns False when fewer review results than stories."""
    # Arrange
    story_id_1 = StoryId("ST-001")
    story_id_2 = StoryId("ST-002")

    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id_1, story_id_2),  # 2 stories
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(),  # 0 review results
    )

    # Act
    result = consumer._all_stories_reviewed(ceremony)

    # Assert
    assert result is False


def test_all_stories_reviewed_returns_false_when_story_missing_result(consumer, ceremony_id):
    """Test that _all_stories_reviewed() returns False when a story has no review result."""
    # Arrange
    story_id_1 = StoryId("ST-001")
    story_id_2 = StoryId("ST-002")

    # Only one story has a review result
    review_result = StoryReviewResult(
        story_id=story_id_1,
        plan_preliminary=None,
        architect_feedback="Architect feedback",
        qa_feedback="QA feedback",
        devops_feedback="DevOps feedback",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
        agent_deliberations=(
            AgentDeliberation(
                agent_id="agent-architect-001",
                role=BacklogReviewRole.ARCHITECT,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-qa-001",
                role=BacklogReviewRole.QA,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
            AgentDeliberation(
                agent_id="agent-devops-001",
                role=BacklogReviewRole.DEVOPS,
                proposal={"content": "Proposal"},
                deliberated_at=datetime.now(UTC),
            ),
        ),
    )

    ceremony = BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        story_ids=(story_id_1, story_id_2),  # 2 stories
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.IN_PROGRESS),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
        started_at=datetime.now(UTC),
        review_results=(review_result,),  # Only 1 review result
    )

    # Act
    result = consumer._all_stories_reviewed(ceremony)

    # Assert
    assert result is False
