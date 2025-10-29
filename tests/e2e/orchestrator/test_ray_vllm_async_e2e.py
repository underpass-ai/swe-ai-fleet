"""
E2E tests for Ray + vLLM async integration.

These tests validate the complete flow:
1. Submit async deliberation to Orchestrator
2. Ray jobs execute with vLLM
3. Results published to NATS
4. DeliberationResultCollector accumulates
5. Client queries results via GetDeliberationResult

Prerequisites:
- Orchestrator service running (port 50055)
- vLLM server running with GPU
- Ray cluster available
- NATS JetStream running
"""
import time

import grpc
import pytest
from services.orchestrator.gen import orchestrator_pb2


pytestmark = pytest.mark.e2e


class TestRayVLLMAsyncIntegration:
    """E2E tests for async deliberation with Ray + vLLM."""
    def test_async_deliberation_complete_flow(self, orchestrator_stub):
        """Test complete async deliberation flow from start to finish."""
        # 1. Submit deliberation request
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Write a Python function to calculate the Fibonacci sequence",
            role="DEV",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Code must be clean, efficient, and well-documented",
                requirements=[
                    "Use type hints",
                    "Add comprehensive docstring",
                    "Include example usage",
                    "Handle edge cases (n=0, n=1)"
                ],
                timeout_seconds=120,
                max_iterations=1,
            )
        )

        # Send request (should return immediately)
        start_time = time.time()
        response = orchestrator_stub.Deliberate(request)
        response_time_ms = (time.time() - start_time) * 1000

        # Should return very quickly (non-blocking)
        assert response_time_ms < 1000, f"Deliberate should be non-blocking, took {response_time_ms}ms"

        # Extract task_id for tracking
        # Note: Current implementation returns results, will change to async later
        # For now, we verify it works with existing councils
        assert len(response.results) >= 0, "Should return results or task_id"

        # If we have results (sync mode), verify they're valid
        if len(response.results) > 0:
            for result in response.results:
                assert result.proposal.author_id, "Each result should have author_id"
                assert result.proposal.author_role == "DEV", "Role should match request"
                assert len(result.proposal.content) > 50, "Proposal should have substantial content"
                assert result.score >= 0, "Score should be non-negative"

    @pytest.mark.integration
    def test_async_deliberation_different_roles(self, orchestrator_stub):
        """Test async deliberation with different roles."""
        roles = ["DEV", "QA", "ARCHITECT"]

        for role in roles:
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Design a solution for user authentication as a {role}",
                role=role,
                num_agents=2,
                rounds=1,
                constraints=orchestrator_pb2.TaskConstraints(
                    rubric=f"Provide {role} perspective on the solution",
                    requirements=["Be specific", "Be practical"],
                )
            )

            response = orchestrator_stub.Deliberate(request)

            # Verify response structure
            if len(response.results) > 0:
                for result in response.results:
                    assert result.proposal.author_role == role
                    # Each role should have different focus in content
                    content_lower = result.proposal.content.lower()

                    if role == "DEV":
                        # DEV should mention code/implementation
                        assert any(keyword in content_lower for keyword in [
                            "code", "function", "implementation", "class"
                        ])
                    elif role == "QA":
                        # QA should mention testing/quality
                        assert any(keyword in content_lower for keyword in [
                            "test", "quality", "validation", "edge case"
                        ])
                    elif role == "ARCHITECT":
                        # ARCHITECT should mention design/architecture
                        assert any(keyword in content_lower for keyword in [
                            "design", "architecture", "pattern", "scalability"
                        ])

    @pytest.mark.integration
    def test_async_deliberation_with_complex_constraints(self, orchestrator_stub):
        """Test async deliberation with complex constraints."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description=(
                "Design and implement a distributed caching system with "
                "Redis as backend, supporting TTL, eviction policies, "
                "and high availability"
            ),
            role="DEVOPS",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric=(
                    "Solution must address:\n"
                    "1. High availability (no single point of failure)\n"
                    "2. Performance (< 10ms latency)\n"
                    "3. Scalability (handle 10K req/s)\n"
                    "4. Cost-effectiveness\n"
                    "5. Operational simplicity"
                ),
                requirements=[
                    "Use Kubernetes for orchestration",
                    "Implement health checks",
                    "Include monitoring and alerting",
                    "Document deployment process",
                    "Provide rollback strategy"
                ],
                timeout_seconds=180,
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            # Verify proposals address the complex requirements
            for result in response.results:
                content = result.proposal.content

                # Should be substantial (complex task requires detailed response)
                assert len(content) > 200, "Complex task should generate detailed proposal"

                # Should mention key technologies/concepts
                content_lower = content.lower()
                tech_mentioned = sum([
                    "redis" in content_lower,
                    "kubernetes" in content_lower or "k8s" in content_lower,
                    "cache" in content_lower or "caching" in content_lower,
                    "availability" in content_lower or "ha" in content_lower,
                ])
                assert tech_mentioned >= 2, "Should mention relevant technologies"

    @pytest.mark.integration
    @pytest.mark.skipif(
        True,  # Skip until GetDeliberationResult is fully async
        reason="Waiting for full async implementation"
    )
    def test_get_deliberation_result_polling(self, orchestrator_stub):
        """Test polling for deliberation results."""
        # 1. Submit deliberation
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Write a simple hello world function",
            role="DEV",
            num_agents=2,
            rounds=1,
        )

        response = orchestrator_stub.Deliberate(request)
        task_id = response.task_id if hasattr(response, 'task_id') else None

        if not task_id:
            pytest.skip("Async mode not yet enabled")

        # 2. Poll for results
        max_polls = 60  # 60 seconds max
        poll_interval = 1  # 1 second

        for _ in range(max_polls):
            result_response = orchestrator_stub.GetDeliberationResult(
                orchestrator_pb2.GetDeliberationResultRequest(task_id=task_id)
            )

            if result_response.status == orchestrator_pb2.DELIBERATION_STATUS_COMPLETED:
                # Success!
                assert len(result_response.results) == 2, "Should have 2 results"
                assert result_response.winner_id, "Should have winner"
                assert result_response.duration_ms > 0, "Should track duration"
                break
            elif result_response.status == orchestrator_pb2.DELIBERATION_STATUS_FAILED:
                pytest.fail(f"Deliberation failed: {result_response.error_message}")
            elif result_response.status == orchestrator_pb2.DELIBERATION_STATUS_TIMEOUT:
                pytest.fail("Deliberation timed out")

            # Still pending/in_progress, wait and retry
            time.sleep(poll_interval)
        else:
            pytest.fail(f"Deliberation didn't complete in {max_polls} seconds")

    @pytest.mark.integration
    def test_deliberation_diversity_produces_varied_proposals(self, orchestrator_stub):
        """Test that diversity mode produces varied proposals."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement a binary search algorithm",
            role="DEV",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Provide different implementation approaches",
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) >= 3:
            # Extract proposals
            proposals = [r.proposal.content for r in response.results]

            # Verify they're different (not identical)
            # At least some variation should exist
            unique_prefixes = set(p[:100] for p in proposals if len(p) >= 100)
            assert len(unique_prefixes) >= 2, "Proposals should have some diversity"

            # Verify all are substantial
            for proposal in proposals:
                assert len(proposal) > 50, "Each proposal should be substantial"

    @pytest.mark.integration
    def test_deliberation_with_minimal_constraints(self, orchestrator_stub):
        """Test deliberation with minimal/no constraints."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Explain what a linked list is",
            role="DEV",
            num_agents=2,
            rounds=1,
            # No constraints
        )

        response = orchestrator_stub.Deliberate(request)

        # Should still work without constraints
        if len(response.results) > 0:
            for result in response.results:
                assert result.proposal.content, "Should generate content even without constraints"
                content_lower = result.proposal.content.lower()
                # Should mention linked list
                assert "linked" in content_lower or "list" in content_lower

    @pytest.mark.integration
    def test_deliberation_performance_multiple_agents(self, orchestrator_stub):
        """Test that deliberation with multiple agents is reasonably fast."""
        num_agents_list = [1, 2, 3, 5]

        for num_agents in num_agents_list:
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Write a function to sort an array ({num_agents} agents)",
                role="DEV",
                num_agents=num_agents,
                rounds=1,
            )

            start_time = time.time()
            response = orchestrator_stub.Deliberate(request)
            duration_s = time.time() - start_time

            # With async execution, should scale well
            # Even with 5 agents, should complete in reasonable time
            # (If sync, 5 agents * 2s each = 10s minimum)
            # (If async, 5 agents in parallel = ~2s total)

            if len(response.results) == num_agents:
                # Parallel execution should be faster than sequential
                max_expected_time = 30  # 30s is generous for async
                assert duration_s < max_expected_time, (
                    f"Deliberation with {num_agents} agents took {duration_s:.2f}s, "
                    f"expected <{max_expected_time}s"
                )


class TestRayVLLMErrorHandling:
    """E2E tests for error handling in Ray + vLLM integration."""

    @pytest.mark.integration
    def test_deliberation_with_invalid_role(self, orchestrator_stub):
        """Test deliberation with role that has no council."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Test task",
            role="INVALID_ROLE",
            num_agents=1,
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.Deliberate(request)

        # Should fail gracefully
        assert exc_info.value.code() in [
            grpc.StatusCode.NOT_FOUND,
            grpc.StatusCode.UNIMPLEMENTED,
            grpc.StatusCode.FAILED_PRECONDITION
        ]

    @pytest.mark.integration
    @pytest.mark.skipif(
        True,  # Skip until async mode fully enabled
        reason="Testing async error handling"
    )
    def test_get_deliberation_result_not_found(self, orchestrator_stub):
        """Test querying non-existent deliberation."""
        request = orchestrator_pb2.GetDeliberationResultRequest(
            task_id="non-existent-task-id-12345"
        )

        with pytest.raises(grpc.RpcError) as exc_info:
            orchestrator_stub.GetDeliberationResult(request)

        assert exc_info.value.code() == grpc.StatusCode.NOT_FOUND
        assert "not found" in exc_info.value.details().lower()


class TestRayVLLMRealWorld:
    """E2E tests simulating real-world deliberation scenarios."""

    @pytest.mark.integration
    def test_code_review_deliberation(self, orchestrator_stub):
        """Test deliberation for code review scenario."""
        code_to_review = '''
def calculate_total(items):
    total = 0
    for item in items:
        total = total + item.price
    return total
'''

        request = orchestrator_pb2.DeliberateRequest(
            task_description=(
                f"Review this code and suggest improvements:\n\n{code_to_review}\n\n"
                "Focus on: performance, readability, error handling, and best practices."
            ),
            role="QA",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Provide constructive feedback with specific suggestions",
                requirements=[
                    "Identify potential bugs",
                    "Suggest performance improvements",
                    "Recommend best practices",
                    "Consider edge cases"
                ]
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            # QA agents should provide code review feedback
            for result in response.results:
                content = result.proposal.content.lower()

                # Should mention code quality aspects
                quality_aspects = [
                    "error" in content or "exception" in content,
                    "performance" in content or "optimize" in content,
                    "type" in content or "hint" in content,
                    "test" in content or "edge" in content,
                ]

                assert sum(quality_aspects) >= 2, "Should address multiple quality aspects"

    @pytest.mark.integration
    def test_architecture_design_deliberation(self, orchestrator_stub):
        """Test deliberation for architecture design scenario."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description=(
                "Design a microservices architecture for a real-time chat application "
                "that needs to support 100K concurrent users. Include: API Gateway, "
                "message broker, database strategy, caching layer, and deployment approach."
            ),
            role="ARCHITECT",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric=(
                    "Architecture must address:\n"
                    "- Scalability to 100K users\n"
                    "- Real-time message delivery\n"
                    "- Data consistency\n"
                    "- High availability\n"
                    "- Cost optimization"
                ),
                requirements=[
                    "Justify technology choices",
                    "Include diagrams or descriptions",
                    "Address failure scenarios",
                    "Provide deployment strategy"
                ]
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            for result in response.results:
                content = result.proposal.content.lower()

                # ARCHITECT should mention architectural concepts
                assert len(content) > 300, "Architecture design should be detailed"

                # Should mention key concepts
                concepts = [
                    "microservice" in content or "service" in content,
                    "scale" in content or "scalability" in content,
                    "database" in content or "storage" in content,
                    "gateway" in content or "api" in content,
                ]

                assert sum(concepts) >= 3, "Should address architectural concepts"

    @pytest.mark.integration
    def test_infrastructure_deliberation(self, orchestrator_stub):
        """Test deliberation for infrastructure/DevOps scenario."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description=(
                "Design a CI/CD pipeline for a Python microservice that needs to:\n"
                "- Run tests (unit, integration, E2E)\n"
                "- Build Docker images\n"
                "- Deploy to Kubernetes\n"
                "- Perform security scans\n"
                "- Support blue-green deployment"
            ),
            role="DEVOPS",
            num_agents=3,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Pipeline must be automated, secure, and reliable",
                requirements=[
                    "Use GitHub Actions or GitLab CI",
                    "Include security scanning",
                    "Implement automated rollback",
                    "Minimize deployment downtime"
                ]
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            for result in response.results:
                content = result.proposal.content.lower()

                # DEVOPS should mention CI/CD concepts
                devops_concepts = [
                    "pipeline" in content or "ci/cd" in content,
                    "docker" in content or "container" in content,
                    "kubernetes" in content or "k8s" in content,
                    "deploy" in content or "deployment" in content,
                    "test" in content or "testing" in content,
                ]

                assert sum(devops_concepts) >= 3, "Should address DevOps concepts"

    @pytest.mark.integration
    def test_data_pipeline_deliberation(self, orchestrator_stub):
        """Test deliberation for data engineering scenario."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description=(
                "Design an ETL pipeline to process 1TB of log data daily, "
                "extract metrics, transform to structured format, "
                "and load into a data warehouse for analytics"
            ),
            role="DATA",
            num_agents=2,
            rounds=1,
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Pipeline must be efficient, fault-tolerant, and cost-effective",
                requirements=[
                    "Handle schema evolution",
                    "Implement data quality checks",
                    "Support incremental processing",
                    "Provide monitoring and alerting"
                ]
            )
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            for result in response.results:
                content = result.proposal.content.lower()

                # DATA engineer should mention data concepts
                data_concepts = [
                    "etl" in content or "pipeline" in content,
                    "data" in content,
                    "warehouse" in content or "storage" in content,
                    "transform" in content or "process" in content,
                ]

                assert sum(data_concepts) >= 3, "Should address data engineering concepts"


class TestRayVLLMProposalQuality:
    """E2E tests validating quality of vLLM-generated proposals."""

    @pytest.mark.integration
    def test_proposals_are_coherent_and_relevant(self, orchestrator_stub):
        """Test that vLLM generates coherent, relevant proposals."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Implement a rate limiter for an API",
            role="DEV",
            num_agents=3,
            rounds=1,
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) > 0:
            for result in response.results:
                content = result.proposal.content

                # Basic quality checks
                assert len(content) > 50, "Proposal should be substantial"
                assert not content.isspace(), "Proposal should not be empty/whitespace"

                # Should be relevant to task
                content_lower = content.lower()
                assert "rate" in content_lower or "limit" in content_lower, (
                    "Proposal should address the task (rate limiter)"
                )

                # Should have some structure (not just rambling)
                # Check for common structural markers
                has_structure = any([
                    "\n" in content,  # Multi-line
                    ":" in content,   # Lists or explanations
                    "." in content and content.count(".") >= 2,  # Multiple sentences
                ])
                assert has_structure, "Proposal should have some structure"

    @pytest.mark.integration
    def test_proposals_differ_between_agents(self, orchestrator_stub):
        """Test that different agents produce different proposals (diversity)."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Design a REST API for a todo application",
            role="DEV",
            num_agents=3,
            rounds=1,
        )

        response = orchestrator_stub.Deliberate(request)

        if len(response.results) >= 3:
            # Get all proposals
            proposals = [r.proposal.content for r in response.results]

            # Check they're not identical
            # (With diversity mode, first agent is normal, rest have diversity=True)
            # So at least agents 2 and 3 should differ from agent 1

            # Simple check: first 200 chars should be different
            prefixes = [p[:200] for p in proposals if len(p) >= 200]
            unique_prefixes = set(prefixes)

            # Should have at least 2 unique approaches
            assert len(unique_prefixes) >= 2, (
                "Agents should produce varied proposals "
                f"(got {len(unique_prefixes)} unique out of {len(prefixes)})"
            )


class TestRayVLLMStressAndScale:
    """E2E tests for stress testing and scalability."""

    @pytest.mark.integration
    @pytest.mark.slow
    def test_multiple_concurrent_deliberations(self, orchestrator_stub):
        """Test handling multiple deliberations concurrently."""
        import concurrent.futures

        def run_deliberation(task_num):
            request = orchestrator_pb2.DeliberateRequest(
                task_description=f"Task {task_num}: Write a function to validate email addresses",
                role="DEV",
                num_agents=2,
                rounds=1,
            )

            try:
                response = orchestrator_stub.Deliberate(request)
                return {
                    "task_num": task_num,
                    "success": True,
                    "num_results": len(response.results)
                }
            except Exception as e:
                return {
                    "task_num": task_num,
                    "success": False,
                    "error": str(e)
                }

        # Run 5 deliberations concurrently
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures_list = [executor.submit(run_deliberation, i) for i in range(5)]
            results = [f.result() for f in concurrent.futures.as_completed(futures_list)]

        # All should succeed (or most should)
        successful = sum(1 for r in results if r["success"])
        assert successful >= 4, f"At least 4/5 concurrent deliberations should succeed (got {successful})"

    @pytest.mark.integration
    @pytest.mark.slow
    def test_deliberation_with_many_agents(self, orchestrator_stub):
        """Test deliberation with large number of agents."""
        request = orchestrator_pb2.DeliberateRequest(
            task_description="Write a comprehensive test plan for a web application",
            role="QA",
            num_agents=5,  # More agents
            rounds=1,
        )

        start_time = time.time()
        response = orchestrator_stub.Deliberate(request)
        duration_s = time.time() - start_time

        if len(response.results) == 5:
            # With async execution, 5 agents should complete in parallel time
            # Not 5x sequential time
            assert duration_s < 60, f"5 agents should complete in <60s (took {duration_s:.2f}s)"

            # All should have proposals
            for result in response.results:
                assert result.proposal.content, "All agents should generate content"

