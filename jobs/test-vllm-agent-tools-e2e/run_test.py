#!/usr/bin/env python3
"""
E2E Test Runner for VLLM Agent with Tools.

This script runs the specific test: test_vllm_agent_with_smart_context
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
    print(f"{BLUE}🚀 VLLM Agent with Tools E2E Test{RESET}")
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
    vllm_url = os.getenv("VLLM_URL", "http://vllm-server.swe-ai-fleet.svc.cluster.local:8000")
    orchestrator_host = os.getenv("ORCHESTRATOR_HOST", "orchestrator.swe-ai-fleet.svc.cluster.local")
    orchestrator_port = os.getenv("ORCHESTRATOR_PORT", "50055")

    print(f"  VLLM_URL: {vllm_url}")
    print(f"  ORCHESTRATOR_HOST: {orchestrator_host}")
    print(f"  ORCHESTRATOR_PORT: {orchestrator_port}")
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

    # Run the specific test
    print(f"{BLUE}🧪 Running E2E test: test_vllm_agent_with_smart_context{RESET}")
    print(f"{BLUE}{'='*70}{RESET}")
    print()

    test_path = "tests/e2e/orchestrator/test_orchestrator_with_tools_e2e.py::test_vllm_agent_with_smart_context"

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

