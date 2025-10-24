#!/usr/bin/env python3
"""
E2E Test: SWE AI Fleet Architecture Verification

Tests the complete architecture flow:
1. Client → Orchestrator (gRPC)
2. Orchestrator → Councils (vLLM agents)
3. Agents → vLLM Server (inference)
4. Results → Client (ranked proposals)

This test verifies:
- ✅ Orchestrator is accessible
- ✅ Councils are initialized with vLLM agents
- ✅ vLLM server is generating real proposals
- ✅ Deliberation produces diverse, quality results
- ✅ Timing confirms real LLM inference (not mocks)
"""

import time
import sys
from pathlib import Path

import grpc
import pytest

# Add project root to path for imports
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.mark.e2e
def test_full_architecture_deliberation():
    """
    Test the complete architecture with real vLLM agents.
    
    Expected behavior:
    - Deliberation takes 30-90 seconds (real vLLM inference)
    - Returns 3 proposals from DEV council
    - Each proposal has meaningful content (>100 chars)
    - Proposals are diverse (not identical)
    """
    import os
    
    # Import generated protobuf (already generated during Docker build)
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
    
    print("\n" + "="*70)
    print("🧪 E2E Test: SWE AI Fleet Architecture")
    print("="*70)
    
    # Connect to Orchestrator (inside cluster)
    orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")
    orchestrator_port = os.getenv("ORCHESTRATOR_PORT", "50055")
    
    print(f"\n📡 Step 1: Connecting to {orchestrator_host}:{orchestrator_port}...")
    channel = grpc.insecure_channel(f"{orchestrator_host}:{orchestrator_port}")
    
    try:
        grpc.channel_ready_future(channel).result(timeout=10)
        print(f"   ✅ Connected successfully")
    except Exception as e:
        pytest.fail(f"❌ Cannot connect to Orchestrator: {e}")
    
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    # 2. Verify councils exist
    print("\n📋 Step 2: Verifying councils are initialized...")
    from services.orchestrator.gen import orchestrator_pb2
    try:
        list_response = stub.ListCouncils(
            orchestrator_pb2.ListCouncilsRequest(include_agents=True)
        )
        
        roles = [c.role for c in list_response.councils]
        print(f"   ✅ Found {len(roles)} councils: {', '.join(roles)}")
        
        assert "DEV" in roles, "DEV council must exist"
        assert len(roles) >= 3, "At least 3 councils should exist"
        
    except grpc.RpcError as e:
        pytest.fail(f"❌ Failed to list councils: {e.code()}: {e.details()}")
    
    # 3. Execute deliberation with real vLLM
    print("\n🧠 Step 3: Testing deliberation with vLLM agents...")
    
    task_description = (
        "Write a Python function to reverse a string. "
        "The function should handle Unicode characters correctly "
        "and include type hints and docstring."
    )
    
    constraints = orchestrator_pb2.TaskConstraints(
        rubric="Clean, readable code with proper documentation",
        requirements=[
            "Use type hints (str -> str)",
            "Add comprehensive docstring",
            "Handle edge cases (empty string, None)",
            "Follow PEP 8 style guide"
        ],
        timeout_seconds=120,
        max_iterations=1
    )
    
    print(f"   📝 Task: {task_description[:60]}...")
    print("   ⏱️  Sending deliberation request (expecting 30-90s)...")
    
    start_time = time.time()
    
    try:
        response = stub.Deliberate(
            orchestrator_pb2.DeliberateRequest(
                task_description=task_description,
                role="DEV",
                rounds=1,
                num_agents=3,
                constraints=constraints
            )
        )
        
        duration_seconds = time.time() - start_time
        
        print(f"\n   ✅ Deliberation completed!")
        print(f"   ⏱️  Duration: {duration_seconds:.1f}s")
        print(f"   📊 Proposals received: {len(response.results)}")
        
        # 4. Verify results quality
        print("\n🔍 Step 4: Verifying result quality...")
        
        # Check timing (real vLLM should take >20s for 3 agents)
        assert duration_seconds > 20, (
            f"Deliberation too fast ({duration_seconds:.1f}s). "
            f"Expected >20s with real vLLM. Are mocks being used?"
        )
        print(f"   ✅ Timing confirms real vLLM (>{duration_seconds:.0f}s, not mocks)")
        
        # Check we got proposals
        assert len(response.results) >= 2, (
            f"Expected at least 2 proposals, got {len(response.results)}"
        )
        print(f"   ✅ Received {len(response.results)} proposals")
        
        # Check proposal quality
        for i, result in enumerate(response.results, 1):
            content = result.proposal.content
            author_id = result.proposal.author_id
            author_role = result.proposal.author_role
            score = result.score
            
            print(f"\n   Agent {i} ({author_id}):")
            print(f"      Role: {author_role}")
            print(f"      Score: {score:.2f}")
            print(f"      Content length: {len(content)} chars")
            
            # Verify content has substance
            assert len(content) > 100, (
                f"Proposal {i} too short ({len(content)} chars). "
                f"Expected >100 chars from real vLLM"
            )
            
            # Verify role matches
            assert author_role == "DEV", (
                f"Expected DEV role, got {author_role}"
            )
            
            # Show preview
            preview = content[:200].replace('\n', ' ')
            print(f"      Preview: {preview}...")
        
        # Check diversity (proposals should be different)
        if len(response.results) >= 2:
            content_1 = response.results[0].proposal.content
            content_2 = response.results[1].proposal.content
            
            # Calculate similarity (simple: count common words)
            words_1 = set(content_1.lower().split())
            words_2 = set(content_2.lower().split())
            common = len(words_1 & words_2)
            total = len(words_1 | words_2)
            similarity = common / total if total > 0 else 0
            
            print(f"\n   📊 Diversity check:")
            print(f"      Similarity between proposals: {similarity:.1%}")
            
            # Proposals should not be too similar (>80% identical)
            assert similarity < 0.8, (
                f"Proposals too similar ({similarity:.1%}). "
                f"Expected diverse responses from different agents"
            )
            print(f"      ✅ Proposals are diverse (<80% similar)")
        
        # 5. Success summary
        print("\n" + "="*70)
        print("✅ ARCHITECTURE TEST PASSED!")
        print("="*70)
        print(f"✓ Orchestrator: Accessible and responding")
        print(f"✓ Councils: {len(roles)} councils initialized")
        print(f"✓ vLLM Agents: Generated {len(response.results)} real proposals")
        print(f"✓ Inference Time: {duration_seconds:.1f}s (real LLM confirmed)")
        print(f"✓ Quality: All proposals >100 chars, diverse content")
        print("="*70 + "\n")
        
    except grpc.RpcError as e:
        pytest.fail(
            f"❌ Deliberation failed: {e.code()}: {e.details()}"
        )

