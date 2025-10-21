#!/usr/bin/env python3
"""Script to show recent deliberations with generated content."""

import grpc
import sys
from datetime import datetime

# Add generated proto path
sys.path.insert(0, '/home/tirso/ai/developents/swe-ai-fleet')

# Import generated protobuf
try:
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc
except ImportError:
    print("❌ Error: Could not import generated protobuf files")
    print("Make sure you're running from the project root")
    sys.exit(1)


def main():
    """Connect to Orchestrator and list recent deliberations."""
    
    # Connect to Orchestrator via port-forward or direct service
    # For local testing: kubectl port-forward -n swe-ai-fleet svc/internal-orchestrator 50055:50055
    channel = grpc.insecure_channel('localhost:50055')
    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(channel)
    
    try:
        print("🔍 Fetching deliberation statistics...")
        request = orchestrator_pb2.GetStatisticsRequest()
        response = stub.GetStatistics(request)
        
        print(f"\n📊 Orchestrator Statistics:")
        print(f"   Total Deliberations: {response.deliberation_count}")
        print(f"   Total Duration: {response.total_duration_ms}ms")
        
        if response.by_role:
            print(f"\n📋 Deliberations by Role:")
            for role_stat in response.by_role:
                avg_duration = role_stat.total_duration_ms / role_stat.count if role_stat.count > 0 else 0
                print(f"   • {role_stat.role}: {role_stat.count} deliberations, avg {avg_duration:.0f}ms")
        
        print("\n✅ Connected successfully to Orchestrator!")
        print("\nNote: To see actual proposal content, we need to:")
        print("1. Enable DEBUG logging in orchestrator")
        print("2. Or query deliberation results via a dedicated RPC")
        print("3. Or consume events from NATS orchestration.deliberation.completed")
        
    except grpc.RpcError as e:
        print(f"❌ gRPC Error: {e.code()}: {e.details()}")
        print("\nMake sure to port-forward the service first:")
        print("kubectl port-forward -n swe-ai-fleet svc/internal-orchestrator 50055:50055")
    finally:
        channel.close()


if __name__ == "__main__":
    main()

