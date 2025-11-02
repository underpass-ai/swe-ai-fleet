"""Unit tests for RejectDecisionUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.usecases import RejectDecisionUseCase
from planning.domain import StoryId


@pytest.mark.asyncio
async def test_reject_decision_success():
    """Test successful decision rejection."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    await use_case.execute(
        story_id=StoryId("s-001"),
        decision_id="d-123",
        rejected_by="po-001",
        reason="Design is too complex",
    )

    # Verify event was published
    messaging.publish_decision_rejected.assert_awaited_once_with(
        story_id="s-001",
        decision_id="d-123",
        rejected_by="po-001",
        reason="Design is too complex",
    )


@pytest.mark.asyncio
async def test_reject_decision_rejects_empty_decision_id():
    """Test that empty decision_id is rejected."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    with pytest.raises(ValueError, match="decision_id cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            decision_id="",
            rejected_by="po",
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_reject_decision_rejects_empty_rejected_by():
    """Test that empty rejected_by is rejected."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    with pytest.raises(ValueError, match="rejected_by cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            decision_id="d-123",
            rejected_by="",
            reason="Reason",
        )


@pytest.mark.asyncio
async def test_reject_decision_requires_reason():
    """Test that reason is required (not optional)."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    with pytest.raises(ValueError, match="rejection reason cannot be empty"):
        await use_case.execute(
            story_id=StoryId("s-001"),
            decision_id="d-123",
            rejected_by="po",
            reason="",
        )


@pytest.mark.asyncio
async def test_reject_decision_strips_whitespace():
    """Test that whitespace is stripped."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    await use_case.execute(
        story_id=StoryId("s-001"),
        decision_id="  d-123  ",
        rejected_by="  po-001  ",
        reason="  Too complex  ",
    )

    messaging.publish_decision_rejected.assert_awaited_once_with(
        story_id="s-001",
        decision_id="d-123",
        rejected_by="po-001",
        reason="Too complex",
    )

