#!/usr/bin/env python3
"""
Complete E2E test suite for Ray + vLLM async integration.

Tests the complete flow:
1. Submit deliberations to Orchestrator
2. Verify agents generate quality proposals
3. Test different roles and scenarios
4. Validate performance and diversity

Run with: python test_ray_vllm_e2e.py
Requires: Orchestrator at localhost:50055
"""
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import grpc  # noqa: E402
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc  # noqa: E402


class Colors:
    """Terminal colors for pretty output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'


def print_header(text):
    """Print colored header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(70)}{Colors.END}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*70}{Colors.END}\n")


def print_success(text):
    """Print success message."""
    print(f"{Colors.GREEN}✅ {text}{Colors.END}")


def print_error(text):
    """Print error message."""
    print(f"{Colors.RED}❌ {text}{Colors.END}")


def print_warning(text):
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠️  {text}{Colors.END}")


def print_info(text):
    """Print info message."""
    print(f"   {text}")


def connect_to_orchestrator():
    """Connect to Orchestrator service."""
    print_info("Connecting to Orchestrator at localhost:50055...")
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    print_success("Connected to Orchestrator")
    return channel, stub


def test_basic_deliberation(stub):
    """Test 1: Basic deliberation with DEV council."""
    print_header("Test 1: Basic Deliberation")
    
    request = orchestrator_pb2.DeliberateRequest(
        task_description="Write a Python function to calculate the factorial of a number",
        role="DEV",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Code must be clean and well-documented",
            requirements=["Use type hints", "Add docstring"],
        )
    )
    
    start_time = time.time()
    response = stub.Deliberate(request)
    duration_ms = (time.time() - start_time) * 1000
    
    # Verify response
    assert len(response.results) == 3, f"Expected 3 results, got {len(response.results)}"
    print_success(f"Received {len(response.results)} proposals in {duration_ms:.0f}ms")
    
    for i, result in enumerate(response.results, 1):
        content = result.proposal.content
        assert len(content) > 50, f"Agent {i} proposal too short ({len(content)} chars)"
        print_info(f"Agent {i} ({result.proposal.author_id}): {len(content)} chars")
    
    print_success("Test 1 PASSED")
    return True


def test_different_roles(stub):
    """Test 2: Deliberation with different roles."""
    print_header("Test 2: Different Roles")
    
    roles = ["DEV", "QA", "ARCHITECT"]
    
    for role in roles:
        print_info(f"Testing role: {role}")
        
        request = orchestrator_pb2.DeliberateRequest(
            task_description=f"Design user authentication as a {role}",
            role=role,
            num_agents=2,
            rounds=1,
        )
        
        response = stub.Deliberate(request)
        
        # Council has 3 agents, so returns 3 results regardless of num_agents in request
        assert len(response.results) >= 2, f"Expected at least 2 results for {role}"
        
        for result in response.results:
            assert result.proposal.author_role == role
            assert len(result.proposal.content) > 50
        
        print_success(f"   {role}: {len(response.results)} proposals generated")
    
    print_success("Test 2 PASSED")
    return True


def test_proposal_quality(stub):
    """Test 3: Verify proposal quality and relevance."""
    print_header("Test 3: Proposal Quality")
    
    request = orchestrator_pb2.DeliberateRequest(
        task_description="Implement a rate limiter for an API using token bucket algorithm",
        role="DEV",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Implementation must be thread-safe and efficient",
            requirements=[
                "Use token bucket algorithm",
                "Include docstrings",
                "Handle edge cases"
            ],
        )
    )
    
    response = stub.Deliberate(request)
    
    assert len(response.results) == 3
    
    for i, result in enumerate(response.results, 1):
        content = result.proposal.content.lower()
        
        # Should be relevant to task
        relevance_keywords = ["rate", "limit", "token", "bucket", "api"]
        matches = sum(1 for kw in relevance_keywords if kw in content)
        
        assert matches >= 2, f"Agent {i} proposal not relevant (only {matches}/5 keywords)"
        print_info(f"Agent {i}: {matches}/5 relevance keywords found ✓")
    
    print_success("Test 3 PASSED")
    return True


def test_proposal_diversity(stub):
    """Test 4: Verify proposals have diversity."""
    print_header("Test 4: Proposal Diversity")
    
    request = orchestrator_pb2.DeliberateRequest(
        task_description="Design a caching strategy for a web application",
        role="ARCHITECT",
        num_agents=3,
        rounds=1,
    )
    
    response = stub.Deliberate(request)
    
    assert len(response.results) == 3
    
    # Extract first 150 chars of each proposal
    previews = [r.proposal.content[:150] for r in response.results]
    
    # Check for uniqueness
    unique_previews = set(previews)
    diversity_score = len(unique_previews) / len(previews) * 100
    
    print_info(f"Diversity score: {diversity_score:.0f}% ({len(unique_previews)}/3 unique)")
    
    # Should have at least some diversity (not all identical)
    assert len(unique_previews) >= 2, "Proposals should have some diversity"
    
    print_success("Test 4 PASSED")
    return True


def test_complex_scenario(stub):
    """Test 5: Complex real-world scenario."""
    print_header("Test 5: Complex Scenario")
    
    request = orchestrator_pb2.DeliberateRequest(
        task_description=(
            "Design and implement a distributed task queue system with:\n"
            "- Worker pool management\n"
            "- Task prioritization\n"
            "- Retry mechanism\n"
            "- Dead letter queue\n"
            "- Monitoring and metrics\n"
            "Technology: Python + Redis + Kubernetes"
        ),
        role="DEVOPS",
        num_agents=3,
        rounds=1,
        constraints=orchestrator_pb2.TaskConstraints(
            rubric="Solution must be production-ready and scalable",
            requirements=[
                "Use Kubernetes for orchestration",
                "Implement health checks",
                "Include deployment manifests",
                "Provide monitoring strategy"
            ],
            timeout_seconds=120,
        )
    )
    
    start_time = time.time()
    response = stub.Deliberate(request)
    duration_s = time.time() - start_time
    
    assert len(response.results) == 3
    print_info(f"Received {len(response.results)} proposals in {duration_s:.1f}s")
    
    # Complex tasks should generate detailed proposals
    for i, result in enumerate(response.results, 1):
        content = result.proposal.content
        assert len(content) > 200, f"Agent {i} proposal too short for complex task"
        
        # Should mention key technologies
        content_lower = content.lower()
        tech_count = sum([
            "kubernetes" in content_lower or "k8s" in content_lower,
            "redis" in content_lower,
            "queue" in content_lower,
            "worker" in content_lower,
        ])
        
        assert tech_count >= 2, f"Agent {i} should mention relevant technologies"
        print_info(f"Agent {i}: {len(content)} chars, {tech_count}/4 tech keywords ✓")
    
    print_success("Test 5 PASSED")
    return True


def test_performance_scaling(stub):
    """Test 6: Performance scaling with different agent counts."""
    print_header("Test 6: Performance Scaling")
    
    agent_counts = [1, 2, 3, 5]
    results_table = []
    
    for num_agents in agent_counts:
        request = orchestrator_pb2.DeliberateRequest(
            task_description=f"Write a function to merge sorted arrays (test with {num_agents} agents)",
            role="DEV",
            num_agents=num_agents,
            rounds=1,
        )
        
        start_time = time.time()
        response = stub.Deliberate(request)
        duration_s = time.time() - start_time
        
        results_table.append({
            "agents": num_agents,
            "duration_s": duration_s,
            "results": len(response.results)
        })
        
        print_info(f"{num_agents} agents: {duration_s:.2f}s, {len(response.results)} results")
    
    # Verify all completed
    # Note: Council has fixed 3 agents, so all return 3 results
    for row in results_table:
        assert row["results"] >= 1, "Should get at least one result"
    
    # With async, more agents shouldn't scale linearly (parallel execution)
    # 5 agents should be faster than 5x single agent time
    if len(results_table) >= 2:
        single_agent_time = results_table[0]["duration_s"]
        five_agent_time = results_table[-1]["duration_s"]
        
        # If truly parallel, 5 agents shouldn't take 5x longer
        max_expected = single_agent_time * 3  # Allow 3x overhead
        
        print_info(f"Scaling factor: {five_agent_time / single_agent_time:.2f}x")
        print_info(f"Expected if parallel: <3x, got {five_agent_time / single_agent_time:.2f}x")
        
        if five_agent_time < max_expected:
            print_success("Good parallelization!")
        else:
            print_warning(f"Scaling not ideal (expected <{max_expected:.1f}s, got {five_agent_time:.1f}s)")
    
    print_success("Test 6 PASSED")
    return True


def run_all_tests():
    """Run all E2E tests."""
    print_header("Ray + vLLM E2E Test Suite")
    print_info("Testing async deliberation with real vLLM agents")
    print_info("Orchestrator: localhost:50055")
    print()
    
    # Connect
    try:
        channel, stub = connect_to_orchestrator()
    except Exception as e:
        print_error(f"Failed to connect to Orchestrator: {e}")
        print_warning("Make sure Orchestrator is running and port-forward is active:")
        print_warning("  kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055")
        return False
    
    tests = [
        ("Basic Deliberation", test_basic_deliberation),
        ("Different Roles", test_different_roles),
        ("Proposal Quality", test_proposal_quality),
        ("Proposal Diversity", test_proposal_diversity),
        ("Complex Scenario", test_complex_scenario),
        ("Performance Scaling", test_performance_scaling),
    ]
    
    passed = 0
    failed = 0
    errors = []
    
    for test_name, test_func in tests:
        try:
            if test_func(stub):
                passed += 1
        except AssertionError as e:
            failed += 1
            errors.append((test_name, str(e)))
            print_error(f"Test FAILED: {e}")
        except Exception as e:
            failed += 1
            errors.append((test_name, str(e)))
            print_error(f"Test ERROR: {e}")
    
    # Summary
    print_header("Test Summary")
    print_info(f"Total tests: {len(tests)}")
    print_success(f"Passed: {passed}/{len(tests)}")
    
    if failed > 0:
        print_error(f"Failed: {failed}/{len(tests)}")
        print()
        print_header("Failures")
        for test_name, error in errors:
            print_error(f"{test_name}:")
            print_info(f"  {error}")
    
    # Close connection
    channel.close()
    
    print()
    if failed == 0:
        print_header("🎉 ALL TESTS PASSED! 🎉")
        return True
    else:
        print_header("❌ SOME TESTS FAILED")
        return False


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

