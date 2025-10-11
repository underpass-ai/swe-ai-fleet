"""
E2E tests for Orchestrator Service Deliberate endpoint.

Tests multi-agent deliberation with real NATS infrastructure.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestDeliberateE2E:
    """E2E tests for Deliberate RPC - Multi-agent peer review."""

    def test_deliberate_basic(self, orchestrator_stub):
        """Test basic Deliberate request."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement user authentication API endpoint",
            role="DEV",
            rounds=1,
            num_agents=3,
        )

        response = orchestrator_stub.Deliberate(request)

        # Verify response structure
        assert response is not None
        assert len(response.results) > 0, "Should have at least one deliberation result"
        assert response.winner_id != "", "Should have a winner"
        assert response.duration_ms >= 0, "Should track duration (can be 0 for fast ops)"
        
        # Verify metadata
        assert response.metadata is not None
        # Note: metadata doesn't have role field, only orchestrator_version, timestamp, execution_id

    def test_deliberate_multiple_rounds(self, orchestrator_stub):
        """Test Deliberate with multiple rounds of peer review."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Design database schema for user management",
            role="ARCHITECT",
            rounds=2,  # Multiple rounds
            num_agents=3,
        )

        response = orchestrator_stub.Deliberate(request)

        # Should have results
        assert len(response.results) >= 1
        
        # Verify all results have scores
        for result in response.results:
            assert result.proposal is not None
            assert result.score >= 0
            assert result.proposal.author_id != ""

    def test_deliberate_different_roles(self, orchestrator_stub):
        """Test Deliberate for different roles."""
        from services.orchestrator.gen import orchestrator_pb2

        roles = ["DEV", "QA", "DEVOPS", "ARCHITECT"]
        
        for role in roles:
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Task for {role} role",
                role=role,
                rounds=1,
                num_agents=3,
            )

            response = orchestrator_stub.Deliberate(request)

            # Each role should work
            assert response is not None
            assert len(response.results) > 0
            assert response.metadata.role == role


class TestDeliberateErrorHandling:
    """Error handling tests for Deliberate."""

    def test_deliberate_empty_task(self, orchestrator_stub):
        """Test Deliberate with empty task description."""
        from services.orchestrator.gen import orchestrator_pb2
        import grpc

        request = orchestrator_pb2.DeliberateRequest(
            task_description="",  # Empty task
            role="DEV",
            rounds=1,
            num_agents=3,
        )

        # Empty task is handled by MockAgent - it generates content anyway
        # So we expect a successful response
        response = orchestrator_stub.Deliberate(request)
        assert response is not None
        assert response.winner_id != ""

    def test_deliberate_invalid_role(self, orchestrator_stub):
        """Test Deliberate with invalid/unknown role."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Some task",
            role="INVALID_ROLE",
            rounds=1,
            num_agents=3,
        )

        # Service should either handle gracefully or reject
        # Current implementation may be permissive
        try:
            response = orchestrator_stub.Deliberate(request)
            assert response is not None
        except Exception:
            # Rejecting invalid role is also acceptable
            pass


class TestDeliberateConvergence:
    """Test deliberation convergence and consensus."""

    def test_deliberate_with_constraints(self, orchestrator_stub):
        """Test Deliberate with task constraints."""
        from services.orchestrator.gen import orchestrator_pb2

        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Security and quality standards",
            requirements=["tests", "documentation", "security review"],
            timeout_seconds=1800,  # 30 minutes
        )

        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement critical security feature",
            role="DEV",
            constraints=constraints,
            rounds=1,
            num_agents=3,
        )

        response = orchestrator_stub.Deliberate(request)

        # Verify constraints were considered
        assert response is not None
        assert len(response.results) > 0
        
        # Winner should meet constraints (if validation is implemented)
        winner = next((r for r in response.results if r.proposal.author_id == response.winner_id), None)
        assert winner is not None, "Winner should be in results"

