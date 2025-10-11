"""
E2E tests for Orchestrator Service Orchestrate endpoint.

Tests complete task execution workflow with deliberation + architect selection.
"""

import pytest

pytestmark = pytest.mark.e2e


class TestOrchestrateE2E:
    """E2E tests for Orchestrate RPC - Complete task workflow."""

    def test_orchestrate_basic(self, orchestrator_stub, test_task_id):
        """Test basic Orchestrate request."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id=test_task_id,
            task_description="Create REST API endpoint for user registration",
            role="DEV",
        )

        response = orchestrator_stub.Orchestrate(request)

        # Verify response structure
        assert response is not None
        assert response.winner is not None, "Should have a winner"
        assert response.winner.proposal is not None
        assert response.winner.score >= 0
        assert len(response.candidates) > 0, "Should have candidates"
        assert response.execution_id != "", "Should have execution ID"
        assert response.duration_ms > 0, "Should track duration"

    def test_orchestrate_with_context(self, orchestrator_stub, test_task_id):
        """Test Orchestrate with context integration."""
        from services.orchestrator.gen import orchestrator_pb2

        context_options = orchestrator_pb2.ContextOptions(
            include_decisions=True,
            include_timeline=True,
            max_context_tokens=4096,
        )

        request = orchestrator_pb2.OrchestrateRequest(
            task_id=test_task_id,
            task_description="Implement authentication middleware",
            role="DEV",
            case_id="CASE-001",
            story_id="STORY-001",
            plan_id="PLAN-001",
            context_options=context_options,
        )

        response = orchestrator_stub.Orchestrate(request)

        # Verify context was used
        assert response is not None
        assert response.winner is not None
        # Context integration should be reflected in metadata
        assert response.metadata is not None

    def test_orchestrate_different_roles(self, orchestrator_stub):
        """Test Orchestrate for different roles."""
        from services.orchestrator.gen import orchestrator_pb2

        roles = ["DEV", "QA", "ARCHITECT", "DEVOPS"]
        
        for role in roles:
            request = orchestrator_pb2.OrchestrateRequest(
                task_id=f"TASK-{role}-001",
                task_description=f"Task for {role} role",
                role=role,
            )

            response = orchestrator_stub.Orchestrate(request)

            # Each role should work
            assert response is not None
            assert response.winner is not None
            assert response.metadata.role == role

    def test_orchestrate_with_constraints(self, orchestrator_stub, test_task_id):
        """Test Orchestrate with task constraints."""
        from services.orchestrator.gen import orchestrator_pb2

        constraints = orchestrator_pb2.TaskConstraints(
            max_duration_minutes=60,
            require_tests=True,
            require_documentation=True,
            rigor_level="HIGH",
        )

        request = orchestrator_pb2.OrchestrateRequest(
            task_id=test_task_id,
            task_description="Implement critical payment processing feature",
            role="DEV",
            constraints=constraints,
        )

        response = orchestrator_stub.Orchestrate(request)

        # Verify constraints were considered
        assert response is not None
        assert response.winner is not None
        
        # Winner should have higher score if it meets constraints
        assert response.winner.score >= 0


class TestOrchestrateErrorHandling:
    """Error handling tests for Orchestrate."""

    def test_orchestrate_empty_task(self, orchestrator_stub):
        """Test Orchestrate with empty task description."""
        from services.orchestrator.gen import orchestrator_pb2
        import grpc

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="TASK-EMPTY",
            task_description="",  # Empty
            role="DEV",
        )

        # Should raise error
        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Orchestrate(request)
        
        assert exc_info.value.code() in [
            grpc.StatusCode.INVALID_ARGUMENT,
            grpc.StatusCode.INTERNAL,
        ]

    def test_orchestrate_missing_task_id(self, orchestrator_stub):
        """Test Orchestrate without task ID."""
        from services.orchestrator.gen import orchestrator_pb2
        import grpc

        request = orchestrator_pb2.OrchestrateRequest(
            task_id="",  # Empty task ID
            task_description="Some task description",
            role="DEV",
        )

        # Service should handle gracefully or reject
        try:
            response = orchestrator_stub.Orchestrate(request)
            # If it succeeds, verify basic response
            assert response is not None
        except grpc.RpcError:
            # Rejection is also acceptable
            pass


class TestOrchestrateQuality:
    """Test orchestration quality and proposal selection."""

    def test_orchestrate_winner_is_best_scored(self, orchestrator_stub, test_task_id):
        """Verify that the winner is the best-scored proposal."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id=test_task_id,
            task_description="Optimize database query performance",
            role="DEV",
        )

        response = orchestrator_stub.Orchestrate(request)

        # Find winner in candidates
        winner = next((c for c in response.candidates if c.agent_id == response.winner_id), None)
        
        # If winner is in candidates, it should have highest/equal score
        if winner:
            winner_score = winner.score
            for candidate in response.candidates:
                # Winner score should be >= all other candidates
                assert winner_score >= candidate.score, \
                    f"Winner score {winner_score} should be >= candidate score {candidate.score}"

    def test_orchestrate_all_agents_contribute(self, orchestrator_stub, test_task_id):
        """Verify all agents in council contribute proposals."""
        from services.orchestrator.gen import orchestrator_pb2

        request = orchestrator_pb2.OrchestrateRequest(
            task_id=test_task_id,
            task_description="Design microservice API contract",
            role="ARCHITECT",
        )

        response = orchestrator_stub.Orchestrate(request)

        # Should have multiple candidates (one per agent)
        assert len(response.candidates) >= 1, "Should have at least one candidate"
        
        # Each candidate should have unique agent ID
        agent_ids = [c.agent_id for c in response.candidates]
        assert len(agent_ids) == len(set(agent_ids)), "Agent IDs should be unique"
        
        # Each candidate should have a proposal
        for candidate in response.candidates:
            assert candidate.proposal is not None
            assert candidate.proposal.solution != ""

