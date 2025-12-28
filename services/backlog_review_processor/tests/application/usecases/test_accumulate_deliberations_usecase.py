"""Unit tests for AccumulateDeliberationsUseCase."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from unittest.mock import AsyncMock

import pytest

from backlog_review_processor.application.ports.planning_port import (
    AddAgentDeliberationRequest,
    PlanningServiceError,
)
from backlog_review_processor.application.usecases.accumulate_deliberations_usecase import (
    AccumulateDeliberationsUseCase,
)
from backlog_review_processor.domain.entities.backlog_review_result import (
    BacklogReviewResult,
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
        self.published_envelopes: list[tuple[str, object]] = []

    async def publish_event(self, subject: str, payload: dict) -> None:
        """Mock publish event."""
        await asyncio.sleep(0.001)  # Small delay to make function properly async
        self.published_events.append((subject, payload))

    async def publish_event_with_envelope(self, subject: str, envelope: object) -> None:
        """Mock publish event with envelope."""
        await asyncio.sleep(0.001)  # Small delay to make function properly async
        self.published_envelopes.append((subject, envelope))


class MockStoragePort:
    """Mock implementation of StoragePort."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.saved_deliberations: list[tuple[BacklogReviewCeremonyId, StoryId, dict]] = []

    async def save_agent_deliberation(
        self,
        ceremony_id: BacklogReviewCeremonyId,
        story_id: StoryId,
        deliberation: object,  # AgentDeliberation
    ) -> None:
        """Mock save deliberation."""
        await asyncio.sleep(0.001)  # Small delay to make function properly async
        self.saved_deliberations.append((ceremony_id, story_id, deliberation))


class MockPlanningPort:
    """Mock implementation of PlanningPort."""

    def __init__(self) -> None:
        """Initialize mock."""
        self.added_deliberations: list[AddAgentDeliberationRequest] = []
        self.should_fail = False
        self.fail_error: PlanningServiceError | None = None

    async def add_agent_deliberation(self, request: AddAgentDeliberationRequest) -> None:
        """Mock add agent deliberation."""
        await asyncio.sleep(0.001)  # Small delay to make function properly async
        if self.should_fail:
            raise self.fail_error or PlanningServiceError("Mock Planning Service error")
        self.added_deliberations.append(request)

    async def create_task(self, request) -> str:
        """Mock create task (not used in these tests)."""
        raise NotImplementedError("Not used in AccumulateDeliberationsUseCase tests")


@pytest.fixture
def messaging_port() -> MockMessagingPort:
    """Create mock messaging port."""
    return MockMessagingPort()


@pytest.fixture
def storage_port() -> MockStoragePort:
    """Create mock storage port."""
    return MockStoragePort()


@pytest.fixture
def planning_port() -> MockPlanningPort:
    """Create mock planning port."""
    return MockPlanningPort()


@pytest.fixture
def use_case(
    messaging_port: MockMessagingPort,
    storage_port: MockStoragePort,
    planning_port: MockPlanningPort,
) -> AccumulateDeliberationsUseCase:
    """Create use case instance."""
    return AccumulateDeliberationsUseCase(
        messaging=messaging_port, storage=storage_port, planning=planning_port
    )


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
    result = BacklogReviewResult(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(result)

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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "QA proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "DevOps proposal"},
            reviewed_at=reviewed_at,
        )
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "QA proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # This third deliberation should trigger the event
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "DevOps proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert
    assert len(messaging_port.published_envelopes) == 1
    subject, envelope = messaging_port.published_envelopes[0]
    assert subject == str(NATSSubject.DELIBERATIONS_COMPLETE)
    # Extract payload from envelope
    payload = envelope.payload
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "QA proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert - No event should be published
    assert len(messaging_port.published_envelopes) == 0


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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal="Simple string proposal",
            reviewed_at=reviewed_at,
        )
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal=proposal_dict,
            reviewed_at=reviewed_at,
        )
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id_1,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id_1,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id_1,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Act - Add only one role for story 2
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id_2,
            agent_id="agent-architect-002",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert - Only story 1 should have published event
    assert len(messaging_port.published_envelopes) == 1
    _, envelope = messaging_port.published_envelopes[0]
    payload = envelope.payload
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
        BacklogReviewResult(
            ceremony_id=ceremony_id_1,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id_1,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id_1,
            story_id=story_id,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Act - Add only one role for ceremony 2
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id_2,
            story_id=story_id,
            agent_id="agent-architect-002",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert - Only ceremony 1 should have published event
    assert len(messaging_port.published_envelopes) == 1
    _, envelope = messaging_port.published_envelopes[0]
    payload = envelope.payload
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal="QA proposal string",
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "DevOps proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert
    assert len(messaging_port.published_envelopes) == 1
    _, envelope = messaging_port.published_envelopes[0]
    payload = envelope.payload
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
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-001",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect 1 proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-architect-002",
            role=BacklogReviewRole.ARCHITECT,
            proposal={"content": "Architect 2 proposal"},
            reviewed_at=reviewed_at,
        )
    )

    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-qa-001",
            role=BacklogReviewRole.QA,
            proposal={"content": "QA proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # This should trigger the event (all 3 roles present, even with multiple architects)
    await use_case.execute(
        BacklogReviewResult(
            ceremony_id=ceremony_id,
            story_id=story_id,
            agent_id="agent-devops-001",
            role=BacklogReviewRole.DEVOPS,
            proposal={"content": "DevOps proposal"},
            reviewed_at=reviewed_at,
        )
    )

    # Assert
    assert len(messaging_port.published_envelopes) == 1
    _, envelope = messaging_port.published_envelopes[0]
    payload = envelope.payload
    # Should have 4 deliberations (2 architects + 1 QA + 1 DEVOPS)
    assert len(payload["agent_deliberations"]) == 4


@pytest.mark.asyncio
async def test_execute_calls_planning_port_add_agent_deliberation(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    planning_port: MockPlanningPort,
) -> None:
    """Test that execute calls PlanningPort.add_agent_deliberation."""
    # Act
    result = BacklogReviewResult(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal", "feedback": "Architect feedback"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(result)

    # Assert
    assert len(planning_port.added_deliberations) == 1
    request = planning_port.added_deliberations[0]
    assert request.ceremony_id == ceremony_id
    assert request.story_id == story_id
    assert request.role == "ARCHITECT"
    assert request.agent_id == "agent-architect-001"
    assert request.feedback == "Architect feedback"  # Extracted from proposal dict
    assert request.proposal == {"content": "Architect proposal", "feedback": "Architect feedback"}
    assert request.reviewed_at == reviewed_at.isoformat()


@pytest.mark.asyncio
async def test_execute_handles_planning_service_error_gracefully(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    planning_port: MockPlanningPort,
    storage_port: MockStoragePort,
) -> None:
    """Test that execute handles PlanningServiceError gracefully."""
    # Arrange - Make planning port fail
    planning_port.should_fail = True
    planning_port.fail_error = PlanningServiceError("Planning Service unavailable")

    # Act
    result = BacklogReviewResult(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-architect-001",
        role=BacklogReviewRole.ARCHITECT,
        proposal={"content": "Architect proposal"},
        reviewed_at=reviewed_at,
    )
    # Should not raise exception
    await use_case.execute(result)

    # Assert - Deliberation should still be saved to storage
    assert len(storage_port.saved_deliberations) == 1
    # Planning port should have been called (even though it failed)
    # The error is caught and logged, but the call was attempted
    assert len(planning_port.added_deliberations) == 0  # Request added before error


@pytest.mark.asyncio
async def test_execute_extracts_feedback_from_proposal_dict(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    planning_port: MockPlanningPort,
) -> None:
    """Test that execute extracts feedback from proposal dict correctly."""
    # Act - Proposal with feedback field
    result = BacklogReviewResult(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-qa-001",
        role=BacklogReviewRole.QA,
        proposal={"feedback": "QA feedback text", "other": "data"},
        reviewed_at=reviewed_at,
    )
    await use_case.execute(result)

    # Assert
    assert len(planning_port.added_deliberations) == 1
    request = planning_port.added_deliberations[0]
    assert request.feedback == "QA feedback text"


@pytest.mark.asyncio
async def test_execute_uses_proposal_as_feedback_when_no_feedback_field(
    use_case: AccumulateDeliberationsUseCase,
    ceremony_id: BacklogReviewCeremonyId,
    story_id: StoryId,
    reviewed_at: datetime,
    planning_port: MockPlanningPort,
) -> None:
    """Test that execute uses proposal as feedback when no feedback field exists."""
    # Act - Proposal without feedback field
    proposal_str = "Simple string proposal"
    result = BacklogReviewResult(
        ceremony_id=ceremony_id,
        story_id=story_id,
        agent_id="agent-devops-001",
        role=BacklogReviewRole.DEVOPS,
        proposal=proposal_str,
        reviewed_at=reviewed_at,
    )
    await use_case.execute(result)

    # Assert
    assert len(planning_port.added_deliberations) == 1
    request = planning_port.added_deliberations[0]
    assert request.feedback == proposal_str
    assert request.proposal == proposal_str
