"""Unit tests for OrchestratorPort DTOs."""

import pytest
from planning.application.ports.orchestrator_port import (
    DeliberationRequest,
    DeliberationResponse,
    DeliberationResult,
    OrchestratorError,
    Proposal,
    TaskConstraints,
)


class TestTaskConstraints:
    """Test suite for TaskConstraints DTO."""

    def test_create_with_defaults(self) -> None:
        """Test creating TaskConstraints with default values."""
        constraints = TaskConstraints()

        assert constraints.rubric == ""
        assert constraints.requirements == ()
        assert constraints.metadata is None
        assert constraints.max_iterations == 3
        assert constraints.timeout_seconds == 180

    def test_create_with_custom_values(self) -> None:
        """Test creating TaskConstraints with custom values."""
        constraints = TaskConstraints(
            rubric="Evaluate technical feasibility",
            requirements=("Must use JWT", "Must have tests"),
            metadata={"priority": "high"},
            max_iterations=5,
            timeout_seconds=300,
        )

        assert constraints.rubric == "Evaluate technical feasibility"
        assert len(constraints.requirements) == 2
        assert constraints.metadata == {"priority": "high"}
        assert constraints.max_iterations == 5
        assert constraints.timeout_seconds == 300

    def test_timeout_zero_raises_value_error(self) -> None:
        """Test that timeout_seconds = 0 raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            TaskConstraints(timeout_seconds=0)

    def test_timeout_negative_raises_value_error(self) -> None:
        """Test that negative timeout raises ValueError."""
        with pytest.raises(ValueError, match="timeout_seconds must be > 0"):
            TaskConstraints(timeout_seconds=-10)

    def test_max_iterations_zero_raises_value_error(self) -> None:
        """Test that max_iterations = 0 raises ValueError."""
        with pytest.raises(ValueError, match="max_iterations must be > 0"):
            TaskConstraints(max_iterations=0)

    def test_immutability(self) -> None:
        """Test that TaskConstraints is immutable."""
        constraints = TaskConstraints()

        with pytest.raises(AttributeError):
            constraints.timeout_seconds = 300  # type: ignore


class TestDeliberationRequest:
    """Test suite for DeliberationRequest DTO."""

    def test_create_valid_request(self) -> None:
        """Test creating a valid DeliberationRequest."""
        request = DeliberationRequest(
            task_description="Review user story for technical feasibility",
            role="ARCHITECT",
        )

        assert request.task_description == "Review user story for technical feasibility"
        assert request.role == "ARCHITECT"
        assert request.constraints is None
        assert request.rounds == 1
        assert request.num_agents == 3

    def test_create_with_all_parameters(self) -> None:
        """Test creating request with all parameters."""
        constraints = TaskConstraints(rubric="Technical review")
        request = DeliberationRequest(
            task_description="Review story",
            role="QA",
            constraints=constraints,
            rounds=2,
            num_agents=5,
        )

        assert request.constraints == constraints
        assert request.rounds == 2
        assert request.num_agents == 5

    def test_empty_task_description_raises_value_error(self) -> None:
        """Test that empty task_description raises ValueError."""
        with pytest.raises(ValueError, match="task_description cannot be empty"):
            DeliberationRequest(
                task_description="",
                role="ARCHITECT",
            )

    def test_whitespace_task_description_raises_value_error(self) -> None:
        """Test that whitespace-only task_description raises ValueError."""
        with pytest.raises(ValueError, match="task_description cannot be empty"):
            DeliberationRequest(
                task_description="   ",
                role="ARCHITECT",
            )

    def test_invalid_role_raises_value_error(self) -> None:
        """Test that invalid role raises ValueError."""
        with pytest.raises(ValueError, match="Invalid role"):
            DeliberationRequest(
                task_description="Review story",
                role="INVALID_ROLE",
            )

    def test_valid_roles(self) -> None:
        """Test that all valid roles are accepted."""
        valid_roles = ("ARCHITECT", "QA", "DEVOPS", "DEV", "DATA")

        for role in valid_roles:
            request = DeliberationRequest(
                task_description="Review story",
                role=role,
            )
            assert request.role == role

    def test_rounds_zero_raises_value_error(self) -> None:
        """Test that rounds = 0 raises ValueError."""
        with pytest.raises(ValueError, match="rounds must be >= 1"):
            DeliberationRequest(
                task_description="Review story",
                role="ARCHITECT",
                rounds=0,
            )

    def test_num_agents_zero_raises_value_error(self) -> None:
        """Test that num_agents = 0 raises ValueError."""
        with pytest.raises(ValueError, match="num_agents must be >= 1"):
            DeliberationRequest(
                task_description="Review story",
                role="ARCHITECT",
                num_agents=0,
            )

    def test_immutability(self) -> None:
        """Test that DeliberationRequest is immutable."""
        request = DeliberationRequest(
            task_description="Review",
            role="ARCHITECT",
        )

        with pytest.raises(AttributeError):
            request.role = "QA"  # type: ignore


class TestProposal:
    """Test suite for Proposal DTO."""

    def test_create_valid_proposal(self) -> None:
        """Test creating a valid Proposal."""
        proposal = Proposal(
            author_id="ARCHITECT-agent-1",
            author_role="ARCHITECT",
            content="Technical review feedback...",
            created_at_ms=1701520800000,
        )

        assert proposal.author_id == "ARCHITECT-agent-1"
        assert proposal.author_role == "ARCHITECT"
        assert len(proposal.content) > 0
        assert proposal.revisions == ()

    def test_create_with_revisions(self) -> None:
        """Test creating proposal with revisions."""
        proposal = Proposal(
            author_id="QA-agent-1",
            author_role="QA",
            content="Updated feedback",
            created_at_ms=1701520800000,
            revisions=("revision 1", "revision 2"),
        )

        assert len(proposal.revisions) == 2

    def test_empty_author_id_raises_value_error(self) -> None:
        """Test that empty author_id raises ValueError."""
        with pytest.raises(ValueError, match="author_id cannot be empty"):
            Proposal(
                author_id="",
                author_role="ARCHITECT",
                content="Content",
                created_at_ms=1701520800000,
            )

    def test_empty_content_raises_value_error(self) -> None:
        """Test that empty content raises ValueError."""
        with pytest.raises(ValueError, match="content cannot be empty"):
            Proposal(
                author_id="agent-1",
                author_role="ARCHITECT",
                content="",
                created_at_ms=1701520800000,
            )

    def test_negative_timestamp_raises_value_error(self) -> None:
        """Test that negative created_at_ms raises ValueError."""
        with pytest.raises(ValueError, match="created_at_ms must be >= 0"):
            Proposal(
                author_id="agent-1",
                author_role="ARCHITECT",
                content="Content",
                created_at_ms=-1,
            )


class TestDeliberationResult:
    """Test suite for DeliberationResult DTO."""

    def test_create_valid_result(self) -> None:
        """Test creating a valid DeliberationResult."""
        proposal = Proposal(
            author_id="agent-1",
            author_role="ARCHITECT",
            content="Content",
            created_at_ms=1701520800000,
        )

        result = DeliberationResult(
            proposal=proposal,
            checks_passed=True,
            score=0.92,
            rank=1,
        )

        assert result.proposal == proposal
        assert result.checks_passed is True
        assert result.score == 0.92
        assert result.rank == 1

    def test_score_negative_raises_value_error(self) -> None:
        """Test that negative score raises ValueError."""
        proposal = Proposal(
            author_id="agent-1",
            author_role="ARCHITECT",
            content="Content",
            created_at_ms=1701520800000,
        )

        with pytest.raises(ValueError, match="score must be 0.0-1.0"):
            DeliberationResult(
                proposal=proposal,
                checks_passed=True,
                score=-0.1,
                rank=1,
            )

    def test_score_above_one_raises_value_error(self) -> None:
        """Test that score > 1.0 raises ValueError."""
        proposal = Proposal(
            author_id="agent-1",
            author_role="ARCHITECT",
            content="Content",
            created_at_ms=1701520800000,
        )

        with pytest.raises(ValueError, match="score must be 0.0-1.0"):
            DeliberationResult(
                proposal=proposal,
                checks_passed=True,
                score=1.5,
                rank=1,
            )

    def test_rank_zero_raises_value_error(self) -> None:
        """Test that rank = 0 raises ValueError."""
        proposal = Proposal(
            author_id="agent-1",
            author_role="ARCHITECT",
            content="Content",
            created_at_ms=1701520800000,
        )

        with pytest.raises(ValueError, match="rank must be >= 1"):
            DeliberationResult(
                proposal=proposal,
                checks_passed=True,
                score=0.92,
                rank=0,
            )


class TestDeliberationResponse:
    """Test suite for DeliberationResponse DTO."""

    @pytest.fixture
    def sample_results(self) -> tuple[DeliberationResult, ...]:
        """Fixture providing sample deliberation results."""
        proposal1 = Proposal(
            author_id="agent-1",
            author_role="ARCHITECT",
            content="Winner proposal",
            created_at_ms=1701520800000,
        )
        proposal2 = Proposal(
            author_id="agent-2",
            author_role="ARCHITECT",
            content="Second proposal",
            created_at_ms=1701520800000,
        )

        result1 = DeliberationResult(
            proposal=proposal1,
            checks_passed=True,
            score=0.95,
            rank=1,
        )
        result2 = DeliberationResult(
            proposal=proposal2,
            checks_passed=True,
            score=0.88,
            rank=2,
        )

        return (result1, result2)

    def test_create_valid_response(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test creating a valid DeliberationResponse."""
        response = DeliberationResponse(
            results=sample_results,
            winner_id="agent-1",
            duration_ms=8542,
        )

        assert len(response.results) == 2
        assert response.winner_id == "agent-1"
        assert response.duration_ms == 8542

    def test_empty_results_raises_value_error(self) -> None:
        """Test that empty results raises ValueError."""
        with pytest.raises(ValueError, match="results cannot be empty"):
            DeliberationResponse(
                results=(),
                winner_id="agent-1",
                duration_ms=1000,
            )

    def test_empty_winner_id_raises_value_error(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test that empty winner_id raises ValueError."""
        with pytest.raises(ValueError, match="winner_id cannot be empty"):
            DeliberationResponse(
                results=sample_results,
                winner_id="",
                duration_ms=1000,
            )

    def test_negative_duration_raises_value_error(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test that negative duration raises ValueError."""
        with pytest.raises(ValueError, match="duration_ms must be >= 0"):
            DeliberationResponse(
                results=sample_results,
                winner_id="agent-1",
                duration_ms=-100,
            )

    def test_get_winner_success(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test getting winner from results."""
        response = DeliberationResponse(
            results=sample_results,
            winner_id="agent-1",
            duration_ms=1000,
        )

        winner = response.get_winner()

        assert winner.proposal.author_id == "agent-1"
        assert winner.rank == 1
        assert winner.score == 0.95

    def test_get_winner_not_found_raises_value_error(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test that get_winner raises if winner_id not in results."""
        response = DeliberationResponse(
            results=sample_results,
            winner_id="agent-999",  # Not in results!
            duration_ms=1000,
        )

        with pytest.raises(ValueError, match="Winner .* not found in results"):
            response.get_winner()

    def test_get_winner_content_success(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test getting winner content."""
        response = DeliberationResponse(
            results=sample_results,
            winner_id="agent-1",
            duration_ms=1000,
        )

        content = response.get_winner_content()

        assert content == "Winner proposal"

    def test_immutability(
        self, sample_results: tuple[DeliberationResult, ...]
    ) -> None:
        """Test that DeliberationResponse is immutable."""
        response = DeliberationResponse(
            results=sample_results,
            winner_id="agent-1",
            duration_ms=1000,
        )

        with pytest.raises(AttributeError):
            response.winner_id = "agent-2"  # type: ignore


class TestOrchestratorError:
    """Test suite for OrchestratorError exception."""

    def test_create_error(self) -> None:
        """Test creating OrchestratorError."""
        error = OrchestratorError("Deliberation failed")

        assert str(error) == "Deliberation failed"

    def test_raise_error(self) -> None:
        """Test raising OrchestratorError."""
        with pytest.raises(OrchestratorError, match="Connection timeout"):
            raise OrchestratorError("Connection timeout")

