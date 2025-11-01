#!/usr/bin/env python3
"""
E2E Test Runner for Ray + vLLM Suite.

This script runs the test suite: test_ray_vllm_e2e
inside the Kubernetes cluster where it can access services via cluster DNS.
"""
import os
import subprocess
import sys
from pathlib import Path

# Colors for output
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
RESET = "\033[0m"


def main():
    """Run the E2E test."""
    print(f"{BLUE}{'='*70}{RESET}")
    print(f"{BLUE}🚀 Ray + vLLM E2E Test Suite{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print()

    # Check if workspace exists (should be cloned by init container)
    workspace = Path("/workspace")
    if not workspace.exists():
        print(f"{RED}❌ Workspace directory not found at /workspace{RESET}")
        print("   Make sure init container cloned the repository")
        sys.exit(1)

    print(f"{GREEN}✓ Workspace found at {workspace}{RESET}")
    print()

    # Change to workspace directory
    os.chdir(workspace)

    # Check if this is a git repo
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        commit = result.stdout.strip()
        print(f"{GREEN}✓ Repository at commit: {commit}{RESET}")
    except subprocess.CalledProcessError:
        print(f"{YELLOW}⚠️  Not a git repository (might be OK if copied differently){RESET}")

    print()

    # Display environment
    print(f"{BLUE}Environment Configuration:{RESET}")
    orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")
    orchestrator_port = os.getenv("ORCHESTRATOR_PORT", "50055")
    vllm_url = os.getenv("VLLM_URL", "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000")

    print(f"  ORCHESTRATOR_HOST: {orchestrator_host}")
    print(f"  ORCHESTRATOR_PORT: {orchestrator_port}")
    print(f"  VLLM_URL: {vllm_url}")
    print()

    # Install project dependencies
    print(f"{BLUE}📦 Installing project dependencies...{RESET}")
    try:
        # Install in editable mode with dev dependencies
        subprocess.run(
            ["pip", "install", "--user", "-q", "-e", ".[dev,grpc]"],
            check=True,
            cwd=workspace,
        )
        print(f"{GREEN}✓ Dependencies installed{RESET}")
    except subprocess.CalledProcessError as e:
        print(f"{RED}❌ Failed to install dependencies: {e}{RESET}")
        sys.exit(1)

    print()
    
    # Generate protobuf stubs (required for gRPC imports)
    print(f"{BLUE}📦 Generating protobuf stubs...{RESET}")
    try:
        # Create gen directory
        subprocess.run(
            ["mkdir", "-p", "services/orchestrator/gen"],
            check=True,
            cwd=workspace,
        )
        
        # Generate orchestrator stubs
        subprocess.run(
            [
                "python", "-m", "grpc_tools.protoc",
                "--proto_path=specs/fleet/orchestrator/v1",
                "--proto_path=specs/fleet/ray_executor/v1",
                "--python_out=services/orchestrator/gen",
                "--grpc_python_out=services/orchestrator/gen",
                "--pyi_out=services/orchestrator/gen",
                "specs/fleet/orchestrator/v1/orchestrator.proto",
                "specs/fleet/ray_executor/v1/ray_executor.proto",
            ],
            check=True,
            cwd=workspace,
        )
        
        # Fix imports
        import fileinput
        import glob
        
        grpc_files = glob.glob("services/orchestrator/gen/*_grpc.py")
        for file_path in grpc_files:
            with fileinput.FileInput(file_path, inplace=True) as file:
                for line in file:
                    print(line.replace("import orchestrator_pb2", "from . import orchestrator_pb2").replace("import ray_executor_pb2", "from . import ray_executor_pb2"), end='')
        
        # Create __init__.py
        init_file = workspace / "services" / "orchestrator" / "gen" / "__init__.py"
        init_file.write_text('from . import orchestrator_pb2, orchestrator_pb2_grpc, ray_executor_pb2, ray_executor_pb2_grpc\n__all__ = ["orchestrator_pb2", "orchestrator_pb2_grpc", "ray_executor_pb2", "ray_executor_pb2_grpc"]')
        
        print(f"{GREEN}✓ Protobuf stubs generated{RESET}")
    except Exception as e:
        print(f"{YELLOW}⚠️  Failed to generate protobuf stubs: {e}{RESET}")
        print("   Trying to continue anyway...")

    print()

    # Run the test suite
    print(f"{BLUE}🧪 Running E2E test: test_ray_vllm_e2e{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print()

    # The test file is in /workspace/tests/e2e/test_ray_vllm_e2e.py
    test_path = "tests/e2e/test_ray_vllm_e2e.py"

    # Run pytest
    try:
        result = subprocess.run(
            [
                "python", "-m", "pytest",
                test_path,
                "-v",
                "-s",  # Show output
                "--tb=short",  # Short traceback format
            ],
            cwd=workspace,
        )

        exit_code = result.returncode

        print()
        print(f"{BLUE}{'='*70}{RESET}")
        if exit_code == 0:
            print(f"{GREEN}✅ Test PASSED!{RESET}")
        else:
            print(f"{RED}❌ Test FAILED with exit code {exit_code}{RESET}")
        print(f"{BLUE}{'='*70}{RESET}")

        sys.exit(exit_code)

    except Exception as e:
        print(f"{RED}❌ Error running test: {e}{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()

