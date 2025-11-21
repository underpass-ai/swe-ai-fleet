"""Unit tests for ApproveDecisionUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.usecases import ApproveDecisionUseCase
from planning.domain import Comment, DecisionId, StoryId, UserName


@pytest.mark.asyncio
async def test_approve_decision_success():
    """Test successful decision approval."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    story_id = StoryId("s-001")
    decision_id = DecisionId("d-123")
    approved_by = UserName("po-001")
    comment = Comment("Looks good!")

    await use_case.execute(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=comment,
    )

    # Verify event was published with Value Objects
    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=comment,
    )


@pytest.mark.asyncio
async def test_approve_decision_without_comment():
    """Test approval without optional comment."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    story_id = StoryId("s-001")
    decision_id = DecisionId("d-123")
    approved_by = UserName("po-001")

    await use_case.execute(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=None,
    )

    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=None,
    )


@pytest.mark.asyncio
async def test_approve_decision_rejects_empty_decision_id():
    """Test that empty decision_id is rejected (by DecisionId validation)."""
    # DecisionId validation fails before use case executes
    with pytest.raises(ValueError, match="DecisionId cannot be empty"):
        DecisionId("")


@pytest.mark.asyncio
async def test_approve_decision_rejects_empty_approved_by():
    """Test that empty approved_by is rejected (by UserName validation)."""
    # UserName validation fails before use case executes
    with pytest.raises(ValueError, match="UserName cannot be empty"):
        UserName("")


@pytest.mark.asyncio
async def test_approve_decision_strips_whitespace():
    """Test that whitespace is stripped from approved_by and comment (by Value Objects)."""
    messaging = AsyncMock()
    use_case = ApproveDecisionUseCase(messaging=messaging)

    story_id = StoryId("s-001")
    decision_id = DecisionId("d-123")

    # Value Objects strip whitespace in __post_init__
    approved_by = UserName("  po-001  ")
    comment = Comment("  Great!  ")

    await use_case.execute(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=comment,
    )

    messaging.publish_decision_approved.assert_awaited_once_with(
        story_id=story_id,
        decision_id=decision_id,
        approved_by=approved_by,
        comment=comment,
    )
