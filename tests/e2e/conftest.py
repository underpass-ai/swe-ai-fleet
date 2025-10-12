"""
Fixtures for E2E tests against Kubernetes cluster.

These tests require:
- Kubernetes cluster running (namespace: swe-ai-fleet)
- Services accessible via kubectl port-forward or Ingress
- KUBECONFIG configured
"""
import os

import grpc
import pytest


@pytest.fixture(scope="module")
def orchestrator_host():
    """Get Orchestrator service host."""
    return os.getenv("ORCHESTRATOR_HOST", "localhost")


@pytest.fixture(scope="module")
def orchestrator_port():
    """Get Orchestrator service port."""
    return int(os.getenv("ORCHESTRATOR_PORT", "50055"))


@pytest.fixture(scope="module")
def orchestrator_channel(orchestrator_host, orchestrator_port):
    """Create gRPC channel to Orchestrator service in cluster."""
    address = f"{orchestrator_host}:{orchestrator_port}"
    channel = grpc.insecure_channel(address)
    
    # Wait for service to be ready
    try:
        grpc.channel_ready_future(channel).result(timeout=5)
    except Exception as e:
        pytest.skip(
            f"Orchestrator not available at {address}. "
            f"Run: kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055"
        )
    
    yield channel
    channel.close()


@pytest.fixture(scope="module")
def orchestrator_stub(orchestrator_channel):
    """Create Orchestrator service gRPC stub."""
    from services.orchestrator.gen import orchestrator_pb2_grpc
    
    return orchestrator_pb2_grpc.OrchestratorServiceStub(orchestrator_channel)

