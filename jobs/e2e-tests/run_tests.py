#!/usr/bin/env python3
"""E2E test runner script.

This script runs the refactored e2e tests and reports results.
Designed to run inside a Kubernetes Job.
"""

import os
import sys
import subprocess


def main() -> int:
    """Run e2e tests and return exit code."""
    print("=" * 80)
    print("🚀 SWE AI Fleet - E2E Test Runner")
    print("=" * 80)
    print()
    
    # Print environment info
    print("📋 Environment:")
    print(f"  CONTEXT_SERVICE_URL: {os.getenv('CONTEXT_SERVICE_URL', 'NOT SET')}")
    print(f"  ORCHESTRATOR_SERVICE_URL: {os.getenv('ORCHESTRATOR_SERVICE_URL', 'NOT SET')}")
    print(f"  NEO4J_URI: {os.getenv('NEO4J_URI', 'NOT SET')}")
    print(f"  VALKEY_HOST: {os.getenv('VALKEY_HOST', 'NOT SET')}")
    print()
    
    # Run pytest with verbose output
    print("🧪 Running e2e tests...")
    print("=" * 80)
    print()
    
    cmd = [
        "pytest",
        "/app/tests/e2e/refactored",
        "-v",
        "-s",
        "--tb=short",
        "--color=yes",
        "-m", "e2e",
        "--asyncio-mode=auto"
    ]
    
    result = subprocess.run(cmd)
    
    print()
    print("=" * 80)
    
    if result.returncode == 0:
        print("✅ All e2e tests PASSED")
    else:
        print("❌ Some e2e tests FAILED")
    
    print("=" * 80)
    
    return result.returncode


if __name__ == "__main__":
    sys.exit(main())

