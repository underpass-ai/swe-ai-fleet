"""Unit tests for ceremony port (AgentDeliberationRequest, CeremonyServiceError, CeremonyPort)."""

from datetime import UTC, datetime

import pytest

from planning.application.ports.ceremony_port import (
    AgentDeliberationRequest,
    CeremonyPort,
    CeremonyServiceError,
)
from planning.domain.value_objects.identifiers.backlog_review_ceremony_id import (
    BacklogReviewCeremonyId,
)
from planning.domain.value_objects.identifiers.story_id import StoryId
from planning.domain.value_objects.statuses.backlog_review_role import (
    BacklogReviewRole,
)


def test_agent_deliberation_request_creation():
    """AgentDeliberationRequest can be created with required fields."""
    req = AgentDeliberationRequest(
        ceremony_id=BacklogReviewCeremonyId("c-1"),
        story_id=StoryId("story-1"),
        role=BacklogReviewRole.ARCHITECT,
        agent_id="agent-1",
        feedback="Looks good",
        proposal='{"tasks": ["t1"]}',
        reviewed_at=datetime.now(UTC),
    )
    assert req.ceremony_id.value == "c-1"
    assert req.story_id.value == "story-1"
    assert req.role == BacklogReviewRole.ARCHITECT
    assert req.agent_id == "agent-1"
    assert req.feedback == "Looks good"
    assert req.proposal == '{"tasks": ["t1"]}'


def test_agent_deliberation_request_frozen():
    """AgentDeliberationRequest is immutable."""
    req = AgentDeliberationRequest(
        ceremony_id=BacklogReviewCeremonyId("c-1"),
        story_id=StoryId("story-1"),
        role=BacklogReviewRole.ARCHITECT,
        agent_id="agent-1",
        feedback="x",
        proposal="{}",
        reviewed_at=datetime.now(UTC),
    )
    with pytest.raises(AttributeError):
        req.agent_id = "other"


def test_ceremony_service_error():
    """CeremonyServiceError can be raised and carries message."""
    with pytest.raises(CeremonyServiceError, match="update failed"):
        raise CeremonyServiceError("update failed")


def test_ceremony_port_abstract():
    """CeremonyPort cannot be instantiated (abstract)."""
    with pytest.raises(TypeError):
        CeremonyPort()
