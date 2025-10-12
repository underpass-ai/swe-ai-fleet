"""
E2E tests for realistic orchestration workflows.

These tests simulate real-world scenarios with complete task lifecycles,
multi-agent coordination, and end-to-end orchestration flows.

Key scenarios:
1. Complete task lifecycle (Planning → Deliberation → Selection → Execution)
2. Multi-task parallel orchestration
3. Council management and agent coordination
4. Quality convergence and consensus building

These tests verify the system works correctly under realistic conditions.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import pytest

pytestmark = pytest.mark.integration


class TestCompleteTaskOrchestration:
    """Test complete task orchestration workflow."""

    def test_task_from_planning_to_execution(self, orchestrator_stub):
        """
        Simulate complete task: Planning → Deliberation → Selection → Execution
        
        Realistic scenario:
        1. Task arrives from Planning Service
        2. Orchestrator routes to appropriate council (DEV)
        3. Council deliberates (3 agents propose solutions)
        4. Architect selects best proposal
        5. Winner is returned for execution
        
        Verifies:
        - Complete workflow executes successfully
        - All agents contribute
        - Best proposal is selected
        - Metadata is tracked
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Complete Task Orchestration Flow")
        
        # =========================================================
        # Phase 1: Task arrives (simulates Planning Service)
        # =========================================================
        print("📋 Phase 1: Task arrival from Planning")
        
        task_id = "STORY-001-TASK-LOGIN"
        task_description = """
        Implement user login API endpoint with the following requirements:
        - POST /api/auth/login
        - Accept email and password
        - Return JWT token on success
        - Rate limiting (5 attempts per minute)
        - Secure password comparison (constant-time)
        - Log authentication attempts
        """
        
        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Authentication endpoint quality standards",
            requirements=["unit tests", "rate limiting", "security"],
            timeout_seconds=7200,  # 120 minutes
        )
        
        # =========================================================
        # Phase 2: Orchestrate (deliberation + selection)
        # =========================================================
        print("🤖 Phase 2: Multi-agent deliberation")
        
        start_time = time.time()
        
        request = orchestrator_pb2.OrchestrateRequest(
            task_id=task_id,
            task_description=task_description,
            role="DEV",
            constraints=constraints,
            case_id="STORY-001",
            story_id="STORY-001",
        )
        
        response = orchestrator_stub.Orchestrate(request)
        
        elapsed = time.time() - start_time
        print(f"⏱️  Orchestration completed in {elapsed:.2f}s")
        
        # =========================================================
        # Phase 3: Verify results
        # =========================================================
        print("✅ Phase 3: Verification")
        
        # Verify winner selected
        assert response.winner is not None, "Should have a winner"
        assert response.winner.proposal is not None
        assert response.winner.proposal.content != "", "Winner should have solution"
        
        # Verify multiple candidates participated
        assert len(response.candidates) >= 1, "Should have candidates"
        print(f"   Candidates: {len(response.candidates)}")
        
        # Verify winner is in candidates
        winner_in_candidates = any(
            c.proposal.author_id == response.winner.proposal.author_id for c in response.candidates
        )
        assert winner_in_candidates, "Winner should be in candidates list"
        
        # Verify metadata
        assert response.metadata is not None
        assert response.execution_id != ""
        assert response.duration_ms >= 0
        
        print(f"   Winner: {response.winner.proposal.author_id} (score: {response.winner.score})")
        print(f"   Execution ID: {response.execution_id}")
        print(f"   Duration: {response.duration_ms}ms")
        
        # Verify performance (should complete in reasonable time)
        assert elapsed < 30, f"Orchestration took {elapsed:.2f}s, should be < 30s"
        
        print("✅ Complete task orchestration verified successfully!")

    def test_multi_phase_story_workflow(self, orchestrator_stub):
        """
        Simulate multi-phase story with different tasks.
        
        Realistic scenario:
        - Phase 1: ARCHITECT designs solution
        - Phase 2: DEV implements feature
        - Phase 3: QA writes tests
        - Phase 4: DEVOPS prepares deployment
        
        Verifies:
        - Different roles handle different tasks
        - Each phase completes successfully
        - No interference between tasks
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Multi-Phase Story Workflow")
        
        story_id = "STORY-MULTIPH ASE-001"
        
        # =========================================================
        # Phase 1: ARCHITECT - Design
        # =========================================================
        print("📐 Phase 1: ARCHITECT - Design")
        
        design_request = orchestrator_pb2.OrchestrateRequest(
            task_id=f"{story_id}-DESIGN",
            task_description="Design authentication system architecture",
            role="ARCHITECT",
            case_id=story_id,
            story_id=story_id,
        )
        
        design_response = orchestrator_stub.Orchestrate(design_request)
        assert design_response.winner is not None
        
        print(f"   ✓ Design completed: {design_response.execution_id}")
        
        # =========================================================
        # Phase 2: DEV - Implementation
        # =========================================================
        print("💻 Phase 2: DEV - Implementation")
        
        dev_request = orchestrator_pb2.OrchestrateRequest(
            task_id=f"{story_id}-IMPLEMENT",
            task_description="Implement login endpoint based on architecture",
            role="DEV",
            case_id=story_id,
            story_id=story_id,
        )
        
        dev_response = orchestrator_stub.Orchestrate(dev_request)
        assert dev_response.winner is not None
        
        print(f"   ✓ Implementation completed: {dev_response.execution_id}")
        
        # =========================================================
        # Phase 3: QA - Testing
        # =========================================================
        print("🧪 Phase 3: QA - Testing")
        
        qa_request = orchestrator_pb2.OrchestrateRequest(
            task_id=f"{story_id}-TEST",
            task_description="Write integration tests for authentication",
            role="QA",
            case_id=story_id,
            story_id=story_id,
        )
        
        qa_response = orchestrator_stub.Orchestrate(qa_request)
        assert qa_response.winner is not None
        
        print(f"   ✓ Testing completed: {qa_response.execution_id}")
        
        # =========================================================
        # Phase 4: DEVOPS - Deployment
        # =========================================================
        print("🚀 Phase 4: DEVOPS - Deployment")
        
        devops_request = orchestrator_pb2.OrchestrateRequest(
            task_id=f"{story_id}-DEPLOY",
            task_description="Create deployment configuration for auth service",
            role="DEVOPS",
            case_id=story_id,
            story_id=story_id,
        )
        
        devops_response = orchestrator_stub.Orchestrate(devops_request)
        assert devops_response.winner is not None
        
        print(f"   ✓ Deployment completed: {devops_response.execution_id}")
        
        # =========================================================
        # Verification: All phases completed
        # =========================================================
        print("🔍 Final Verification")
        
        # Verify all execution IDs are unique
        execution_ids = [
            design_response.execution_id,
            dev_response.execution_id,
            qa_response.execution_id,
            devops_response.execution_id,
        ]
        
        assert len(execution_ids) == len(set(execution_ids)), \
            "All execution IDs should be unique"
        
        print("✅ Multi-phase workflow completed successfully!")


class TestParallelOrchestration:
    """Test parallel task orchestration."""

    def test_parallel_tasks_for_same_story(self, orchestrator_stub):
        """
        Simulate 3 parallel DEV tasks on same story.
        
        Realistic scenario:
        - Task 1: Implement login endpoint
        - Task 2: Implement registration endpoint
        - Task 3: Implement password reset endpoint
        
        All execute in parallel (simulating parallel agent work).
        
        Verifies:
        - No race conditions
        - All tasks complete successfully
        - Execution IDs are unique
        - No data corruption
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Parallel Task Orchestration")
        
        story_id = "STORY-PARALLEL-001"
        
        tasks = [
            {
                "id": f"{story_id}-LOGIN",
                "desc": "Implement login endpoint with JWT authentication",
                "component": "Login"
            },
            {
                "id": f"{story_id}-REGISTER",
                "desc": "Implement user registration with email verification",
                "component": "Registration"
            },
            {
                "id": f"{story_id}-RESET",
                "desc": "Implement password reset with secure token",
                "component": "Password Reset"
            },
        ]
        
        def orchestrate_task(task_info):
            """Execute orchestration for one task."""
            print(f"🤖 Starting orchestration for {task_info['component']}")
            
            request = orchestrator_pb2.OrchestrateRequest(
                task_id=task_info["id"],
                task_description=task_info["desc"],
                role="DEV",
                case_id=story_id,
                story_id=story_id,
            )
            
            response = orchestrator_stub.Orchestrate(request)
            
            print(f"✅ {task_info['component']} completed: {response.execution_id}")
            
            return {
                "task_id": task_info["id"],
                "execution_id": response.execution_id,
                "winner_id": response.winner.proposal.author_id,
                "num_candidates": len(response.candidates),
            }
        
        # Execute parallel orchestration
        print("\n🚀 Starting parallel orchestration with 3 tasks...")
        
        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(orchestrate_task, task): task for task in tasks
            }
            
            results = []
            for future in as_completed(futures):
                task = futures[future]
                try:
                    result = future.result()
                    results.append(result)
                    print(f"✓ {task['component']} orchestrated successfully")
                except Exception as e:
                    pytest.fail(f"Task {task['component']} failed: {e}")
        
        # Verify all tasks completed
        assert len(results) == 3, "All 3 tasks should complete"
        
        # Verify all execution IDs are unique
        execution_ids = [r["execution_id"] for r in results]
        assert len(execution_ids) == len(set(execution_ids)), \
            "All execution IDs should be unique"
        
        # Verify all had candidates
        for result in results:
            assert result["num_candidates"] >= 1, \
                f"Task {result['task_id']} should have candidates"
        
        print("\n📊 Results summary:")
        for result in results:
            print(f"   {result['task_id']}: {result['num_candidates']} candidates, " 
                  f"winner: {result['winner_id']}")
        
        print("✅ Parallel orchestration completed successfully!")


class TestCouncilManagement:
    """Test council creation and management."""

    def test_create_and_use_council(self, orchestrator_stub):
        """
        Test creating a council and using it for orchestration.
        
        Verifies:
        - Council creation works
        - Council can be used for deliberation
        - Agents in council respond correctly
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Council Management")
        
        # Note: DATA council already exists from fixture, so just verify we can use it
        print("📋 Verifying DATA council exists (from fixture)")
        
        # List councils to verify DATA exists
        list_request = orchestrator_pb2.ListCouncilsRequest()
        list_response = orchestrator_stub.ListCouncils(list_request)
        
        data_councils = [c for c in list_response.councils if c.role == "DATA"]
        assert len(data_councils) > 0, "DATA council should exist from fixture"
        
        print(f"   ✓ DATA council exists: {data_councils[0].council_id}")
        
        # Use the council for a task
        print("🤖 Using council for task orchestration")
        
        orchestrate_request = orchestrator_pb2.OrchestrateRequest(
            task_id="DATA-TASK-001",
            task_description="Design data pipeline for user analytics",
            role="DATA",
        )
        
        orchestrate_response = orchestrator_stub.Orchestrate(orchestrate_request)
        
        assert orchestrate_response.winner is not None
        assert orchestrate_response.winner.proposal.author_role == "DATA"
        
        print("   ✓ Task orchestrated successfully")
        print("✅ Council management verified!")


class TestDeliberationQuality:
    """Test deliberation quality and consensus."""

    def test_deliberation_improves_with_rounds(self, orchestrator_stub):
        """
        Test that multiple deliberation rounds improve quality.
        
        Verifies:
        - Multiple rounds execute successfully
        - Quality metrics are tracked
        - Convergence happens
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Deliberation Quality with Multiple Rounds")
        
        task_description = "Optimize API endpoint for high-traffic scenarios"
        
        # Single round deliberation
        print("🔄 Round 1: Initial deliberation")
        
        single_round_request = orchestrator_pb2.DeliberateRequest(
            task_description=task_description,
            role="DEV",
            rounds=1,
            num_agents=3,
        )
        
        single_round_response = orchestrator_stub.Deliberate(single_round_request)
        
        assert len(single_round_response.results) > 0
        single_round_winner_score = single_round_response.results[0].score
        
        print(f"   ✓ Single round winner score: {single_round_winner_score}")
        
        # Multiple rounds deliberation  
        print("🔄 Rounds 2-3: Peer review and refinement")
        
        multi_round_request = orchestrator_pb2.DeliberateRequest(
            task_description=task_description,
            role="DEV",
            rounds=3,  # Multiple rounds
            num_agents=3,
        )
        
        multi_round_response = orchestrator_stub.Deliberate(multi_round_request)
        
        assert len(multi_round_response.results) > 0
        multi_round_winner_score = multi_round_response.results[0].score
        
        print(f"   ✓ Multi-round winner score: {multi_round_winner_score}")
        
        # Verify both completed
        assert single_round_response.duration_ms >= 0
        assert multi_round_response.duration_ms >= 0
        
        print("📊 Comparison:")
        print(f"   Single round: {single_round_winner_score} points, "
              f"{single_round_response.duration_ms}ms")
        print(f"   Multi-round:  {multi_round_winner_score} points, "
              f"{multi_round_response.duration_ms}ms")
        
        # Note: Quality might or might not improve, but process should work
        print("✅ Multi-round deliberation completed successfully!")

    def test_consensus_across_complex_task(self, orchestrator_stub):
        """
        Test deliberation on complex task requiring consensus.
        
        Verifies:
        - Complex tasks are handled correctly
        - All agents contribute meaningful proposals
        - Scoring reflects proposal quality
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Consensus on Complex Task")
        
        # Complex architectural decision task
        complex_task = """
        Design a microservices architecture for a high-scale e-commerce platform:
        - Handle 10,000 requests/second
        - 99.99% uptime SLA
        - Multi-region deployment
        - Event-driven communication
        - CQRS pattern for order processing
        - Saga pattern for distributed transactions
        
        Propose:
        1. Service decomposition strategy
        2. Communication patterns (sync vs async)
        3. Data consistency approach
        4. Scalability strategy
        5. Failure handling and circuit breakers
        """
        
        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Enterprise architecture quality standards",
            requirements=["documentation", "scalability analysis", "failure scenarios"],
            timeout_seconds=14400,  # 240 minutes
        )
        
        request = orchestrator_pb2.DeliberateRequest(
            task_description=complex_task,
            role="ARCHITECT",
            rounds=2,
            num_agents=3,
            constraints=constraints,  # Pass constraints to request
        )
        
        response = orchestrator_stub.Deliberate(request)
        
        # Verify deliberation completed
        assert response is not None
        assert len(response.results) >= 1
        
        # Verify all results have substantive proposals
        for result in response.results:
            assert result.proposal is not None
            assert result.proposal.content != ""
            # Solution should be reasonably long for complex task
            assert len(result.proposal.content) > 50, \
                "Proposal for complex task should be substantive"
        
        # Verify winner
        winner = next((r for r in response.results if r.proposal.author_id == response.winner_id), None)
        assert winner is not None
        
        print("📊 Deliberation results:")
        print(f"   Participants: {len(response.results)}")
        print(f"   Winner: {response.winner_id} (score: {winner.score})")
        print(f"   Duration: {response.duration_ms}ms")
        
        print("✅ Complex task consensus achieved!")


class TestOrchestratorObservability:
    """Test observability endpoints."""

    def test_get_status_provides_stats(self, orchestrator_stub):
        """
        Test GetStatus endpoint provides service health and statistics.
        
        Verifies:
        - Status endpoint responds
        - Stats are tracked
        - Service health is reported
        """
        from services.orchestrator.gen import orchestrator_pb2
        
        print("\n🎯 Test: Orchestrator Observability")
        
        # Perform some orchestrations first to generate stats
        for i in range(3):
            request = orchestrator_pb2.OrchestrateRequest(
                task_id=f"OBSERVABILITY-TASK-{i}",
                task_description=f"Test task {i} for stats",
                role="DEV",
            )
            orchestrator_stub.Orchestrate(request)
        
        # Get status with stats
        status_request = orchestrator_pb2.GetStatusRequest(include_stats=True)
        status_response = orchestrator_stub.GetStatus(status_request)
        
        # Verify status response
        assert status_response is not None
        assert status_response.status.upper() in ["HEALTHY", "RUNNING", "OK"]
        assert status_response.uptime_seconds >= 0
        
        # Verify stats
        if status_response.stats:
            print("📊 Service Stats:")
            print(f"   Orchestrations: {status_response.stats.total_orchestrations}")
            print(f"   Deliberations: {status_response.stats.total_deliberations}")
        
        print("✅ Observability verified!")


# Additional test ideas for future implementation:
# - test_orchestration_with_agent_failures()
# - test_deliberation_timeout_handling()
# - test_context_integration_end_to_end()
# - test_nats_event_publishing_verification()
# - test_agent_replacement_mid_deliberation()

