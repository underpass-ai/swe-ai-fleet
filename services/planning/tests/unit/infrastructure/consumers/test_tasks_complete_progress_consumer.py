"""Unit tests for TasksCompleteProgressConsumer."""

import asyncio
import json
from datetime import UTC, datetime
from unittest.mock import AsyncMock, Mock

import pytest
from planning.domain.entities.backlog_review_ceremony import BacklogReviewCeremony
from planning.domain.entities.task import Task
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.identifiers.task_id import TaskId
from planning.domain.value_objects.review.story_review_result import (
    StoryReviewResult,
)
from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
    BacklogReviewCeremonyStatus,
)
from planning.domain.value_objects.statuses.review_approval_status import (
    ReviewApprovalStatus,
    ReviewApprovalStatusEnum,
)
from planning.domain.value_objects.statuses.task_status import TaskStatus
from planning.domain.value_objects.statuses.task_type import TaskType
from planning.infrastructure.consumers.tasks_complete_progress_consumer import (
    TasksCompleteProgressConsumer,
)


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
    """Mock Storage port."""
    return AsyncMock()


@pytest.fixture
def consumer(mock_nats_client, mock_jetstream, mock_storage):
    """Create TasksCompleteProgressConsumer instance."""
    return TasksCompleteProgressConsumer(
        nats_client=mock_nats_client,
        jetstream=mock_jetstream,
        storage=mock_storage,
    )


@pytest.fixture
def ceremony_id():
    """Sample ceremony ID."""
    return BacklogReviewCeremonyId("BRC-123")


@pytest.fixture
def story_id_1():
    """Sample story ID 1."""
    return StoryId("s-001")


@pytest.fixture
def story_id_2():
    """Sample story ID 2."""
    return StoryId("s-002")


@pytest.fixture
def approved_review_result(story_id_1):
    """Review result with APPROVED status."""
    from planning.domain.value_objects.actors.user_name import UserName

    return StoryReviewResult(
        story_id=story_id_1,
        plan_preliminary=None,
        architect_feedback="",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.APPROVED),
        reviewed_at=datetime.now(UTC),
        approved_by=UserName("po@example.com"),
        approved_at=datetime.now(UTC),
        po_notes="Approved",
    )


@pytest.fixture
def rejected_review_result(story_id_2):
    """Review result with REJECTED status."""
    # Create a pending result first, then reject it
    pending = StoryReviewResult(
        story_id=story_id_2,
        plan_preliminary=None,
        architect_feedback="",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
    )

    # reject() method doesn't take parameters - it just changes status
    return pending.reject()


@pytest.fixture
def pending_review_result(story_id_1):
    """Review result with PENDING status."""
    return StoryReviewResult(
        story_id=story_id_1,
        plan_preliminary=None,
        architect_feedback="",
        qa_feedback="",
        devops_feedback="",
        recommendations=(),
        approval_status=ReviewApprovalStatus(ReviewApprovalStatusEnum.PENDING),
        reviewed_at=datetime.now(UTC),
    )


@pytest.fixture
def reviewing_ceremony(ceremony_id, story_id_1, story_id_2, approved_review_result, rejected_review_result):
    """Ceremony in REVIEWING status with all reviews decided."""
    from planning.domain.value_objects.actors.user_name import UserName
    from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
        BacklogReviewCeremonyStatusEnum,
    )

    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        created_at=now,
        updated_at=now,
        story_ids=(story_id_1, story_id_2),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        review_results=(approved_review_result, rejected_review_result),
        started_at=now,  # Required for REVIEWING status
    )


@pytest.fixture
def reviewing_ceremony_with_pending(ceremony_id, story_id_1, story_id_2, approved_review_result, pending_review_result):
    """Ceremony in REVIEWING status with some reviews pending."""
    from planning.domain.value_objects.actors.user_name import UserName
    from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
        BacklogReviewCeremonyStatusEnum,
    )

    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        created_at=now,
        updated_at=now,
        story_ids=(story_id_1, story_id_2),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.REVIEWING),
        review_results=(approved_review_result, pending_review_result),
        started_at=now,  # Required for REVIEWING status
    )


@pytest.fixture
def completed_ceremony(ceremony_id, story_id_1, story_id_2, approved_review_result, rejected_review_result):
    """Ceremony in COMPLETED status."""
    from planning.domain.value_objects.actors.user_name import UserName
    from planning.domain.value_objects.statuses.backlog_review_ceremony_status import (
        BacklogReviewCeremonyStatusEnum,
    )

    now = datetime.now(UTC)
    return BacklogReviewCeremony(
        ceremony_id=ceremony_id,
        created_by=UserName("po@example.com"),
        created_at=now,
        updated_at=now,
        story_ids=(story_id_1, story_id_2),
        status=BacklogReviewCeremonyStatus(BacklogReviewCeremonyStatusEnum.COMPLETED),
        review_results=(approved_review_result, rejected_review_result),
        started_at=now,
        completed_at=now,
    )


@pytest.fixture
def sample_task(story_id_1):
    """Sample task."""
    return Task(
        task_id=TaskId("t-001"),
        story_id=story_id_1,
        title="Test task",
        description="Test description",
        status=TaskStatus.TODO,
        type=TaskType.DEVELOPMENT,
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


@pytest.mark.asyncio
async def test_handle_message_auto_completes_ceremony_when_all_conditions_met(
    consumer, mock_storage, ceremony_id, story_id_1, reviewing_ceremony, sample_task
):
    """Test that ceremony is auto-completed when all conditions are met."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage to return ceremony and tasks for all stories
    mock_storage.get_backlog_review_ceremony.return_value = reviewing_ceremony
    mock_storage.list_tasks.return_value = [sample_task]  # All stories have tasks
    mock_storage.save_backlog_review_ceremony.return_value = None

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Ceremony was saved (auto-completed)
    mock_storage.save_backlog_review_ceremony.assert_awaited_once()
    saved_ceremony = mock_storage.save_backlog_review_ceremony.call_args[0][0]
    assert saved_ceremony.status.is_completed()
    assert saved_ceremony.completed_at is not None

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_does_not_auto_complete_when_story_has_no_tasks(
    consumer, mock_storage, ceremony_id, story_id_1, reviewing_ceremony
):
    """Test that ceremony is NOT auto-completed when a story has no tasks."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage: ceremony exists, but one story has no tasks
    mock_storage.get_backlog_review_ceremony.return_value = reviewing_ceremony
    # First story has tasks, second story has no tasks
    call_count = 0
    async def list_tasks_side_effect(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return [Mock()]  # First story has tasks
        return []  # Second story has no tasks
    mock_storage.list_tasks.side_effect = list_tasks_side_effect

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Ceremony was NOT saved (not auto-completed)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_does_not_auto_complete_when_reviews_pending(
    consumer, mock_storage, ceremony_id, story_id_1, reviewing_ceremony_with_pending, sample_task
):
    """Test that ceremony is NOT auto-completed when some reviews are pending."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage: ceremony exists with pending reviews, all stories have tasks
    mock_storage.get_backlog_review_ceremony.return_value = reviewing_ceremony_with_pending
    mock_storage.list_tasks.return_value = [sample_task]  # All stories have tasks

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Ceremony was NOT saved (not auto-completed)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_does_not_auto_complete_when_ceremony_not_reviewing(
    consumer, mock_storage, ceremony_id, story_id_1, completed_ceremony, sample_task
):
    """Test that ceremony is NOT auto-completed when not in REVIEWING status."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage: ceremony exists but is already COMPLETED
    mock_storage.get_backlog_review_ceremony.return_value = completed_ceremony
    mock_storage.list_tasks.return_value = [sample_task]

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Ceremony was NOT saved (already completed)
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()

    # Assert: Message ACKed
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_ceremony_id(consumer, mock_storage):
    """Test that message is NAKed when ceremony_id is missing."""
    # Arrange: Create mock message without ceremony_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "story_id": "s-001",
        "tasks_created": 5,
    })

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed
    mock_msg.nak.assert_awaited_once()
    mock_msg.ack.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_missing_story_id(consumer, mock_storage):
    """Test that message is NAKed when story_id is missing."""
    # Arrange: Create mock message without story_id
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": "BRC-123",
        "tasks_created": 5,
    })

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed
    mock_msg.nak.assert_awaited_once()
    mock_msg.ack.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_ceremony_not_found(consumer, mock_storage, ceremony_id, story_id_1):
    """Test that message is ACKed when ceremony is not found."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage: ceremony not found
    mock_storage.get_backlog_review_ceremony.return_value = None

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (don't retry if ceremony doesn't exist)
    mock_msg.ack.assert_awaited_once()
    mock_storage.save_backlog_review_ceremony.assert_not_awaited()


@pytest.mark.asyncio
async def test_handle_message_handles_validation_error(consumer, mock_storage):
    """Test that message is ACKed when validation error occurs."""
    # Arrange: Create mock message with valid IDs but storage raises ValueError
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": "BRC-123",
        "story_id": "s-001",
        "tasks_created": 5,
    })

    # Mock storage to raise ValueError during get (domain validation error)
    # This happens when creating BacklogReviewCeremonyId or StoryId fails
    mock_storage.get_backlog_review_ceremony.side_effect = ValueError("Invalid ceremony_id")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message ACKed (don't retry validation errors)
    mock_msg.ack.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_handles_generic_exception(consumer, mock_storage, ceremony_id, story_id_1):
    """Test that message is NAKed when generic exception occurs."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage to raise generic exception
    mock_storage.get_backlog_review_ceremony.side_effect = Exception("Unexpected error")

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: Message NAKed (retry on unexpected errors)
    mock_msg.nak.assert_awaited_once()


@pytest.mark.asyncio
async def test_handle_message_checks_all_stories_for_tasks(
    consumer, mock_storage, ceremony_id, story_id_1, reviewing_ceremony, sample_task
):
    """Test that all stories are checked for tasks before auto-completing."""
    # Arrange: Create mock message
    mock_msg = AsyncMock()
    mock_msg.data = Mock()
    mock_msg.data.decode.return_value = json.dumps({
        "ceremony_id": ceremony_id.value,
        "story_id": story_id_1.value,
        "tasks_created": 5,
    })

    # Mock storage: ceremony exists, all stories have tasks
    mock_storage.get_backlog_review_ceremony.return_value = reviewing_ceremony
    mock_storage.list_tasks.return_value = [sample_task]
    mock_storage.save_backlog_review_ceremony.return_value = None

    # Act
    await consumer._handle_message(mock_msg)

    # Assert: list_tasks was called for each story in the ceremony
    assert mock_storage.list_tasks.await_count == len(reviewing_ceremony.story_ids)

    # Verify calls were made with correct story_ids
    call_args_list = [call[1]["story_id"] for call in mock_storage.list_tasks.await_args_list]
    assert all(story_id in call_args_list for story_id in reviewing_ceremony.story_ids)


@pytest.mark.asyncio
async def test_handle_message_logs_auto_complete_conditions(
    consumer, mock_storage, ceremony_id, story_id_1, reviewing_ceremony_with_pending, sample_task, caplog
):
    """Test that auto-complete conditions are logged when not met."""
    import logging

    # Set logging level to INFO to capture log messages
    with caplog.at_level(logging.INFO):
        # Arrange: Create mock message
        mock_msg = AsyncMock()
        mock_msg.data = Mock()
        mock_msg.data.decode.return_value = json.dumps({
            "ceremony_id": ceremony_id.value,
            "story_id": story_id_1.value,
            "tasks_created": 5,
        })

        # Mock storage: ceremony exists with pending reviews, all stories have tasks
        mock_storage.get_backlog_review_ceremony.return_value = reviewing_ceremony_with_pending
        mock_storage.list_tasks.return_value = [sample_task]

        # Act
        await consumer._handle_message(mock_msg)

        # Assert: Log message about conditions not being met
        assert "not ready for auto-complete" in caplog.text
        assert "all_stories_have_tasks=True" in caplog.text
        assert "all_reviews_decided=False" in caplog.text


@pytest.mark.asyncio
async def test_start_creates_subscription_and_starts_polling(consumer, mock_jetstream):
    """Test that start() creates subscription and starts polling task."""
    # Arrange: Mock subscription
    mock_subscription = AsyncMock()
    mock_jetstream.pull_subscribe.return_value = mock_subscription

    # Act: Use timeout to prevent hanging
    try:
        await asyncio.wait_for(consumer.start(), timeout=5.0)
    except TimeoutError:
        pytest.fail("test_start_creates_subscription_and_starts_polling timed out after 5 seconds")

    # Assert: Subscription created
    mock_jetstream.pull_subscribe.assert_awaited_once()

    # Assert: Polling task created
    assert consumer._polling_task is not None

    # Cleanup: Cancel task to avoid hanging
    consumer._polling_task.cancel()
    try:
        await asyncio.wait_for(consumer._polling_task, timeout=1.0)
    except (TimeoutError, asyncio.CancelledError):
        pass


@pytest.mark.asyncio
async def test_start_raises_exception_on_failure(consumer, mock_jetstream):
    """Test that start() raises exception when subscription fails."""
    # Arrange: Mock subscription to raise exception
    mock_jetstream.pull_subscribe.side_effect = Exception("NATS connection failed")

    # Act & Assert: Exception is raised
    with pytest.raises(Exception, match="NATS connection failed"):
        await consumer.start()


@pytest.mark.asyncio
async def test_stop_cancels_polling_task(consumer):
    """Test that stop() cancels polling task."""
    # Arrange: Create a real task that will be cancelled
    async def dummy_task():
        await asyncio.sleep(10)  # Long sleep to simulate polling

    consumer._polling_task = asyncio.create_task(dummy_task())

    # Act: Use timeout to prevent hanging
    try:
        await asyncio.wait_for(consumer.stop(), timeout=2.0)
    except (TimeoutError, asyncio.CancelledError):
        # CancelledError is expected when task is cancelled
        pass

    # Assert: Task was cancelled (no exception raised)
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_stop_handles_cancelled_error(consumer):
    """Test that stop() handles CancelledError properly."""
    # Arrange: Create a real task that will be cancelled
    async def dummy_task():
        await asyncio.sleep(10)

    consumer._polling_task = asyncio.create_task(dummy_task())

    # Act: stop() re-raises CancelledError, so we expect it
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(consumer.stop(), timeout=2.0)

    # Assert: Task was cancelled
    assert consumer._polling_task.cancelled()


@pytest.mark.asyncio
async def test_poll_messages_handles_timeout(consumer):
    """Test that _poll_messages() handles TimeoutError gracefully."""
    # Arrange: Mock subscription to raise TimeoutError, then CancelledError to break loop
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

    # Act & Assert: Should raise CancelledError after handling timeout
    with pytest.raises(asyncio.CancelledError):
        await asyncio.wait_for(consumer._poll_messages(), timeout=3.0)

    # Assert: Fetch was called multiple times (timeout handled, loop continued)
    assert call_count >= 2


@pytest.mark.asyncio
async def test_poll_messages_handles_generic_error(consumer):
    """Test that _poll_messages() handles generic exceptions."""
    # Arrange: Mock subscription to raise generic exception, then CancelledError to break loop
    mock_subscription = AsyncMock()
    call_count = 0

    async def mock_fetch(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        await asyncio.sleep(0)  # Make function properly async
        if call_count == 1:
            raise Exception("Unexpected error")
        else:
            raise asyncio.CancelledError()  # Break loop

    mock_subscription.fetch = mock_fetch
    consumer._subscription = mock_subscription

    # Arrange: Mock sleep to avoid delays
    from unittest.mock import patch

    with patch(
        "planning.infrastructure.consumers.tasks_complete_progress_consumer.asyncio.sleep",
        new_callable=AsyncMock,
    ):
        # Act & Assert: Should raise CancelledError after handling error
        with pytest.raises(asyncio.CancelledError):
            await asyncio.wait_for(consumer._poll_messages(), timeout=3.0)

    # Assert: Fetch was called (error handled)
    assert call_count >= 1

