"""
Unit tests for Orchestrator Service gRPC server.
"""

from unittest.mock import Mock, patch

import grpc
import pytest

# Mark all tests as unit tests
pytestmark = pytest.mark.unit

# Test fixtures - mock connection values (not real credentials)
TEST_GRPC_PORT = "50055"


@pytest.fixture
def mock_system_config():
    """Mock SystemConfig."""
    mock = Mock()
    mock.get_agent_config = Mock(return_value={})
    return mock


@pytest.fixture
def mock_scoring():
    """Mock Scoring service."""
    mock = Mock()
    mock.run_check_suite = Mock(return_value=Mock(
        policy=Mock(passed=True, violations=[], message=""),
        lint=Mock(passed=True, error_count=0, warning_count=0, errors=[]),
        dryrun=Mock(passed=True, output="", exit_code=0, message="")
    ))
    mock.score_checks = Mock(return_value=0.95)
    return mock


@pytest.fixture
def mock_deliberate_usecase():
    """Mock Deliberate use case."""
    mock = Mock()
    mock.execute = Mock(return_value=[
        Mock(
            proposal=Mock(
                author=Mock(agent_id="dev-agent-0", role=Mock(name="DEV")),
                content="Solution 1"
            ),
            checks=Mock(
                policy=Mock(passed=True, violations=[], message=""),
                lint=Mock(passed=True, error_count=0, warning_count=0, errors=[]),
                dryrun=Mock(passed=True, output="", exit_code=0, message="")
            ),
            score=0.95
        ),
        Mock(
            proposal=Mock(
                author=Mock(agent_id="dev-agent-1", role=Mock(name="DEV")),
                content="Solution 2"
            ),
            checks=Mock(
                policy=Mock(passed=True, violations=[], message=""),
                lint=Mock(passed=True, error_count=0, warning_count=0, errors=[]),
                dryrun=Mock(passed=True, output="", exit_code=0, message="")
            ),
            score=0.85
        ),
    ])
    return mock


@pytest.fixture
def mock_orchestrate_usecase():
    """Mock Orchestrate use case."""
    mock = Mock()
    mock.execute = Mock(return_value={
        "winner": Mock(
            proposal=Mock(
                author=Mock(agent_id="dev-agent-0", role=Mock(name="DEV")),
                content="Winner solution"
            ),
            checks=Mock(
                policy=Mock(passed=True, violations=[], message=""),
                lint=Mock(passed=True, error_count=0, warning_count=0, errors=[]),
                dryrun=Mock(passed=True, output="", exit_code=0, message="")
            ),
            score=0.95
        ),
        "candidates": [
            Mock(
                proposal=Mock(
                    author=Mock(agent_id="dev-agent-1", role=Mock(name="DEV")),
                    content="Candidate solution"
                ),
                checks=Mock(
                    policy=Mock(passed=True, violations=[], message=""),
                    lint=Mock(passed=True, error_count=0, warning_count=0, errors=[]),
                    dryrun=Mock(passed=True, output="", exit_code=0, message="")
                ),
                score=0.85
            )
        ]
    })
    return mock


@pytest.fixture
def orchestrator_servicer(mock_system_config):
    """Create OrchestratorServiceServicer with mocked dependencies."""
    with (
        patch('services.orchestrator.server.SystemConfig', return_value=mock_system_config),
        patch('services.orchestrator.server.Scoring'),
        patch('services.orchestrator.server.Deliberate'),
        patch('services.orchestrator.server.Orchestrate'),
        patch('services.orchestrator.server.ArchitectSelectorService'),
    ):
        from services.orchestrator.server import OrchestratorServiceServicer

        servicer = OrchestratorServiceServicer(config=mock_system_config)

        yield servicer


class TestDeliberate:
    """Test Deliberate gRPC method."""

    def test_deliberate_success(self, orchestrator_servicer, mock_deliberate_usecase):
        """Test successful Deliberate request."""
        from services.orchestrator.gen import orchestrator_pb2

        # Mock the council
        orchestrator_servicer.councils["DEV"] = mock_deliberate_usecase

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement user authentication",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="High quality, secure code",
                requirements=["Unit tests", "Documentation"],
                max_iterations=10,
                timeout_seconds=300
            ),
            rounds=1,
            num_agents=3
        )

        grpc_context = Mock()

        response = orchestrator_servicer.Deliberate(request, grpc_context)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.DeliberateResponse)
        assert len(response.results) == 2
        assert response.winner_id == "dev-agent-0"
        assert response.duration_ms > 0

    def test_deliberate_unknown_role(self, orchestrator_servicer):
        """Test Deliberate with unknown role."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test task",
            role="UNKNOWN",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        grpc_context = Mock()

        response = orchestrator_servicer.Deliberate(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INVALID_ARGUMENT)
        assert response is not None

    def test_deliberate_error_handling(self, orchestrator_servicer):
        """Test Deliberate error handling."""
        from services.orchestrator.gen import orchestrator_pb2

        # Mock council to raise exception
        mock_council = Mock()
        mock_council.execute = Mock(side_effect=Exception("Test error"))
        orchestrator_servicer.councils["DEV"] = mock_council

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test task",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        grpc_context = Mock()

        response = orchestrator_servicer.Deliberate(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response is not None


class TestOrchestrate:
    """Test Orchestrate gRPC method."""

    def test_orchestrate_success(self, orchestrator_servicer, mock_orchestrate_usecase):
        """Test successful Orchestrate request."""
        from services.orchestrator.gen import orchestrator_pb2

        # Mock the orchestrator
        orchestrator_servicer.orchestrator = mock_orchestrate_usecase

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="task-001",
            task_description="Implement feature X",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="High quality",
                requirements=["Tests", "Docs"]
            )
        )

        grpc_context = Mock()

        response = orchestrator_servicer.Orchestrate(request, grpc_context)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.OrchestrateResponse)
        assert response.winner is not None
        assert response.winner.proposal.author_id == "dev-agent-0"
        assert len(response.candidates) == 1
        assert len(response.execution_id) > 0
        assert response.duration_ms > 0

    def test_orchestrate_error_handling(self, orchestrator_servicer):
        """Test Orchestrate error handling."""
        from services.orchestrator.gen import orchestrator_pb2

        # Mock orchestrator to raise exception
        orchestrator_servicer.orchestrator.execute = Mock(side_effect=Exception("Test error"))

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="task-001",
            task_description="Test task",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        grpc_context = Mock()

        response = orchestrator_servicer.Orchestrate(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response is not None


class TestGetStatus:
    """Test GetStatus gRPC method."""

    def test_get_status_basic(self, orchestrator_servicer):
        """Test GetStatus without stats."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        grpc_context = Mock()

        response = orchestrator_servicer.GetStatus(request, grpc_context)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.GetStatusResponse)
        assert response.status == "healthy"
        assert response.uptime_seconds >= 0

    def test_get_status_with_stats(self, orchestrator_servicer):
        """Test GetStatus with statistics."""
        from services.orchestrator.gen import orchestrator_pb2

        # Add some stats
        orchestrator_servicer.stats["total_deliberations"] = 10
        orchestrator_servicer.stats["total_orchestrations"] = 5
        orchestrator_servicer.stats["total_duration_ms"] = 15000
        orchestrator_servicer.stats["role_counts"]["DEV"] = 8

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=True
        )

        grpc_context = Mock()

        response = orchestrator_servicer.GetStatus(request, grpc_context)

        assert response is not None
        assert response.status == "healthy"
        assert response.stats is not None
        assert response.stats.total_deliberations == 10
        assert response.stats.total_orchestrations == 5
        assert response.stats.avg_deliberation_time_ms == 1000.0
        assert response.stats.active_councils == len(orchestrator_servicer.councils)

    def test_get_status_error_handling(self, orchestrator_servicer):
        """Test GetStatus error handling."""
        from services.orchestrator.gen import orchestrator_pb2

        # Force an error by breaking start_time
        orchestrator_servicer.start_time = "invalid"

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        grpc_context = Mock()

        response = orchestrator_servicer.GetStatus(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.INTERNAL)
        assert response.status == "unhealthy"


class TestHelperMethods:
    """Test helper methods."""

    def test_generate_execution_id(self, orchestrator_servicer):
        """Test _generate_execution_id method."""
        exec_id1 = orchestrator_servicer._generate_execution_id("task description")
        exec_id2 = orchestrator_servicer._generate_execution_id("task description")

        # Different calls should produce different IDs (due to timestamp)
        # But both should be 16 characters
        assert len(exec_id1) == 16
        assert len(exec_id2) == 16

    def test_proto_to_constraints(self, orchestrator_servicer):
        """Test _proto_to_constraints method."""
        from services.orchestrator.gen import orchestrator_pb2

        proto_constraints = orchestrator_pb2.TaskConstraints(
            rubric="Test rubric",
            requirements=["req1", "req2"],
            max_iterations=5,
            timeout_seconds=100
        )

        constraints = orchestrator_servicer._proto_to_constraints(proto_constraints)

        assert constraints.rubric == "Test rubric"
        assert list(constraints.requirements) == ["req1", "req2"]
        assert constraints.max_iterations == 5
        assert constraints.timeout_seconds == 100

    def test_check_suite_to_proto(self, orchestrator_servicer):
        """Test _check_suite_to_proto method."""
        check_suite = Mock(
            policy=Mock(passed=True, violations=[], message="OK"),
            lint=Mock(passed=False, error_count=2, warning_count=1, errors=["error1", "error2"]),
            dryrun=Mock(passed=True, output="Success", exit_code=0, message="OK")
        )

        proto_suite = orchestrator_servicer._check_suite_to_proto(check_suite)

        assert proto_suite.policy.passed is True
        assert proto_suite.lint.passed is False
        assert proto_suite.lint.error_count == 2
        assert proto_suite.dryrun.passed is True
        assert proto_suite.all_passed is False  # Because lint failed

