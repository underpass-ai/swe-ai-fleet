"""Unit tests for ApproveDecisionUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.usecases import ApproveDecisionUseCase
from planning.domain import StoryId


@pytest.mark.asyncio
async def test_approve_decision_success():
    """Test successful decision approval."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    await use_case.execute(
        story_id=StoryId("s-001"),
        decision_id="d-123",
        approved_by="po-001",
        comment="Looks good!",
    )

    # Verify event was published
    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id="s-001",
        decision_id="d-123",
        approved_by="po-001",
        comment="Looks good!",
    )


@pytest.mark.asyncio
async def test_approve_decision_without_comment():
    """Test approval without optional comment."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    await use_case.execute(
        story_id=StoryId("s-001"),
        decision_id="d-123",
        approved_by="po-001",
        comment=None,
    )

    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id="s-001",
        decision_id="d-123",
        approved_by="po-001",
        comment=None,
    )


@pytest.mark.asyncio
async def test_approve_decision_rejects_empty_decision_id():
    """Test that empty decision_id is rejected."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    with pytest.raises(ValueError, match="decision_id cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            decision_id="",
            approved_by="po",
        )


@pytest.mark.asyncio
async def test_approve_decision_rejects_empty_approved_by():
    """Test that empty approved_by is rejected."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    with pytest.raises(ValueError, match="approved_by cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            decision_id="d-123",
            approved_by="",
        )


@pytest.mark.asyncio
async def test_approve_decision_strips_whitespace():
    """Test that whitespace is stripped."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    await use_case.execute(
        story_id=StoryId("s-001"),
        decision_id="  d-123  ",
        approved_by="  po-001  ",
        comment="  Great!  ",
    )

    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id="s-001",
        decision_id="d-123",
        approved_by="po-001",
        comment="Great!",
    )

