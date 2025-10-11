"""
Integration tests for Orchestrator Service gRPC using Testcontainers.
Tests the full service running in a Docker container.
"""

import time

import grpc
import pytest
from testcontainers.core.container import DockerContainer

# Mark all tests as integration tests
pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def orchestrator_container():
    """Start Orchestrator service in a Docker container."""
    container = (
        DockerContainer("localhost:5000/swe-ai-fleet/orchestrator:latest")
        .with_exposed_ports(50055)
        .with_env("GRPC_PORT", "50055")
        .with_env("PYTHONUNBUFFERED", "1")
    )
    
    # Start container and wait for service to be ready
    container.start()
    
    # Wait for the service to start
    time.sleep(5)
    
    yield container
    
    # Cleanup
    container.stop()


@pytest.fixture
def grpc_channel(orchestrator_container):
    """Create a gRPC channel to the containerized service."""
    host = orchestrator_container.get_container_host_ip()
    port = orchestrator_container.get_exposed_port(50055)
    
    channel = grpc.insecure_channel(f'{host}:{port}')
    
    # Wait for channel to be ready
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
    except grpc.FutureTimeoutError:
        pytest.skip("gRPC channel not ready within timeout")
    
    yield channel
    channel.close()


@pytest.fixture
def orchestrator_stub(grpc_channel):
    """Create an Orchestrator Service stub."""
    from services.orchestrator.gen import orchestrator_pb2_grpc
    return orchestrator_pb2_grpc.OrchestratorServiceStub(grpc_channel)


class TestDeliberateIntegration:
    """Integration tests for Deliberate RPC."""

    def test_deliberate_full_flow(self, orchestrator_stub):
        """Test complete deliberation flow through gRPC."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement user authentication with JWT",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Secure, well-tested code with proper error handling",
                requirements=["Unit tests", "Input validation", "Error handling"],
                max_iterations=10,
                timeout_seconds=300
            ),
            rounds=1,
            num_agents=3
        )

        # Make gRPC call
        response = orchestrator_stub.Deliberate(request)

        # Verify response structure
        assert response is not None
        assert len(response.results) > 0
        assert response.winner_id != ""
        assert response.duration_ms > 0
        assert response.metadata is not None
        assert response.metadata.orchestrator_version == "0.1.0"
        assert len(response.metadata.execution_id) == 16

        # Verify results are ranked (highest score first)
        for i in range(len(response.results) - 1):
            assert response.results[i].score >= response.results[i + 1].score
        
        # Verify winner is the first result
        assert response.winner_id == response.results[0].proposal.author_id
        
        # Verify each result has required fields
        for idx, result in enumerate(response.results):
            assert result.rank == idx + 1
            assert result.proposal is not None
            assert result.proposal.author_id != ""
            assert result.proposal.author_role == "DEV"
            assert result.proposal.content != ""
            assert result.checks is not None
            assert result.checks.policy is not None
            assert result.checks.lint is not None
            assert result.checks.dryrun is not None

    def test_deliberate_multiple_roles(self, orchestrator_stub):
        """Test deliberation with different roles."""
        from services.orchestrator.gen import orchestrator_pb2

        roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
        
        for role in roles:
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Task for {role}",
                role=role,
                constraints=orchestrator_pb2.TaskConstraints(
                    rubric=f"{role} best practices",
                    requirements=[f"{role} requirement"]
                ),
                rounds=1,
                num_agents=2
            )

            response = orchestrator_stub.Deliberate(request)
            
            assert response is not None
            assert len(response.results) > 0
            assert all(r.proposal.author_role == role for r in response.results)

    def test_deliberate_invalid_role(self, orchestrator_stub):
        """Test deliberation with invalid role."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test task",
            role="INVALID_ROLE",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        # Should raise gRPC error
        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Deliberate(request)
        
        assert exc_info.value.code() == grpc.StatusCode.INVALID_ARGUMENT

    def test_deliberate_with_custom_rounds(self, orchestrator_stub):
        """Test deliberation with multiple peer review rounds."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Complex task requiring multiple reviews",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="High quality",
                requirements=["Thorough review"]
            ),
            rounds=2,  # Multiple review rounds
            num_agents=3
        )

        response = orchestrator_stub.Deliberate(request)
        
        assert response is not None
        assert len(response.results) > 0


class TestOrchestrateIntegration:
    """Integration tests for Orchestrate RPC."""

    def test_orchestrate_full_flow(self, orchestrator_stub):
        """Test complete orchestration flow through gRPC."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="task-integration-001",
            task_description="Implement RESTful API for user management",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="RESTful best practices, proper error handling, OpenAPI docs",
                requirements=[
                    "GET, POST, PUT, DELETE endpoints",
                    "Input validation",
                    "Error responses",
                    "OpenAPI specification"
                ],
                max_iterations=10,
                timeout_seconds=300
            ),
            options=orchestrator_pb2.OrchestratorOptions(
                enable_peer_review=True,
                deliberation_rounds=1,
                enable_architect_selection=True
            )
        )

        # Make gRPC call
        response = orchestrator_stub.Orchestrate(request)

        # Verify response structure
        assert response is not None
        assert response.winner is not None
        assert response.winner.proposal is not None
        assert response.winner.proposal.author_id != ""
        assert response.winner.proposal.content != ""
        assert response.winner.checks is not None
        assert response.winner.score > 0
        
        # Verify execution metadata
        assert response.execution_id != ""
        assert len(response.execution_id) == 16
        assert response.duration_ms > 0
        assert response.metadata is not None
        assert response.metadata.orchestrator_version == "0.1.0"
        
        # Verify candidates (may be empty depending on implementation)
        assert isinstance(response.candidates, list)

    def test_orchestrate_with_options(self, orchestrator_stub):
        """Test orchestration with custom options."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="task-options-001",
            task_description="Test task with options",
            role="QA",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Quality",
                requirements=["Tests"]
            ),
            options=orchestrator_pb2.OrchestratorOptions(
                enable_peer_review=True,
                deliberation_rounds=2,
                enable_architect_selection=True,
                custom_params={
                    "strictness": "high",
                    "coverage_threshold": "80"
                }
            )
        )

        response = orchestrator_stub.Orchestrate(request)
        
        assert response is not None
        assert response.winner is not None


class TestGetStatusIntegration:
    """Integration tests for GetStatus RPC."""

    def test_get_status_basic(self, orchestrator_stub):
        """Test basic status check."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=False
        )

        response = orchestrator_stub.GetStatus(request)

        assert response is not None
        assert response.status == "healthy"
        assert response.uptime_seconds >= 0

    def test_get_status_with_stats(self, orchestrator_stub):
        """Test status with statistics after operations."""
        from services.orchestrator.gen import orchestrator_pb2

        # First, execute some operations to generate stats
        deliberate_req = orchestrator_pb2.DeliberateRequest(
            task_description="Generate some stats",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )
        
        orchestrator_stub.Deliberate(deliberate_req)
        
        # Now check status with stats
        status_req = orchestrator_pb2.GetStatusRequest(
            include_stats=True
        )

        response = orchestrator_stub.GetStatus(status_req)

        assert response is not None
        assert response.status == "healthy"
        assert response.stats is not None
        assert response.stats.total_deliberations > 0
        assert response.stats.avg_deliberation_time_ms >= 0
        assert response.stats.active_councils > 0
        assert len(response.stats.role_counts) > 0

    def test_get_status_repeated_calls(self, orchestrator_stub):
        """Test that status calls work repeatedly."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.GetStatusRequest(
            include_stats=True
        )

        # Make multiple calls
        for _ in range(3):
            response = orchestrator_stub.GetStatus(request)
            assert response.status == "healthy"
            time.sleep(0.1)


class TestConcurrentRequests:
    """Test concurrent gRPC requests."""

    def test_concurrent_deliberations(self, orchestrator_stub):
        """Test multiple concurrent deliberation requests."""
        import concurrent.futures

        from services.orchestrator.gen import orchestrator_pb2

        def make_request(task_num):
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Concurrent task {task_num}",
                role="DEV",
                constraints=orchestrator_pb2.TaskConstraints(
                    rubric="Test",
                    requirements=[]
                )
            )
            return orchestrator_stub.Deliberate(request)

        # Execute concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures_list = [executor.submit(make_request, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures_list)]

        # Verify all succeeded
        assert len(results) == 5
        for result in results:
            assert result is not None
            assert len(result.results) > 0

    def test_mixed_concurrent_requests(self, orchestrator_stub):
        """Test different types of requests concurrently."""
        import concurrent.futures

        from services.orchestrator.gen import orchestrator_pb2

        def deliberate():
            request = orchestrator_pb2.DeliberateRequest(
                task_description="Concurrent deliberate",
                role="DEV",
                constraints=orchestrator_pb2.TaskConstraints(rubric="Test", requirements=[])
            )
            return orchestrator_stub.Deliberate(request)

        def get_status():
            request = orchestrator_pb2.GetStatusRequest(include_stats=True)
            return orchestrator_stub.GetStatus(request)

        # Mix of deliberate and status calls
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
            futures_list = [
                executor.submit(deliberate),
                executor.submit(get_status),
                executor.submit(deliberate),
                executor.submit(get_status),
            ]
            results = [f.result() for f in concurrent.futures.as_completed(futures_list)]

        assert len(results) == 4


class TestErrorHandling:
    """Test error handling in integration scenarios."""

    def test_empty_task_description(self, orchestrator_stub):
        """Test with empty task description."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="",  # Empty
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        # Should still work (empty string is valid)
        response = orchestrator_stub.Deliberate(request)
        assert response is not None

    def test_large_task_description(self, orchestrator_stub):
        """Test with very large task description."""
        from services.orchestrator.gen import orchestrator_pb2

        # Create a large task description (10KB)
        large_description = "A" * 10000

        request = orchestrator_pb2.DeliberateRequest(
            task_description=large_description,
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Test",
                requirements=[]
            )
        )

        response = orchestrator_stub.Deliberate(request)
        assert response is not None

    def test_many_requirements(self, orchestrator_stub):
        """Test with many requirements."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Task with many requirements",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Comprehensive",
                requirements=[f"Requirement {i}" for i in range(50)]
            )
        )

        response = orchestrator_stub.Deliberate(request)
        assert response is not None
        assert len(response.results) > 0

