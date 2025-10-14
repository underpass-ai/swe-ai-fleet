#!/usr/bin/env python3
"""
Setup all councils (DEV, QA, ARCHITECT, DEVOPS, DATA) in Orchestrator.
Run once to initialize all councils with vLLM agents.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import grpc  # noqa: E402
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc  # noqa: E402


def setup_councils():
    """Create all councils."""
    print("🔧 Setting up all councils...")
    
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    roles = ["DEV", "QA", "ARCHITECT", "DEVOPS", "DATA"]
    
    for role in roles:
        print(f"\n📝 Creating {role} council...")
        
        try:
            response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
                role=role,
                num_agents=3,
                config=orchestrator_pb2.CouncilConfig(
                    deliberation_rounds=1,
                    enable_peer_review=False
                )
            ))
            
            print(f"✅ {role} council created:")
            print(f"   Council ID: {response.council_id}")
            print(f"   Agents: {response.agents_created}")
            print(f"   Agent IDs: {', '.join(response.agent_ids)}")
            
        except grpc.RpcError as e:
            if e.code() == grpc.StatusCode.ALREADY_EXISTS:
                print(f"✅ {role} council already exists")
            else:
                print(f"❌ Failed to create {role} council: {e.details()}")
                raise
    
    # List all councils
    print("\n📋 All councils:")
    list_response = stub.ListCouncils(orchestrator_pb2.ListCouncilsRequest())
    
    for council in list_response.councils:
        print(f"   - {council.role}: {council.num_agents} agents")
    
    channel.close()
    print("\n✅ All councils setup complete!")


if __name__ == "__main__":
    setup_councils()

