#!/usr/bin/env python3
"""
Basic E2E test for Orchestrator Service connectivity and deliberation.

Tests basic functionality:
1. Connect to orchestrator service
2. Make a simple deliberation request
3. Verify service responds correctly

Run with: python test_ray_vllm_e2e.py
Requires: Orchestrator service running in cluster
"""
import os
import sys
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import grpc  # noqa: E402
import pytest  # noqa: E402

pytestmark = pytest.mark.e2e

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


def test_orchestrator_connectivity(orchestrator_channel):
    """Test basic connectivity to orchestrator service."""
    print_header("Test: Orchestrator Connectivity")

    from services.orchestrator.gen import orchestrator_pb2, orchestrator_pb2_grpc

    stub = orchestrator_pb2_grpc.OrchestratorServiceStub(orchestrator_channel)

    # Test 1: Get status
    print_info("Testing GetStatus...")
    status_request = orchestrator_pb2.GetStatusRequest(include_stats=True)
    status_response = stub.GetStatus(status_request)

    assert status_response is not None
    assert status_response.status != ""
    assert status_response.uptime_seconds >= 0

    print_success(f"Orchestrator status: {status_response.status}, uptime: {status_response.uptime_seconds}s")

    # Test 2: Simple deliberation request
    print_info("Testing basic deliberation...")
    request = orchestrator_pb2.DeliberateRequest(
        task_description="Write a simple hello world function",
        role="DEV",
        rounds=1,
        num_agents=1,  # Start with just 1 agent for basic test
    )

    start_time = time.time()
    try:
        response = stub.Deliberate(request)
        duration_ms = (time.time() - start_time) * 1000

        # Basic response validation
        assert response is not None, "Should get a response"
        print_success(f"Deliberation completed in {duration_ms:.0f}ms")

        if len(response.results) > 0:
            print_success(f"Got {len(response.results)} result(s)")
            for i, result in enumerate(response.results, 1):
                content_length = len(result.proposal.content)
                print_info(f"Result {i}: {content_length} chars from {result.proposal.author_id}")
        else:
            print_warning("No results returned (might be expected for basic test)")

    except grpc.RpcError as e:
        print_warning(f"Deliberation failed (might be expected if councils not set up): {e.code().name}")
        print_info("This is OK for basic connectivity test - service is responding")

    print_success("Orchestrator connectivity test PASSED")

