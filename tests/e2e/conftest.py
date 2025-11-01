"""
Fixtures for E2E tests against Kubernetes cluster.

These tests require:
- Kubernetes cluster running (namespace: swe-ai-fleet)
- Services accessible via kubectl port-forward or Ingress
- KUBECONFIG configured
"""
import os
import time

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
    except Exception:
        pytest.skip(
            f"Orchestrator not available at {address}. "
            f"Run: kubectl port-forward -n swe-ai-fleet svc/orchestrator 50055:50055"
        )

    yield channel
    channel.close()


@pytest.fixture(scope="module")
def orchestrator_stub(orchestrator_channel):
    """Create Orchestrator service gRPC stub."""
    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(orchestrator_channel)

    required_roles = ("DEV", "QA", "ARCHITECT", "DEVOPS")

    try:
        response = stub.ListCouncils(
            orchestrator_pb2.ListCouncilsRequest(include_agents=False)
        )
        existing_roles = {council.role for council in response.councils}
    except grpc.RpcError as error:
        pytest.skip(
            "Unable to list councils on orchestrator: "
            f"{error.code().name} - {error.details()}"
        )

    missing_roles = [role for role in required_roles if role not in existing_roles]

    for role in missing_roles:
        create_request = orchestrator_pb2.CreateCouncilRequest(
            role=role,
            num_agents=3,
            config=orchestrator_pb2.CouncilConfig(
                deliberation_rounds=1,
                enable_peer_review=True,
                agent_type="RAY_VLLM",
                model_profile="Qwen/Qwen3-0.6B",
            ),
        )

        try:
            stub.CreateCouncil(create_request)
        except grpc.RpcError as error:
            details = (error.details() or "").lower()
            if error.code() == grpc.StatusCode.INTERNAL and "already exists" in details:
                continue
            pytest.fail(
                f"Failed to create council {role}: {error.code().name} - {error.details()}"
            )

        # Wait for the council to become visible to subsequent requests
        deadline = time.time() + 20.0
        while time.time() < deadline:
            refresh = stub.ListCouncils(
                orchestrator_pb2.ListCouncilsRequest(include_agents=False)
            )
            if any(c.role == role for c in refresh.councils):
                break
            time.sleep(1.0)
        else:
            pytest.fail(f"Council {role} was not ready after creation request")

    return stub

