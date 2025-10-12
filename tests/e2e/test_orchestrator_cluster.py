"""
E2E tests for Orchestrator service running in Kubernetes cluster.

These tests connect to the real Orchestrator service via kubectl port-forward
and validate the complete Ray + vLLM integration in production.

Prerequisites:
- Kubernetes cluster with swe-ai-fleet namespace
- Orchestrator service running
- kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055
"""
import pytest

from services.orchestrator.gen import orchestrator_pb2


@pytest.mark.e2e
class TestOrchestratorCluster:
    """E2E tests for Orchestrator in Kubernetes cluster."""
    
    def test_create_council(self, orchestrator_stub):
        """Test creating a council with vLLM agents in cluster."""
        council_config = orchestrator_pb2.CouncilConfig(
            deliberation_rounds=1,
            enable_peer_review=False
        )
        
        try:
            response = orchestrator_stub.CreateCouncil(
                orchestrator_pb2.CreateCouncilRequest(
                    role="DEV",
                    num_agents=3,
                    config=council_config
                )
            )
            
            assert response.council_id
            assert response.agents_created >= 3
            assert len(response.agent_ids) >= 3
            
        except Exception as e:
            if "ALREADY_EXISTS" in str(e):
                pytest.skip("Council already exists")
            else:
                raise
    
    def test_list_councils(self, orchestrator_stub):
        """Test listing councils in cluster."""
        response = orchestrator_stub.ListCouncils(
            orchestrator_pb2.ListCouncilsRequest()
        )
        
        assert len(response.councils) > 0
        
        # Should have at least DEV council
        roles = [c.role for c in response.councils]
        assert "DEV" in roles
    
    def test_deliberate_with_vllm_agents(self, orchestrator_stub):
        """Test deliberation with real vLLM agents in cluster."""
        task_description = "Write a Python function to calculate factorial"
        
        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Function must be recursive with type hints",
            requirements=[
                "Code must be clean",
                "Follow PEP 8",
                "Keep it simple"
            ],
            timeout_seconds=60,
            max_iterations=3
        )
        
        response = orchestrator_stub.Deliberate(
            orchestrator_pb2.DeliberateRequest(
                task_description=task_description,
                role="DEV",
                rounds=1,
                num_agents=3,
                constraints=constraints
            )
        )
        
        # Verify response
        assert len(response.results) >= 2, "Should get at least 2 proposals"
        
        for result in response.results:
            assert result.proposal.content
            assert len(result.proposal.content) > 50, "Proposal should have content"
            assert result.proposal.author_role == "DEV"
    
    def test_deliberate_different_roles(self, orchestrator_stub):
        """Test deliberation with different roles in cluster."""
        roles_to_test = ["DEV", "QA", "ARCHITECT"]
        
        for role in roles_to_test:
            # Create council if not exists
            try:
                orchestrator_stub.CreateCouncil(
                    orchestrator_pb2.CreateCouncilRequest(
                        role=role,
                        num_agents=3
                    )
                )
            except Exception:
                pass  # Already exists
            
            # Test deliberation
            response = orchestrator_stub.Deliberate(
                orchestrator_pb2.DeliberateRequest(
                    task_description=f"Task for {role} role",
                    role=role,
                    rounds=1,
                    num_agents=2,
                    constraints=orchestrator_pb2.TaskConstraints(
                        rubric=f"Requirements for {role}",
                        timeout_seconds=60
                    )
                )
            )
            
            assert len(response.results) >= 1, f"Should get results for {role}"
            assert response.results[0].proposal.author_role == role
    
    def test_proposal_quality(self, orchestrator_stub):
        """Test that proposals from cluster have good quality."""
        task_description = (
            "Implement a REST API endpoint for user authentication "
            "with JWT tokens and refresh token mechanism"
        )
        
        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Must include security best practices",
            requirements=[
                "Use bcrypt for password hashing",
                "Implement token refresh",
                "Add rate limiting",
                "Include error handling"
            ],
            timeout_seconds=120
        )
        
        response = orchestrator_stub.Deliberate(
            orchestrator_pb2.DeliberateRequest(
                task_description=task_description,
                role="DEV",
                rounds=1,
                num_agents=3,
                constraints=constraints
            )
        )
        
        # Verify proposals have relevant keywords
        keywords = ["auth", "token", "jwt", "password", "security", "api"]
        
        for result in response.results:
            content_lower = result.proposal.content.lower()
            matches = sum(1 for kw in keywords if kw in content_lower)
            assert matches >= 2, f"Proposal should mention at least 2 keywords: {keywords}"

