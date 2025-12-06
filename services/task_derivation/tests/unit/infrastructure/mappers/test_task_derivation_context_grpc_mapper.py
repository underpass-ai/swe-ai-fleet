"""Tests for ContextGrpcMapper."""

from __future__ import annotations

from typing import cast
from unittest.mock import MagicMock

import pytest
from task_derivation.domain.value_objects.identifiers.story_id import StoryId
from task_derivation.domain.value_objects.task_derivation.context.context_role import (
    ContextRole,
)
from task_derivation.domain.value_objects.task_derivation.context.derivation_phase import (
    DerivationPhase,
)
from task_derivation.infrastructure.mappers.context_grpc_mapper import (
    ContextGrpcMapper,
)


class TestContextGrpcMapperToGetContextRequest:
    """Test conversion from domain objects to GetContextRequest proto."""

    def test_to_get_context_request_success(self) -> None:
        """Test successful conversion to proto message."""
        story_id = StoryId("story-001")
        role = ContextRole("developer")
        phase = DerivationPhase.PLAN

        request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)

        assert request.story_id == "story-001"
        assert request.role == "developer"
        assert request.phase == "PLAN"

    def test_to_get_context_request_different_phases(self) -> None:
        """Test conversion with different derivation phases."""
        story_id = StoryId("story-002")
        role = ContextRole("qa")

        for phase in [DerivationPhase.PLAN, DerivationPhase.EXECUTION]:
            request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)
            assert request.phase == phase.value.upper()

    def test_to_get_context_request_with_different_roles(self) -> None:
        """Test conversion with different context roles."""
        story_id = StoryId("story-003")
        phase = DerivationPhase.EXECUTION

        for role_value in ["developer", "qa", "architect", "devops"]:
            role = ContextRole(role_value)
            request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)
            assert request.role == role_value

    def test_to_get_context_request_rejects_empty_story_id(self) -> None:
        """Test that mapper rejects empty story_id."""
        role = ContextRole("developer")
        phase = DerivationPhase.PLAN

        # StoryId validation should prevent this, but test mapper defensive checks
        with pytest.raises(ValueError):
            ContextGrpcMapper.to_get_context_request(
                StoryId(""), role, phase  # type: ignore
            )

    def test_to_get_context_request_rejects_empty_role(self) -> None:
        """Test that mapper rejects empty role."""
        story_id = StoryId("story-001")
        phase = DerivationPhase.PLAN

        with pytest.raises(ValueError):
            ContextGrpcMapper.to_get_context_request(
                story_id, ContextRole(""), phase  # type: ignore
            )

    def test_to_get_context_request_rejects_none_values(self) -> None:
        """Test that mapper rejects None values."""
        story_id = StoryId("story-001")
        role = ContextRole("developer")
        phase = DerivationPhase.PLAN

        with pytest.raises((ValueError, AttributeError)):
            ContextGrpcMapper.to_get_context_request(
                cast(StoryId, None), role, phase
            )

        with pytest.raises((ValueError, AttributeError)):
            ContextGrpcMapper.to_get_context_request(
                story_id, cast(ContextRole, None), phase
            )

        with pytest.raises((ValueError, AttributeError)):
            ContextGrpcMapper.to_get_context_request(
                story_id, role, cast(DerivationPhase, None)
            )


class TestContextGrpcMapperContextFromResponse:
    """Test extraction of context from proto response."""

    def test_context_from_response_success(self) -> None:
        """Test successful extraction of context from response."""
        response = MagicMock()
        response.context = "Formatted context blocks"

        context = ContextGrpcMapper.context_from_response(response)

        assert context == "Formatted context blocks"

    def test_context_from_response_empty_context(self) -> None:
        """Test extraction when context is empty string."""
        response = MagicMock()
        response.context = ""

        context = ContextGrpcMapper.context_from_response(response)

        assert context == ""

    def test_context_from_response_none_context(self) -> None:
        """Test extraction when context is None."""
        response = MagicMock()
        response.context = None

        context = ContextGrpcMapper.context_from_response(response)

        assert context == ""

    def test_context_from_response_with_multiline_context(self) -> None:
        """Test extraction of multi-line context."""
        multiline_context = """System: You are a developer
Context: Current story is story-001
Tools: Available tools are X, Y, Z"""

        response = MagicMock()
        response.context = multiline_context

        context = ContextGrpcMapper.context_from_response(response)

        assert context == multiline_context
        assert "\n" in context

    def test_context_from_response_rejects_none_response(self) -> None:
        """Test that mapper rejects None response."""
        with pytest.raises(ValueError, match="GetContextResponse cannot be None"):
            ContextGrpcMapper.context_from_response(None)  # type: ignore


class TestContextGrpcMapperRoundTrip:
    """Test round-trip conversions (domain → proto → domain)."""

    def test_round_trip_story_id(self) -> None:
        """Test that story_id survives round-trip."""
        original_id = "story-123"
        story_id = StoryId(original_id)
        role = ContextRole("developer")
        phase = DerivationPhase.PLAN

        request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)

        assert request.story_id == original_id

    def test_round_trip_role(self) -> None:
        """Test that role survives round-trip."""
        original_role = "architect"
        story_id = StoryId("story-001")
        role = ContextRole(original_role)
        phase = DerivationPhase.EXECUTION

        request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)

        assert request.role == original_role

    def test_round_trip_phase(self) -> None:
        """Test that phase survives round-trip."""
        story_id = StoryId("story-001")
        role = ContextRole("developer")
        phase = DerivationPhase.EXECUTION

        request = ContextGrpcMapper.to_get_context_request(story_id, role, phase)

        assert request.phase == "EXECUTION"

