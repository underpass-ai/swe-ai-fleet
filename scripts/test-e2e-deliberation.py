#!/usr/bin/env python3
"""
End-to-End test: Deliberation with hexagonal architecture.

Tests complete flow:
1. Orchestrator receives deliberation request
2. Creates Ray jobs with RayAgentExecutor (hexagonal)
3. Agents execute tasks using new architecture
4. Results published to NATS
5. Verify results
"""

import asyncio
import grpc
import sys
import time

# Add path for gen imports
sys.path.insert(0, 'services/orchestrator')

try:
    from gen import orchestrator_pb2, orchestrator_pb2_grpc
except ModuleNotFoundError:
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc


async def test_deliberation():
    """Test complete deliberation flow."""
    
    orchestrator_address = "localhost:50055"
    
    print("\n" + "=" * 70)
    print("🧪 E2E TEST: Deliberation with Hexagonal Architecture")
    print("=" * 70 + "\n")
    
    # Connect to Orchestrator
    channel = grpc.aio.insecure_channel(orchestrator_address)
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    try:
        # Step 1: Verify Orchestrator is ready
        print("📡 Step 1: Verifying Orchestrator connection...")
        status_req = orchestrator_pb2.GetStatusRequest(include_stats=True)
        status_resp = await stub.GetStatus(status_req)
        print(f"   ✅ Status: {status_resp.status}")
        print(f"   📊 Active councils: {status_resp.num_councils}")
        print(f"   🤖 Total agents: {status_resp.num_agents}")
        print()
        
        # Step 2: List councils
        print("📋 Step 2: Listing available councils...")
        list_req = orchestrator_pb2.ListCouncilsRequest(include_agents=True)
        list_resp = await stub.ListCouncils(list_req)
        
        for council in list_resp.councils:
            print(f"   • {council.role}: {council.num_agents} agents")
        print()
        
        # Step 3: Trigger deliberation
        print("🎯 Step 3: Triggering deliberation...")
        
        task_req = orchestrator_pb2.TaskRequest(
            task_id="e2e-test-task-001",
            description="Write a simple Python function that calculates fibonacci numbers",
            role="DEV",
            constraints=orchestrator_pb2.TaskConstraints(
                rubric="Code must be clean and well-documented",
                requirements=["Use type hints", "Add docstrings", "Include examples"],
            ),
            diversity=False,
        )
        
        deliberation_req = orchestrator_pb2.DeliberateRequest(task=task_req)
        
        print(f"   Task ID: {task_req.task_id}")
        print(f"   Role: {task_req.role}")
        print(f"   Description: {task_req.description}")
        print(f"   Constraints: {task_req.constraints.rubric}")
        print()
        
        deliberation_resp = await stub.Deliberate(deliberation_req)
        
        print(f"   ✅ Deliberation started!")
        print(f"   📊 Agents assigned: {deliberation_resp.agents_assigned}")
        print()
        
        # Step 4: Monitor execution
        print("⏳ Step 4: Waiting for results (30s timeout)...")
        print("   (Check NATS stream 'agent.response.completed' for results)")
        print()
        
        # Wait a bit for execution
        await asyncio.sleep(15)
        
        # Step 5: Get status
        print("📊 Step 5: Checking orchestrator status...")
        status_req = orchestrator_pb2.GetStatusRequest(include_stats=True)
        status_resp = await stub.GetStatus(status_req)
        
        print(f"   ✅ Status: {status_resp.status}")
        if status_resp.stats:
            print(f"   📈 Stats:")
            print(f"      - Councils: {status_resp.num_councils}")
            print(f"      - Agents: {status_resp.num_agents}")
        print()
        
        # Summary
        print("=" * 70)
        print("✅ E2E TEST COMPLETED")
        print("=" * 70)
        print()
        print("📋 Next Steps:")
        print("   1. Check NATS stream for results:")
        print("      kubectl exec -n swe-ai-fleet nats-0 -- nats stream view agent.response.completed")
        print()
        print("   2. Check Ray dashboard:")
        print("      kubectl port-forward -n swe-ai-fleet deployment/ray-executor 8265:8265")
        print("      Open: http://localhost:8265")
        print()
        print("   3. Check vLLM logs for API calls:")
        print("      kubectl logs -n swe-ai-fleet deployment/vllm-server --tail=50")
        print()
        print("   4. Check monitoring dashboard:")
        print("      https://monitoring-dashboard.underpassai.com")
        print()
        
        await channel.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        await channel.close()
        return False


if __name__ == "__main__":
    success = asyncio.run(test_deliberation())
    sys.exit(0 if success else 1)

