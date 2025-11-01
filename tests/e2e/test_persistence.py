#!/usr/bin/env python3
"""
Test script to verify data persistence from Orchestrator to Context Service
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))
sys.path.insert(0, str(project_root / "services" / "orchestrator"))

import grpc
from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc


def main():
    print("🔍 Testing Orchestrator -> Context Service persistence...")
    
    # Connect to Orchestrator
    orchestrator_host = "localhost:50055"
    channel = grpc.insecure_channel(orchestrator_host)
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    print(f"✅ Connected to Orchestrator at {orchestrator_host}")
    
    # Create a council
    print("\n📋 Creating DEV council with 3 real vLLM agents...")
    response = stub.CreateCouncil(orchestrator_pb2.CreateCouncilRequest(
        role="DEV",
        num_agents=3,
        config=orchestrator_pb2.CouncilConfig(
            deliberation_rounds=1,
            enable_peer_review=False,
            agent_type="RAY_VLLM"  # Real vLLM agents
        )
    ))
    
    council_id = response.council_id
    print(f"✅ Council created: {council_id}")
    print(f"   Agents: {', '.join(response.agent_ids)}")
    
    # Execute deliberation
    print("\n🤔 Executing deliberation...")
    task = "Implement a simple Redis caching layer for frequently accessed data"
    
    deliberation_response = stub.Deliberate(orchestrator_pb2.DeliberateRequest(
        council_id=council_id,
        task=task
    ))
    
    print("\n✅ Deliberation completed!")
    print(f"   Consensus: {deliberation_response.consensus}")
    print(f"   Confidence: {deliberation_response.confidence:.2f}")
    
    if deliberation_response.proposals:
        print(f"\n📝 Proposals ({len(deliberation_response.proposals)}):")
        for i, proposal in enumerate(deliberation_response.proposals, 1):
            print(f"   {i}. Agent {proposal.agent_id}")
            print(f"      Proposal: {proposal.proposal[:100]}...")
    
    print("\n✅ Test completed. Now check Neo4j and ValKey for stored data.")
    print("\nNext steps:")
    print("1. kubectl exec -n swe-ai-fleet neo4j-0 -- cypher-shell -u neo4j -p testpassword 'MATCH (n) RETURN labels(n), count(n);'")
    print("2. kubectl exec -n swe-ai-fleet valkey-0 -- valkey-cli KEYS '*'")


if __name__ == "__main__":
    main()

