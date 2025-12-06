"""Unit tests for ReviewStoryWithCouncilsUseCase."""

from unittest.mock import AsyncMock

import pytest
from planning.application.ports import ContextPort, ContextResponse, OrchestratorPort
from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    DeliberationResponse,
    DeliberationResult,
    Proposal,
)
from planning.application.usecases.review_story_with_councils_usecase import (
    ReviewStoryWithCouncilsUseCase,
)
from planning.domain.value_objects.identifiers.story_id import StoryId


class TestReviewStoryWithCouncilsUseCase:
    """Test suite for ReviewStoryWithCouncilsUseCase."""

    @pytest.fixture
    def context_port(self) -> ContextPort:
        """Fixture providing mock ContextPort."""
        mock = AsyncMock(spec=ContextPort)
        mock.get_context.return_value = ContextResponse(
            context="Story: Implement user authentication\n\nDescription: ...",
            token_count=1500,
            scopes=("story_details", "technical_context"),
            version="v1",
        )
        return mock

    @pytest.fixture
    def orchestrator_port(self) -> OrchestratorPort:
        """Fixture providing mock OrchestratorPort."""
        mock = AsyncMock(spec=OrchestratorPort)

        # Default response for deliberations
        def create_response(role: str) -> DeliberationResponse:
            proposal = Proposal(
                author_id=f"{role}-agent-1",
                author_role=role,
                content=f"{role} feedback: Implementation looks feasible. Recommendations included.",
                created_at_ms=1701520800000,
            )
            result = DeliberationResult(
                proposal=proposal,
                checks_passed=True,
                score=0.92,
                rank=1,
            )
            return DeliberationResponse(
                results=(result,),
                winner_id=f"{role}-agent-1",
                duration_ms=5000,
            )

        mock.deliberate.side_effect = lambda req: create_response(req.role)
        return mock

    @pytest.fixture
    def use_case(
        self,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
    ) -> ReviewStoryWithCouncilsUseCase:
        """Fixture providing the use case."""
        return ReviewStoryWithCouncilsUseCase(
            orchestrator=orchestrator_port,
            context=context_port,
        )

    @pytest.mark.asyncio
    async def test_review_with_three_councils_success(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
        context_port: ContextPort,
        orchestrator_port: OrchestratorPort,
    ) -> None:
        """Test reviewing story with default 3 councils."""
        story_id = StoryId("ST-123")

        result = await use_case.execute(story_id)

        # Verify context was fetched
        context_port.get_context.assert_awaited_once()
        call_args = context_port.get_context.call_args
        assert call_args[1]["story_id"] == "ST-123"
        from planning.domain.value_objects.statuses.backlog_review_phase import (
            BacklogReviewPhase,
        )
        assert call_args[1]["phase"] == BacklogReviewPhase.DESIGN.value

        # Verify 3 deliberations (ARCHITECT, QA, DEVOPS)
        assert orchestrator_port.deliberate.await_count == 3

        # Verify result has all components
        assert result.story_id == story_id
        assert result.plan_preliminary is not None
        assert result.architect_feedback
        assert result.qa_feedback
        assert result.devops_feedback
        assert result.approval_status.is_pending()
        assert len(result.recommendations) > 0

    @pytest.mark.asyncio
    async def test_plan_preliminary_has_tasks_outline(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
    ) -> None:
        """Test that generated plan has tasks_outline (hybrid flow)."""
        story_id = StoryId("ST-123")

        result = await use_case.execute(story_id)

        assert result.plan_preliminary is not None
        assert len(result.plan_preliminary.tasks_outline) > 0
        # Default placeholder tasks should exist
        assert any("Setup" in task for task in result.plan_preliminary.tasks_outline)

    @pytest.mark.asyncio
    async def test_custom_roles(
        self,
        orchestrator_port: OrchestratorPort,
        context_port: ContextPort,
    ) -> None:
        """Test reviewing with custom roles."""
        use_case = ReviewStoryWithCouncilsUseCase(
            orchestrator=orchestrator_port,
            context=context_port,
        )
        story_id = StoryId("ST-123")

        result = await use_case.execute(
            story_id,
            roles=("ARCHITECT", "QA"),  # Only 2 roles
        )

        # Verify result is valid
        assert result is not None
        assert result.story_id == story_id

        # Should call deliberate only 2 times
        assert orchestrator_port.deliberate.await_count == 2

    @pytest.mark.asyncio
    async def test_context_service_error_propagates(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
        context_port: ContextPort,
    ) -> None:
        """Test that Context Service errors propagate."""
        context_port.get_context.side_effect = Exception("Context Service unavailable")

        with pytest.raises(Exception, match="Context Service unavailable"):
            await use_case.execute(StoryId("ST-123"))

    @pytest.mark.asyncio
    async def test_orchestrator_error_propagates(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
        orchestrator_port: OrchestratorPort,
    ) -> None:
        """Test that Orchestrator errors propagate."""
        orchestrator_port.deliberate.side_effect = Exception("Orchestrator timeout")

        with pytest.raises(Exception, match="Orchestrator timeout"):
            await use_case.execute(StoryId("ST-123"))

    @pytest.mark.asyncio
    async def test_deliberation_requests_have_correct_structure(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
        orchestrator_port: OrchestratorPort,
    ) -> None:
        """Test that deliberation requests are properly structured."""
        story_id = StoryId("ST-123")

        await use_case.execute(story_id)

        # Check first deliberation call
        first_call_args = orchestrator_port.deliberate.call_args_list[0]
        request: DeliberationRequest = first_call_args[0][0]

        assert isinstance(request, DeliberationRequest)
        assert request.task_description
        assert request.role in ("ARCHITECT", "QA", "DEVOPS")
        assert request.constraints is not None
        assert request.rounds == 1
        assert request.num_agents == 3

    @pytest.mark.asyncio
    async def test_feedbacks_extracted_from_winner(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
        orchestrator_port: OrchestratorPort,
    ) -> None:
        """Test that feedbacks are extracted from winner proposals."""
        story_id = StoryId("ST-123")

        result = await use_case.execute(story_id)

        # Feedbacks should contain content from winner proposals
        assert "ARCHITECT feedback" in result.architect_feedback or "feasible" in result.architect_feedback.lower()
        assert len(result.qa_feedback) > 0
        assert len(result.devops_feedback) > 0

    @pytest.mark.asyncio
    async def test_plan_complexity_estimated(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
    ) -> None:
        """Test that plan complexity is estimated from feedbacks."""
        story_id = StoryId("ST-123")

        result = await use_case.execute(story_id)

        assert result.plan_preliminary.estimated_complexity in ("LOW", "MEDIUM", "HIGH")

    @pytest.mark.asyncio
    async def test_recommendations_generated(
        self,
        use_case: ReviewStoryWithCouncilsUseCase,
    ) -> None:
        """Test that recommendations are generated."""
        story_id = StoryId("ST-123")

        result = await use_case.execute(story_id)

        assert len(result.recommendations) > 0
        assert all(isinstance(rec, str) for rec in result.recommendations)

