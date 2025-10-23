"""
Local integration test for Ray + VLLMAgent without needing full cluster.

Tests the Ray job integration without requiring:
- NATS server
- Context Service
- Orchestrator gRPC

Can run with just Ray installed locally.
"""

import tempfile
from pathlib import Path

import pytest


@pytest.fixture
def test_workspace():
    """Create test workspace."""
    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "src").mkdir()
        (workspace / "src" / "utils.py").write_text("# Utils\n")

        # Git init
        import subprocess

        subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@local"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )

        yield workspace


@pytest.mark.integration
def test_vllm_agent_local_without_ray(test_workspace):
    """
    Test VLLMAgent works locally without Ray (simplest test).
    
    This tests the agent in isolation with real tools.
    """
    import asyncio

    from core.agents import VLLMAgent

    # Create agent
    agent = VLLMAgent(
        agent_id="test-agent-001",
        role="DEV",
        workspace_path=test_workspace,
        enable_tools=True,
    )

    # Execute task
    result = asyncio.run(
        agent.execute_task(
            task="Add hello_world() function to src/utils.py",
            context="Python 3.13 project",
            constraints={"abort_on_error": False},  # Don't abort if pytest fails
        )
    )

    # Verify (main goal: function added)
    assert len(result.operations) > 0
    
    # Check function was added (key outcome)
    utils_content = (test_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content
    
    # File operations should succeed
    file_ops = [op for op in result.operations if op["tool"] == "files"]
    assert all(op["success"] for op in file_ops)


@pytest.mark.integration
@pytest.mark.skip(reason="Requires Ray running locally")
def test_vllm_agent_job_with_ray_no_nats(test_workspace):
    """
    Test VLLMAgentJob with Ray but without NATS (partial integration).
    
    This tests:
    - Ray actor creation
    - VLLMAgent execution
    - Tool usage
    
    But skips NATS publishing (mocked).
    """
    import asyncio

    import ray
    from core.ray_jobs.vllm_agent_job import VLLMAgentJobBase

    # Start Ray locally
    if not ray.is_initialized():
        ray.init(ignore_reinit_error=True)

    # Create job WITHOUT Ray decorator for testing
    job = VLLMAgentJobBase(
        agent_id="test-agent-002",
        role="DEV",
        vllm_url="http://localhost:8000",
        model="Qwen/Qwen3-0.6B",
        nats_url="nats://localhost:4222",  # Won't actually connect
        workspace_path=str(test_workspace),
        enable_tools=True,
    )

    # Execute job manually (without NATS)
    # This will fail at NATS connection, but we can test agent execution separately
    assert job.vllm_agent is not None, "VLLMAgent should be initialized"
    assert job.enable_tools is True

    # Test agent directly
    result = asyncio.run(
        job.vllm_agent.execute_task(
            task="List files in workspace",
            context="Test project",
        )
    )

    assert result.success
    assert len(result.operations) > 0

    ray.shutdown()


@pytest.mark.integration
def test_agent_with_smart_context_vs_massive():
    """
    Demonstrate the innovation: Smart context vs massive context.
    
    This test shows that agents work efficiently with small, focused context.
    """
    import asyncio
    import tempfile
    from pathlib import Path

    from core.agents import VLLMAgent

    with tempfile.TemporaryDirectory() as tmpdir:
        workspace = Path(tmpdir)
        (workspace / "src").mkdir()

        # Create a realistic project structure (50+ files)
        for i in range(50):
            (workspace / "src" / f"module_{i}.py").write_text(f"# Module {i}\n")

        # Git init
        import subprocess

        subprocess.run(["git", "init"], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.name", "Test"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(
            ["git", "config", "user.email", "test@local"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )
        subprocess.run(["git", "add", "."], cwd=workspace, capture_output=True, check=True)
        subprocess.run(
            ["git", "commit", "-m", "init"],
            cwd=workspace,
            capture_output=True,
            check=True,
        )

        # Scenario 1: Agent with SMART context (our approach)
        smart_context = """
Task: Modify module_25.py
Relevant files: src/module_25.py, src/module_24.py (depends on 25)
"""

        agent = VLLMAgent(
            agent_id="smart-agent",
            role="DEV",
            workspace_path=workspace,
            enable_tools=True,
        )

        result_smart = asyncio.run(
            agent.execute_task(
                task="Add function to src/module_25.py",
                context=smart_context,  # Small, focused
            )
        )

        # Verify: Agent reads only relevant files
        assert result_smart.success
        file_ops = [op for op in result_smart.operations if op["tool"] == "files"]
        assert len(file_ops) <= 3, f"Should read <=3 files, read {len(file_ops)}"

        # Scenario 2: Other systems would need to include all 50 files in context
        # (Not testing this, just documenting the difference)

        # Our innovation: Agent + smart context + focused tools = efficient ✅

