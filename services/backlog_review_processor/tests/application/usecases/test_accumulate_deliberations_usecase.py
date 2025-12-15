"""Unit tests for AccumulateDeliberationsUseCase."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backlog_review_processor.application.usecases.accumulate_deliberations_usecase import (
    AccumulateDeliberationsUseCase,
)
from backlog_review_processor.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from backlog_review_processor.domain.value_objects.identifiers.story_id import StoryId
from backlog_review_processor.domain.value_objects.nats_subject import NATSSubject
from backlog_review_processor.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


class MockMessagingPort:
    """Mock implementation of MessagingPort."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.published_events: list[tuple[str, dict]] = []

    def publish_event(self, subject: str, payload: dict) -> None:
        """Mock publish event."""
        self.published_events.append((subject, payload))


class MockStoragePort:
    """Mock implementation of StoragePort."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.saved_deliberations: list[tuple[BacklogReviewCeremonyId, StoryId, dict]] = []

    def save_agent_deliberation(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        deliberation: object,  # AgentDeliberation
    ) -> None:
        """Mock save deliberation."""
        self.saved_deliberations.append((ceremony_id, story_id, deliberation))


@pytest.fixture
def messaging_port() -> MockMessagingPort:
    """Create mock messaging port."""
    return MockMessagingPort()


@pytest.fixture
def storage_port() -> MockStoragePort:
    """Create mock storage port."""
    return MockStoragePort()


@pytest.fixture
def use_case(
    messaging_port: MockMessagingPort, storage_port: MockStoragePort
) -> AccumulateDeliberationsUseCase:
    """Create use case instance."""
    return AccumulateDeliberationsUseCase(messaging=messaging_port, storage=storage_port)


@pytest.fixture
def ceremony_id() -> BacklogReviewCeremonyId:
    """Create test ceremony ID."""
    return BacklogReviewCeremonyId("ceremony-123")


@pytest.fixture
def story_id() -> StoryId:
    """Create test story ID."""
    return StoryId("ST-456")


@pytest.fixture
def reviewed_at() -> datetime:
    """Create test timestamp."""
    return datetime.now(UTC)


@pytest.mark.asyncio
async def test_execute_accumulates_single_deliberation(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    storage_port: MockStoragePort,
) -> None:
    """Test that execute accumulates a single deliberation."""
    # Act
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(storage_port.saved_deliberations) == 1
    saved_ceremony_id, saved_story_id, saved_deliberation = storage_port.saved_deliberations[0]
    assert saved_ceremony_id == ceremony_id
    assert saved_story_id == story_id
    assert saved_deliberation.agent_id == "agent-architect-001"
    assert saved_deliberation.role == BacklogReviewRole.ARCHITECT
    assert saved_deliberation.proposal == {"content": "Architect proposal"}


@pytest.mark.asyncio
async def test_execute_accumulates_multiple_deliberations_same_story(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    storage_port: MockStoragePort,
) -> None:
    """Test that execute accumulates multiple deliberations for the same story."""
    # Act - Add 3 deliberations (one per role)
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "QA proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "DevOps proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(storage_port.saved_deliberations) == 3
    roles = {d[2].role for d in storage_port.saved_deliberations}
    assert roles == {BacklogReviewRole.ARCHITECT, BacklogReviewRole.QA, BacklogReviewRole.DEVOPS}


@pytest.mark.asyncio
async def test_execute_publishes_event_when_all_roles_complete(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that execute publishes event when all roles have deliberated."""
    # Act - Add all 3 required roles
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "QA proposal"},
        reviewed_at=reviewed_at,
    )

    # This third deliberation should trigger the event
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "DevOps proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(messaging_port.published_events) == 1
    subject, payload = messaging_port.published_events[0]
    assert subject == str(NATSSubject.DELIBERATIONS_COMPLETE)
    assert payload["ceremony_id"] == ceremony_id.value
    assert payload["story_id"] == story_id.value
    assert len(payload["agent_deliberations"]) == 3


@pytest.mark.asyncio
async def test_execute_does_not_publish_event_when_roles_incomplete(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that execute does not publish event when not all roles have deliberated."""
    # Act - Add only 2 roles (missing DEVOPS)
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "QA proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert - No event should be published
    assert len(messaging_port.published_events) == 0


@pytest.mark.asyncio
async def test_execute_handles_string_proposal(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    storage_port: MockStoragePort,
) -> None:
    """Test that execute handles string proposals."""
    # Act
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal="Simple string proposal",
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(storage_port.saved_deliberations) == 1
    _, _, saved_deliberation = storage_port.saved_deliberations[0]
    assert saved_deliberation.proposal == "Simple string proposal"


@pytest.mark.asyncio
async def test_execute_handles_dict_proposal(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    storage_port: MockStoragePort,
) -> None:
    """Test that execute handles dict proposals."""
    # Act
    proposal_dict = {"content": "Proposal content", "metadata": {"key": "value"}}
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal=proposal_dict,
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(storage_port.saved_deliberations) == 1
    _, _, saved_deliberation = storage_port.saved_deliberations[0]
    assert saved_deliberation.proposal == proposal_dict


@pytest.mark.asyncio
async def test_execute_separates_deliberations_by_story(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that execute separates deliberations by story."""
    story_id_1 = StoryId("ST-001")
    story_id_2 = StoryId("ST-002")

    # Act - Complete all roles for story 1
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id_1,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id_1,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id_1,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )

    # Act - Add only one role for story 2
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id_2,
        agent_id="agent-architect-002",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert - Only story 1 should have published event
    assert len(messaging_port.published_events) == 1
    _, payload = messaging_port.published_events[0]
    assert payload["story_id"] == story_id_1.value


@pytest.mark.asyncio
async def test_execute_separates_deliberations_by_ceremony(
    use_case: AccumulateDeliberationsUseCase,
    story_id: StoryId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that execute separates deliberations by ceremony."""
    ceremony_id_1 = BacklogReviewCeremonyId("ceremony-001")
    ceremony_id_2 = BacklogReviewCeremonyId("ceremony-002")

    # Act - Complete all roles for ceremony 1
    await use_case.execute(
        ceremony_id=ceremony_id_1,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(
        ceremony_id=ceremony_id_1,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(
        ceremony_id=ceremony_id_1,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )

    # Act - Add only one role for ceremony 2
    await use_case.execute(
        ceremony_id=ceremony_id_2,
        story_id=story_id,
        agent_id="agent-architect-002",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert - Only ceremony 1 should have published event
    assert len(messaging_port.published_events) == 1
    _, payload = messaging_port.published_events[0]
    assert payload["ceremony_id"] == ceremony_id_1.value


@pytest.mark.asyncio
async def test_execute_event_payload_contains_all_deliberations(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that published event payload contains all accumulated deliberations."""
    # Act - Add all 3 roles
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal="QA proposal string",
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "DevOps proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(messaging_port.published_events) == 1
    _, payload = messaging_port.published_events[0]
    assert len(payload["agent_deliberations"]) == 3

    # Verify deliberation details
    agent_ids = {d["agent_id"] for d in payload["agent_deliberations"]}
    assert agent_ids == {"agent-architect-001", "agent-qa-001", "agent-devops-001"}

    roles = {d["role"] for d in payload["agent_deliberations"]}
    assert roles == {"ARCHITECT", "QA", "DEVOPS"}


@pytest.mark.asyncio
async def test_execute_handles_multiple_agents_same_role(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    messaging_port: MockMessagingPort,
) -> None:
    """Test that execute handles multiple agents with the same role."""
    # Act - Add 2 architects, then QA and DEVOPS
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect 1 proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-002",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect 2 proposal"},
        reviewed_at=reviewed_at,
    )

    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"content": "QA proposal"},
        reviewed_at=reviewed_at,
    )

    # This should trigger the event (all 3 roles present, even with multiple architects)
    await use_case.execute(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal={"content": "DevOps proposal"},
        reviewed_at=reviewed_at,
    )

    # Assert
    assert len(messaging_port.published_events) == 1
    _, payload = messaging_port.published_events[0]
    # Should have 4 deliberations (2 architects + 1 QA + 1 DEVOPS)
    assert len(payload["agent_deliberations"]) == 4
