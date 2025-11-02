#!/usr/bin/env python3
"""E2E test runner script.

This script runs connection tests first, then the refactored e2e tests.
Designed to run inside a Kubernetes Job.

Scope: test_001 only (Neo4j + Valkey persistence validation)
"""

import os
import subprocess
import sys


def run_connection_tests() -> bool:
    """Run connection tests to validate Neo4j and Valkey connectivity."""
    print("=" * 80)
    print("STEP 1: Connection Tests (Neo4j + Valkey)")
    print("=" * 80)
    print()
    
    result = subprocess.run([
        "python",
        "/app/tests/e2e/refactored/test_connections.py"
    ])
    
    return result.returncode == 0


def main() -> int:
    """Run connection tests then e2e tests and return exit code."""
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
    
    # Step 1: Connection tests
    if not run_connection_tests():
        print()
        print("=" * 80)
        print("❌ Connection tests failed. Aborting e2e tests.")
        print("=" * 80)
        return 1
    
    # Step 2: E2E tests (test_001 only - Neo4j + Valkey persistence)
    print()
    print("=" * 80)
    print("STEP 2: E2E Tests (test_001 - Story Persistence)")
    print("=" * 80)
    print()
    print("📝 Scope: test_001_story_persistence.py only")
    print("   - Validates ProjectCase node in Neo4j")
    print("   - Validates story hash in Valkey")
    print("   - test_002 (multi-agent planning) is OUT OF SCOPE")
    print()
    
    cmd = [
        "pytest",
        "/app/tests/e2e/refactored/test_001_story_persistence.py",
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

