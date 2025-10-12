#!/usr/bin/env python3
"""
Test script to validate Orchestrator with vLLM agents.
Connects to Orchestrator Service via gRPC and tests basic deliberation.
"""
import sys
from pathlib import Path

import grpc

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc  # noqa: E402


def test_create_council():
    """Test creating a council with vLLM agents."""
    print("🔧 Connecting to Orchestrator at localhost:50055...")
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    try:
        print("✅ Connected!")
        
        # Create a DEV council (if not exists)
        print("\n📝 Creating DEV council with vLLM agents...")
        council_config = orchestrator_pb2.CouncilConfig(
            deliberation_rounds=1,
            enable_peer_review=False
        )
        
        try:
            response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
                role="DEV",
                num_agents=3,
                config=council_config
            ))
            
            print(f"✅ Council created: {response.council_id}")
            print(f"   Number of agents: {response.agents_created}")
            print(f"   Agent IDs: {', '.join(response.agent_ids)}")
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                print("✅ Council already exists (reusing existing DEV council)")
            else:
                raise
        
        # List councils
        print("\n📋 Listing all councils...")
        list_response = stub.ListCouncils(orchestrator_pb2.ListCouncilsRequest())
        
        for council in list_response.councils:
            print(f"   - {council.role}: {council.num_agents} agents")
        
        # Test deliberation
        print("\n🧠 Testing deliberation with vLLM agents...")
        task_description = "Write a Python function to calculate the factorial of a number"
        
        constraints = orchestrator_pb2.TaskConstraints(
            rubric="Function must be recursive, include type hints, and add docstring",
            requirements=[
                "Code must be clean",
                "Follow PEP 8",
                "Keep it simple"
            ],
            timeout_seconds=60,
            max_iterations=3
        )
        
        print("   Sending deliberation request to DEV council...")
        print(f"   Task: {task_description}")
        
        deliberate_response = stub.Deliberate(orchestrator_pb2.DeliberateRequest(
            task_description=task_description,
            role="DEV",
            rounds=1,
            num_agents=3,
            constraints=constraints
        ))
        
        print("\n✅ Deliberation completed!")
        print(f"   Duration: {deliberate_response.duration_ms}ms")
        print(f"   Total results: {len(deliberate_response.results)}")
        
        for i, result in enumerate(deliberate_response.results, 1):
            print(f"\n   Agent {i}:")
            print(f"      Author: {result.proposal.author_role} ({result.proposal.author_id})")
            print(f"      Score: {result.score:.2f}")
            content = result.proposal.content
            content_preview = content[:200] + "..." if len(content) > 200 else content
            print(f"      Content preview: {content_preview}")
        
        print("\n🎉 SUCCESS: vLLM agents are working correctly!")
        return True
        
    except grpc.RpcError as e:
        print(f"\n❌ gRPC Error: {e.code()}: {e.details()}")
        return False
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        channel.close()


if __name__ == "__main__":
    print("=" * 70)
    print("  vLLM Orchestrator Integration Test")
    print("=" * 70)
    
    success = test_create_council()
    sys.exit(0 if success else 1)

