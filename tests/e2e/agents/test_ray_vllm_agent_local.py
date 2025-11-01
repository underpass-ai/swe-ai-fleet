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

    from core.agents_and_tools.agents.domain.entities.core.execution_constraints import (
        ExecutionConstraints,
    )
    from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
        AgentInitializationConfig,
    )
    from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import (
        VLLMAgentFactory,
    )

    # Create agent config following DDD/Hexagonal architecture
    config = AgentInitializationConfig(
        agent_id="test-agent-001",
        role="DEV",
        workspace_path=test_workspace,
        vllm_url="http://localhost:8000",  # Default for testing
        enable_tools=True,
    )

    # Use factory to create agent with all dependencies injected
    agent = VLLMAgentFactory.create(config)

    # Create execution constraints
    constraints = ExecutionConstraints(
        max_operations=20,
        abort_on_error=False,  # Don't abort if pytest fails
        iterative=False,
    )

    # Execute task
    result = asyncio.run(
        agent.execute_task(
            task="Add hello_world() function to src/utils.py",
            context="Python 3.13 project",
            constraints=constraints,
        )
    )

    # Verify (main goal: function added)
    all_operations = result.operations.get_all()
    assert len(all_operations) > 0

    # Check function was added (key outcome)
    utils_content = (test_workspace / "src" / "utils.py").read_text()
    assert "hello_world" in utils_content

    # File operations should succeed (Operations collection entity)
    file_ops = result.operations.get_by_tool("files")
    successful_file_ops = [op for op in file_ops if op.success]
    assert len(successful_file_ops) > 0, "At least some file operations should succeed"


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

    # This test needs to be refactored - VLLMAgentJobBase no longer exists
    # The new architecture uses VLLMAgentFactory + RayAgentExecutor
    pytest.skip(
        "VLLMAgentJobBase removed - needs refactoring to use RayAgentExecutor or VLLMAgentFactory"
    )


@pytest.mark.integration
def test_agent_with_smart_context_vs_massive():
    """
    Demonstrate the innovation: Smart context vs massive context.

    This test shows that agents work efficiently with small, focused context.
    """
    import asyncio
    import tempfile
    from pathlib import Path

    from core.agents_and_tools.agents.domain.entities.core.execution_constraints import (
        ExecutionConstraints,
    )
    from core.agents_and_tools.agents.infrastructure.dtos.agent_initialization_config import (
        AgentInitializationConfig,
    )
    from core.agents_and_tools.agents.infrastructure.factories.vllm_agent_factory import (
        VLLMAgentFactory,
    )

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

        # Create agent config
        config = AgentInitializationConfig(
            agent_id="smart-agent",
            role="DEV",
            workspace_path=workspace,
            vllm_url="http://localhost:8000",
            enable_tools=True,
        )

        # Use factory to create agent
        agent = VLLMAgentFactory.create(config)

        # Create constraints
        constraints = ExecutionConstraints(max_operations=20, abort_on_error=False)

        result_smart = asyncio.run(
            agent.execute_task(
                task="Add function to src/module_25.py",
                context=smart_context,  # Small, focused
                constraints=constraints,
            )
        )

        # Verify: Agent reads only relevant files
        assert result_smart.success
        # Operations is a collection entity
        file_ops = result_smart.operations.get_by_tool("files")
        assert len(file_ops) <= 3, f"Should read <=3 files, read {len(file_ops)}"

        # Scenario 2: Other systems would need to include all 50 files in context
        # (Not testing this, just documenting the difference)

        # Our innovation: Agent + smart context + focused tools = efficient ✅

