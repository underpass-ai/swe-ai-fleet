"""
Simple integration tests for Orchestrator Service.
These tests expect the service to be already running (via docker-compose or manually).
No testcontainers required - just pure gRPC client tests.
"""

import os
import time

import grpc
import pytest

# Mark all tests as integration tests and skip (require running service)
pytestmark = [
    pytest.mark.integration,
    pytest.mark.skip(reason="Requires Orchestrator service running (manual setup)")
]


@pytest.fixture(scope="module")
def orchestrator_host():
    """Get orchestrator host from environment or default to localhost."""
    return os.getenv("ORCHESTRATOR_HOST", "localhost")


@pytest.fixture(scope="module")
def orchestrator_port():
    """Get orchestrator port from environment or default to 50055."""
    return int(os.getenv("ORCHESTRATOR_PORT", "50055"))


@pytest.fixture(scope="module")
def grpc_channel(orchestrator_host, orchestrator_port):
    """Create a gRPC channel to the orchestrator service."""
    address = f"{orchestrator_host}:{orchestrator_port}"
    channel = grpc.insecure_channel(address)
    
    # Wait for channel to be ready
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
    except grpc.FutureTimeoutError:
        pytest.skip(f"Orchestrator service not available at {address}")
    
    yield channel
    channel.close()


@pytest.fixture
def orchestrator_stub(grpc_channel):
    """Create an Orchestrator Service stub."""
    from services.orchestrator.gen import orchestrator_pb2_grpc
    return orchestrator_pb2_grpc.OrchestratorServiceStub(grpc_channel)


class TestBasicConnectivity:
    """Test basic connectivity to the service."""

    def test_service_is_reachable(self, grpc_channel):
        """Test that we can connect to the service."""
        assert grpc_channel is not None

    def test_get_status(self, orchestrator_stub):
        """Test GetStatus RPC - most basic check."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        response = orchestrator_stub.GetStatus(request)

        assert response is not None
        assert response.status == "healthy"
        assert response.uptime_seconds >= 0


class TestDeliberateBasic:
    """Basic tests for Deliberate RPC."""

    def test_deliberate_not_implemented(self, orchestrator_stub):
        """Test that Deliberate returns UNIMPLEMENTED when no agents configured."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Simple task",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Quality",
                requirements=[]
            )
        )

        # Should return UNIMPLEMENTED error since no agents are configured
        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Deliberate(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED
        assert "No agents configured" in exc_info.value.details()


class TestOrchestrateBasic:
    """Basic tests for Orchestrate RPC."""

    def test_orchestrate_not_implemented(self, orchestrator_stub):
        """Test that Orchestrate returns UNIMPLEMENTED when no agents configured."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="test-001",
            task_description="Test task",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Quality",
                requirements=[]
            )
        )

        # Should return UNIMPLEMENTED error since no agents are configured
        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Orchestrate(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED
        assert "No agents configured" in exc_info.value.details()


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_role(self, orchestrator_stub):
        """Test with invalid role (also returns UNIMPLEMENTED without agents)."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test",
            role="INVALID_ROLE",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Deliberate(request)
        
        # Without agents configured, any role returns UNIMPLEMENTED
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED


class TestNewAPIs:
    """Test new RPCs from API refactor."""

    def test_list_councils(self, orchestrator_stub):
        """Test ListCouncils RPC."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.ListCouncilsRequest(
            role_filter="",
            include_agents=False
        )

        response = orchestrator_stub.ListCouncils(request)

        assert response is not None
        assert isinstance(response, orchestrator_pb2.ListCouncilsResponse)
        # Currently empty since no agents configured
        assert len(response.councils) == 0

    def test_register_agent_not_implemented(self, orchestrator_stub):
        """Test RegisterAgent returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.RegisterAgentRequest(
            agent_id="test-agent-001",
            role="DEV"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.RegisterAgent(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED

    def test_derive_subtasks_not_implemented(self, orchestrator_stub):
        """Test DeriveSubtasks returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeriveSubtasksRequest(
            case_id="case-001",
            plan_id="plan-001",
            roles=["DEV", "QA"]
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.DeriveSubtasks(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED

    def test_get_task_context_not_implemented(self, orchestrator_stub):
        """Test GetTaskContext returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetTaskContextRequest(
            task_id="task-001",
            case_id="case-001",
            role="DEV",
            phase="BUILD"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.GetTaskContext(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED

    def test_process_planning_event_not_implemented(self, orchestrator_stub):
        """Test ProcessPlanningEvent returns UNIMPLEMENTED."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.PlanningEventRequest(
            event_type="TRANSITION",
            case_id="case-001",
            from_state="DRAFT",
            to_state="BUILD",
            timestamp_ms=int(time.time() * 1000)
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.ProcessPlanningEvent(request)
        
        assert exc_info.value.code() == grpc.StatusCode.UNIMPLEMENTED

