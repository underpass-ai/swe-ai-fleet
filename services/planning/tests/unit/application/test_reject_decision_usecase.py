"""Unit tests for RejectDecisionUseCase."""

from unittest.mock import AsyncMock

import pytest

from planning.application.usecases import RejectDecisionUseCase
from planning.domain import DecisionId, Reason, StoryId, UserName


@pytest.mark.asyncio
async def test_reject_decision_success():
    """Test successful decision rejection."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    story_id = StoryId("s-001")
    decision_id = DecisionId("d-123")

    await use_case.execute(
        story_id=story_id,
        decision_id=decision_id,
        rejected_by="po-001",
        reason="Design is too complex",
    )

    # Verify event was published with Value Objects
    messaging.publish_decision_rejected.assert_awaited_once_with(
        story_id=story_id,
        decision_id=decision_id,
        rejected_by="po-001",
        reason="Design is too complex",
    )


@pytest.mark.asyncio
async def test_reject_decision_rejects_empty_decision_id():
    """Test that empty decision_id is rejected (by DecisionId validation)."""
    # DecisionId validation fails before use case executes
    with pytest.raises(ValueError, match="DecisionId cannot be empty"):
        DecisionId("")


@pytest.mark.asyncio
async def test_reject_decision_rejects_empty_rejected_by():
    """Test that empty rejected_by is rejected (by UserName validation)."""
    # UserName validation fails before use case executes
    with pytest.raises(ValueError, match="UserName cannot be empty"):
        UserName("")


@pytest.mark.asyncio
async def test_reject_decision_requires_reason():
    """Test that reason is required (by Reason validation)."""
    # Reason validation fails before use case executes
    with pytest.raises(ValueError, match="Reason cannot be empty"):
        Reason("")


@pytest.mark.asyncio
async def test_reject_decision_with_value_objects():
    """Test rejection with all Value Objects (no string stripping needed)."""
    messaging = AsyncMock()
    use_case = RejectDecisionUseCase(messaging=messaging)

    story_id = StoryId("s-001")
    decision_id = DecisionId("d-123")
    rejected_by = UserName("po-001")
    reason = Reason("Too complex")

    await use_case.execute(
        story_id=story_id,
        decision_id=decision_id,
        rejected_by=rejected_by,
        reason=reason,
    )

    messaging.publish_decision_rejected.assert_awaited_once_with(
        story_id=story_id,
        decision_id=decision_id,
        rejected_by=rejected_by,
        reason=reason,
    )
