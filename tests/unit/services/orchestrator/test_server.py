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
    """Create OrchestratorServiceServicer with hexagonal architecture DI."""
    import services.orchestrator.server as orch_server
    from unittest.mock import MagicMock
    
    # Create mock ports (hexagonal architecture with DI)
    mock_ray_executor = MagicMock()
    mock_council_query = MagicMock()
    mock_agent_factory = MagicMock()
    mock_council_factory = MagicMock()
    mock_config_port = MagicMock()
    mock_config_port.get_config_value = MagicMock(side_effect=lambda k, d: d)  # Return defaults
    mock_scoring = MagicMock()
    mock_architect = MagicMock()
    
    # Create servicer with all dependencies injected
    servicer = orch_server.OrchestratorServiceServicer(
        config=mock_system_config,
        ray_executor=mock_ray_executor,
        council_query=mock_council_query,
        agent_factory=mock_agent_factory,
        council_factory=mock_council_factory,
        config_port=mock_config_port,
        scoring=mock_scoring,
        architect=mock_architect,
        result_collector=None
    )
    
    yield servicer


class TestDeliberate:
    """Test Deliberate gRPC method."""

    @pytest.mark.asyncio
    async def test_deliberate_no_agents(self, orchestrator_servicer):
        """Test Deliberate returns UNIMPLEMENTED when no agents configured."""
        from services.orchestrator.gen import orchestrator_pb2

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

        response = await orchestrator_servicer.Deliberate(request, grpc_context)

        # Should return UNIMPLEMENTED since no councils configured
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response is not None
        assert isinstance(response, orchestrator_pb2.DeliberateResponse)

    @pytest.mark.asyncio
    async def test_deliberate_unknown_role(self, orchestrator_servicer):
        """Test Deliberate with unknown role - still returns UNIMPLEMENTED."""
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

        response = await orchestrator_servicer.Deliberate(request, grpc_context)

        # Without agents, always returns UNIMPLEMENTED regardless of role
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response is not None

    @pytest.mark.asyncio
    async def test_deliberate_error_handling(self, orchestrator_servicer):
        """Test Deliberate error handling - returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test task",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        grpc_context = Mock()

        response = await orchestrator_servicer.Deliberate(request, grpc_context)

        # Without agents configured, returns UNIMPLEMENTED
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response is not None


class TestOrchestrate:
    """Test Orchestrate gRPC method."""

    @pytest.mark.asyncio
    async def test_orchestrate_no_agents(self, orchestrator_servicer):
        """Test Orchestrate returns UNIMPLEMENTED when no agents configured."""
        from services.orchestrator.gen import orchestrator_pb2

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

        response = await orchestrator_servicer.Orchestrate(request, grpc_context)

        # Should return UNIMPLEMENTED since no agents configured
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response is not None
        assert isinstance(response, orchestrator_pb2.OrchestrateResponse)

    @pytest.mark.asyncio
    async def test_orchestrate_error_handling(self, orchestrator_servicer):
        """Test Orchestrate returns UNIMPLEMENTED when no agents configured."""
        from services.orchestrator.gen import orchestrator_pb2

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

        response = await orchestrator_servicer.Orchestrate(request, grpc_context)

        # Should return UNIMPLEMENTED since no agents configured
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response is not None


class TestGetStatus:
    """Test GetStatus gRPC method."""

    @pytest.mark.asyncio
    async def test_get_status_basic(self, orchestrator_servicer):
        """Test GetStatus without stats."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        grpc_context = Mock()

        response = await orchestrator_servicer.GetStatus(request, grpc_context)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.GetStatusResponse)
        assert response.status == "healthy"
        assert response.uptime_seconds >= 0

    @pytest.mark.asyncio
    async def test_get_status_with_stats(self, orchestrator_servicer):
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

        response = await orchestrator_servicer.GetStatus(request, grpc_context)

        assert response is not None
        assert response.status == "healthy"
        assert response.stats is not None
        assert response.stats.total_deliberations == 10
        assert response.stats.total_orchestrations == 5
        # Use approximate comparison for float
        assert abs(response.stats.avg_deliberation_time_ms - 1000.0) < 0.1
        assert response.stats.active_councils == len(orchestrator_servicer.councils)

    @pytest.mark.asyncio
    async def test_get_status_error_handling(self, orchestrator_servicer):
        """Test GetStatus error handling."""
        from services.orchestrator.gen import orchestrator_pb2

        # Force an error by breaking start_time
        orchestrator_servicer.start_time = "invalid"

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        grpc_context = Mock()

        response = await orchestrator_servicer.GetStatus(request, grpc_context)

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

        # Verify that constraints is a TaskConstraints domain object
        assert constraints.rubric["description"] == "Test rubric"
        assert constraints.rubric["requirements"] == ["req1", "req2"]
        assert constraints.architect_rubric["k"] == 3
        assert constraints.architect_rubric["criteria"] == "Test rubric"
        assert constraints.additional_constraints["max_iterations"] == 5
        assert constraints.additional_constraints["timeout_seconds"] == 100

    def test_check_suite_to_proto(self, orchestrator_servicer):
        """Test _check_suite_to_proto method."""
        check_suite = Mock(
            policy=Mock(ok=True, violations=[], message="OK"),
            lint=Mock(ok=False, issues=["error1", "error2"]),
            dryrun=Mock(ok=True, errors=[], output="Success", exit_code=0, message="OK")
        )

        proto_suite = orchestrator_servicer._check_suite_to_proto(check_suite)

        assert proto_suite.policy.passed is True
        assert proto_suite.lint.passed is False
        assert proto_suite.lint.error_count == 2  # len(issues)
        assert len(proto_suite.lint.errors) == 2
        assert proto_suite.dryrun.passed is True
        assert proto_suite.all_passed is False  # Because lint failed


class TestNewRPCs:
    """Test new RPCs added in API refactor."""

    @pytest.mark.asyncio
    async def test_list_councils(self, orchestrator_servicer):
        """Test ListCouncils RPC - only functional new RPC."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.ListCouncilsRequest(
            role_filter="",
            include_agents=True
        )

        grpc_context = Mock()
        response = await orchestrator_servicer.ListCouncils(request, grpc_context)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.ListCouncilsResponse)
        # Currently returns empty since no councils configured
        assert len(response.councils) == 0

    @pytest.mark.asyncio
    async def test_register_agent_no_council(self, orchestrator_servicer):
        """Test RegisterAgent when council doesn't exist."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.RegisterAgentRequest(
            agent_id="test-agent",
            role="DEV"
        )

        grpc_context = Mock()
        response = await orchestrator_servicer.RegisterAgent(request, grpc_context)

        # Should return NOT_FOUND when council doesn't exist
        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.NOT_FOUND)
        assert response.success is False

    @pytest.mark.asyncio
    async def test_derive_subtasks_unimplemented(self, orchestrator_servicer):
        """Test DeriveSubtasks returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeriveSubtasksRequest(
            case_id="case-001",
            plan_id="plan-001",
            roles=["DEV", "QA"]
        )

        grpc_context = Mock()
        response = await orchestrator_servicer.DeriveSubtasks(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response.total_tasks == 0

    @pytest.mark.asyncio
    async def test_get_task_context_unimplemented(self, orchestrator_servicer):
        """Test GetTaskContext returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetTaskContextRequest(
            task_id="task-001",
            case_id="case-001",
            role="DEV",
            phase="BUILD"
        )

        grpc_context = Mock()
        response = await orchestrator_servicer.GetTaskContext(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response.token_count == 0

    @pytest.mark.asyncio
    async def test_process_planning_event_unimplemented(self, orchestrator_servicer):
        """Test ProcessPlanningEvent returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.PlanningEventRequest(
            event_type="TRANSITION",
            case_id="case-001",
            from_state="DRAFT",
            to_state="BUILD"
        )

        grpc_context = Mock()
        response = await orchestrator_servicer.ProcessPlanningEvent(request, grpc_context)

        grpc_context.set_code.assert_called_once_with(grpc.StatusCode.UNIMPLEMENTED)
        assert response.processed is False

